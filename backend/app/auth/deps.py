from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.jwt import decode_platform_jwt, extract_email_from_payload
from backend.app.config import AUTH_REQUIRED, PLATFORM_JWT_ISSUER, PLATFORM_JWT_SECRET
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.subscription.utils import (
    calculate_expiry,
    ensure_subscription_status,
    has_active_subscription,
)

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session | None = Depends(get_db),
) -> User | None:
    if credentials is None:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to compare drawings.",
            )
        return None

    if db is None:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication database is not configured.",
            )
        return None

    if not PLATFORM_JWT_SECRET:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication token verification is not configured.",
            )
        return None

    payload = decode_platform_jwt(
        credentials.credentials,
        secret=PLATFORM_JWT_SECRET,
        issuer=PLATFORM_JWT_ISSUER or "https://auth.kvshvl.in",
        audience="kvshvl-platform",
    )
    email = extract_email_from_payload(payload)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            name=payload.get("name") if isinstance(payload.get("name"), str) else None,
            google_id=payload.get("sub") if isinstance(payload.get("sub"), str) else None,
            credits=0,
            subscription_tier="trial",
            subscription_status="active",
            subscription_expires_at=calculate_expiry("trial"),
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to provision user account.",
                ) from None

    ensure_subscription_status(user, db)
    db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


def require_active_subscription():
    def check_subscription(user: User | None = Depends(get_current_user)) -> User | None:
        if user is None or not has_active_subscription(user):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Active subscription required. Please upgrade to continue.",
            )
        return user

    return check_subscription
