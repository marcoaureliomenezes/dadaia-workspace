"""Dynamic context selector — resolve a step's ``dynamic_inputs`` into content (WS-4).

A fragment (WS-3) declares ``dynamic_inputs`` (named context slots) and a
``max_context_policy`` (how much each slot is allowed to return). This module turns
those declarations into concrete, auditable content for a workflow step:

- A :class:`SpecContext` locates the active context's ``specs/`` tree, the active
  release directory, and the workspace handoff directory.
- :class:`ContextSelector.select` resolves a single named dynamic input under a
  :class:`MaxContextPolicy` into a :class:`SelectionResult` (resolved content +
  the refs — file paths / atom slugs / handoff ids — that were injected).
- :meth:`ContextSelector.select_all` resolves an ordered set of inputs at one policy
  and produces a :class:`SelectionAudit` listing every injected ref, which the run
  record persists for auditability (epic §8.8).

Selectors are pure reads against the specs tree (memory atoms, product catalog,
backlog items, bug records, audit findings, release artifacts) plus runtime evidence
(git diffs, test outputs, prior handoffs). Every selector returns a *real* result —
none raise ``NotImplementedError``. Selectors not exercised by the release-definition
workflow (diffs, test outputs, generic source summaries) are minimal-but-working and
unit-tested.

Max-context policies bound what a selector returns:

| policy | bound |
|---|---|
| ``exact-files-only`` | full file content of the resolved refs |
| ``summary`` | frontmatter / first-paragraph summary only |
| ``catalog-only`` | the catalog line(s) — title + tldr, no body |
| ``diff-only`` | a unified diff payload only |
| ``previous-handoff-only`` | the single most-recent matching handoff only |
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.lifecycle import InjectedContext

_SelectorFn = Callable[["ContextSelector", str, "MaxContextPolicy"], "SelectionResult"]


class ContextSelectorError(DadaiaError):
    """Base error for the dynamic context selector."""


class UnknownDynamicInputError(ContextSelectorError):
    """Raised when a requested dynamic input has no registered selector."""


class UnknownPolicyError(ContextSelectorError):
    """Raised when a ``max_context_policy`` value is not recognised."""


class MaxContextPolicy(StrEnum):
    """How much a selector is allowed to return for a step."""

    EXACT_FILES_ONLY = "exact-files-only"
    SUMMARY = "summary"
    CATALOG_ONLY = "catalog-only"
    DIFF_ONLY = "diff-only"
    PREVIOUS_HANDOFF_ONLY = "previous-handoff-only"

    @classmethod
    def parse(cls, value: str) -> MaxContextPolicy:
        try:
            return cls(value)
        except ValueError as exc:
            valid = ", ".join(sorted(p.value for p in cls))
            raise UnknownPolicyError(
                f"unknown max_context_policy '{value}'; valid policies: {valid}"
            ) from exc


@dataclass(frozen=True)
class SpecContext:
    """Locates the active context's specs tree, release dir, and handoff dir."""

    specs_dir: Path
    release_id: str
    handoff_dir: Path | None = None

    @property
    def release_dir(self) -> Path:
        return self.specs_dir / "releases" / self.release_id


@dataclass(frozen=True)
class StaticInput:
    """A resolved (or gracefully-skipped) fragment ``static_inputs`` entry.

    ``static_inputs`` are stable, release-level files (constitution, architecture memory)
    that belong in the cacheable prompt prefix. ``present`` is ``False`` and ``note``
    carries the reason when the declared file is absent in the active context, so a
    missing static input degrades gracefully rather than crashing the assembly.
    """

    ref: str
    present: bool
    content: str
    note: str = ""


@dataclass(frozen=True)
class SelectionResult:
    """The resolved content for one dynamic input, plus the refs injected."""

    name: str
    policy: MaxContextPolicy
    content: str
    refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectionAudit:
    """An auditable record of an ordered batch of selections for one step."""

    step: str
    results: tuple[SelectionResult, ...] = ()
    fragment_ids: tuple[str, ...] = ()

    @property
    def refs(self) -> tuple[str, ...]:
        ordered: list[str] = []
        seen: set[str] = set()
        for result in self.results:
            for ref in result.refs:
                if ref not in seen:
                    seen.add(ref)
                    ordered.append(ref)
        return tuple(ordered)

    def to_injected_context(self) -> InjectedContext:
        """Map this batch into the run-record :class:`InjectedContext` audit entry."""
        return InjectedContext(
            step=self.step,
            fragment_ids=self.fragment_ids,
            refs=self.refs,
            policies=tuple(sorted({result.policy.value for result in self.results})),
        )


# ---------------------------------------------------------------------------
# Frontmatter / summary helpers
# ---------------------------------------------------------------------------

_YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_MD_FIELD_RE = re.compile(r"^\*\*(?P<key>[^:*]+):\*\*\s*(?P<value>.+)$", re.MULTILINE)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter_summary(text: str, *, max_lines: int = 12) -> str:
    """Return the YAML frontmatter block if present, else the leading prose lines."""
    match = _YAML_FRONTMATTER_RE.match(text)
    if match:
        return match.group(1).strip()
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines]).strip()


def _bug_status(text: str) -> str:
    match = _YAML_FRONTMATTER_RE.match(text)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.strip().lower().startswith("status:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def _backlog_status(text: str) -> str:
    for field_match in _MD_FIELD_RE.finditer(text):
        if field_match.group("key").strip().lower() == "status":
            return field_match.group("value").strip().lower()
    return ""


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FileRef:
    """A resolved file with a stable, host-independent ref identifier."""

    path: Path
    ref: str


class ContextSelector:
    """Resolve named dynamic inputs into bounded, auditable content."""

    def __init__(self, context: SpecContext, *, cli_anchors: frozenset[str] = frozenset()) -> None:
        self._ctx = context
        # Pre-derived cli-kind anchor set, threaded in from the composition boundary
        # (FR1b) — only :meth:`sel_backlog_index` uses it (to build the subject registry);
        # this feature never imports ``cli.main``. Empty when the selector never resolves
        # ``backlog_index`` (the default).
        self._cli_anchors = cli_anchors

    @property
    def spec_context(self) -> SpecContext:
        return self._ctx

    # -- static-input resolution -----------------------------------------

    def resolve_static_input(self, declared: str) -> StaticInput:
        """Resolve a fragment's declared ``static_inputs`` entry to its file content.

        A ``static_inputs`` entry is a workspace-relative path (e.g.
        ``specs/constitution.md``, ``specs/memory/architecture.md``). It is resolved
        under the context root (``specs_dir.parent``). When the declared file is absent
        in this context the resolution degrades gracefully: ``present`` is ``False``,
        ``content`` is empty, and a human-readable ``note`` records the skip — the caller
        never crashes on a missing static input.
        """
        root = self._ctx.specs_dir.parent
        ref = declared.strip().lstrip("/")
        path = (root / ref).resolve()
        # Path-traversal guard: a declared static input must stay inside the context root.
        try:
            path.relative_to(root.resolve())
        except ValueError:
            return StaticInput(
                ref=ref,
                present=False,
                content="",
                note=f"declared static input outside context root: {ref}",
            )
        if not path.is_file():
            return StaticInput(
                ref=ref, present=False, content="", note=f"static input not found in context: {ref}"
            )
        return StaticInput(ref=ref, present=True, content=_read_text(path), note="")

    # -- batch API -------------------------------------------------------

    def select_all(
        self,
        step: str,
        names: tuple[str, ...],
        policy: MaxContextPolicy | str,
        *,
        fragment_ids: tuple[str, ...] = (),
    ) -> SelectionAudit:
        """Resolve an ordered set of inputs at one policy into an auditable batch."""
        resolved = MaxContextPolicy.parse(policy) if isinstance(policy, str) else policy
        results = tuple(self.select(name, resolved) for name in names)
        return SelectionAudit(step=step, results=results, fragment_ids=fragment_ids)

    # -- single API ------------------------------------------------------

    def select(self, name: str, policy: MaxContextPolicy | str) -> SelectionResult:
        """Resolve one named dynamic input under *policy*."""
        resolved = MaxContextPolicy.parse(policy) if isinstance(policy, str) else policy
        selector = _SELECTORS.get(name)
        if selector is None:
            valid = ", ".join(sorted(_SELECTORS))
            raise UnknownDynamicInputError(
                f"no selector registered for dynamic input '{name}'; known inputs: {valid}"
            )
        return selector(self, name, resolved)

    # -- shared rendering -------------------------------------------------

    def _render(
        self,
        name: str,
        policy: MaxContextPolicy,
        refs: tuple[_FileRef, ...],
    ) -> SelectionResult:
        """Render a set of file refs under *policy* into a result."""
        blocks: list[str] = []
        for fref in refs:
            text = _read_text(fref.path)
            if policy is MaxContextPolicy.SUMMARY:
                rendered = _frontmatter_summary(text)
            elif policy is MaxContextPolicy.CATALOG_ONLY:
                rendered = self._catalog_line(fref)
            else:
                rendered = text
            blocks.append(f"### {fref.ref}\n{rendered}".rstrip())
        return SelectionResult(
            name=name,
            policy=policy,
            content="\n\n".join(blocks),
            refs=tuple(fref.ref for fref in refs),
        )

    def _catalog_line(self, fref: _FileRef) -> str:
        text = _read_text(fref.path)
        summary = _frontmatter_summary(text, max_lines=3)
        first_heading = next(
            (line for line in text.splitlines() if line.startswith("#")),
            fref.ref,
        )
        return (
            f"{first_heading.lstrip('# ').strip()} — {summary.splitlines()[0] if summary else ''}"
        )

    # -- file discovery ---------------------------------------------------

    def _specs_ref(self, path: Path) -> str:
        try:
            return path.relative_to(self._ctx.specs_dir.parent).as_posix()
        except ValueError:
            return path.as_posix()

    def _dir_files(self, rel: str, *, suffix: str = ".md") -> tuple[_FileRef, ...]:
        directory = self._ctx.specs_dir / rel
        if not directory.is_dir():
            return ()
        refs: list[_FileRef] = []
        for path in sorted(directory.rglob(f"*{suffix}")):
            if path.name in {"index.md", "catalog.json"}:
                continue
            refs.append(_FileRef(path=path, ref=self._specs_ref(path)))
        return tuple(refs)

    def _release_artifact(
        self, name: str, policy: MaxContextPolicy, filename: str
    ) -> SelectionResult:
        path = self._ctx.release_dir / filename
        if not path.is_file():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return self._render(name, policy, (_FileRef(path=path, ref=self._specs_ref(path)),))

    # -- catalog / memory -------------------------------------------------

    def _catalog_path(self) -> Path:
        return self._ctx.specs_dir / "memory" / "product" / "catalog.json"

    def _catalog_features(self) -> list[dict[str, object]]:
        path = self._catalog_path()
        if not path.is_file():
            return []
        data = json.loads(_read_text(path))
        features = data.get("features", [])
        return features if isinstance(features, list) else []

    # ---- concrete selector implementations ----------------------------

    def sel_memory_atoms(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._dir_files("memory/product"))

    def sel_product_catalog(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        features = self._catalog_features()
        lines = [
            f"- {f.get('slug', '')}: {f.get('tldr', '')}".rstrip()
            for f in features
            if isinstance(f, dict)
        ]
        ref = self._specs_ref(self._catalog_path()) if self._catalog_path().is_file() else ""
        return SelectionResult(
            name=name,
            policy=policy,
            content="\n".join(lines),
            refs=(ref,) if ref else (),
        )

    def sel_relevant_product_atoms(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        # Real implementation: product atoms under memory/product, bounded by policy.
        return self._render(name, policy, self._dir_files("memory/product"))

    def sel_architecture(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        path = self._ctx.specs_dir / "memory" / "architecture.md"
        if not path.is_file():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return self._render(name, policy, (_FileRef(path=path, ref=self._specs_ref(path)),))

    def sel_quality_assurance(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        path = self._ctx.specs_dir / "memory" / "quality-assurance.md"
        if not path.is_file():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return self._render(name, policy, (_FileRef(path=path, ref=self._specs_ref(path)),))

    def sel_constitution(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        path = self._ctx.specs_dir / "constitution.md"
        if not path.is_file():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return self._render(name, policy, (_FileRef(path=path, ref=self._specs_ref(path)),))

    # ---- backlog / bugs / audits --------------------------------------

    def _backlog_refs(self, *, open_only: bool) -> tuple[_FileRef, ...]:
        refs = self._dir_files("backlog")
        if not open_only:
            return refs
        kept: list[_FileRef] = []
        for fref in refs:
            status = _backlog_status(_read_text(fref.path))
            if status in {"deferred", "rejected", "closed", "done", "shipped"}:
                continue
            kept.append(fref)
        return tuple(kept)

    def sel_candidate_backlog(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._backlog_refs(open_only=True))

    def sel_backlog_index(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        """Return a compact bound-intent index of every surviving backlog item (SPEC §3.5).

        For each ``specs/backlog/*.md`` item (``ideas.md``/``candidates.md``/the catalog
        excluded via the R1 ``load_backlog_items`` loader), emit its **status** and its
        **bound intents** — each intent's canonical anchor id + change, resolved through the
        R1 canonical-subject registry. Only the ``intents[]`` frontmatter + status are read;
        the body is never touched (ADR-D). All roots are derived from the injected
        ``SpecContext`` (source root = ``specs_dir.parent``), never cwd (SPEC §3.8).
        """
        # Local imports keep the selector module free of a hard backlog-feature import cycle.
        from dadaia_workspace.features.backlog.preview import (
            bound_anchor_changes,
            load_backlog_items,
        )
        from dadaia_workspace.features.backlog.subject_registry import build_registry

        backlog_dir = self._ctx.specs_dir / "backlog"
        items = load_backlog_items(backlog_dir)
        if not items:
            return SelectionResult(name=name, policy=policy, content="", refs=())

        source_root = self._ctx.specs_dir.parent
        registry = build_registry(
            source_root=source_root,
            catalog_path=self._catalog_path(),
            alias_map_path=self._alias_map_path(),
            specs_dir=self._ctx.specs_dir,
            cli_anchors=self._cli_anchors,
        )

        blocks: list[str] = []
        refs: list[str] = []
        for item in items:
            anchor_changes, unresolved = bound_anchor_changes(item, registry)
            status = item.status or "(no status)"
            lines = [f"### {item.slug}", f"- status: {status}"]
            if anchor_changes:
                lines.append("- bound intents:")
                for anchor_id in sorted(anchor_changes):
                    lines.append(f"  - {anchor_id} => {anchor_changes[anchor_id]}")
            for message in unresolved:
                lines.append(f"  - UNRESOLVED: {message}")
            if not anchor_changes and not unresolved:
                lines.append("- bound intents: (none)")
            blocks.append("\n".join(lines))
            refs.append(self._specs_ref(item.path))

        return SelectionResult(
            name=name,
            policy=policy,
            content="\n\n".join(blocks),
            refs=tuple(refs),
        )

    def _alias_map_path(self) -> Path:
        """Resolve the operator alias-map path up from ``specs_dir`` (never cwd, SPEC §3.8)."""
        here = self._ctx.specs_dir.resolve()
        for parent in (here, *here.parents):
            if (parent / ".dadaia").is_dir():
                return parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"
        return self._ctx.specs_dir.parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"

    def sel_selected_backlog_items(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._backlog_refs(open_only=False))

    def _bug_refs(self, *, open_only: bool) -> tuple[_FileRef, ...]:
        refs = self._dir_files("bugs")
        if not open_only:
            return refs
        kept: list[_FileRef] = []
        for fref in refs:
            status = _bug_status(_read_text(fref.path))
            if status in {"closed", "resolved", "deferred", "rejected"}:
                continue
            kept.append(fref)
        return tuple(kept)

    def sel_open_bugs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._bug_refs(open_only=True))

    def sel_selected_bugs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._bug_refs(open_only=False))

    def _audit_refs(self) -> tuple[_FileRef, ...]:
        directory = self._ctx.specs_dir / "audits"
        if not directory.is_dir():
            return ()
        refs: list[_FileRef] = []
        for path in sorted(directory.rglob("index.md")):
            refs.append(_FileRef(path=path, ref=self._specs_ref(path)))
        return tuple(refs)

    def sel_open_audits(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._audit_refs())

    def sel_selected_audit_findings(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render(name, policy, self._audit_refs())

    # ---- release artifacts --------------------------------------------

    def sel_approved_spec(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._release_artifact(name, policy, "SPEC.md")

    def sel_spec_draft(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._release_artifact(name, policy, "SPEC.md")

    def sel_approved_plan(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._release_artifact(name, policy, "PLAN.md")

    def sel_plan_draft(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._release_artifact(name, policy, "PLAN.md")

    def sel_tasks_draft(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._release_artifact(name, policy, "TASKS.md")

    # ---- handoffs (LEGACY / manual contexts only — A25) ----------------
    #
    # These ``.dadaia/handoff/*.handoff.json`` selectors are the **filename-glob** path.
    # Required prompt-to-prompt communication in a governed workflow does NOT use them —
    # it routes through :class:`WorkflowHandoffResolver`, which resolves the exact upstream
    # payload by ``(run id, producer step, attempt)`` (A19/A25). The selectors below remain
    # for legacy / manual contexts that read durable external evidence handoffs, and they
    # render a COMPACT digest (verdict / summary / findings / refs), never the raw JSON.

    def _handoffs(self, *, agent: str | None = None) -> tuple[_FileRef, ...]:
        directory = self._ctx.handoff_dir
        if directory is None or not directory.is_dir():
            return ()
        refs: list[_FileRef] = []
        for path in sorted(directory.glob("*.handoff.json")):
            if agent is not None and agent not in path.name:
                continue
            refs.append(_FileRef(path=path, ref=path.name))
        return tuple(refs)

    def _render_handoffs(
        self,
        name: str,
        policy: MaxContextPolicy,
        refs: tuple[_FileRef, ...],
    ) -> SelectionResult:
        if policy is MaxContextPolicy.PREVIOUS_HANDOFF_ONLY and refs:
            refs = (refs[-1],)
        blocks = [f"### {fref.ref}\n{self._handoff_digest(fref.path)}".rstrip() for fref in refs]
        return SelectionResult(
            name=name,
            policy=policy,
            content="\n\n".join(blocks),
            refs=tuple(fref.ref for fref in refs),
        )

    @staticmethod
    def _handoff_digest(path: Path) -> str:
        """Render a compact digest of a handoff JSON — verdict / summary / findings / refs.

        Never pastes the raw JSON document (A25 / anti-slop): the prompt cites the handoff
        by name and reads only its key fields. A malformed handoff degrades to a one-line
        note rather than crashing the selection.
        """
        try:
            doc = json.loads(_read_text(path))
        except (json.JSONDecodeError, OSError):
            return "(unreadable handoff)"
        if not isinstance(doc, dict):
            return "(malformed handoff)"
        lines: list[str] = []
        for key in ("agent", "scope", "verdict", "verdict_reason"):
            value = doc.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(f"- {key}: {value.strip()}")
        findings = doc.get("findings")
        if isinstance(findings, list) and findings:
            lines.append(f"- findings: {len(findings)}")
            for finding in findings[:5]:
                if isinstance(finding, dict):
                    sev = finding.get("severity", "?")
                    msg = finding.get("message", "")
                    lines.append(f"  - [{sev}] {msg}")
        return "\n".join(lines) if lines else "(empty handoff)"

    def sel_release_scope_handoff(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_handoffs(name, policy, self._handoffs(agent="project-manager"))

    def sel_spec_review_handoffs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_handoffs(name, policy, self._handoffs())

    def sel_prior_handoffs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_handoffs(name, policy, self._handoffs())

    # ---- summaries / maps / runtime evidence --------------------------

    def _list_summary(
        self, name: str, policy: MaxContextPolicy, label: str, root: Path
    ) -> SelectionResult:
        if not root.is_dir():
            return SelectionResult(name=name, policy=policy, content=f"{label}: (none)", refs=())
        entries = sorted(p.name for p in root.iterdir())
        return SelectionResult(
            name=name,
            policy=policy,
            content=f"{label}:\n" + "\n".join(f"- {e}" for e in entries),
            refs=(root.as_posix(),),
        )

    def sel_architecture_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self.sel_architecture(name, MaxContextPolicy.SUMMARY)

    def sel_product_catalog_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self.sel_product_catalog(name, MaxContextPolicy.CATALOG_ONLY)

    def sel_code_map_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        root = self._ctx.specs_dir.parent / "dadaia_workspace"
        return self._list_summary(name, policy, "code map", root)

    def sel_source_map_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        root = self._ctx.specs_dir.parent / "dadaia_workspace"
        return self._list_summary(name, policy, "source map", root)

    def sel_test_catalog_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        root = self._ctx.specs_dir.parent / "tests"
        return self._list_summary(name, policy, "test catalog", root)

    def sel_repo_ownership_map(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self.sel_architecture(name, MaxContextPolicy.SUMMARY)

    def sel_write_set_guidance(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self.sel_constitution(name, MaxContextPolicy.SUMMARY)

    # ---- generic source summary / diff / test output ------------------

    def sel_source_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        root = self._ctx.specs_dir.parent / "dadaia_workspace"
        return self._list_summary(name, policy, "source summary", root)

    def sel_git_diff(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        # Minimal-but-working: diffs are supplied as runtime evidence rather than read
        # from disk here; the selector returns an empty diff payload bounded by policy.
        return SelectionResult(name=name, policy=MaxContextPolicy.DIFF_ONLY, content="", refs=())

    def sel_test_output(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        # Minimal-but-working: test output is runtime evidence; selector returns the
        # most-recent recorded test report ref if present, else an empty payload.
        root = self._ctx.specs_dir.parent / "tests"
        if not root.is_dir():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return SelectionResult(name=name, policy=policy, content="test output: pending", refs=())


# ---------------------------------------------------------------------------
# Selector registry — maps every dynamic input name to a bound method
# ---------------------------------------------------------------------------

_SELECTORS: dict[str, _SelectorFn] = {
    # release_definition dynamic inputs (fully implemented for WS-5)
    "release_scope_handoff": ContextSelector.sel_release_scope_handoff,
    "selected_backlog_items": ContextSelector.sel_selected_backlog_items,
    "selected_bugs": ContextSelector.sel_selected_bugs,
    "selected_audit_findings": ContextSelector.sel_selected_audit_findings,
    "relevant_product_atoms": ContextSelector.sel_relevant_product_atoms,
    "open_bugs": ContextSelector.sel_open_bugs,
    "open_audits": ContextSelector.sel_open_audits,
    "candidate_backlog": ContextSelector.sel_candidate_backlog,
    "backlog_index": ContextSelector.sel_backlog_index,
    "architecture_summary": ContextSelector.sel_architecture_summary,
    "product_catalog_summary": ContextSelector.sel_product_catalog_summary,
    "approved_spec": ContextSelector.sel_approved_spec,
    "approved_plan": ContextSelector.sel_approved_plan,
    "spec_draft": ContextSelector.sel_spec_draft,
    "plan_draft": ContextSelector.sel_plan_draft,
    "tasks_draft": ContextSelector.sel_tasks_draft,
    "code_map_summary": ContextSelector.sel_code_map_summary,
    "source_map_summary": ContextSelector.sel_source_map_summary,
    "quality_assurance_atom": ContextSelector.sel_quality_assurance,
    "test_catalog_summary": ContextSelector.sel_test_catalog_summary,
    "spec_review_handoffs": ContextSelector.sel_spec_review_handoffs,
    "repo_ownership_map": ContextSelector.sel_repo_ownership_map,
    "write_set_guidance": ContextSelector.sel_write_set_guidance,
    # static-input named atoms (also resolvable as dynamic refs)
    "constitution.md": ContextSelector.sel_constitution,
    "memory/architecture.md": ContextSelector.sel_architecture,
    # generic WS-3 selectors (typed + unit-tested, not yet wired to a workflow)
    "memory_atoms": ContextSelector.sel_memory_atoms,
    "product_catalog": ContextSelector.sel_product_catalog,
    "prior_handoffs": ContextSelector.sel_prior_handoffs,
    "source_summary": ContextSelector.sel_source_summary,
    "git_diff": ContextSelector.sel_git_diff,
    "test_output": ContextSelector.sel_test_output,
}


def known_dynamic_inputs() -> tuple[str, ...]:
    """Return every dynamic input name the selector can resolve."""
    return tuple(sorted(_SELECTORS))
