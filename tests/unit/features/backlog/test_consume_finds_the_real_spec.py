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


def test_a_release_id_may_not_escape_the_releases_tree(tmp_path: Path) -> None:
    """`--release-id` is joined into a path; an id like `..` walked out of the tree.

    Found in the pre-push security review of this branch. `build_release_spec_path`
    joined the caller's release id straight onto `releases/`, so `--release-id ..`
    resolved to `releases/../SPEC.md` and `--release-id /etc` hijacked the root
    entirely. The file read is then parsed for a `**Consumes:**` line, so an id that
    escapes turns an unrelated document into release input.
    """
    specs = _specs(tmp_path)
    (specs / "SPEC.md").write_text("**Consumes:** planted\n", encoding="utf-8")

    for escaping in ("..", "../..", "/etc", "v0.1.0/../..", "a/b"):
        with pytest.raises(DadaiaError) as excinfo:
            build_release_spec_path(tmp_path, context="demo", release_id=escaping)
        assert "release id" in str(excinfo.value).lower(), escaping


def test_the_canonical_release_id_forms_still_resolve(tmp_path: Path) -> None:
    """The guard must not reject what `release new` and `specs release open` produce."""
    specs = _specs(tmp_path)
    for release_id in ("v0.1.0", "hotfix-auth"):
        target = specs / "releases" / release_id
        target.mkdir(parents=True)
        (target / "SPEC.md").write_text(f"{release_id}\n", encoding="utf-8")
        resolved = build_release_spec_path(tmp_path, context="demo", release_id=release_id)
        assert resolved.read_text(encoding="utf-8") == f"{release_id}\n"


def test_consume_refuses_to_silently_drop_a_previously_recorded_slug(tmp_path: Path) -> None:
    """Re-consuming a SHRUNK `**Consumes:**` line must refuse, naming what was lost.

    `backlog consume` rewrote `consumed_backlog.json` from the SPEC alone, comparing
    against nothing. Editing a slug out of the line and re-running silently produced a
    smaller ledger — so an item recorded as consumed by this release stopped being
    tracked, and nothing would ever remove it from the live backlog. The recipe's own
    R-19 step 4 exists to catch exactly this: a verification that cannot fail is not a
    verification (bug backlog-consume-shrink-not-refused).
    """
    from dadaia_workspace.features.backlog.ledger import shrunk_consumed_slugs

    previous = {"slug-a": {"anchor:a"}, "slug-b": {"anchor:b"}, "slug-c": {"anchor:c"}}

    assert shrunk_consumed_slugs(previous, ("slug-a", "slug-b", "slug-c")) == ()
    assert shrunk_consumed_slugs(previous, ("slug-a", "slug-b")) == ("slug-c",)
    assert shrunk_consumed_slugs(previous, ("slug-a",)) == ("slug-b", "slug-c")
    # Growing the set is normal maturation, never a refusal.
    assert shrunk_consumed_slugs(previous, ("slug-a", "slug-b", "slug-c", "slug-d")) == ()
    # No prior ledger — the first consume of a release has nothing to lose.
    assert shrunk_consumed_slugs({}, ("slug-a",)) == ()
