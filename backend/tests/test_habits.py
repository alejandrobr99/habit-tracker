"""API and service tests for habits."""

from datetime import UTC, date, datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient

from app.models import HabitFrequency
from app.services.habits import calculate_streak

DAYS_PER_WEEK = 7


def create_habit(
    client: TestClient,
    *,
    name: str = "Read",
    frequency: str = "daily",
    color: str = "#3366FF",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/habits",
        json={
            "name": name,
            "description": "Read with focus",
            "frequency": frequency,
            "color": color,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_health_and_cors(client: TestClient):
    health_response = client.get("/health")
    assert health_response.status_code == status.HTTP_200_OK
    assert health_response.json() == {"status": "ok"}

    cors_response = client.options(
        "/api/v1/habits",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors_response.status_code == status.HTTP_200_OK
    assert cors_response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_habit_crud_and_archiving(client: TestClient):
    created = create_habit(client)
    habit_id = created["id"]
    assert created["status"] == "active"
    assert created["created_at"].endswith("Z")
    assert created["updated_at"].endswith("Z")

    listed = client.get("/api/v1/habits")
    assert listed.status_code == status.HTTP_200_OK
    assert [habit["id"] for habit in listed.json()] == [habit_id]

    updated = client.patch(
        f"/api/v1/habits/{habit_id}",
        json={
            "name": "Read books",
            "frequency": "weekly",
            "color": "#112233",
        },
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["name"] == "Read books"
    assert updated.json()["frequency"] == "weekly"

    archived = client.delete(f"/api/v1/habits/{habit_id}")
    assert archived.status_code == status.HTTP_200_OK
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/habits").json() == []

    archived_list = client.get(
        "/api/v1/habits",
        params={"status": "archived"},
    )
    assert [habit["id"] for habit in archived_list.json()] == [habit_id]


def test_habit_validation_and_missing_habit(client: TestClient):
    invalid = client.post(
        "/api/v1/habits",
        json={
            "name": "",
            "frequency": "monthly",
            "color": "blue",
        },
    )
    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    missing = client.patch("/api/v1/habits/999", json={"name": "Missing"})
    invalid_null = client.patch("/api/v1/habits/999", json={"name": None})
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert invalid_null.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_check_in_is_idempotent_and_deletable(client: TestClient):
    habit = create_habit(client)
    habit_id = habit["id"]
    check_in_url = f"/api/v1/habits/{habit_id}/check-ins/2026-08-08"

    first = client.put(check_in_url)
    second = client.put(check_in_url)
    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert first.json()["id"] == second.json()["id"]

    deleted = client.delete(check_in_url)
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert client.delete(check_in_url).status_code == status.HTTP_404_NOT_FOUND

    client.delete(f"/api/v1/habits/{habit_id}")
    archived_check_in = client.put(
        f"/api/v1/habits/{habit_id}/check-ins/2026-08-09",
    )
    assert archived_check_in.status_code == status.HTTP_409_CONFLICT


def test_daily_and_weekly_streak_calculation():
    as_of = date(2026, 8, 8)
    expected_streak = 3
    daily_dates = {
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
    }
    assert calculate_streak(daily_dates, HabitFrequency.DAILY, as_of) == expected_streak

    weekly_dates = {
        date(2026, 7, 20),
        date(2026, 7, 29),
        date(2026, 8, 3),
    }
    assert calculate_streak(weekly_dates, HabitFrequency.WEEKLY, as_of) == expected_streak


def test_weekly_summary(client: TestClient):
    habit = create_habit(client)
    habit_id = habit["id"]
    today = datetime.now(UTC).date()
    week_start = today - timedelta(days=today.weekday())
    completed_dates = [week_start + timedelta(days=offset) for offset in range(today.weekday() + 1)]
    for completed_date in completed_dates:
        response = client.put(
            f"/api/v1/habits/{habit_id}/check-ins/{completed_date.isoformat()}",
        )
        assert response.status_code == status.HTTP_200_OK

    summary_response = client.get(
        "/api/v1/habits/weekly-summary",
        params={"week_start": week_start.isoformat()},
    )
    assert summary_response.status_code == status.HTTP_200_OK
    summary = summary_response.json()
    assert summary["week_start"] == week_start.isoformat()
    assert summary["habits"][0]["completed_count"] == len(completed_dates)
    assert summary["habits"][0]["target_count"] == DAYS_PER_WEEK
    assert summary["habits"][0]["current_streak"] == len(completed_dates)

    invalid_week = client.get(
        "/api/v1/habits/weekly-summary",
        params={"week_start": (week_start + timedelta(days=1)).isoformat()},
    )
    assert invalid_week.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
