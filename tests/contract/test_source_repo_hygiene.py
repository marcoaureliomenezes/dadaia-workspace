"""Source-repo hygiene contracts for files that must be visible to review/CI."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=_REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_sdd_gate_artifacts_visible_and_noncanonical_content_stays_gitignored() -> None:
    """The SDD gate cannot depend on local-only files hidden from git (release-tree
    content is tracked by default since the gitignore-verdict-evidence-untrackable-
    fourth-recurrence structural fix), while non-canonical scratch/private content
    still stays hidden by the narrow ignore patterns that survive the inversion."""
    visible_paths = [
        "specs/releases/ACTIVE.md",
        "specs/releases/v9.9.9/SPEC.md",
        "specs/releases/v9.9.9/PLAN.md",
        "specs/releases/v9.9.9/TASKS.md",
        "specs/releases/v9.9.9/CLOSURE.md",
        "specs/releases/v9.9.9/GRILL.md",
        "specs/releases/v9.9.9/OQ-DECISIONS.md",
        # Each alpha-N closes with a qa-engineer review COMMITTED to the branch
        # (DADAIA.md §5); bug gitignore-alpha-qa-review-untrackable: the blanket
        # /specs/releases/*/* ignore had no negation for it, so the law was
        # silently undefeatable without git add -f (v0.5.0's ALPHA-1-QA.md was
        # force-added exactly that way).
        "specs/releases/v9.9.9/ALPHA-1-QA.md",
        "specs/releases/v9.9.9/ALPHA-12-QA.md",
        # The pre-PR six-axis code-reviewer review runs BEFORE the archive move,
        # committed to the branch (FR5/ADR R3, v0.4.2); bug
        # gitignore-code-review-artifact-untrackable: same class as the ALPHA-N-QA
        # gap above — the blanket /specs/releases/*/* ignore had no negation for it
        # either, so this law-mandated artifact needed git add -f on its first
        # execution (T-042-18). PRE-PR-REVIEW.md is the TASKS-declared canonical name.
        "specs/releases/v9.9.9/PRE-PR-REVIEW.md",
        # v0.4.4-reviews-dir-untrackable-gitignore-recurrence: third recurrence of the
        # same class — the per-segment qa-engineer close and software-architect AR-N
        # rulings under reviews/ were silently swallowed too.
        "specs/releases/v9.9.9/reviews/S1-qa-close.md",
        "specs/releases/v9.9.9/reviews/S1-AR2-ruling.md",
        # alpha/rc segment files (ADR-1/ADR-5).
        "specs/releases/v9.9.9/alpha-1/SPEC.md",
        "specs/releases/v9.9.9/rc-1/TASKS.md",
        # gitignore-verdict-evidence-untrackable-fourth-recurrence (this bug's own
        # regression seam): FR4's verdicts/ transport, the CI security-verdict-gate
        # commit, had no whitelist line either — the class's fourth instance, closed
        # by inverting the rule (release-tree content tracked by default) instead of
        # a fifth per-artifact line.
        "specs/releases/v9.9.9/verdicts/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.handoff.json",
        "specs/_archive/releases/v9.9.8/SPEC.md",
        "specs/_archive/releases/v9.9.8/PLAN.md",
        "specs/_archive/releases/v9.9.8/TASKS.md",
        "specs/_archive/releases/v9.9.8/CLOSURE.md",
        "specs/_archive/releases/v9.9.8/alpha-1/SPEC.md",
        "specs/_archive/releases/v9.9.8/verdicts/"
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.handoff.json",
        # Bug records are repository truth (bug-registration-guardrail); the
        # /specs/* privacy backstop must not hide them from review/CI.
        "specs/bugs/some-bug.md",
        "specs/audits/20991231T235959Z/index.md",
        # Backlog is PM-curated repository truth (v0.1.49 FR1 — bug
        # backlog-gitignored-governance-vacuous): live entries, the curated
        # index, and _archive durable copies are all visible to review/CI.
        "specs/backlog/candidates.md",
        "specs/backlog/some-entry.md",
        "specs/backlog/_archive/some-consumed-entry.md",
    ]
    ignored = [path for path in visible_paths if _is_ignored(path)]
    assert ignored == []

    ignored_paths = [
        # Backlog opt-in is Markdown-only (v0.1.49 FR1): non-md content and the
        # _archive/.gitkeep placeholder stay hidden by the privacy backstop.
        "specs/backlog/non-markdown-attachment.png",
        "specs/backlog/_archive/.gitkeep",
        "specs/bugs/non-markdown-attachment.png",
        # The inverted release-tree rule (gitignore-verdict-evidence-untrackable-
        # fourth-recurrence) still hides exactly the two classes the original
        # catch-all ever protected: private local-notes.md and tmp/ scratch dirs,
        # at any depth (release root or nested inside an alpha-N/rc-N segment).
        "specs/releases/v9.9.9/local-notes.md",
        "specs/releases/v9.9.9/tmp/debug.json",
        "specs/releases/v9.9.9/alpha-1/local-notes.md",
        "specs/releases/v9.9.9/alpha-1/tmp/debug.json",
        "specs/_archive/releases/v9.9.8/local-notes.md",
    ]
    not_ignored = [path for path in ignored_paths if not _is_ignored(path)]
    assert not_ignored == []
