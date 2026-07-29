"""A resume adds to the record of what happened; it does not rewrite it.

Bug ``r23-resume-overwrites-ledger-owned-step-payload`` (validator R23 / R-11): the
prescribed ``backlog_author`` resume ran without an immutable-collision error and rewrote
its existing attempt-0 payload, changing the ledger content hash from
``51098bfa…`` to ``e94eca76…`` while the record still pointed at
``backlog_author-attempt-0.step-payload.json``.

The data plane calls itself immutable in its own docstrings, and it is — per
``(step, attempt)``. The hole is that every produce site hard-coded ``attempt=0``, so a
resumed step produced at the SAME key, the ledger ``upsert`` replaced the record, and the
earlier attempt ceased to exist. What was destroyed is exactly the evidence an operator
needs after an interruption: what the first attempt actually wrote.

An attempt is not a slot to reuse. Numbering the resumed run's produce as the NEXT attempt
keeps both, which is what "immutable" was supposed to mean, and consumers resolve the
latest attempt rather than a literal zero.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_handoff import (
    WorkflowStepLedger,
    WorkflowStepRecord,
)

pytestmark = pytest.mark.unit


def _record(step: str, attempt: int, content_hash: str) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        run_id="rid",
        producer_step=step,
        attempt=attempt,
        output_schema="generic-step-handoff-v1",
        payload_ref=f"{step}-attempt-{attempt}.step-payload.json",
        content_hash=content_hash,
        produced_at="2026-07-29T00:00:00Z",
    )


def test_next_attempt_never_lands_on_an_occupied_key() -> None:
    from dadaia_workspace.features.lifecycle.workflows._fragment_gate import next_attempt_for

    ledger = WorkflowStepLedger(records=(_record("backlog_author", 0, "51098bfa"),))
    assert next_attempt_for(ledger, "backlog_author") == 1, (
        "producing at an occupied key is what let a resume overwrite the ledger-owned "
        "payload and change its content hash in place"
    )


def test_a_step_that_never_ran_starts_at_zero() -> None:
    from dadaia_workspace.features.lifecycle.workflows._fragment_gate import next_attempt_for

    assert next_attempt_for(WorkflowStepLedger(records=()), "backlog_author") == 0


def test_the_earlier_attempt_survives_the_later_one() -> None:
    """The whole point: after a resume, BOTH attempts are readable.

    Upsert-at-attempt-0 was not a storage detail — it deleted the record of what the
    interrupted attempt wrote, which is the first thing anyone wants after an interruption.
    """
    ledger = WorkflowStepLedger(records=(_record("backlog_author", 0, "51098bfa"),))

    after = ledger.upsert(_record("backlog_author", 1, "e94eca76"))

    assert [(r.attempt, r.content_hash) for r in after.records] == [
        (0, "51098bfa"),
        (1, "e94eca76"),
    ]
    assert after.latest_attempt("backlog_author") is not None
    assert after.latest_attempt("backlog_author").attempt == 1


def test_a_consumer_resolves_the_latest_attempt_not_a_literal_zero() -> None:
    """The other half. Preserving attempt 0 is useless if consumers still read it.

    Without this, the fix above would leave every downstream step consuming the payload
    from the attempt that was interrupted — strictly worse than the overwrite it replaced.
    """
    ledger = WorkflowStepLedger(
        records=(
            _record("backlog_author", 0, "51098bfa"),
            _record("backlog_author", 1, "e94eca76"),
        )
    )
    latest = ledger.latest_attempt("backlog_author")
    assert latest is not None and latest.content_hash == "e94eca76"
