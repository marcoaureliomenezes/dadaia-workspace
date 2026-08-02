"""`backlog consume` must read the SPEC that `specs release open` actually writes.

The only scaffolder that exists nests the artifacts inside a segment —
``releases/<id>/alpha-1/SPEC.md`` — while the consume path looked for a flat
``releases/<id>/SPEC.md``. It therefore never found a real release's SPEC, parsed an
empty string, and reported "nothing to consume" with exit 0: a silent no-op that is
indistinguishable from a release that genuinely consumes nothing.

Reported by the consumer-side validator as
``r6-backlog-consume-spec-path-ignores-segment-nesting`` (CRITICAL).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.container import build_release_spec_path
from dadaia_workspace.core.exceptions import DadaiaError


def _specs(tmp_path: Path, context: str = "demo") -> Path:
    specs = tmp_path / "repos" / context / "specs"
    (specs / "releases").mkdir(parents=True)
    return specs


def test_a_segment_nested_spec_is_found(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    nested = specs / "releases" / "v0.1.0" / "alpha-1"
    nested.mkdir(parents=True)
    (nested / "SPEC.md").write_text("**Consumes:** item-um\n", encoding="utf-8")

    resolved = build_release_spec_path(tmp_path, context="demo", release_id="v0.1.0")

    assert resolved == nested / "SPEC.md"


def test_a_flat_spec_still_wins_when_present(tmp_path: Path) -> None:
    """`release new` writes the flat shape; it must keep resolving to itself."""
    specs = _specs(tmp_path)
    release = specs / "releases" / "v0.1.0"
    (release / "alpha-1").mkdir(parents=True)
    (release / "alpha-1" / "SPEC.md").write_text("nested\n", encoding="utf-8")
    (release / "SPEC.md").write_text("flat\n", encoding="utf-8")

    resolved = build_release_spec_path(tmp_path, context="demo", release_id="v0.1.0")

    assert resolved.read_text(encoding="utf-8") == "flat\n"


def test_the_latest_segment_wins_over_an_earlier_one(tmp_path: Path) -> None:
    """A release matures alpha-1 -> alpha-2 -> rc-1; the current SPEC is the last one."""
    specs = _specs(tmp_path)
    release = specs / "releases" / "v0.1.0"
    for segment in ("alpha-1", "alpha-2", "rc-1"):
        (release / segment).mkdir(parents=True)
        (release / segment / "SPEC.md").write_text(f"{segment}\n", encoding="utf-8")

    resolved = build_release_spec_path(tmp_path, context="demo", release_id="v0.1.0")

    assert resolved.read_text(encoding="utf-8") == "rc-1\n"


def test_a_release_with_no_spec_anywhere_fails_loudly(tmp_path: Path) -> None:
    """Silence here was the whole defect: no SPEC must never read as 'consumes nothing'."""
    specs = _specs(tmp_path)
    (specs / "releases" / "v0.1.0" / "alpha-1").mkdir(parents=True)

    with pytest.raises(DadaiaError) as excinfo:
        build_release_spec_path(tmp_path, context="demo", release_id="v0.1.0")

    message = str(excinfo.value)
    assert "v0.1.0" in message
    assert "SPEC.md" in message


def test_an_absent_release_fails_loudly_too(tmp_path: Path) -> None:
    _specs(tmp_path)

    with pytest.raises(DadaiaError):
        build_release_spec_path(tmp_path, context="demo", release_id="v9.9.9")


def test_a_declared_slug_with_no_intents_refuses_as_a_clean_error() -> None:
    """A designed validation failure must never be reported as a product defect.

    `ConsumesBindError` inherited from `Exception`, so the CLI's fallback handler
    classified a perfectly correct refusal — "this slug binds to zero anchors" — as
    "unexpected ConsumesBindError … This is a dadaia-workspace defect, please report
    it". The tool accused itself of a bug for doing its job (F-22 / R-27 class).
    """
    from dadaia_workspace.features.backlog.consumes import ConsumesBindError

    assert issubclass(ConsumesBindError, DadaiaError)
