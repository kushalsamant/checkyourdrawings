import pytest
from fastapi import HTTPException

from backend.app.auth.job_access import assert_job_access
from backend.app.auth.user import AuthenticatedUser
from backend.app.models.comparison_job import ComparisonJob


def _job(
    *,
    user_email: str | None = None,
    anon_session_id: str | None = None,
) -> ComparisonJob:
    return ComparisonJob(
        status="completed",
        priority=0,
        user_email=user_email,
        anon_session_id=anon_session_id,
        platform_user_id=None,
        drawing_a_path="/tmp/a.pdf",
        drawing_b_path="/tmp/b.pdf",
        drawing_a_name="a.pdf",
        drawing_b_name="b.pdf",
    )


def _user(email: str = "owner@example.com") -> AuthenticatedUser:
    return AuthenticatedUser(
        email=email,
        name="Owner",
        google_id="google-1",
        paid=False,
        priority=False,
        tier="free",
    )


class TestAssertJobAccess:
    def test_signed_in_owner_allowed(self) -> None:
        assert_job_access(_job(user_email="owner@example.com"), _user(), None)

    def test_signed_in_wrong_user_forbidden(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            assert_job_access(_job(user_email="owner@example.com"), _user("other@example.com"), None)
        assert exc_info.value.status_code == 403

    def test_signed_in_job_requires_auth(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            assert_job_access(_job(user_email="owner@example.com"), None, "session-a")
        assert exc_info.value.status_code == 403

    def test_anonymous_owner_allowed(self) -> None:
        assert_job_access(
            _job(anon_session_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            None,
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )

    def test_anonymous_wrong_session_forbidden(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            assert_job_access(
                _job(anon_session_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
                None,
                "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            )
        assert exc_info.value.status_code == 403

    def test_legacy_job_without_owner_forbidden(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            assert_job_access(_job(), _user(), "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        assert exc_info.value.status_code == 403
