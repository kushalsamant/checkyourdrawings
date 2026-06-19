from datetime import UTC, datetime, timedelta

PAID_TIERS = frozenset({"weekly", "monthly", "yearly"})

SUBSCRIPTION_DURATIONS: dict[str, timedelta] = {
    "trial": timedelta(days=7),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "yearly": timedelta(days=365),
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def calculate_expiry(
    tier: str,
    reference: datetime | None = None,
) -> datetime:
    duration = SUBSCRIPTION_DURATIONS.get(tier)
    if duration is None:
        raise ValueError(f"Unknown subscription tier: {tier}")

    ref = reference or datetime.now(UTC).replace(tzinfo=None)
    return ref + duration


def is_paid_tier(tier: str | None) -> bool:
    return tier in PAID_TIERS


def has_active_subscription(user) -> bool:
    if not user.is_active:
        return False
    if user.subscription_status != "active":
        return False
    if user.subscription_expires_at is None:
        return False
    return _as_utc(user.subscription_expires_at) > datetime.now(UTC)


def ensure_subscription_status(user, db) -> None:
    if user.subscription_status != "active":
        return
    if user.subscription_expires_at is None:
        return
    if _as_utc(user.subscription_expires_at) > datetime.now(UTC):
        return

    user.subscription_status = "inactive"
    db.add(user)
    db.commit()
