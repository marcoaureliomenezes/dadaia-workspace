"""A bootstrap failure must report what actually happened, not one hardcoded story.

One message covered three different outcomes and asserted the same cause for all of
them: "the running distribution could not be re-packed as a local wheel". The consumer
validator hit the offline half of F-18 with `DADAIA_BOOTSTRAP_PACKAGE` already pointing
at a local wheel and got exactly that line — while the log directly above it showed the
re-pack had *succeeded*. The real failure was dependency resolution with no index, and
the prescribed remedy was the one already applied
(bug `init-offline-bootstrap-repack-misdiagnosed-as-repack-failure`).

R-27 class: a gate must name the defect it actually found. So must a failure message.
"""

from __future__ import annotations

from dadaia_workspace.infrastructure.python_env import bootstrap_failure_message


def test_a_successful_repack_is_never_reported_as_a_repack_failure() -> None:
    text = bootstrap_failure_message(
        spec="/opt/candidate/dadaia_workspace-0.4.2-py3-none-any.whl",
        repack="dadaia_workspace-0.4.2-py3-none-any.whl",
        pip_tail="ERROR: No matching distribution found for jinja2<4.0,>=3.1",
        spec_from_operator=True,
    )

    assert "could not be re-packed" not in text, text
    assert "dadaia_workspace-0.4.2-py3-none-any.whl" in text


def test_an_absent_repack_still_says_so() -> None:
    text = bootstrap_failure_message(
        spec="dadaia-workspace==0.4.2", repack=None, pip_tail="", spec_from_operator=False
    )

    assert "could not be re-packed" in text


def test_the_remedy_already_applied_is_not_prescribed_again() -> None:
    """The operator pointed DADAIA_BOOTSTRAP_PACKAGE at a wheel; saying "point it at a
    wheel" is a dead end that reads as the tool not knowing its own state."""
    text = bootstrap_failure_message(
        spec="/opt/candidate/w.whl", repack="w.whl", pip_tail="", spec_from_operator=True
    )

    assert "DADAIA_BOOTSTRAP_PACKAGE=/path/to" not in text, text
    assert "--find-links" in text, "offline needs the dependencies reachable, name how"


def test_the_escape_hatch_is_still_named_when_it_has_not_been_used() -> None:
    text = bootstrap_failure_message(
        spec="dadaia-workspace==0.4.2", repack=None, pip_tail="", spec_from_operator=False
    )

    assert "DADAIA_BOOTSTRAP_PACKAGE" in text


def test_the_installer_output_is_carried_verbatim() -> None:
    text = bootstrap_failure_message(
        spec="s",
        repack=None,
        pip_tail="ERROR: No matching distribution found for rich",
        spec_from_operator=False,
    )

    assert "No matching distribution found for rich" in text
