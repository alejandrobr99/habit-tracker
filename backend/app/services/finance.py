"""Business logic for personal finance."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Budget,
    Category,
    FinanceSettings,
    FinanceTransaction,
    FinanceType,
    ResourceStatus,
)
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    MonthlySummaryRead,
    SummaryCategoryRead,
    TransactionCreate,
    TransactionUpdate,
)

CURRENCIES = {"COP": 2, "USD": 2, "EUR": 2}


class FinanceNotFoundError(Exception):
    """Raised when a requested finance resource does not exist."""


class FinanceConflictError(Exception):
    """Raised when a finance operation conflicts with persisted state."""


def get_settings(db: Session, user_id: int) -> FinanceSettings:
    """Return configured finance settings."""
    settings = db.scalar(
        select(FinanceSettings).where(FinanceSettings.user_id == user_id),
    )
    if settings is None:
        raise FinanceNotFoundError
    return settings


def put_settings(db: Session, user_id: int, currency: str) -> tuple[FinanceSettings, bool]:
    """Create or idempotently update base-currency settings."""
    minor_unit = CURRENCIES.get(currency)
    if minor_unit is None:
        raise ValueError
    settings = db.scalar(
        select(FinanceSettings).where(FinanceSettings.user_id == user_id),
    )
    if settings is None:
        settings = FinanceSettings(
            user_id=user_id,
            base_currency=currency,
            minor_unit=minor_unit,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings, True
    if settings.base_currency == currency:
        return settings, False
    has_transactions = (
        db.scalar(
            select(FinanceTransaction.id).where(FinanceTransaction.user_id == user_id).limit(1),
        )
        is not None
    )
    has_budgets = (
        db.scalar(
            select(Budget.id).where(Budget.user_id == user_id).limit(1),
        )
        is not None
    )
    if has_transactions or has_budgets:
        raise FinanceConflictError
    settings.base_currency = currency
    settings.minor_unit = minor_unit
    settings.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(settings)
    return settings, False


def list_categories(
    db: Session,
    user_id: int,
    category_status: ResourceStatus,
) -> list[Category]:
    """List categories in stable type and case-insensitive name order."""
    statement = (
        select(Category)
        .where(
            Category.user_id == user_id,
            Category.status == category_status,
        )
        .order_by(Category.type, func.lower(Category.name), Category.id)
    )
    return list(db.scalars(statement))


def create_category(db: Session, user_id: int, payload: CategoryCreate) -> Category:
    """Create a unique active category."""
    _ensure_unique_category(db, user_id, payload.name, payload.type)
    category = Category(user_id=user_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    user_id: int,
    category_id: int,
    payload: CategoryUpdate,
) -> Category:
    """Update a category while preserving referenced type semantics."""
    category = _get_category(db, user_id, category_id)
    values = payload.model_dump(exclude_unset=True)
    new_name = values.get("name", category.name)
    new_type = values.get("type", category.type)
    _ensure_unique_category(
        db,
        user_id,
        new_name,
        new_type,
        exclude_id=category.id,
    )
    if new_type != category.type:
        has_transaction = db.scalar(
            select(FinanceTransaction.id)
            .where(FinanceTransaction.category_id == category.id)
            .limit(1),
        )
        has_budget = db.scalar(
            select(Budget.id).where(Budget.category_id == category.id).limit(1),
        )
        if has_transaction is not None or has_budget is not None:
            raise FinanceConflictError
    for field, value in values.items():
        setattr(category, field, value)
    category.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(category)
    return category


def archive_category(db: Session, user_id: int, category_id: int) -> None:
    """Archive a category without removing its history."""
    category = _get_category(db, user_id, category_id)
    category.status = ResourceStatus.ARCHIVED
    category.updated_at = datetime.now(UTC)
    db.commit()


def list_transactions(db: Session, user_id: int, month: str) -> list[FinanceTransaction]:
    """List transactions for one civil month."""
    start, end = month_bounds(month)
    statement = (
        select(FinanceTransaction)
        .where(
            FinanceTransaction.user_id == user_id,
            FinanceTransaction.date >= start,
            FinanceTransaction.date < end,
        )
        .order_by(FinanceTransaction.date.desc(), FinanceTransaction.id.desc())
    )
    return list(db.scalars(statement))


def create_transaction(
    db: Session,
    user_id: int,
    payload: TransactionCreate,
) -> FinanceTransaction:
    """Create a transaction after validating settings and category."""
    _require_settings(db, user_id)
    _validate_category(db, user_id, payload.category_id, payload.type)
    transaction = FinanceTransaction(user_id=user_id, **payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction(
    db: Session,
    user_id: int,
    transaction_id: int,
) -> FinanceTransaction:
    """Return one transaction."""
    transaction = db.scalar(
        select(FinanceTransaction).where(
            FinanceTransaction.id == transaction_id,
            FinanceTransaction.user_id == user_id,
        ),
    )
    if transaction is None:
        raise FinanceNotFoundError
    return transaction


def update_transaction(
    db: Session,
    user_id: int,
    transaction_id: int,
    payload: TransactionUpdate,
) -> FinanceTransaction:
    """Apply a validated partial transaction update."""
    transaction = get_transaction(db, user_id, transaction_id)
    values = payload.model_dump(exclude_unset=True)
    transaction_type = values.get("type", transaction.type)
    category_id = values.get("category_id", transaction.category_id)
    _validate_category(db, user_id, category_id, transaction_type)
    for field, value in values.items():
        setattr(transaction, field, value)
    transaction.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, user_id: int, transaction_id: int) -> None:
    """Delete one transaction."""
    transaction = get_transaction(db, user_id, transaction_id)
    db.delete(transaction)
    db.commit()


def list_budgets(db: Session, user_id: int, month: str) -> list[Budget]:
    """List monthly budgets ordered by category name."""
    statement = (
        select(Budget)
        .join(Category, Category.id == Budget.category_id)
        .where(
            Budget.user_id == user_id,
            Category.user_id == user_id,
            Budget.month == month,
        )
        .order_by(func.lower(Category.name), Budget.id)
    )
    return list(db.scalars(statement))


def put_budget(
    db: Session,
    user_id: int,
    month: str,
    category_id: int,
    limit_minor: int,
) -> tuple[Budget, bool]:
    """Create or replace a monthly category budget."""
    _require_settings(db, user_id)
    _validate_category(db, user_id, category_id, FinanceType.EXPENSE)
    statement = select(Budget).where(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.category_id == category_id,
    )
    budget = db.scalar(statement)
    if budget is None:
        budget = Budget(
            user_id=user_id,
            month=month,
            category_id=category_id,
            limit_minor=limit_minor,
        )
        db.add(budget)
        try:
            db.flush()
        except IntegrityError as error:
            db.rollback()
            budget = db.scalar(statement)
            if budget is None:
                raise FinanceConflictError from error
            budget.limit_minor = limit_minor
            budget.updated_at = datetime.now(UTC)
            db.flush()
            return budget, False
        return budget, True
    budget.limit_minor = limit_minor
    budget.updated_at = datetime.now(UTC)
    db.flush()
    return budget, False


def delete_budget(
    db: Session,
    user_id: int,
    month: str,
    category_id: int,
) -> None:
    """Delete a monthly category budget."""
    budget = db.scalar(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.category_id == category_id,
        ),
    )
    if budget is None:
        raise FinanceNotFoundError
    db.delete(budget)
    db.commit()


def build_summary(db: Session, user_id: int, month: str) -> MonthlySummaryRead:
    """Derive a monthly summary from persisted transactions and budgets."""
    settings = _require_settings(db, user_id)
    transactions = list_transactions(db, user_id, month)
    budgets = list_budgets(db, user_id, month)
    category_ids = {item.category_id for item in transactions} | {
        item.category_id for item in budgets
    }
    categories = {
        category.id: category
        for category in db.scalars(
            select(Category).where(
                Category.user_id == user_id,
                Category.id.in_(category_ids),
            ),
        )
    }
    actuals: dict[int, int] = {}
    income = 0
    expense = 0
    for transaction in transactions:
        actuals[transaction.category_id] = (
            actuals.get(transaction.category_id, 0) + transaction.amount_minor
        )
        if transaction.type == FinanceType.INCOME:
            income += transaction.amount_minor
        else:
            expense += transaction.amount_minor
    limits = {budget.category_id: budget.limit_minor for budget in budgets}
    rows = []
    for category_id in category_ids:
        category = categories[category_id]
        actual = actuals.get(category_id, 0)
        limit = limits.get(category_id)
        rows.append(
            SummaryCategoryRead(
                category_id=category_id,
                category_name=category.name,
                type=category.type,
                actual_minor=actual,
                budget_minor=limit,
                remaining_minor=None if limit is None else limit - actual,
            ),
        )
    rows.sort(key=lambda item: (item.type.value, item.category_name.casefold(), item.category_id))
    budgeted = sum(limits.values())
    budget_spent = sum(actuals.get(category_id, 0) for category_id in limits)
    return MonthlySummaryRead(
        month=month,
        currency=settings.base_currency,
        income_minor=income,
        expense_minor=expense,
        balance_minor=income - expense,
        budgeted_minor=budgeted,
        budget_remaining_minor=budgeted - budget_spent,
        categories=rows,
    )


def month_bounds(month: str) -> tuple[date, date]:
    """Return inclusive start and exclusive end dates for a validated month."""
    try:
        start = date.fromisoformat(f"{month}-01")
    except ValueError as error:
        raise ValueError from error
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, next_month


def _get_category(db: Session, user_id: int, category_id: int) -> Category:
    """Return a category or raise."""
    category = db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        ),
    )
    if category is None:
        raise FinanceNotFoundError
    return category


def _validate_category(
    db: Session,
    user_id: int,
    category_id: int,
    category_type: FinanceType,
) -> Category:
    """Require an active category matching the requested type."""
    category = _get_category(db, user_id, category_id)
    if category.status != ResourceStatus.ACTIVE or category.type != category_type:
        raise FinanceConflictError
    return category


def _ensure_unique_category(
    db: Session,
    user_id: int,
    name: str,
    category_type: FinanceType,
    exclude_id: int | None = None,
) -> None:
    """Reject duplicate active category names without case sensitivity."""
    statement = select(Category.id).where(
        Category.user_id == user_id,
        func.lower(Category.name) == name.casefold(),
        Category.type == category_type,
        Category.status == ResourceStatus.ACTIVE,
    )
    if exclude_id is not None:
        statement = statement.where(Category.id != exclude_id)
    if db.scalar(statement.limit(1)) is not None:
        raise FinanceConflictError


def _require_settings(db: Session, user_id: int) -> FinanceSettings:
    """Require configured base-currency settings."""
    try:
        return get_settings(db, user_id)
    except FinanceNotFoundError as error:
        raise FinanceConflictError from error
