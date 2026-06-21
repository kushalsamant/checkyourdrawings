from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    email: str
    name: str | None
    google_id: str | None
    paid: bool
    priority: bool
    tier: str
