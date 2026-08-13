"""API and service tests for habits."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Habit,
    HabitFrequency,
    HabitKind,
    HabitStatus,
    User,
    UserRole,
    UserStatus,
)
from app.services.habits import calculate_streak

DAYS_PER_WEEK = 7
THREE_MONTHS = 3
COMPLETE_PERCENTAGE = 100


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


def set_habit_created_date(
    session_factory: sessionmaker[Session],
    habit_id: int,
    created_date: date,
) -> None:
    """Set a deterministic civil creation date for heatmap tests."""
    with session_factory() as db:
        habit = db.get(Habit, habit_id)
        assert habit is not None
        habit.created_at = datetime.combine(created_date, time.min, tzinfo=UTC)
        db.commit()


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


def test_progress_heatmap_defaults_to_current_month_without_habits(client: TestClient):
    today = datetime.now(UTC).date()

    response = client.get("/api/v1/habits/progress-heatmap")

    assert response.status_code == status.HTTP_200_OK
    heatmap = response.json()
    assert heatmap["start_date"] == today.replace(day=1).isoformat()
    assert heatmap["end_date"] == today.isoformat()
    assert heatmap["months"] == 1
    assert heatmap["habits"] == []
    assert len(heatmap["days"]) == today.day
    assert all(
        day["eligible_count"] == 0 and day["completed_count"] == 0 and day["percentage"] is None
        for day in heatmap["days"]
    )


def test_progress_heatmap_three_month_range_and_two_of_three(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    today = datetime.now(UTC).date()
    first_current_month = today.replace(day=1)
    previous_month_end = first_current_month - timedelta(days=1)
    expected_start = previous_month_end.replace(day=1) - timedelta(days=1)
    expected_start = expected_start.replace(day=1)
    habits = [create_habit(client, name=f"Habit {index}") for index in range(3)]
    for habit in habits:
        set_habit_created_date(session_factory, int(habit["id"]), expected_start)
    for habit in habits[:2]:
        response = client.put(
            f"/api/v1/habits/{habit['id']}/check-ins/{today.isoformat()}",
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.get(
        "/api/v1/habits/progress-heatmap",
        params={"months": 3},
    )

    assert response.status_code == status.HTTP_200_OK
    heatmap = response.json()
    assert heatmap["start_date"] == expected_start.isoformat()
    assert heatmap["end_date"] == today.isoformat()
    assert heatmap["months"] == THREE_MONTHS
    assert heatmap["days"][-1] == {
        "date": today.isoformat(),
        "completed_count": 2,
        "eligible_count": 3,
        "percentage": 67,
    }


def test_progress_heatmap_filters_to_requested_subset(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    today = datetime.now(UTC).date()
    included = create_habit(client, name="Included")
    excluded = create_habit(client, name="Excluded")
    for habit in (included, excluded):
        set_habit_created_date(session_factory, int(habit["id"]), today.replace(day=1))
        response = client.put(
            f"/api/v1/habits/{habit['id']}/check-ins/{today.isoformat()}",
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.get(
        "/api/v1/habits/progress-heatmap",
        params={"habit_ids": included["id"]},
    )

    assert response.status_code == status.HTTP_200_OK
    heatmap = response.json()
    assert [habit["id"] for habit in heatmap["habits"]] == [included["id"]]
    assert heatmap["days"][-1]["completed_count"] == 1
    assert heatmap["days"][-1]["eligible_count"] == 1
    assert heatmap["days"][-1]["percentage"] == COMPLETE_PERCENTAGE


def test_progress_heatmap_respects_creation_date_and_weekly_check_in_date(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    today = datetime.now(UTC).date()
    start_date = today.replace(day=1)
    created_date = min(start_date + timedelta(days=1), today)
    weekly = create_habit(client, name="Weekly", frequency="weekly")
    set_habit_created_date(session_factory, int(weekly["id"]), created_date)
    if created_date > start_date:
        response = client.put(
            f"/api/v1/habits/{weekly['id']}/check-ins/{start_date.isoformat()}",
        )
        assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/api/v1/habits/{weekly['id']}/check-ins/{created_date.isoformat()}",
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/api/v1/habits/progress-heatmap")

    assert response.status_code == status.HTTP_200_OK
    days = {day["date"]: day for day in response.json()["days"]}
    if created_date > start_date:
        assert days[start_date.isoformat()] == {
            "date": start_date.isoformat(),
            "completed_count": 0,
            "eligible_count": 0,
            "percentage": None,
        }
    assert days[created_date.isoformat()]["completed_count"] == 1
    assert days[created_date.isoformat()]["percentage"] == COMPLETE_PERCENTAGE
    for day in days.values():
        if day["date"] != created_date.isoformat():
            assert day["completed_count"] == 0


def test_progress_heatmap_rejects_invalid_months(client: TestClient):
    for months in (0, 2, 4):
        response = client.get(
            "/api/v1/habits/progress-heatmap",
            params={"months": months},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_progress_heatmap_rejects_duplicate_or_excessive_filters(client: TestClient):
    habit = create_habit(client)
    habit_id = habit["id"]

    duplicate = client.get(
        "/api/v1/habits/progress-heatmap",
        params=[("habit_ids", habit_id), ("habit_ids", habit_id)],
    )
    excessive = client.get(
        "/api/v1/habits/progress-heatmap",
        params=[("habit_ids", index) for index in range(51)],
    )

    assert duplicate.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert excessive.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_progress_heatmap_hides_foreign_and_missing_habits(
    client: TestClient,
    session_factory: sessionmaker[Session],
):
    with session_factory() as db:
        other_user = User(
            username="other",
            display_name="Other",
            password_hash="not-used",
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(other_user)
        db.flush()
        foreign_habit = Habit(
            user_id=other_user.id,
            name="Private",
            description=None,
            direction=HabitKind.BUILD,
            frequency=HabitFrequency.DAILY,
            status=HabitStatus.ACTIVE,
            color="#123456",
        )
        db.add(foreign_habit)
        db.commit()
        foreign_habit_id = foreign_habit.id

    foreign = client.get(
        "/api/v1/habits/progress-heatmap",
        params={"habit_ids": foreign_habit_id},
    )
    missing = client.get(
        "/api/v1/habits/progress-heatmap",
        params={"habit_ids": 999_999},
    )

    assert foreign.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_progress_heatmap_rejects_archived_habit_filter(client: TestClient):
    habit = create_habit(client)
    habit_id = habit["id"]
    assert client.delete(f"/api/v1/habits/{habit_id}").status_code == status.HTTP_200_OK

    response = client.get(
        "/api/v1/habits/progress-heatmap",
        params={"habit_ids": habit_id},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
