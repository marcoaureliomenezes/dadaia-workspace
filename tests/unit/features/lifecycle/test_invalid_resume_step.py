"""Bug r4d-resume-preflight-invalid-step-traceback (Consumer R4-D, F-22 class).

A blocked preflight reports ``blocked_at_step: "preflight"``, so the operator applies
``--resume-from preflight`` — but ``preflight`` is a GATE, not a pipeline step
(``implement`` / ``review_combined`` / ``close``). The prescribed remedy is impossible,
and applying it raised a raw ``ValueError`` traceback: the same contradiction-loop class
as release-definition-retry-collides-with-immutable-tasks-payload, now with a crash.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.exceptions import DadaiaError


def test_invalid_resume_from_is_clean_dadaia_error_naming_valid_steps() -> None:
    """Every workflow that accepts --resume-from must reject an unknown step with a
    DadaiaError naming the VALID labels — never a raw ValueError traceback."""
    from dadaia_workspace.features.lifecycle.pipeline import InvalidResumeStepError

    assert issubclass(InvalidResumeStepError, DadaiaError)
    assert issubclass(InvalidResumeStepError, ValueError)  # back-compat


@pytest.mark.parametrize("bad", ["preflight", "nope"])
def test_preflight_is_not_a_resumable_step_and_says_so(bad: str) -> None:
    from dadaia_workspace.features.lifecycle.pipeline import InvalidResumeStepError

    err = InvalidResumeStepError.for_labels(bad, ("implement", "review_combined", "close"))
    msg = str(err)
    assert bad in msg
    assert "implement" in msg and "review_combined" in msg and "close" in msg
    assert isinstance(err, DadaiaError)
    if bad == "preflight":
        # The specific dead end Consumer hit: name it and point at the real remedy.
        assert "preflight" in msg.lower() and "gate" in msg.lower()
