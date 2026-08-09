"""HTTP routes for private gamification."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResourceStatus
from app.schemas import (
    BadgeRead,
    FinanceWeeklyReviewRead,
    ProgressRead,
    RedemptionCreate,
    RedemptionRead,
    RewardCreate,
    RewardRead,
    RewardUpdate,
    StreakRecoveryCreate,
    StreakRecoveryRead,
    WeeklyChallengeCreate,
    WeeklyChallengeRead,
    XpEntryRead,
)
from app.services import gamification as service

router = APIRouter(prefix="/gamification", tags=["gamification"])
recovery_router = APIRouter(prefix="/habits", tags=["gamification"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/progress", response_model=ProgressRead)
def get_progress(db: DatabaseSession) -> ProgressRead:
    """Return calculated XP and level progress."""
    return service.progress(db)


@router.get("/xp-entries", response_model=list[XpEntryRead])
def get_xp_entries(db: DatabaseSession) -> list[XpEntryRead]:
    """Return the immutable XP ledger."""
    return [XpEntryRead.model_validate(item) for item in service.list_xp_entries(db)]


@router.get("/badges", response_model=list[BadgeRead])
def get_badges(db: DatabaseSession) -> list[BadgeRead]:
    """Return all badge catalog entries."""
    return service.list_badges(db)


@router.get("/weekly-challenges", response_model=WeeklyChallengeRead)
def get_weekly_challenge(week_start: date, db: DatabaseSession) -> WeeklyChallengeRead:
    """Return a weekly challenge."""
    try:
        return service.get_weekly_challenge(db, week_start)
    except service.GamificationNotFoundError as error:
        raise _not_found("Weekly challenge not found") from error


@router.post(
    "/weekly-challenges",
    response_model=WeeklyChallengeRead,
    status_code=status.HTTP_201_CREATED,
)
def post_weekly_challenge(
    payload: WeeklyChallengeCreate,
    db: DatabaseSession,
) -> WeeklyChallengeRead:
    """Create one weekly challenge."""
    try:
        return service.create_weekly_challenge(db, payload)
    except service.GamificationNotFoundError as error:
        raise _not_found("Habit not found") from error
    except service.GamificationConflictError as error:
        raise _conflict("Challenge week already exists or habit is archived") from error
    except service.GamificationValidationError as error:
        raise _validation("week_start must be a Monday") from error


@router.delete("/weekly-challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weekly_challenge(challenge_id: int, db: DatabaseSession) -> Response:
    """Delete an active weekly challenge."""
    try:
        service.delete_weekly_challenge(db, challenge_id)
    except service.GamificationNotFoundError as error:
        raise _not_found("Weekly challenge not found") from error
    except service.GamificationConflictError as error:
        raise _conflict("Only active challenges can be deleted") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rewards", response_model=list[RewardRead])
def get_rewards(
    db: DatabaseSession,
    reward_status: Annotated[ResourceStatus, Query(alias="status")] = ResourceStatus.ACTIVE,
) -> list[RewardRead]:
    """List personal rewards."""
    return [RewardRead.model_validate(item) for item in service.list_rewards(db, reward_status)]


@router.post("/rewards", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
def post_reward(payload: RewardCreate, db: DatabaseSession) -> RewardRead:
    """Create a personal reward."""
    return RewardRead.model_validate(service.create_reward(db, payload))


@router.patch("/rewards/{reward_id}", response_model=RewardRead)
def patch_reward(reward_id: int, payload: RewardUpdate, db: DatabaseSession) -> RewardRead:
    """Update a personal reward."""
    try:
        reward = service.update_reward(db, reward_id, payload)
    except service.GamificationNotFoundError as error:
        raise _not_found("Reward not found") from error
    return RewardRead.model_validate(reward)


@router.delete("/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reward(reward_id: int, db: DatabaseSession) -> Response:
    """Archive a personal reward."""
    try:
        service.archive_reward(db, reward_id)
    except service.GamificationNotFoundError as error:
        raise _not_found("Reward not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reward-redemptions", response_model=RedemptionRead)
def post_redemption(
    payload: RedemptionCreate,
    response: Response,
    db: DatabaseSession,
) -> RedemptionRead:
    """Redeem a reward with an idempotency key."""
    try:
        redemption, created = service.redeem_reward(
            db,
            payload.reward_id,
            str(payload.idempotency_key),
        )
    except service.GamificationNotFoundError as error:
        raise _not_found("Reward not found") from error
    except service.GamificationConflictError as error:
        raise _conflict("Reward is unavailable or available XP is insufficient") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return RedemptionRead.model_validate(redemption)


@router.get("/reward-redemptions", response_model=list[RedemptionRead])
def get_redemptions(db: DatabaseSession) -> list[RedemptionRead]:
    """List reward redemptions."""
    return [RedemptionRead.model_validate(item) for item in service.list_redemptions(db)]


@recovery_router.post(
    "/{habit_id}/streak-recoveries",
    response_model=StreakRecoveryRead,
    status_code=status.HTTP_201_CREATED,
)
def post_streak_recovery(
    habit_id: int,
    payload: StreakRecoveryCreate,
    db: DatabaseSession,
) -> StreakRecoveryRead:
    """Recover an eligible missing daily streak date."""
    try:
        recovery = service.create_recovery(
            db,
            habit_id,
            payload.recovered_date,
            today=datetime.now(UTC).date(),
        )
    except service.GamificationNotFoundError as error:
        raise _not_found("Habit not found") from error
    except service.GamificationConflictError as error:
        raise _conflict("Habit or monthly recovery is not eligible") from error
    except service.GamificationValidationError as error:
        raise _validation("Recovered date is not eligible") from error
    return StreakRecoveryRead.model_validate(recovery)


@router.put("/finance-reviews/{week_start}", response_model=FinanceWeeklyReviewRead)
def put_finance_review(
    week_start: date,
    response: Response,
    db: DatabaseSession,
) -> FinanceWeeklyReviewRead:
    """Create a weekly finance review idempotently."""
    try:
        review, created = service.put_finance_review(
            db,
            week_start,
            today=datetime.now(UTC).date(),
        )
    except service.GamificationValidationError as error:
        raise _validation("week_start must be a non-future Monday") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return FinanceWeeklyReviewRead.model_validate(review)


def _not_found(detail: str) -> HTTPException:
    """Build a not-found response."""
    return HTTPException(status.HTTP_404_NOT_FOUND, detail)


def _conflict(detail: str) -> HTTPException:
    """Build a conflict response."""
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _validation(detail: str) -> HTTPException:
    """Build a domain-validation response."""
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)
