"""Branch policy — the gitflow v2 contract (v0.4.4 FR3; split out of ``service.py`` at
v0.5.1 K7, "split chokepoints.service into its four modules; one verdict store").

Zero I/O, zero dependency on anything else in this package: :class:`PushRef` (the
parsed pre-push stdin shape), the three permitted branch patterns, and
:func:`push_ref_policy_decision` (the per-ref loop :func:`~dadaia_workspace.features.
chokepoints.push_gate.push_gate_decision` runs first, before either specs-scan step).
:class:`Decision` — the shared outcome shape every chokepoint gate returns — lives here
too: this module has no internal-package dependency, so every sibling module (``pre_commit``,
``push_gate``, ``verdict``) imports it from here rather than duplicating it or reaching
into ``__init__.py`` (which itself re-exports from this module, never the reverse).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Decision",
    "PushRef",
    "branch_name_is_permitted",
    "check_branch_policy",
    "context_slug_for_path",
    "parse_push_refs",
    "parse_push_stdin",
]


@dataclass(frozen=True)
class Decision:
    """Outcome of a chokepoint gate.

    ``allowed`` is the only thing the git hook keys its exit code on. ``warn`` carries an
    advisory line that is logged/printed but never blocks (the DP-4 degradation path).
    ``message`` is the human-facing block/allow explanation.
    """

    allowed: bool
    message: str = ""
    warn: str | None = None


#: A pre-push sha is 40-char (SHA-1) or 64-char (SHA-256) hex (v0.11.0 FR7/A7.3) — an
#: option-shaped value (``--glob=refs/nonexistent``) is malformed, never a silent no-op
#: (CWE-88/CWE-20). The all-zero deletion sentinel is 40 hex characters and already
#: matches — no special case needed.
_SHA_SHAPE_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

#: git's zero-sha deletion sentinel (40 hex zeros) — imported by ``push_gate`` too.
ZERO_SHA = "0" * 40


def _is_sha_shaped(value: str) -> bool:
    return bool(_SHA_SHAPE_RE.match(value))


@dataclass(frozen=True)
class PushRef:
    """One parsed pre-push stdin ref line.

    git feeds the pre-push hook lines of ``<local-ref> <local-sha> <remote-ref>
    <remote-sha>`` on stdin. The push gate keys ONLY on ``local_sha`` (never
    ``git rev-parse HEAD``): a zero ``local_sha`` is a branch deletion.
    """

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def is_deletion(self) -> bool:
        """True when this ref is being deleted (zero local sha) — passes with no verdict."""
        return self.local_sha == ZERO_SHA or not self.local_sha

    @property
    def is_tag(self) -> bool:
        """True when this ref is a tag push — passes with no verdict (DP-5)."""
        return self.local_ref.startswith("refs/tags/")


def parse_push_stdin(stdin_text: str) -> tuple[list[PushRef], int]:
    """Parse pre-push stdin into :class:`PushRef` rows plus a malformed-line count.

    A non-empty line that does not split into exactly four fields is counted, not
    silently dropped — the gate FAILS CLOSED on any malformed line (T-060-07 finding 1:
    a policy gate that skips what it cannot parse is a policy gate that can be
    disabled without a trace; ``git push --no-verify`` is the sanctioned bypass).

    v0.11.0 FR7/A7.1-A7.3: both shas are additionally validated against
    :data:`_SHA_SHAPE_RE` — a violation reuses the SAME malformed-line counter and the
    SAME fail-closed message (no new branch), so an option-shaped ``local_sha`` (the
    measured silent-no-op class) refuses instead of producing a successful empty
    ``git rev-list``.
    """
    refs: list[PushRef] = []
    malformed = 0
    for raw in stdin_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            malformed += 1
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if not _is_sha_shaped(local_sha) or not _is_sha_shaped(remote_sha):
            malformed += 1
            continue
        refs.append(PushRef(local_ref, local_sha, remote_ref, remote_sha))
    return refs, malformed


def parse_push_refs(stdin_text: str) -> list[PushRef]:
    """Back-compat wrapper over :func:`parse_push_stdin` (refs only)."""
    return parse_push_stdin(stdin_text)[0]


# ── The three permitted branch patterns (v0.4.4 FR3 / T-044-06 — the gitflow v2 -------
# inversion). The gitflow law (DADAIA.md §4, operator ruling 2026-08-23): exactly three
# branch patterns exist — no ``v`` prefix, no ``hotfix`` row (G2 retires it outright) —
# and ``feature/{M.m.p}`` is the ONLY pushable one; ``develop`` and ``main`` advance by
# PR only. This tuple is the ONE pattern source — the pre-push hook and the CI
# pr-source-guard both encode the model, and any second regex copy is drift (A3.2).
_MAIN_RE = re.compile(r"^main$")
_DEVELOP_RE = re.compile(r"^develop$")
_FEATURE_RE = re.compile(r"^feature/\d+\.\d+\.\d+$")

_PERMITTED_BRANCH_RES: tuple[re.Pattern[str], ...] = (_MAIN_RE, _DEVELOP_RE, _FEATURE_RE)

HEADS_PREFIX = "refs/heads/"


def branch_name_is_permitted(branch: str) -> bool:
    """True when *branch* matches one of the three permitted patterns.

    ``main`` | ``develop`` | ``feature/M.m.p`` — no leading ``v``, no suffix, no
    ``hotfix`` row (G2). Matching one of these patterns does not by itself mean
    *branch* is pushable — only ``feature/M.m.p`` is (see :func:`check_branch_policy`).
    """
    return any(pattern.match(branch) for pattern in _PERMITTED_BRANCH_RES)


def _refuse_branch(branch: str, local_ref: str) -> Decision:
    """Actionable refusal for a non-pushable ref (A4.2 shape: rule + permitted + fix)."""
    if branch == "main":
        return Decision(
            allowed=False,
            message=(
                "[pre-push] BLOCKED: 'main' is never pushed directly — it advances only "
                "via a PR from 'develop' (gitflow law, DADAIA.md §4).\n"
                "  Fix: push your work to 'develop' (via the PR below), then open the "
                "PR develop → main."
            ),
        )
    if branch == "develop":
        return Decision(
            allowed=False,
            message=(
                "[pre-push] BLOCKED: 'develop' is never pushed directly — it advances "
                "only via a PR from 'feature/{M.m.p}' (gitflow law, DADAIA.md §4).\n"
                "  Fix: push your work on 'feature/{M.m.p}' instead, then open the PR "
                "feature/{M.m.p} → develop."
            ),
        )
    return Decision(
        allowed=False,
        message=(
            f"[pre-push] BLOCKED: ref '{local_ref}' is outside the three permitted "
            "branch patterns — main, develop, feature/M.m.p (gitflow law, "
            "DADAIA.md §4). Only 'feature/M.m.p' is pushable.\n"
            "  Fix: rebuild the work on a permitted branch (git checkout -b "
            "feature/M.m.p from main), push it, then open the PR "
            "feature/M.m.p → develop."
        ),
    )


def check_branch_policy(refs: list[PushRef]) -> Decision | None:
    """Step 1 of :func:`~dadaia_workspace.features.chokepoints.push_gate.push_gate_decision`
    (DADAIA.md §4): every non-deletion, non-tag ref must be
    ``refs/heads/feature/{M.m.p}``, pushed to the SAME remote name — ``develop``/``main``
    are refused outright (PR only); names outside the three permitted patterns are
    refused as invalid. Returns the first refusal, or ``None`` when every ref clears
    branch policy (tags and deletions are never checked here — the caller has already
    excluded them from *refs*).
    """
    for ref in refs:
        if not ref.local_ref.startswith(HEADS_PREFIX):
            return Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: local ref '{ref.local_ref}' is not a branch "
                    "head — only a 'refs/heads/feature/M.m.p' branch may be pushed "
                    "(gitflow law, DADAIA.md §4).\n"
                    "  Fix: check out your feature/M.m.p branch (git checkout "
                    "feature/M.m.p) and push it directly instead of pushing a "
                    "detached or symbolic ref."
                ),
            )
        branch = ref.local_ref[len(HEADS_PREFIX) :]
        if not _FEATURE_RE.match(branch):
            return _refuse_branch(branch, ref.local_ref)
        if ref.remote_ref != f"{HEADS_PREFIX}{branch}":
            return Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: refspec aims local '{branch}' at remote "
                    f"'{ref.remote_ref}' — only refs/heads/{branch} → "
                    f"refs/heads/{branch} is pushable (gitflow law, DADAIA.md §4; "
                    "'develop' and 'main' advance via PR only).\n"
                    f"  Fix: push {branch} to {branch} (git push origin {branch}) "
                    "and open the PR feature/M.m.p → develop for anything meant to "
                    "land there."
                ),
            )
    return None


# ---------------------------------------------------------------------------------------
# Context resolution — derive the slug from the repo path, NEVER first-ALIVE.
# ---------------------------------------------------------------------------------------
def context_slug_for_path(workspace: Path, repo_root: Path) -> str | None:
    """Return the context slug for a repo at ``repo_root`` under ``workspace``.

    A Spec Context repo lives at ``<workspace>/repos/<slug>``. The slug is that single path
    component — derived from the path, never from the first-ALIVE registry entry. Returns
    ``None`` when ``repo_root`` is not directly under ``<workspace>/repos/`` (e.g. the
    library repo run standalone, or the workspace root itself).
    """
    try:
        rel = repo_root.resolve().relative_to((workspace / "repos").resolve())
    except (ValueError, OSError):
        return None
    parts = rel.parts
    if len(parts) != 1:
        return None
    return parts[0]
