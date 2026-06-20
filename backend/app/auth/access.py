from backend.app.models.user import User
from backend.app.subscription.utils import has_active_subscription, is_paid_tier


def user_has_paid_access(user: User | None) -> bool:
    if user is None:
        return False
    return has_active_subscription(user) and is_paid_tier(user.subscription_tier)
