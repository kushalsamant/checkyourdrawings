from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    email: str
    name: str | None
    google_id: str | None
    platform_user_id: int | None
    paid: bool
    priority: bool
    tier: str
