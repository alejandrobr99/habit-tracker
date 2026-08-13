"""Tests for document normalization and human-confirmed OCR persistence."""

import io
import time
from types import SimpleNamespace

import pytest
from google.genai import errors
from PIL import Image

from app.config import Settings
from app.models import Category, FinanceSettings, FinanceType, ResourceStatus
from app.schemas import OcrConfirmRequest, OcrProposedTransactionRead, TransactionCreate
from app.services import finance_import

EXPECTED_INPUT_TOKENS = 10
EXPECTED_OUTPUT_TOKENS = 5
PROVIDER_UNAVAILABLE_STATUS = 503


def test_normalize_image_reencodes_without_original_metadata() -> None:
    """Accepted images become a bounded JPEG payload."""
    source = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(source, format="PNG")

    normalized, mime_type = finance_import._normalize_document(source.getvalue(), "receipt.png")

    assert mime_type == "image/jpeg"
    assert normalized.startswith(b"\xff\xd8\xff")


def test_normalize_rejects_pdf_with_active_content() -> None:
    """PDF actions are rejected before any provider call."""
    with pytest.raises(finance_import.OcrDocumentError):
        finance_import._normalize_document(b"%PDF-1.7 /JavaScript", "statement.pdf")


def test_parse_response_accepts_provider_parsed_payload(session_factory) -> None:
    """Structured SDK responses are parsed without relying on response text."""
    response = SimpleNamespace(
        parsed={"transactions": []},
        text=None,
        usage_metadata=SimpleNamespace(
            prompt_token_count=EXPECTED_INPUT_TOKENS,
            candidates_token_count=EXPECTED_OUTPUT_TOKENS,
        ),
    )

    with session_factory() as db:
        rows, input_tokens, output_tokens = finance_import._parse_response(response, db, 1)

    assert rows == []
    assert input_tokens == EXPECTED_INPUT_TOKENS
    assert output_tokens == EXPECTED_OUTPUT_TOKENS


def test_provider_failure_releases_budget_reservation(session_factory, monkeypatch) -> None:
    """A temporary provider failure does not consume the internal OCR budget."""
    source = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(source, format="PNG")

    def fail_provider(*_args, **_kwargs):
        raise errors.ServerError(
            PROVIDER_UNAVAILABLE_STATUS,
            {"error": {"message": "unavailable"}},
        )

    monkeypatch.setattr(finance_import, "_call_gemini", fail_provider)
    settings = Settings(GEMINI_API_KEY="test-key", ocr_enabled=True)

    with session_factory() as db:
        with pytest.raises(finance_import.OcrUnavailableError):
            finance_import.preview_document(
                db,
                1,
                source.getvalue(),
                "receipt.png",
                settings,
            )

        budget = finance_import._get_or_create_budget(db, 1, settings.ocr_budget_microusd)
        assert budget.reserved_microusd == 0
        assert budget.spent_microusd == 0


def test_confirm_preview_is_atomic(session_factory) -> None:
    """An incompatible row prevents every proposed row from being persisted."""
    with session_factory() as db:
        db.add(FinanceSettings(user_id=1, base_currency="COP", minor_unit=2))
        category = Category(
            user_id=1,
            name="Alimentación",
            type=FinanceType.EXPENSE,
            color="#536B57",
            status=ResourceStatus.ACTIVE,
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        token = "test-import-token"
        finance_import._previews[token] = (
            time.monotonic() + 60,
            1,
            "a" * 64,
            [
                OcrProposedTransactionRead(
                    row_id="row-1",
                    type=FinanceType.EXPENSE,
                    amount_minor=100,
                    date="2026-08-12",
                    description="Compra",
                    category_id=category.id,
                    category_name=category.name,
                    confidence="high",
                ),
            ],
            1,
        )
        payload = OcrConfirmRequest(
            rows=[
                TransactionCreate(
                    type=FinanceType.EXPENSE,
                    amount_minor=100,
                    category_id=category.id,
                    date="2026-08-12",
                    description="Compra",
                ),
                TransactionCreate(
                    type=FinanceType.EXPENSE,
                    amount_minor=200,
                    category_id=9999,
                    date="2026-08-12",
                    description="Otra compra",
                ),
            ],
        )

        with pytest.raises(finance_import.FinanceConflictError):
            finance_import.confirm_preview(db, 1, token, payload)

        assert db.query(finance_import.FinanceTransaction).count() == 0
