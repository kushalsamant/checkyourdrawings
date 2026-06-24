from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from backend.app.config import ANONYMOUS_ALLOWANCE_TOTAL
from backend.app.models.anonymous_allowance import AnonymousAllowance
from backend.app.services.anonymous_allowance import (
    get_successful_comparison_count,
    record_anonymous_success,
    remaining_anonymous_allowance,
)


class TestAnonymousAllowanceService:
    def test_remaining_defaults_to_total(self) -> None:
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None

        assert remaining_anonymous_allowance(db, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") == (
            ANONYMOUS_ALLOWANCE_TOTAL
        )

    def test_remaining_reflects_usage(self) -> None:
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = AnonymousAllowance(
            anon_session_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            successful_comparisons=2,
        )

        assert remaining_anonymous_allowance(db, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") == (
            ANONYMOUS_ALLOWANCE_TOTAL - 2
        )

    def test_record_anonymous_success_creates_row(self) -> None:
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None

        record_anonymous_success(db, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert isinstance(added, AnonymousAllowance)
        assert added.successful_comparisons == 1
        db.commit.assert_called_once()

    def test_record_anonymous_success_increments_existing(self) -> None:
        db = MagicMock(spec=Session)
        row = AnonymousAllowance(
            anon_session_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            successful_comparisons=4,
        )
        db.query.return_value.filter.return_value.first.return_value = row

        record_anonymous_success(db, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

        assert row.successful_comparisons == 5
        assert get_successful_comparison_count(db, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") == 5
