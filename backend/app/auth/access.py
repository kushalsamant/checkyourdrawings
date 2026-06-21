from backend.app.auth.user import AuthenticatedUser


def user_has_paid_access(user: AuthenticatedUser | None) -> bool:
    if user is None:
        return False
    return user.paid
