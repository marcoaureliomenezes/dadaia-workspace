"""Wiring test for .github/scripts/pr-verdict-check.sh (v0.4.4 FR4, T-044-07).

The security verdict that used to gate every push (pre-push hook, per-pushed-sha) is
deleted from that path (A3.4, T-044-06) and relocates to a CI PR gate keyed on the PR
head sha (FR4). A GitHub Actions checkout never sees ``.dadaia/handoff/`` — it is a
workspace-local, gitignored directory (``features/chokepoints/service.py``'s module
docstring; ``dadaia ci gc-push-verdicts`` only ever reads it from a local clone) — so
the evidence this gate reads is a COMMITTED copy of the security-reviewer's APPROVED
handoff, placed on the branch at
``specs/releases/<release-id>/verdicts/<reviewed-sha>.handoff.json`` (the same
"review artifact committed on the branch" cadence DADAIA.md §4 (Gitflow) already uses
for a qa-engineer segment close).

Because the verdict evidence file cannot be part of the very commit whose sha it
names (committing the file changes the tree, hence the sha — a real chicken-and-egg
git property, not a script quirk), "covers the PR head sha" (A4.3) is defined as: the
verdict's ``metrics.commit_sha`` is the PR head itself, OR an ancestor of it where
every path that differs between the two is itself under
``specs/releases/*/verdicts/*`` — i.e. nothing but more verdict evidence landed after
the reviewed commit. Each test below proves one branch of that rule against a real,
disposable git repository (dadaia-test-stewardship: "No real venvs built in tests" —
this is a plain git repo, not a venv, and costs a few kilobytes on tmp_path).

Extended for bug ``verdict-gate-cannot-resolve-evidence-after-release-archive`` (HIGH,
T-044-50): the gate used to resolve ``RELEASE_ID`` by reading
``specs/releases/ACTIVE.md``'s ``release:`` line — a LIFECYCLE POINTER that legitimately
reads ``none`` once a release closes, failing the release-id canon before any directory
was ever read, and leaving the evidence unreachable even when supplied explicitly
because the verdicts directory built from it never looked in
``specs/_archive/releases/<id>/verdicts/`` (where closure ``git mv``s it). The fix
deletes the ACTIVE.md read entirely and resolves evidence BY THE ARTIFACT: a glob over
every release's verdicts directory, live and archived, optionally narrowed (never
required, never an error on ``none``/unset) by ``RELEASE_ID``.

Intent: CONTRACT — v0.4.4 A4.3, A4.5 (T-044-07); HIGH bug
verdict-gate-cannot-resolve-evidence-after-release-archive (T-044-50)
Owner: software-engineer
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "pr-verdict-check.sh"
_RELEASE_ID = "v9.9.9"
_TEST_PATH = "/usr/bin:/bin"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _head(repo: Path) -> str:
    return _git("rev-parse", "HEAD", cwd=repo).stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with an ACTIVE.md pointing at ``_RELEASE_ID``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.invalid", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    releases_dir = repo / "specs" / "releases"
    releases_dir.mkdir(parents=True)
    (releases_dir / "ACTIVE.md").write_text(
        f"release: {_RELEASE_ID}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: bootstrap", cwd=repo)
    return repo


def _commit_code_change(repo: Path, content: str) -> str:
    (repo / "app.py").write_text(content, encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "feat: change app.py", cwd=repo)
    return _head(repo)


def _commit_verdict(
    repo: Path,
    *,
    covers_sha: str,
    verdict: str = "APPROVED",
    agent: str = "security-reviewer",
    release_id: str = _RELEASE_ID,
) -> str:
    payload = {
        "schema_version": "handoff-v1.2",
        "agent": agent,
        "context": "dadaia-workspace",
        "release_id": release_id,
        "verdict": verdict,
        "metrics": {"commit_sha": covers_sha},
    }
    verdicts_dir = repo / "specs" / "releases" / release_id / "verdicts"
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    (verdicts_dir / f"{covers_sha}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: attach security verdict", cwd=repo)
    return _head(repo)


def _commit_verdict_archived(
    repo: Path,
    *,
    covers_sha: str,
    verdict: str = "APPROVED",
    agent: str = "security-reviewer",
    release_id: str = _RELEASE_ID,
) -> str:
    """Places the verdict directly under ``specs/releases/_archive/<id>/verdicts/`` —
    the v6 per-area-archive shape release closure produces by ``git mv``-ing the whole
    release directory (verdicts included) out of the live tree, per T-044-50's fix scope
    and T-050-06A's canon rename (bug
    pr-verdict-check-wiring-fixture-archived-verdict-path-predates-v6-canon: this
    fixture used to place evidence at the pre-v6 ``specs/_archive/releases/<id>/``
    layout, which the canon-derived script never resolves against).
    """
    payload = {
        "schema_version": "handoff-v1.2",
        "agent": agent,
        "context": "dadaia-workspace",
        "release_id": release_id,
        "verdict": verdict,
        "metrics": {"commit_sha": covers_sha},
    }
    verdicts_dir = repo / "specs" / "releases" / "_archive" / release_id / "verdicts"
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    (verdicts_dir / f"{covers_sha}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: archive security verdict", cwd=repo)
    return _head(repo)


def _set_active_release_none(repo: Path) -> str:
    """Mirrors the real closure step (``dd-release-implement`` step 12): once a
    release archives, ``ACTIVE.md`` legitimately reads ``release: none``.
    """
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        "release: none\nphase: ARCHIVED\n", encoding="utf-8"
    )
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: close release (ACTIVE.md -> none)", cwd=repo)
    return _head(repo)


def _run_script(
    repo: Path, head_sha: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": _TEST_PATH, "PR_HEAD_SHA": head_sha, **(extra_env or {})}
    return subprocess.run(
        ["bash", str(_SCRIPT)], cwd=str(repo), capture_output=True, text=True, env=env
    )


def test_script_exists_and_is_executable() -> None:
    assert _SCRIPT.is_file(), f"expected script at {_SCRIPT}"
    if os.name != "nt":
        mode = _SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "script must be executable (chmod +x)"


def test_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_no_qualifying_evidence_anywhere_fails_closed_naming_expected_shape(
    tmp_path: Path,
) -> None:
    """T-044-50 item 5: with no verdict file in either tree (live or archived), the
    gate must fail closed and name the expected shape — no longer "directory not
    found" (there is no single directory any more, only a glob across two trees).
    """
    repo = _init_repo(tmp_path)
    head = _head(repo)
    result = _run_script(repo, head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "verdicts" in result.stdout + result.stderr


def test_exact_sha_match_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    # The PR head IS the reviewed sha itself (no trailing commit needed in this case).
    result = _run_script(repo, reviewed)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ancestor_with_pure_evidence_trailing_commit_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed)
    assert evidence_head != reviewed
    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr


def test_unreviewed_code_change_after_the_review_fails(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    drifted_head = _commit_code_change(repo, "print('v3 - unreviewed')\n")
    result = _run_script(repo, drifted_head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "app.py" in result.stdout + result.stderr


def test_rejected_verdict_does_not_qualify(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, verdict="REJECTED")
    result = _run_script(repo, evidence_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_wrong_agent_does_not_qualify(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, agent="qa-engineer")
    result = _run_script(repo, evidence_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_sha_not_ancestor_of_head_fails(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    # A divergent branch's tip is never an ancestor of the reviewed line's history.
    _git("checkout", "-q", "-b", "unrelated", "main", cwd=repo)
    unrelated_head = _commit_code_change(repo, "print('unrelated branch')\n")
    result = _run_script(repo, unrelated_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_release_id_env_override_narrows_the_glob(tmp_path: Path) -> None:
    """T-044-50: RELEASE_ID is optional NARROWING only, post-fix — never a required
    pointer. Evidence committed under a release id ACTIVE.md does not name (v8.8.8,
    while ACTIVE.md still names v9.9.9) qualifies with no override at all, because
    resolution is by artifact glob (``*``) rather than by ACTIVE.md's value. Supplying
    RELEASE_ID matching the evidence's own release id still qualifies. Supplying a
    DIFFERENT, canonical release id narrows the glob and excludes that evidence —
    proving the override is a real narrowing, not a no-op.
    """
    repo = _init_repo(tmp_path)  # ACTIVE.md names v9.9.9, never read by the fixed script
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, release_id="v8.8.8")

    unnarrowed = _run_script(repo, evidence_head)
    assert unnarrowed.returncode == 0, unnarrowed.stdout + unnarrowed.stderr

    matching_override = _run_script(repo, evidence_head, {"RELEASE_ID": "v8.8.8"})
    assert matching_override.returncode == 0, matching_override.stdout + matching_override.stderr

    excluding_override = _run_script(repo, evidence_head, {"RELEASE_ID": "v9.9.9"})
    assert excluding_override.returncode != 0, excluding_override.stdout + excluding_override.stderr


def test_release_id_none_literal_behaves_as_no_narrowing_never_an_error(
    tmp_path: Path,
) -> None:
    """T-044-50: RELEASE_ID="none" — the exact literal ACTIVE.md carries at closure,
    were some future caller to forward it — must behave identically to unset: no
    narrowing, never a canon-pattern error. This is the explicit boundary the fix
    prescription calls out: 'none'/unset = no narrowing, never an error.
    """
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed)

    result = _run_script(repo, evidence_head, {"RELEASE_ID": "none"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "does not match the canonical release-id pattern" not in (result.stdout + result.stderr)


def test_active_md_absence_has_no_effect_since_it_is_no_longer_read(tmp_path: Path) -> None:
    """T-044-50: ACTIVE.md is deleted as a read entirely (the structural fix), so its
    absence must have ZERO effect — the failure (still fail-closed, no evidence
    anywhere) must never mention ACTIVE.md, proving the pointer read is gone rather
    than merely made lenient.
    """
    repo = tmp_path / "bare-repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.invalid", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: bootstrap", cwd=repo)
    head = _head(repo)

    result = _run_script(repo, head)
    assert result.returncode != 0
    assert "ACTIVE.md" not in (result.stdout + result.stderr)


def test_git_diff_failure_fails_closed_not_open(tmp_path: Path) -> None:
    """T-044-45 F-2 (1/2): a git failure while proving 'nothing unreviewed landed
    since the review' must never be silently read as an empty (i.e. clean) diff.

    ``$(git diff --name-only "$sha" "$PR_HEAD_SHA")`` used to be expanded straight
    into a heredoc body — a shape whose failure does NOT trip ``set -euo pipefail``,
    so a failing ``git diff`` degraded the check to "assume nothing unreviewed
    landed" and the verdict passed. A ``git`` shim that fails only the ``diff``
    subcommand (every other git call the script and its fixtures make — init,
    commit, cat-file, merge-base — is forwarded to the real binary) proves the
    fix-closed behaviour: the script must exit non-zero, never PASS.
    """
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed)
    assert evidence_head != reviewed

    real_git = shutil.which("git")
    assert real_git is not None, "the ambient test environment must provide a real git"
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "diff" ]; then\n'
        "  echo 'fatal: simulated git diff failure for T-044-45 F-2' >&2\n"
        "  exit 128\n"
        "fi\n"
        f'exec "{real_git}" "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)

    result = _run_script(repo, evidence_head, {"PATH": f"{shim_dir}:{_TEST_PATH}"})
    assert result.returncode != 0, (
        "a failing 'git diff' must fail the gate closed, never PASS on an "
        f"unproven diff: {result.stdout + result.stderr}"
    )
    assert "PASS" not in result.stdout


def test_malicious_release_id_is_rejected_before_path_interpolation(tmp_path: Path) -> None:
    """T-044-45 F-2 (2/2), carried through T-044-50: RELEASE_ID, when explicitly
    supplied as an override, is interpolated straight into the verdicts glob. A
    path-traversal-shaped value must be refused before it ever reaches a path, with a
    clear diagnostic — not silently normalised, not allowed through. (Post T-044-50,
    ACTIVE.md is no longer a channel for this value at all — see
    ``test_release_id_traversal_in_active_md_has_no_effect_since_active_md_is_ignored``
    — so only the explicit-override channel remains to prove closed here.)
    """
    repo = _init_repo(tmp_path)
    head = _head(repo)

    result = _run_script(repo, head, {"RELEASE_ID": "../../etc"})
    assert result.returncode != 0, result.stdout + result.stderr
    assert "RELEASE_ID" in result.stdout + result.stderr


def test_commit_sha_head_literal_does_not_qualify_the_gate(tmp_path: Path) -> None:
    """T-044-46 S-1 — RED against the pre-fix script, GREEN after the shape check.

    Reviewer's exact repro: the only handoff on the branch "reviews" via the literal
    ref name ``HEAD`` rather than a real 40-hex sha, and an unreviewed production
    change lands on the same branch. A GitHub Actions checkout puts the job's
    ``HEAD`` at the PR head sha, so this test commits the verdict handoff (naming
    ``HEAD``) as the PR head itself — the same state the CI job would see: the
    repo's actual ``HEAD`` ref and ``PR_HEAD_SHA`` name the identical commit.

    Unfixed, the script accepts ``sha="HEAD"``: ``git cat-file -e HEAD^{commit}``
    resolves against the checkout's real HEAD, ``git merge-base --is-ancestor HEAD
    "$PR_HEAD_SHA"`` is trivially true (a commit is its own ancestor), and
    ``git diff --name-only HEAD "$PR_HEAD_SHA"`` is empty (same commit) — both halves
    of the coverage proof collapse into tautologies and the gate PASSes on a commit
    that was never reviewed by any real sha. Fixed, the 40-hex shape check SKIPs the
    handoff before it ever reaches a git argv, no qualifying handoff remains, and the
    gate FAILs.
    """
    repo = _init_repo(tmp_path)
    # Unreviewed production change landing on the PR branch — no verdict ever names
    # this commit's own sha.
    _commit_code_change(repo, "print('v2 - never actually reviewed by a real sha')\n")
    # The only handoff on the branch claims coverage via the literal ref "HEAD".
    pr_head = _commit_verdict(repo, covers_sha="HEAD")

    result = _run_script(repo, pr_head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "PASS" not in result.stdout


def test_well_formed_ancestor_sha_with_only_verdict_drift_still_passes(tmp_path: Path) -> None:
    """No regression: the T-044-46 S-1 shape check must not reject a real, well-formed
    40-hex ancestor sha whose only trailing drift is more verdict evidence.

    Distinct from ``test_ancestor_with_pure_evidence_trailing_commit_passes`` in what
    it pins: that a genuine git-object-id sha (40 lowercase hex chars, sanity-checked
    below) survives the new ``^[0-9a-fA-F]{40}$`` predicate and still reaches PASS —
    the boundary condition the S-1 fix must not break.
    """
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    assert len(reviewed) == 40 and all(c in "0123456789abcdef" for c in reviewed), (
        "sanity: the reviewed sha must be a real 40-hex git object id, not a symbolic ref"
    )
    evidence_head = _commit_verdict(repo, covers_sha=reviewed)
    assert evidence_head != reviewed

    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_release_id_traversal_in_active_md_has_no_effect_since_active_md_is_ignored(
    tmp_path: Path,
) -> None:
    """T-044-50: the F-2 attack this test used to pin (a PR-controlled ACTIVE.md
    feeding a traversal-shaped value into RELEASE_ID) is eliminated by deletion, not
    merely defended: ACTIVE.md is not read at all post-fix, so even a malicious
    ``release:`` line sits inert. Proven two ways in one test: (1) legitimate
    evidence committed under a real release id is still found via the unnarrowed
    glob, regardless of the malicious ACTIVE.md content sitting alongside it; (2) no
    error ever mentions RELEASE_ID, because the malicious value is never read, let
    alone validated.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.invalid", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    releases_dir = repo / "specs" / "releases"
    releases_dir.mkdir(parents=True)
    (releases_dir / "ACTIVE.md").write_text(
        "release: ../../etc\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: bootstrap", cwd=repo)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, release_id="v9.9.9")

    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RELEASE_ID" not in (result.stdout + result.stderr)


def test_archived_release_tree_evidence_with_active_release_none_passes(tmp_path: Path) -> None:
    """T-044-50 item 1 — the bug's exact repro, RED against the pre-fix script,
    GREEN after: at a closed release (ACTIVE.md 'release: none', mirroring
    ``dd-release-implement`` step 12's archive) the security-reviewer's APPROVED
    verdict has already been ``git mv``'d into
    ``specs/releases/_archive/<id>/verdicts/`` by the closure that just ran. The gate
    must still PASS — resolving evidence by the artifact, never the ACTIVE.md
    pointer that legitimately (and, pre-fix, fatally) reads 'none' here.
    """
    repo = _init_repo(tmp_path)
    _commit_code_change(repo, "print('v2')\n")
    closure_head = _set_active_release_none(repo)
    evidence_head = _commit_verdict_archived(repo, covers_sha=closure_head)
    assert evidence_head != closure_head

    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_live_tree_evidence_passes_regardless_of_active_md_release_id(tmp_path: Path) -> None:
    """T-044-50 item 2 — no regression: live-tree evidence
    (``specs/releases/<id>/verdicts/``) still PASSES after the fix, even when
    ACTIVE.md names a DIFFERENT, mismatched release than the evidence's own
    directory — proving resolution is now by artifact, never by a pointer that has
    to agree with it.
    """
    repo = _init_repo(tmp_path)  # ACTIVE.md names v9.9.9
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, release_id="v7.7.7")

    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_archived_evidence_with_trailing_unreviewed_production_change_fails(
    tmp_path: Path,
) -> None:
    """T-044-50 item 3: mixing archived-tree verdict evidence with a genuinely
    unreviewed production change landing AFTER the review must still FAIL — the
    widened only-verdict-drift exemption (now matching both
    ``specs/releases/*/verdicts/*`` and ``specs/releases/_archive/*/verdicts/*``)
    must not swallow a real production diff just because it happens to land near
    archived evidence.
    """
    repo = _init_repo(tmp_path)
    _commit_code_change(repo, "print('v2')\n")
    closure_head = _set_active_release_none(repo)
    _commit_verdict_archived(repo, covers_sha=closure_head)
    drifted_head = _commit_code_change(repo, "print('v3 - unreviewed after archive')\n")

    result = _run_script(repo, drifted_head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "app.py" in result.stdout + result.stderr
