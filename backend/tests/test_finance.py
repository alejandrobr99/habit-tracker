"""API tests for personal finance."""

from io import BytesIO

from fastapi import status
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Budget
from app.services import finance as finance_service

MINOR_UNIT = 2
INCOME_AMOUNT = 500_00
EXPENSE_AMOUNT = 150_00
BUDGET_AMOUNT = 180_00
BALANCE_AMOUNT = 350_00
REMAINING_AMOUNT = 30_00
CATEGORY_COUNT = 2
FIRST_BUDGET_XP = 20


def configure_finance(client: TestClient) -> tuple[int, int]:
    """Configure currency and return income and expense category IDs."""
    created = client.put("/api/v1/finance/settings", json={"base_currency": "cop"})
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["minor_unit"] == MINOR_UNIT
    assert (
        client.put(
            "/api/v1/finance/settings",
            json={"base_currency": "COP"},
        ).status_code
        == status.HTTP_200_OK
    )
    income = client.post(
        "/api/v1/finance/categories",
        json={"name": "Salary", "type": "income", "color": "#112233"},
    ).json()
    expense = client.post(
        "/api/v1/finance/categories",
        json={"name": "Food", "type": "expense", "color": "#445566"},
    ).json()
    return income["id"], expense["id"]


def test_settings_categories_and_conflicts(client: TestClient):
    assert client.get("/api/v1/finance/settings").status_code == status.HTTP_404_NOT_FOUND
    assert (
        client.put(
            "/api/v1/finance/settings",
            json={"base_currency": "ZZZ"},
        ).status_code
        == status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    income_id, expense_id = configure_finance(client)

    duplicate = client.post(
        "/api/v1/finance/categories",
        json={"name": "food", "type": "expense", "color": "#AABBCC"},
    )
    assert duplicate.status_code == status.HTTP_409_CONFLICT
    updated = client.patch(
        f"/api/v1/finance/categories/{expense_id}",
        json={"name": "Meals"},
    )
    assert updated.json()["name"] == "Meals"
    assert (
        client.patch(
            "/api/v1/finance/categories/999",
            json={"name": "Missing"},
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    archived = client.delete(f"/api/v1/finance/categories/{income_id}")
    assert archived.status_code == status.HTTP_204_NO_CONTENT
    archived_list = client.get(
        "/api/v1/finance/categories",
        params={"status": "archived"},
    ).json()
    assert archived_list[0]["id"] == income_id
    assert (
        client.delete(
            "/api/v1/finance/categories/999",
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_transaction_budget_and_summary_flow(client: TestClient):
    income_id, expense_id = configure_finance(client)
    income = client.post(
        "/api/v1/finance/transactions",
        json={
            "type": "income",
            "amount_minor": 500_00,
            "category_id": income_id,
            "date": "2026-08-01",
            "description": "Synthetic salary",
            "note": None,
        },
    )
    expense = client.post(
        "/api/v1/finance/transactions",
        json={
            "type": "expense",
            "amount_minor": 125_00,
            "category_id": expense_id,
            "date": "2026-08-02",
            "description": "Synthetic meal",
            "note": "test data",
        },
    )
    assert income.status_code == status.HTTP_201_CREATED
    assert expense.status_code == status.HTTP_201_CREATED
    transaction_id = expense.json()["id"]
    assert (
        client.get(
            f"/api/v1/finance/transactions/{transaction_id}",
        ).status_code
        == status.HTTP_200_OK
    )
    listed = client.get(
        "/api/v1/finance/transactions",
        params={"month": "2026-08"},
    ).json()
    assert [item["id"] for item in listed] == [transaction_id, income.json()["id"]]

    updated = client.patch(
        f"/api/v1/finance/transactions/{transaction_id}",
        json={"amount_minor": 150_00, "note": None},
    )
    assert updated.json()["amount_minor"] == EXPENSE_AMOUNT
    assert (
        client.patch(
            f"/api/v1/finance/transactions/{transaction_id}",
            json={"category_id": income_id},
        ).status_code
        == status.HTTP_409_CONFLICT
    )
    assert (
        client.get(
            "/api/v1/finance/transactions/999",
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    budget_url = f"/api/v1/finance/budgets/2026-08/{expense_id}"
    budget = client.put(budget_url, json={"limit_minor": 200_00})
    assert budget.status_code == status.HTTP_201_CREATED
    progress_after_first_budget = client.get("/api/v1/gamification/progress").json()
    assert progress_after_first_budget["lifetime_xp"] == FIRST_BUDGET_XP
    awarded_badges = {
        badge["code"]
        for badge in client.get("/api/v1/gamification/badges").json()
        if badge["awarded"]
    }
    assert "budget_ready" in awarded_badges
    replaced = client.put(budget_url, json={"limit_minor": 180_00})
    assert replaced.status_code == status.HTTP_200_OK
    assert client.get("/api/v1/gamification/progress").json()["lifetime_xp"] == FIRST_BUDGET_XP
    assert (
        client.get(
            "/api/v1/finance/budgets",
            params={"month": "2026-08"},
        ).json()[0]["limit_minor"]
        == BUDGET_AMOUNT
    )

    summary = client.get(
        "/api/v1/finance/summary",
        params={"month": "2026-08"},
    ).json()
    assert summary["income_minor"] == INCOME_AMOUNT
    assert summary["expense_minor"] == EXPENSE_AMOUNT
    assert summary["balance_minor"] == BALANCE_AMOUNT
    assert summary["budget_remaining_minor"] == REMAINING_AMOUNT
    assert len(summary["categories"]) == CATEGORY_COUNT
    assert (
        client.put(
            "/api/v1/finance/settings",
            json={"base_currency": "USD"},
        ).status_code
        == status.HTTP_409_CONFLICT
    )

    assert client.delete(budget_url).status_code == status.HTTP_204_NO_CONTENT
    assert client.delete(budget_url).status_code == status.HTTP_404_NOT_FOUND
    assert (
        client.delete(
            f"/api/v1/finance/transactions/{transaction_id}",
        ).status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        client.delete(
            "/api/v1/finance/transactions/999",
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_transaction_range_and_excel_export(client: TestClient):
    """Return and export a bounded range in descending date order."""
    _, expense_id = configure_finance(client)
    for date_value, description in (
        ("2026-03-01", "March expense"),
        ("2026-08-02", "August expense"),
        ("2026-09-01", "Outside range"),
    ):
        response = client.post(
            "/api/v1/finance/transactions",
            json={
                "type": "expense",
                "amount_minor": 100_00,
                "category_id": expense_id,
                "date": date_value,
                "description": description,
                "note": "private note",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    listed = client.get(
        "/api/v1/finance/transactions",
        params={"month": "2026-08"},
    )
    assert [item["description"] for item in listed.json()] == ["August expense"]

    ranged = client.get(
        "/api/v1/finance/transactions/range",
        params={"start_month": "2026-03", "end_month": "2026-08"},
    )
    assert ranged.status_code == status.HTTP_200_OK
    assert [item["description"] for item in ranged.json()] == [
        "August expense",
        "March expense",
    ]

    exported = client.get(
        "/api/v1/finance/transactions/export",
        params={"start_month": "2026-03", "end_month": "2026-08"},
    )
    assert exported.status_code == status.HTTP_200_OK
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in exported.headers["content-type"]
    )
    workbook = load_workbook(BytesIO(exported.content), read_only=True)
    rows = list(workbook.active.values)
    assert rows[0] == ("Fecha", "Tipo", "Descripción", "Categoría", "Valor", "Moneda")
    assert rows[1][0] == "2026-08-02"
    assert "private note" not in str(rows)
    selected_export = client.get(
        "/api/v1/finance/transactions/export-selected",
        params=[("months", "2026-03"), ("months", "2026-08")],
    )
    assert selected_export.status_code == status.HTTP_200_OK


def test_finance_validation_and_missing_settings(client: TestClient):
    invalid_month = client.get(
        "/api/v1/finance/transactions",
        params={"month": "2026-13"},
    )
    assert invalid_month.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        client.get(
            "/api/v1/finance/summary",
            params={"month": "2026-08"},
        ).status_code
        == status.HTTP_409_CONFLICT
    )
    invalid_amount = client.post(
        "/api/v1/finance/transactions",
        json={
            "type": "expense",
            "amount_minor": 1.5,
            "category_id": 1,
            "date": "2026-08-01",
            "description": "Synthetic",
        },
    )
    assert invalid_amount.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_budget_put_recovers_when_a_concurrent_insert_wins(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch,
):
    _, expense_id = configure_finance(client)
    month = "2026-08"
    competing_limit = 100_00
    requested_limit = 180_00

    with session_factory() as db:
        original_flush = db.flush
        race_triggered = False

        def flush_with_competing_insert(objects=None):
            nonlocal race_triggered
            if not race_triggered:
                race_triggered = True
                with session_factory() as competitor:
                    competitor.add(
                        Budget(
                            user_id=1,
                            month=month,
                            category_id=expense_id,
                            limit_minor=competing_limit,
                        ),
                    )
                    competitor.commit()
                raise IntegrityError("INSERT finance_budgets", {}, Exception("unique"))
            return original_flush(objects)

        monkeypatch.setattr(db, "flush", flush_with_competing_insert)
        budget, created = finance_service.put_budget(
            db,
            1,
            month,
            expense_id,
            requested_limit,
        )
        db.commit()

        assert created is False
        assert budget.limit_minor == requested_limit
        assert len(finance_service.list_budgets(db, 1, month)) == 1
