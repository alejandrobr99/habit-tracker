"""API tests for private gamification."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import StreakRecovery

CHALLENGE_TOTAL_XP = 50
LEDGER_ENTRY_COUNT = 2
SEVEN_CHECK_INS_XP = 70
AVAILABLE_AFTER_REDEMPTION = 40
XP_AFTER_REVIEW = 85


def create_habit(client: TestClient, name: str = "Walk") -> int:
    """Create a daily build habit and return its ID."""
    response = client.post(
        "/api/v1/habits",
        json={
            "name": name,
            "description": None,
            "direction": "build",
            "frequency": "daily",
            "color": "#336699",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_check_in_challenge_xp_badges_and_direction_conflict(client: TestClient):
    habit_id = create_habit(client)
    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    challenge = client.post(
        "/api/v1/gamification/weekly-challenges",
        json={
            "week_start": monday.isoformat(),
            "habit_id": habit_id,
            "target_count": 1,
        },
    )
    assert challenge.status_code == status.HTTP_201_CREATED
    challenge_id = challenge.json()["id"]
    duplicate = client.post(
        "/api/v1/gamification/weekly-challenges",
        json={
            "week_start": monday.isoformat(),
            "habit_id": None,
            "target_count": 2,
        },
    )
    assert duplicate.status_code == status.HTTP_409_CONFLICT

    check_in_url = f"/api/v1/habits/{habit_id}/check-ins/{today.isoformat()}"
    first = client.put(check_in_url)
    repeated = client.put(check_in_url)
    assert first.json()["id"] == repeated.json()["id"]
    progress = client.get("/api/v1/gamification/progress").json()
    assert progress["lifetime_xp"] == CHALLENGE_TOTAL_XP
    assert progress["available_xp"] == CHALLENGE_TOTAL_XP
    assert progress["level"] == 1

    fetched = client.get(
        "/api/v1/gamification/weekly-challenges",
        params={"week_start": monday.isoformat()},
    ).json()
    assert fetched["status"] == "completed"
    assert fetched["progress_count"] == 1
    assert (
        client.delete(
            f"/api/v1/gamification/weekly-challenges/{challenge_id}",
        ).status_code
        == status.HTTP_409_CONFLICT
    )
    badges = client.get("/api/v1/gamification/badges").json()
    awarded = {item["code"] for item in badges if item["awarded"]}
    assert {"first_step", "challenge_complete"} <= awarded
    assert len(client.get("/api/v1/gamification/xp-entries").json()) == LEDGER_ENTRY_COUNT

    direction_change = client.patch(
        f"/api/v1/habits/{habit_id}",
        json={"direction": "avoid"},
    )
    assert direction_change.status_code == status.HTTP_409_CONFLICT
    client.delete(check_in_url)
    client.put(check_in_url)
    assert client.get("/api/v1/gamification/progress").json()["lifetime_xp"] == CHALLENGE_TOTAL_XP


def test_rewards_redemptions_and_finance_review(client: TestClient):
    habit_id = create_habit(client)
    today = datetime.now(UTC).date()
    for offset in range(7):
        check_date = today - timedelta(days=offset)
        client.put(f"/api/v1/habits/{habit_id}/check-ins/{check_date.isoformat()}")
    progress = client.get("/api/v1/gamification/progress").json()
    assert progress["lifetime_xp"] == SEVEN_CHECK_INS_XP

    reward = client.post(
        "/api/v1/gamification/rewards",
        json={"name": "Quiet break", "description": None, "cost_xp": 30},
    )
    assert reward.status_code == status.HTTP_201_CREATED
    reward_id = reward.json()["id"]
    updated = client.patch(
        f"/api/v1/gamification/rewards/{reward_id}",
        json={"description": "Synthetic reward"},
    )
    assert updated.status_code == status.HTTP_200_OK
    key = str(uuid4())
    redemption = client.post(
        "/api/v1/gamification/reward-redemptions",
        json={"reward_id": reward_id, "idempotency_key": key},
    )
    repeated = client.post(
        "/api/v1/gamification/reward-redemptions",
        json={"reward_id": reward_id, "idempotency_key": key},
    )
    assert redemption.status_code == status.HTTP_201_CREATED
    assert repeated.status_code == status.HTTP_200_OK
    assert redemption.json()["id"] == repeated.json()["id"]
    assert (
        client.get("/api/v1/gamification/progress").json()["available_xp"]
        == AVAILABLE_AFTER_REDEMPTION
    )
    assert len(client.get("/api/v1/gamification/reward-redemptions").json()) == 1

    expensive = client.post(
        "/api/v1/gamification/rewards",
        json={"name": "Large reward", "cost_xp": 10_000},
    ).json()
    insufficient = client.post(
        "/api/v1/gamification/reward-redemptions",
        json={"reward_id": expensive["id"], "idempotency_key": str(uuid4())},
    )
    assert insufficient.status_code == status.HTTP_409_CONFLICT
    assert (
        client.delete(
            f"/api/v1/gamification/rewards/{reward_id}",
        ).status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        client.get(
            "/api/v1/gamification/rewards",
            params={"status": "archived"},
        ).json()[0]["id"]
        == reward_id
    )

    monday = today - timedelta(days=today.weekday())
    review_url = f"/api/v1/gamification/finance-reviews/{monday.isoformat()}"
    assert client.put(review_url).status_code == status.HTTP_201_CREATED
    assert client.put(review_url).status_code == status.HTTP_200_OK
    assert client.get("/api/v1/gamification/progress").json()["lifetime_xp"] == XP_AFTER_REVIEW


def test_streak_recovery_and_challenge_validation(client: TestClient):
    habit_id = create_habit(client, "Recover")
    today = datetime.now(UTC).date()
    recovered_date = today - timedelta(days=1)
    response = client.post(
        f"/api/v1/habits/{habit_id}/streak-recoveries",
        json={"recovered_date": recovered_date.isoformat()},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert (
        client.post(
            f"/api/v1/habits/{habit_id}/streak-recoveries",
            json={"recovered_date": (today - timedelta(days=2)).isoformat()},
        ).status_code
        == status.HTTP_409_CONFLICT
    )
    assert client.get("/api/v1/gamification/progress").json()["lifetime_xp"] == 0

    monday = today - timedelta(days=today.weekday())
    summary = client.get(
        "/api/v1/habits/weekly-summary",
        params={"week_start": monday.isoformat()},
    ).json()
    assert summary["habits"][0]["current_streak"] == 1
    invalid = client.post(
        "/api/v1/gamification/weekly-challenges",
        json={
            "week_start": (monday + timedelta(days=1)).isoformat(),
            "habit_id": habit_id,
            "target_count": 1,
        },
    )
    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    missing = client.get(
        "/api/v1/gamification/weekly-challenges",
        params={"week_start": (monday + timedelta(weeks=5)).isoformat()},
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_database_rejects_two_recoveries_for_the_same_habit_month(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    habit_id = create_habit(client, "Monthly recovery")
    with session_factory() as db:
        db.add(
            StreakRecovery(
                habit_id=habit_id,
                recovered_date=datetime(2026, 8, 1, tzinfo=UTC).date(),
                recovery_month="2026-08",
            ),
        )
        db.commit()

    with session_factory() as db:
        db.add(
            StreakRecovery(
                habit_id=habit_id,
                recovered_date=datetime(2026, 8, 2, tzinfo=UTC).date(),
                recovery_month="2026-08",
            ),
        )
        with pytest.raises(IntegrityError):
            db.commit()
