import pytest

from benchwork.athanor import AthanorError
from benchwork.execution_contracts import derive_execution_retry_eligible_due_at_v1


def _due_at(**overrides: object) -> str:
    arguments: dict[str, object] = {
        "terminal_recorded_at": "2026-08-06T00:00:00Z",
        "backoff_kind": "NONE",
        "backoff_base_seconds": 0,
        "backoff_cap_seconds": 0,
        "backoff_ordinal": 1,
    }
    arguments.update(overrides)
    return derive_execution_retry_eligible_due_at_v1(**arguments)  # type: ignore[arg-type]


def test_retry_due_at_uses_rfc0012_none_fixed_and_bounded_exponential_backoff() -> None:
    assert _due_at() == "2026-08-06T00:00:00Z"
    assert _due_at(
        backoff_kind="FIXED", backoff_base_seconds=7, backoff_cap_seconds=99
    ) == "2026-08-06T00:00:07Z"
    assert _due_at(
        backoff_kind="EXPONENTIAL", backoff_base_seconds=3, backoff_cap_seconds=20,
        backoff_ordinal=3,
    ) == "2026-08-06T00:00:12Z"
    assert _due_at(
        backoff_kind="EXPONENTIAL", backoff_base_seconds=3, backoff_cap_seconds=20,
        backoff_ordinal=5,
    ) == "2026-08-06T00:00:20Z"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"backoff_kind": "UNKNOWN"}, "backoff kind"),
        ({"backoff_kind": "NONE", "backoff_base_seconds": 1}, "NONE backoff"),
        ({"backoff_kind": "FIXED", "backoff_base_seconds": 0, "backoff_cap_seconds": 1}, "FIXED backoff"),
        ({"backoff_ordinal": 0}, "ordinal"),
        ({"backoff_ordinal": True}, "ordinal"),
        ({"terminal_recorded_at": "2026-08-06T00:00:00+00:00"}, "canonical timestamp"),
    ],
)
def test_retry_due_at_fails_closed_for_invalid_inputs(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(AthanorError, match=message):
        _due_at(**overrides)


def test_retry_due_at_rejects_unrepresentable_utc_result() -> None:
    with pytest.raises(AthanorError, match="unrepresentable"):
        _due_at(
            terminal_recorded_at="9999-12-31T23:59:59Z",
            backoff_kind="FIXED",
            backoff_base_seconds=1,
            backoff_cap_seconds=1,
        )
