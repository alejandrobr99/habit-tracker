"""HTTP routes for personal finance."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResourceStatus
from app.schemas import (
    BudgetRead,
    BudgetWrite,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    FinanceSettingsRead,
    FinanceSettingsWrite,
    Month,
    MonthlySummaryRead,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)
from app.services import finance as finance_service
from app.services import gamification as gamification_service

router = APIRouter(prefix="/finance", tags=["finance"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/settings", response_model=FinanceSettingsRead)
def get_settings(db: DatabaseSession) -> FinanceSettingsRead:
    """Return configured finance settings."""
    try:
        settings = finance_service.get_settings(db)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Finance settings not found") from error
    return FinanceSettingsRead.model_validate(settings)


@router.put("/settings", response_model=FinanceSettingsRead)
def put_settings(
    payload: FinanceSettingsWrite,
    response: Response,
    db: DatabaseSession,
) -> FinanceSettingsRead:
    """Create or update base-currency settings."""
    try:
        settings, created = finance_service.put_settings(db, payload.base_currency)
    except ValueError as error:
        raise HTTPException(422, "Unsupported currency code") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Base currency cannot change while financial data exists") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return FinanceSettingsRead.model_validate(settings)


@router.get("/categories", response_model=list[CategoryRead])
def get_categories(
    db: DatabaseSession,
    category_status: Annotated[ResourceStatus, Query(alias="status")] = ResourceStatus.ACTIVE,
) -> list[CategoryRead]:
    """List categories by lifecycle state."""
    return [
        CategoryRead.model_validate(item)
        for item in finance_service.list_categories(db, category_status)
    ]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def post_category(payload: CategoryCreate, db: DatabaseSession) -> CategoryRead:
    """Create a financial category."""
    try:
        category = finance_service.create_category(db, payload)
    except finance_service.FinanceConflictError as error:
        raise _conflict("An active category with this name and type already exists") from error
    return CategoryRead.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def patch_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DatabaseSession,
) -> CategoryRead:
    """Partially update a category."""
    try:
        category = finance_service.update_category(db, category_id, payload)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Category update conflicts with existing data") from error
    return CategoryRead.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DatabaseSession) -> Response:
    """Archive a category."""
    try:
        finance_service.archive_category(db, category_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/transactions", response_model=list[TransactionRead])
def get_transactions(month: Month, db: DatabaseSession) -> list[TransactionRead]:
    """List transactions for a month."""
    return [
        TransactionRead.model_validate(item)
        for item in finance_service.list_transactions(db, month)
    ]


@router.post("/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def post_transaction(payload: TransactionCreate, db: DatabaseSession) -> TransactionRead:
    """Create a transaction."""
    try:
        transaction = finance_service.create_transaction(db, payload)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Finance settings or a compatible active category is required") from error
    return TransactionRead.model_validate(transaction)


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, db: DatabaseSession) -> TransactionRead:
    """Return one transaction."""
    try:
        transaction = finance_service.get_transaction(db, transaction_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction not found") from error
    return TransactionRead.model_validate(transaction)


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def patch_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: DatabaseSession,
) -> TransactionRead:
    """Partially update a transaction."""
    try:
        transaction = finance_service.update_transaction(db, transaction_id, payload)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction or category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("A compatible active category is required") from error
    return TransactionRead.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: DatabaseSession) -> Response:
    """Delete one transaction."""
    try:
        finance_service.delete_transaction(db, transaction_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budgets", response_model=list[BudgetRead])
def get_budgets(month: Month, db: DatabaseSession) -> list[BudgetRead]:
    """List budgets for a month."""
    return [BudgetRead.model_validate(item) for item in finance_service.list_budgets(db, month)]


@router.put("/budgets/{month}/{category_id}", response_model=BudgetRead)
def put_budget(
    month: Month,
    category_id: int,
    payload: BudgetWrite,
    response: Response,
    db: DatabaseSession,
) -> BudgetRead:
    """Create or replace a monthly category budget."""
    try:
        budget, created = finance_service.put_budget(
            db,
            month,
            category_id,
            payload.limit_minor,
        )
        if created:
            gamification_service.process_first_budget(db)
        db.commit()
        db.refresh(budget)
    except finance_service.FinanceNotFoundError as error:
        db.rollback()
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        db.rollback()
        raise _conflict("Finance settings and an active expense category are required") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return BudgetRead.model_validate(budget)


@router.delete("/budgets/{month}/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(month: Month, category_id: int, db: DatabaseSession) -> Response:
    """Delete a monthly category budget."""
    try:
        finance_service.delete_budget(db, month, category_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Budget not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=MonthlySummaryRead)
def get_summary(month: Month, db: DatabaseSession) -> MonthlySummaryRead:
    """Return a derived monthly summary."""
    try:
        return finance_service.build_summary(db, month)
    except finance_service.FinanceConflictError as error:
        raise _conflict("Finance settings are required") from error


def _not_found(detail: str) -> HTTPException:
    """Build a not-found response."""
    return HTTPException(status.HTTP_404_NOT_FOUND, detail)


def _conflict(detail: str) -> HTTPException:
    """Build a conflict response."""
    return HTTPException(status.HTTP_409_CONFLICT, detail)
