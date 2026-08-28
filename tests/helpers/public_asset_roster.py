"""Derived inventory of ``dadaia_workspace/public/**`` (v0.4.5 FR3,
``byte-golden-test-inventory-roster-split``).

``test_install_target_goldens.py`` and ``test_public_assets_profile.py`` used to pin
the FULL per-file inventory of every public asset inside their byte goldens
(``install_target_resolution_v0158.json``, ``doctor_all_four_v0158.json``) — adding or
removing a single skill/agent/rule file forced a golden regen whose huge multi-line
diff also hid whether a genuine POLICY change (a target-mapping rule, a header/banner,
a mode/newline convention) slipped in alongside it (v0.4.4 AR-1).

This module is the single, DERIVED source of that inventory dimension: it scans
``dadaia_workspace/public/**`` at test time and hands back the exact roster the two
goldens used to hand-pin, plus two filters that strip inventory-shaped lines out of a
captured ``install()``/``doctor()`` transcript, leaving only target-mapping policy.

It reuses :class:`FileSystemPublicAssetManager`'s own private walk
(``_iter_files``/``_is_ignored_public_asset``) rather than reimplementing the
include/exclude rules by hand — that walk is the EXACT enumeration ``install()``,
``doctor()`` and ``stage()`` call internally (``dadaia_workspace/infrastructure/
public_assets.py``), so this roster can never drift from the product's own discovery.
No *public* (non-underscore) method offers the same full recursive walk with the real
ignore semantics: ``list_all()`` only reports one level of category-entry names, too
coarse to reconcile against ``doctor()``'s per-file ``stage:<relpath>`` loop. Reaching
for the manager's own private primitive beats hand-rolling a second, independently
maintained scan — exactly the "coupled inventory, kept twice" class FR3/FR4 retire.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def default_public_dir() -> Path:
    """The package's real ``dadaia_workspace/public/`` tree — the same root
    ``install()``/``doctor()``/``stage()`` read from by default."""
    return FileSystemPublicAssetManager()._public_dir  # noqa: SLF001


def scan(public_dir: Path | None = None) -> list[str]:
    """Every real (non-ignored) asset file under *public_dir*, POSIX-relative, sorted.

    Defaults to :func:`default_public_dir` — the real package tree. A caller
    exercising a mutated COPY of ``public/`` (never the real tree) passes that copy's
    root explicitly, so the roster stays self-consistent with whatever was actually
    scanned to produce the capture under test.
    """
    mgr = FileSystemPublicAssetManager()
    root = public_dir if public_dir is not None else mgr._public_dir  # noqa: SLF001
    return sorted(p.relative_to(root).as_posix() for p in mgr._iter_files(root))  # noqa: SLF001


#: The two staged-artifact VALIDITY checks ``doctor()`` appends unconditionally
#: alongside its per-roster-asset ``stage:<relpath>`` loop (``public_assets.py``,
#: ``stage:manifest.json``/``stage:agents.index.json``) — not roster entries
#: themselves, so :func:`stage_asset_paths` excludes them from the exact roster match.
_DOCTOR_STAGE_VALIDITY_LABELS = frozenset({"manifest.json", "agents.index.json"})


def stage_asset_paths(doctor_lines: list[str]) -> set[str]:
    """The roster-corresponding ``stage:<relpath>`` paths in a captured ``doctor()``
    transcript (already ``tests.helpers.golden_platform.norm_path_line``-normalized).

    An EXACT extraction (not a heuristic) — ``doctor()``'s first loop emits one
    ``stage:<relpath>`` line per roster entry, so the result is meant to equal
    :func:`scan`'s output exactly for a healthy, fully-staged tree (the roster
    assertion, A3.1).
    """
    paths = {line.partition(":")[2] for line in doctor_lines if line.startswith("[ok] stage:")}
    return paths - _DOCTOR_STAGE_VALIDITY_LABELS


def _is_roster_derived(payload: str, roster: list[str]) -> bool:
    """True when *payload* is a literal, unrenamed copy of one roster asset — i.e. it
    equals, or ends with ``"/" + ...``, that asset's public-relative path.

    An extension-changing render (Codex's ``.md`` -> ``.toml`` transform, the merged
    ``.claude/settings.json``, the ``DADAIA.md``/``AGENTS.md`` guardrail-family
    renames) deliberately does NOT match: a transform's output is BEHAVIOUR, not raw
    inventory, and stays policy-pinned in the golden.
    """
    return any(payload == rel or payload.endswith("/" + rel) for rel in roster)


def policy_only_install_lines(lines: list[str], roster: list[str]) -> list[str]:
    """Drop every ``install()``-captured line that is a literal roster-asset copy.

    *lines* are already normalized (``tests.helpers.golden_platform.norm_path_line``
    — a ``<WS>/`` prefix, no host path). What survives is target-mapping policy: the
    fixed ``[stage] <WS>/.dadaia/agentic/<category>`` lines (one per ``_COPY_DIRS``
    entry, never per-asset) and the small set of synthesized/renamed files
    (the ``AGENTS.md`` guardrail family, the ``DADAIA.md`` fan-out,
    ``.claude/settings.json``, the Codex ``.toml`` renders, the kimi-code hook
    shims) — none of which fan out when a skill/agent/rule file is merely added or
    removed under ``public/``.
    """
    kept: list[str] = []
    for line in lines:
        marker, bracket, rest = line.partition("]")
        payload = rest.strip().removeprefix("<WS>/") if bracket else line
        if _is_roster_derived(payload, roster):
            continue
        kept.append(line)
    return kept


def policy_only_doctor_lines(lines: list[str], roster: list[str]) -> list[str]:
    """Drop every ``doctor()``-captured ``<label>:<relpath>`` line whose ``relpath`` is
    a literal roster-asset copy.

    ``doctor()`` reports two roster-shaped families, both ``<label>:<path>``: its own
    first loop (``public_assets.py``) walks ``_iter_files(self._public_dir)`` and
    emits one ``stage:<relpath>`` line per roster entry (public -> staged copy,
    ``relpath`` an EXACT roster path); ``runtime_expectations()`` then emits one
    ``<target>:<relpath-under-target>`` line per roster entry PER applicable L1 runtime
    (staged -> projected copy, e.g. ``agents:skills/…``, ``claude:agents/….md``,
    ``dadaia:scripts/….sh``) — the doctor-side mirror of the install-line fan-out
    :func:`policy_only_install_lines` filters. Splitting on the first ``:`` and
    suffix-matching the tail against the roster (via :func:`_is_roster_derived`)
    catches both families uniformly. Everything else — lines with no ``:`` at all
    (``public-privacy``), or whose tail is prose/a generated-file name rather than a
    literal roster path (``codex:trust-boundary — …``, ``claude:settings.json``,
    ``law:DADAIA.md``'s renamed fan-out, the D-CX-* codex-drift checks, the
    ``stage:manifest.json``/``stage:agents.index.json`` validity lines) — is bounded,
    fixed-cardinality doctor policy, never per-public-asset fan-out, and stays.
    """
    kept: list[str] = []
    for line in lines:
        marker, bracket, rest = line.partition("]")
        payload = rest.strip() if bracket else line
        _label, colon, tail = payload.partition(":")
        if colon and _is_roster_derived(tail, roster):
            continue
        kept.append(line)
    return kept
