"""Request-boundary security controls: origin, limits, password policy, and events."""

from __future__ import annotations

import logging
import re
from collections import deque
from collections.abc import Awaitable, Callable, MutableMapping
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request

from app.config import Settings

UNKNOWN_CLIENT_IP = "unknown"
ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_LOGIN_FAILURES_PER_ACCOUNT = 5
MAX_LOGIN_FAILURES_PER_ORIGIN = 20
MAX_PASSWORD_CHANGES_PER_ACCOUNT = 5
MAX_TRACKED_KEYS = 2048
MIN_DISTINCT_PASSWORD_CHARACTERS = 5
MAX_LOG_VALUE_LENGTH = 80

TOO_LARGE_DETAIL = "La solicitud es demasiada grande."

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)
STRICT_TRANSPORT_SECURITY = "max-age=31536000; includeSubDomains"

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

_COMMON_PASSWORDS = frozenset(
    {
        "administrador",
        "contrasena1234",
        "contraseña1234",
        "iloveyou1234",
        "password1234",
        "passwordpassword",
        "qwertyuiop1234",
        "welcome123456",
        "123456789012",
        "1234567890123",
        "12345678901234",
        "abcdefghijkl",
        "letmein12345",
        "administrator",
        "planner123456",
    },
)

_UNSAFE_LOG_CHARACTERS = re.compile(r"[^\w.@:/\-]", re.UNICODE)

security_logger = logging.getLogger("planner.security")


def configure_security_logging() -> None:
    """Send security events to standard error exactly once per process."""
    logger = logging.getLogger("planner")
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_security_event(event: str, **fields: object) -> None:
    """Record a security event without credentials or domain data.

    Values are sanitized so that a hostile field cannot forge additional log lines.
    """
    details = " ".join(
        f"{key}={_sanitize_log_value(value)}" for key, value in fields.items() if value is not None
    )
    security_logger.info("event=%s %s", event, details)


def _sanitize_log_value(value: object) -> str:
    """Return a single-token representation safe to write to a log line."""
    text = str(value)[:MAX_LOG_VALUE_LENGTH]
    return _UNSAFE_LOG_CHARACTERS.sub("_", text) or "-"


def resolve_client_ip(request: Request, settings: Settings) -> str:
    """Return the client address the deployment can actually vouch for.

    Each proxy appends to ``X-Forwarded-For``, so only the last
    ``trusted_proxy_hops`` entries are verifiable; anything to their left is
    chosen by the caller and must never influence a security decision.
    """
    hops = settings.trusted_proxy_hops
    if hops > 0:
        forwarded = request.headers.get("x-forwarded-for")
        entries = [entry.strip() for entry in (forwarded or "").split(",") if entry.strip()]
        if entries:
            return entries[max(0, len(entries) - hops)]
    client = request.client
    return client.host if client else UNKNOWN_CLIENT_IP


class AttemptLimiter:
    """Bounded in-process failure ledger for the single deployed replica."""

    def __init__(
        self,
        max_failures: int,
        window: timedelta = ATTEMPT_WINDOW,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        """Create an empty ledger with the given budget and capacity."""
        self._max_failures = max_failures
        self._window = window
        self._max_keys = max_keys
        self._failures: dict[str, deque[datetime]] = {}

    def is_blocked(self, key: str, now: datetime) -> bool:
        """Return whether the budget for a key is exhausted.

        Reading a budget never allocates an entry, so probing cannot grow the ledger.
        """
        failures = self._failures.get(key)
        if failures is None:
            return False
        self._drop_expired(failures, now)
        return len(failures) >= self._max_failures

    def record_failure(self, key: str, now: datetime) -> None:
        """Charge one failure to a key."""
        failures = self._failures.get(key)
        if failures is None:
            self._evict(now)
            failures = deque(maxlen=self._max_failures)
            self._failures[key] = failures
        self._drop_expired(failures, now)
        failures.append(now)

    def clear(self, key: str) -> None:
        """Release the budget of a key after a legitimate success."""
        self._failures.pop(key, None)

    def reset(self) -> None:
        """Forget every tracked key."""
        self._failures.clear()

    @property
    def tracked_keys(self) -> int:
        """Return how many keys the ledger currently holds."""
        return len(self._failures)

    def _drop_expired(self, failures: deque[datetime], now: datetime) -> None:
        """Remove failures older than the window."""
        cutoff = now - self._window
        while failures and failures[0] <= cutoff:
            failures.popleft()

    def _evict(self, now: datetime) -> None:
        """Keep the ledger within capacity before adding a new key."""
        if len(self._failures) < self._max_keys:
            return
        cutoff = now - self._window
        expired = [
            key
            for key, failures in self._failures.items()
            if not failures or failures[-1] <= cutoff
        ]
        for key in expired:
            del self._failures[key]
        while len(self._failures) >= self._max_keys:
            oldest = min(self._failures, key=lambda key: self._failures[key][-1])
            del self._failures[oldest]


login_account_limiter = AttemptLimiter(MAX_LOGIN_FAILURES_PER_ACCOUNT)
login_origin_limiter = AttemptLimiter(MAX_LOGIN_FAILURES_PER_ORIGIN)
password_change_limiter = AttemptLimiter(MAX_PASSWORD_CHANGES_PER_ACCOUNT)


def password_policy_error(password: str, username: str) -> str | None:
    """Return why a password is unacceptable, or ``None`` when it is fine.

    Length is validated by the request schema. This adds only the checks that
    stop a password from being trivially guessable, without imposing composition
    rules that push people toward predictable substitutions.
    """
    normalized = password.casefold()
    account = username.casefold().strip()
    if account and (account in normalized or normalized in account):
        return "La contraseña no puede contener tu nombre de usuario."
    if normalized in _COMMON_PASSWORDS:
        return "Esa contraseña es demasiado común. Elige una frase personal."
    if len(set(normalized)) < MIN_DISTINCT_PASSWORD_CHARACTERS:
        return "La contraseña necesita más variedad de caracteres."
    return None


AsgiReceive = Callable[[], Awaitable[MutableMapping[str, Any]]]
AsgiSend = Callable[[MutableMapping[str, Any]], Awaitable[None]]


class _BodyBudget:
    """Counts the bytes of one request body and cuts it off at the maximum."""

    def __init__(self, receive: AsgiReceive, send: AsgiSend, max_bytes: int) -> None:
        """Wrap the ASGI channels of a single request."""
        self._receive = receive
        self._send = send
        self._max_bytes = max_bytes
        self._received = 0
        self.exceeded = False

    async def receive(self) -> MutableMapping[str, Any]:
        """Return the next body chunk, or a disconnect once the budget is spent."""
        message = await self._receive()
        if message["type"] != "http.request":
            return message
        self._received += len(message.get("body", b""))
        if self._received > self._max_bytes:
            self.exceeded = True
            return {"type": "http.disconnect"}
        return message

    async def send(self, message: MutableMapping[str, Any]) -> None:
        """Forward a response message unless the body was already rejected."""
        if self.exceeded:
            return
        await self._send(message)


class RequestSizeLimitMiddleware:
    """Reject oversized bodies before the application reads them.

    A declared ``Content-Length`` is checked first, and the received bytes are
    counted as they arrive so a caller cannot understate or omit the length.
    """

    def __init__(
        self,
        app: Any,  # noqa: ANN401 - ASGI application
        max_bytes: int,
        ocr_max_bytes: int = 0,
    ) -> None:  # noqa: ANN401 - ASGI application
        """Wrap an ASGI application with a body size budget."""
        self.app = app
        self.max_bytes = max_bytes
        self.ocr_max_bytes = ocr_max_bytes

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: AsgiReceive,
        send: AsgiSend,
    ) -> None:
        """Pass the request through unless its body exceeds the maximum."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        max_bytes = self._max_bytes_for_path(scope.get("path", ""))
        if self._declares_oversized_body(scope, max_bytes):
            await self._reject(scope, send, max_bytes)
            return
        budget = _BodyBudget(receive, send, max_bytes)
        try:
            await self.app(scope, budget.receive, budget.send)
        except Exception:
            # A cut-off body surfaces as a disconnect inside the application; the
            # 413 below is the real answer, so only unrelated failures propagate.
            if not budget.exceeded:
                raise
        if budget.exceeded:
            await self._reject(scope, send, max_bytes)

    def _max_bytes_for_path(self, path: str) -> int:
        """Return the request budget for the normal API or OCR upload."""
        if self.ocr_max_bytes and path.endswith("/finance/imports/preview"):
            return self.ocr_max_bytes
        return self.max_bytes

    def _declares_oversized_body(
        self,
        scope: MutableMapping[str, Any],
        max_bytes: int,
    ) -> bool:
        """Return whether the declared content length exceeds the maximum."""
        for name, value in scope.get("headers", []):
            if name != b"content-length":
                continue
            try:
                return int(value) > max_bytes
            except ValueError:
                return True
        return False

    async def _reject(
        self,
        scope: MutableMapping[str, Any],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
        max_bytes: int,
    ) -> None:
        """Answer with a generic 413 and record the event."""
        log_security_event(
            "request_too_large",
            method=scope.get("method"),
            path=scope.get("path"),
            limit=max_bytes,
        )
        body = f'{{"detail":"{TOO_LARGE_DETAIL}"}}'.encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            },
        )
        await send({"type": "http.response.body", "body": body})
