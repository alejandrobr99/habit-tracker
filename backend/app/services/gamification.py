"""Business logic for private gamification."""

from datetime import UTC, date, datetime, timedelta
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    BadgeAward,
    BadgeCode,
    FinanceWeeklyReview,
    Habit,
    HabitCheckIn,
    HabitFrequency,
    HabitStatus,
    ResourceStatus,
    Reward,
    RewardRedemption,
    StreakRecovery,
    WeeklyChallenge,
    XpEntry,
    XpSourceType,
)
from app.schemas import (
    BadgeRead,
    ProgressRead,
    RewardCreate,
    RewardUpdate,
    WeeklyChallengeCreate,
    WeeklyChallengeRead,
)

BADGES = {
    BadgeCode.FIRST_STEP: ("Primer paso", "Primer check-in de hábito."),
    BadgeCode.STEADY_SEVEN: ("Siete avances", "Siete check-ins acumulados."),
    BadgeCode.CHALLENGE_COMPLETE: ("Desafío cumplido", "Primer desafío semanal completado."),
    BadgeCode.BUDGET_READY: ("Presupuesto listo", "Primer presupuesto configurado."),
    BadgeCode.WEEKLY_REVIEWED: ("Semana revisada", "Primera revisión financiera semanal."),
    BadgeCode.REWARD_CLAIMED: ("Recompensa elegida", "Primer canje de recompensa."),
}
STEADY_CHECK_IN_COUNT = 7
_REDEMPTION_LOCK = Lock()


class GamificationNotFoundError(Exception):
    """Raised when a gamification resource does not exist."""


class GamificationConflictError(Exception):
    """Raised when a gamification state transition is not allowed."""


class GamificationValidationError(Exception):
    """Raised when a domain date is not eligible."""


def progress(db: Session) -> ProgressRead:
    """Calculate lifetime and available XP."""
    lifetime = int(
        db.scalar(
            select(func.coalesce(func.sum(XpEntry.amount), 0)).where(XpEntry.amount > 0),
        )
        or 0,
    )
    available = int(db.scalar(select(func.coalesce(func.sum(XpEntry.amount), 0))) or 0)
    level = lifetime // 100 + 1
    return ProgressRead(
        lifetime_xp=lifetime,
        available_xp=max(0, available),
        level=level,
        level_start_xp=(level - 1) * 100,
        next_level_xp=level * 100,
    )


def list_xp_entries(db: Session) -> list[XpEntry]:
    """List the XP ledger newest first."""
    return list(db.scalars(select(XpEntry).order_by(XpEntry.created_at.desc(), XpEntry.id.desc())))


def list_badges(db: Session) -> list[BadgeRead]:
    """Return the complete badge catalog with award state."""
    awards = {award.badge_code: award for award in db.scalars(select(BadgeAward))}
    return [
        BadgeRead(
            code=code,
            name=name,
            description=description,
            awarded=code in awards,
            awarded_at=awards[code].awarded_at if code in awards else None,
        )
        for code, (name, description) in BADGES.items()
    ]


def process_check_in(db: Session, check_in: HabitCheckIn) -> None:
    """Recognize an ordinary check-in and evaluate its weekly challenge."""
    _add_xp(
        db,
        10,
        XpSourceType.HABIT_CHECK_IN,
        f"{check_in.habit_id}:{check_in.check_in_date.isoformat()}",
        check_in.check_in_date,
    )
    _award_badge(db, BadgeCode.FIRST_STEP)
    count = int(db.scalar(select(func.count(HabitCheckIn.id))) or 0)
    if count >= STEADY_CHECK_IN_COUNT:
        _award_badge(db, BadgeCode.STEADY_SEVEN)
    week_start = check_in.check_in_date - timedelta(days=check_in.check_in_date.weekday())
    challenge = db.scalar(
        select(WeeklyChallenge).where(WeeklyChallenge.week_start == week_start),
    )
    if challenge is None or challenge.completed_at is not None:
        return
    if challenge.habit_id is not None and challenge.habit_id != check_in.habit_id:
        return
    week_end = week_start + timedelta(days=7)
    statement = select(func.count(HabitCheckIn.id)).where(
        HabitCheckIn.check_in_date >= week_start,
        HabitCheckIn.check_in_date < week_end,
    )
    if challenge.habit_id is not None:
        statement = statement.where(HabitCheckIn.habit_id == challenge.habit_id)
    check_in_count = int(db.scalar(statement) or 0)
    if check_in_count >= challenge.target_count:
        challenge.completed_at = datetime.now(UTC)
        db.flush()
        _add_xp(
            db,
            40,
            XpSourceType.WEEKLY_CHALLENGE,
            str(challenge.id),
            check_in.check_in_date,
        )
        _award_badge(db, BadgeCode.CHALLENGE_COMPLETE)


def process_first_budget(db: Session) -> None:
    """Recognize the first budget setup idempotently."""
    _add_xp(
        db,
        20,
        XpSourceType.FINANCE_BUDGET_SETUP,
        "initial",
        datetime.now(UTC).date(),
    )
    _award_badge(db, BadgeCode.BUDGET_READY)


def get_weekly_challenge(db: Session, week_start: date) -> WeeklyChallengeRead:
    """Return one weekly challenge and projected state."""
    challenge = db.scalar(
        select(WeeklyChallenge).where(WeeklyChallenge.week_start == week_start),
    )
    if challenge is None:
        raise GamificationNotFoundError
    return _challenge_read(db, challenge)


def create_weekly_challenge(
    db: Session,
    payload: WeeklyChallengeCreate,
) -> WeeklyChallengeRead:
    """Create one challenge for a Monday-based week."""
    if payload.week_start.weekday() != 0:
        raise GamificationValidationError
    if db.scalar(
        select(WeeklyChallenge.id).where(WeeklyChallenge.week_start == payload.week_start),
    ):
        raise GamificationConflictError
    if payload.habit_id is not None:
        habit = db.get(Habit, payload.habit_id)
        if habit is None:
            raise GamificationNotFoundError
        if habit.status != HabitStatus.ACTIVE:
            raise GamificationConflictError
    challenge = WeeklyChallenge(**payload.model_dump())
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return _challenge_read(db, challenge)


def delete_weekly_challenge(db: Session, challenge_id: int) -> None:
    """Delete a challenge only while its projected state is active."""
    challenge = db.get(WeeklyChallenge, challenge_id)
    if challenge is None:
        raise GamificationNotFoundError
    if _challenge_status(challenge) != "active":
        raise GamificationConflictError
    db.delete(challenge)
    db.commit()


def list_rewards(db: Session, reward_status: ResourceStatus) -> list[Reward]:
    """List rewards by lifecycle state."""
    return list(
        db.scalars(
            select(Reward)
            .where(Reward.status == reward_status)
            .order_by(Reward.created_at, Reward.id),
        ),
    )


def create_reward(db: Session, payload: RewardCreate) -> Reward:
    """Create a personal reward."""
    reward = Reward(**payload.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


def update_reward(db: Session, reward_id: int, payload: RewardUpdate) -> Reward:
    """Update a personal reward."""
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise GamificationNotFoundError
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reward, field, value)
    reward.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(reward)
    return reward


def archive_reward(db: Session, reward_id: int) -> None:
    """Archive a reward."""
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise GamificationNotFoundError
    reward.status = ResourceStatus.ARCHIVED
    reward.updated_at = datetime.now(UTC)
    db.commit()


def redeem_reward(
    db: Session,
    reward_id: int,
    idempotency_key: str,
) -> tuple[RewardRedemption, bool]:
    """Redeem a reward and debit XP in one transaction."""
    with _REDEMPTION_LOCK:
        return _redeem_reward_locked(db, reward_id, idempotency_key)


def _redeem_reward_locked(
    db: Session,
    reward_id: int,
    idempotency_key: str,
) -> tuple[RewardRedemption, bool]:
    """Serialize the available-XP check and atomic redemption write."""
    existing = db.scalar(
        select(RewardRedemption).where(
            RewardRedemption.idempotency_key == idempotency_key,
        ),
    )
    if existing is not None:
        return existing, False
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise GamificationNotFoundError
    if reward.status != ResourceStatus.ACTIVE or progress(db).available_xp < reward.cost_xp:
        raise GamificationConflictError
    redemption = RewardRedemption(
        reward_id=reward.id,
        cost_xp=reward.cost_xp,
        idempotency_key=idempotency_key,
    )
    db.add(redemption)
    db.flush()
    _add_xp(
        db,
        -reward.cost_xp,
        XpSourceType.REWARD_REDEMPTION,
        str(redemption.id),
        datetime.now(UTC).date(),
    )
    _award_badge(db, BadgeCode.REWARD_CLAIMED)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = db.scalar(
            select(RewardRedemption).where(
                RewardRedemption.idempotency_key == idempotency_key,
            ),
        )
        if existing is None:
            raise GamificationConflictError from error
        return existing, False
    db.refresh(redemption)
    return redemption, True


def list_redemptions(db: Session) -> list[RewardRedemption]:
    """List reward redemptions newest first."""
    return list(
        db.scalars(
            select(RewardRedemption).order_by(
                RewardRedemption.redeemed_at.desc(),
                RewardRedemption.id.desc(),
            ),
        ),
    )


def create_recovery(
    db: Session,
    habit_id: int,
    recovered_date: date,
    *,
    today: date,
) -> StreakRecovery:
    """Recover an eligible missing date for a daily habit."""
    habit = db.get(Habit, habit_id)
    if habit is None:
        raise GamificationNotFoundError
    if habit.status != HabitStatus.ACTIVE or habit.frequency != HabitFrequency.DAILY:
        raise GamificationConflictError
    if recovered_date not in {today - timedelta(days=1), today - timedelta(days=2)}:
        raise GamificationValidationError
    has_check_in = db.scalar(
        select(HabitCheckIn.id).where(
            HabitCheckIn.habit_id == habit_id,
            HabitCheckIn.check_in_date == recovered_date,
        ),
    )
    if has_check_in is not None:
        raise GamificationValidationError
    existing = db.scalar(
        select(StreakRecovery).where(
            StreakRecovery.habit_id == habit_id,
            StreakRecovery.recovered_date == recovered_date,
        ),
    )
    if existing is not None:
        return existing
    month_prefix = recovered_date.strftime("%Y-%m")
    monthly = db.scalar(
        select(StreakRecovery.id).where(
            StreakRecovery.habit_id == habit_id,
            func.strftime("%Y-%m", StreakRecovery.recovered_date) == month_prefix,
        ),
    )
    if monthly is not None:
        raise GamificationConflictError
    recovery = StreakRecovery(habit_id=habit_id, recovered_date=recovered_date)
    db.add(recovery)
    db.commit()
    db.refresh(recovery)
    return recovery


def put_finance_review(
    db: Session,
    week_start: date,
    *,
    today: date,
) -> tuple[FinanceWeeklyReview, bool]:
    """Create a weekly finance review and recognition idempotently."""
    if week_start.weekday() != 0 or week_start > today:
        raise GamificationValidationError
    existing = db.scalar(
        select(FinanceWeeklyReview).where(FinanceWeeklyReview.week_start == week_start),
    )
    if existing is not None:
        return existing, False
    review = FinanceWeeklyReview(week_start=week_start)
    db.add(review)
    db.flush()
    _add_xp(
        db,
        15,
        XpSourceType.FINANCE_WEEKLY_REVIEW,
        str(review.id),
        week_start,
    )
    _award_badge(db, BadgeCode.WEEKLY_REVIEWED)
    db.commit()
    db.refresh(review)
    return review, True


def _challenge_read(db: Session, challenge: WeeklyChallenge) -> WeeklyChallengeRead:
    """Build a challenge response with derived progress and state."""
    statement = select(func.count(HabitCheckIn.id)).where(
        HabitCheckIn.check_in_date >= challenge.week_start,
        HabitCheckIn.check_in_date < challenge.week_start + timedelta(days=7),
    )
    if challenge.habit_id is not None:
        statement = statement.where(HabitCheckIn.habit_id == challenge.habit_id)
    return WeeklyChallengeRead(
        id=challenge.id,
        week_start=challenge.week_start,
        habit_id=challenge.habit_id,
        target_count=challenge.target_count,
        status=_challenge_status(challenge),
        progress_count=int(db.scalar(statement) or 0),
        completed_at=challenge.completed_at,
        created_at=challenge.created_at,
    )


def _challenge_status(challenge: WeeklyChallenge) -> str:
    """Project a challenge state without a scheduled task."""
    if challenge.completed_at is not None:
        return "completed"
    if datetime.now(UTC).date() >= challenge.week_start + timedelta(days=7):
        return "expired"
    return "active"


def _add_xp(
    db: Session,
    amount: int,
    source_type: XpSourceType,
    source_id: str,
    occurred_on: date,
) -> XpEntry:
    """Add an XP entry if its source has not been recognized."""
    existing = db.scalar(
        select(XpEntry).where(
            XpEntry.source_type == source_type,
            XpEntry.source_id == source_id,
        ),
    )
    if existing is not None:
        return existing
    entry = XpEntry(
        amount=amount,
        source_type=source_type,
        source_id=source_id,
        occurred_on=occurred_on,
    )
    db.add(entry)
    db.flush()
    return entry


def _award_badge(db: Session, badge_code: BadgeCode) -> None:
    """Award a badge once."""
    if db.scalar(select(BadgeAward.id).where(BadgeAward.badge_code == badge_code)) is None:
        db.add(BadgeAward(badge_code=badge_code))
        db.flush()
