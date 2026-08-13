"""HTTP routes for personal finance."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth import ReadyUser
from app.config import Settings, get_settings
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
    OcrBudgetRead,
    OcrConfirmRead,
    OcrConfirmRequest,
    OcrPreviewRead,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)
from app.services import finance as finance_service
from app.services import finance_import as finance_import_service
from app.services import gamification as gamification_service

router = APIRouter(prefix="/finance", tags=["finance"])
DatabaseSession = Annotated[Session, Depends(get_db)]
RuntimeSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/settings", response_model=FinanceSettingsRead)
def get_settings(db: DatabaseSession, user: ReadyUser) -> FinanceSettingsRead:
    """Return configured finance settings."""
    try:
        settings = finance_service.get_settings(db, user.id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Finance settings not found") from error
    return FinanceSettingsRead.model_validate(settings)


@router.put("/settings", response_model=FinanceSettingsRead)
def put_settings(
    payload: FinanceSettingsWrite,
    response: Response,
    db: DatabaseSession,
    user: ReadyUser,
) -> FinanceSettingsRead:
    """Create or update base-currency settings."""
    try:
        settings, created = finance_service.put_settings(
            db,
            user.id,
            payload.base_currency,
        )
    except ValueError as error:
        raise HTTPException(422, "Unsupported currency code") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Base currency cannot change while financial data exists") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return FinanceSettingsRead.model_validate(settings)


@router.get("/categories", response_model=list[CategoryRead])
def get_categories(
    db: DatabaseSession,
    user: ReadyUser,
    category_status: Annotated[ResourceStatus, Query(alias="status")] = ResourceStatus.ACTIVE,
) -> list[CategoryRead]:
    """List categories by lifecycle state."""
    return [
        CategoryRead.model_validate(item)
        for item in finance_service.list_categories(db, user.id, category_status)
    ]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def post_category(
    payload: CategoryCreate,
    db: DatabaseSession,
    user: ReadyUser,
) -> CategoryRead:
    """Create a financial category."""
    try:
        category = finance_service.create_category(db, user.id, payload)
    except finance_service.FinanceConflictError as error:
        raise _conflict("An active category with this name and type already exists") from error
    return CategoryRead.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def patch_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DatabaseSession,
    user: ReadyUser,
) -> CategoryRead:
    """Partially update a category."""
    try:
        category = finance_service.update_category(
            db,
            user.id,
            category_id,
            payload,
        )
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Category update conflicts with existing data") from error
    return CategoryRead.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: DatabaseSession,
    user: ReadyUser,
) -> Response:
    """Archive a category."""
    try:
        finance_service.archive_category(db, user.id, category_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/transactions", response_model=list[TransactionRead])
def get_transactions(
    month: Month,
    db: DatabaseSession,
    user: ReadyUser,
) -> list[TransactionRead]:
    """List transactions for a month."""
    return [
        TransactionRead.model_validate(item)
        for item in finance_service.list_transactions(db, user.id, month)
    ]


@router.post("/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def post_transaction(
    payload: TransactionCreate,
    db: DatabaseSession,
    user: ReadyUser,
) -> TransactionRead:
    """Create a transaction."""
    try:
        transaction = finance_service.create_transaction(db, user.id, payload)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("Finance settings or a compatible active category is required") from error
    return TransactionRead.model_validate(transaction)


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    db: DatabaseSession,
    user: ReadyUser,
) -> TransactionRead:
    """Return one transaction."""
    try:
        transaction = finance_service.get_transaction(db, user.id, transaction_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction not found") from error
    return TransactionRead.model_validate(transaction)


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def patch_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: DatabaseSession,
    user: ReadyUser,
) -> TransactionRead:
    """Partially update a transaction."""
    try:
        transaction = finance_service.update_transaction(
            db,
            user.id,
            transaction_id,
            payload,
        )
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction or category not found") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict("A compatible active category is required") from error
    return TransactionRead.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: DatabaseSession,
    user: ReadyUser,
) -> Response:
    """Delete one transaction."""
    try:
        finance_service.delete_transaction(db, user.id, transaction_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Transaction not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budgets", response_model=list[BudgetRead])
def get_budgets(
    month: Month,
    db: DatabaseSession,
    user: ReadyUser,
) -> list[BudgetRead]:
    """List budgets for a month."""
    return [
        BudgetRead.model_validate(item) for item in finance_service.list_budgets(db, user.id, month)
    ]


@router.put("/budgets/{month}/{category_id}", response_model=BudgetRead)
def put_budget(
    month: Month,
    category_id: int,
    payload: BudgetWrite,
    db: DatabaseSession,
    user: ReadyUser,
) -> BudgetRead | JSONResponse:
    """Create or replace a monthly category budget."""
    try:
        budget, created = finance_service.put_budget(
            db,
            user.id,
            month,
            category_id,
            payload.limit_minor,
        )
        if created:
            gamification_service.process_first_budget(db, user.id)
        db.commit()
        db.refresh(budget)
    except finance_service.FinanceNotFoundError as error:
        db.rollback()
        raise _not_found("Category not found") from error
    except finance_service.FinanceConflictError as error:
        db.rollback()
        raise _conflict("Finance settings and an active expense category are required") from error
    result = BudgetRead.model_validate(budget)
    if created:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result.model_dump(mode="json"),
        )
    return result


@router.delete("/budgets/{month}/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    month: Month,
    category_id: int,
    db: DatabaseSession,
    user: ReadyUser,
) -> Response:
    """Delete a monthly category budget."""
    try:
        finance_service.delete_budget(db, user.id, month, category_id)
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Budget not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=MonthlySummaryRead)
def get_summary(
    month: Month,
    db: DatabaseSession,
    user: ReadyUser,
) -> MonthlySummaryRead:
    """Return a derived monthly summary."""
    try:
        return finance_service.build_summary(db, user.id, month)
    except finance_service.FinanceConflictError as error:
        raise _conflict("Finance settings are required") from error


@router.post("/imports/preview", response_model=OcrPreviewRead)
async def preview_import(
    db: DatabaseSession,
    user: ReadyUser,
    settings: RuntimeSettings,
    file: Annotated[UploadFile, File()],
) -> OcrPreviewRead:
    """Analyze one financial document without persisting its content."""
    try:
        content = await file.read()
        return finance_import_service.preview_document(
            db,
            user.id,
            content,
            file.filename or "",
            settings,
        )
    except finance_import_service.OcrUnavailableError as error:
        raise HTTPException(503, "La importación OCR no está disponible.") from error
    except finance_import_service.OcrBudgetError as error:
        raise _conflict("El presupuesto o el límite de análisis no está disponible.") from error
    except finance_import_service.OcrDocumentError as error:
        raise HTTPException(
            422,
            "El documento no es válido o supera los límites permitidos.",
        ) from error
    except finance_import_service.OcrPreviewError as error:
        raise HTTPException(502, "No pudimos analizar el documento.") from error


@router.post("/imports/{import_token}/confirm", response_model=OcrConfirmRead)
def confirm_import(
    import_token: str,
    payload: OcrConfirmRequest,
    db: DatabaseSession,
    user: ReadyUser,
) -> OcrConfirmRead:
    """Persist edited OCR rows atomically after human confirmation."""
    try:
        transactions, _ = finance_import_service.confirm_preview(
            db,
            user.id,
            import_token,
            payload,
        )
    except finance_service.FinanceNotFoundError as error:
        raise _not_found("Importación no encontrada o expirada") from error
    except finance_service.FinanceConflictError as error:
        raise _conflict(
            "La importación ya fue confirmada o contiene una categoría inválida",
        ) from error
    return OcrConfirmRead(
        imported_count=len(transactions),
        transactions=[TransactionRead.model_validate(item) for item in transactions],
    )


@router.get("/imports/budget", response_model=OcrBudgetRead)
def get_import_budget(
    db: DatabaseSession,
    user: ReadyUser,
    settings: RuntimeSettings,
) -> OcrBudgetRead:
    """Return the current OCR budget without revealing document data."""
    return finance_import_service.get_budget(db, user.id, settings.ocr_budget_microusd)


def _not_found(detail: str) -> HTTPException:
    """Build a not-found response."""
    return HTTPException(status.HTTP_404_NOT_FOUND, detail)


def _conflict(detail: str) -> HTTPException:
    """Build a conflict response."""
    return HTTPException(status.HTTP_409_CONFLICT, detail)
