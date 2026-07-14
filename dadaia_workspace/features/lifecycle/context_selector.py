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
none raise ``NotImplementedError``. Git-diff and test-output evidence are resolved
through optional injected providers (``diff_provider`` / ``test_output_provider``,
see :class:`ContextSelector.__init__`) rather than read from disk here — this module
stays subprocess-free (``features-no-subprocess`` import-linter contract); the real
git-backed provider lives in ``infrastructure/git_evidence.py`` and is wired by
``container.py``.

Every selector additionally applies bounded-corpus discipline (release review R-01..R-07,
v0.2.x prompt-scoping pass): open/live items only (never archived or closed), a hard cap
on how many full-text items a batch selector renders (the remainder degrades to a
one-line pointer, never silently dropped from the audit ref trail), and a per-step
selector-identity dedupe in :meth:`ContextSelector.select_all` so two fragment-vocabulary
names that resolve the same underlying selector (e.g. ``task_group`` and
``declared_write_set``, both backed by :meth:`ContextSelector.sel_tasks_draft`) inject
their content once per step, not once per name.

Max-context policies bound what a selector returns:

| policy | bound |
|---|---|
| ``exact-files-only`` | full file content of the resolved refs (still item-capped) |
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
    """Locates the active context's specs tree, release dir, and handoff dir.

    ``phase`` (v0.1.57 FR2) is the active ``ACTIVE.md`` lifecycle phase, resolved and threaded
    by the container builders (the READ stays in the features/container layer — this core-facing
    model stays IO-free). Additive-optional: ``None`` when there is no active release or the
    ``ACTIVE.md`` is absent/malformed (fail-open). A selector or fragment may declare an optional
    phase gate against it; no fragment declares one this release, so it is inert-until-declared.
    """

    specs_dir: Path
    release_id: str
    handoff_dir: Path | None = None
    phase: str | None = None

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
    """Return a backlog item's status, YAML frontmatter first, legacy bold-field fallback.

    Current backlog items carry YAML frontmatter (``status: candidate`` /
    ``status: superseded`` / ...); older fixtures and a handful of legacy docs still use
    the bold-Markdown ``**Status:** ...`` field with no frontmatter block. Checking YAML
    first, then falling back to the legacy field, keeps both formats correctly classified
    by :meth:`ContextSelector._backlog_refs` (review finding R-01: an item whose real
    status is ``deferred``/``superseded`` must not read as "open" merely because it uses
    the newer frontmatter format the old regex never looked at).
    """
    match = _YAML_FRONTMATTER_RE.match(text)
    if match:
        for line in match.group(1).splitlines():
            if line.strip().lower().startswith("status:"):
                return line.split(":", 1)[1].strip().lower()
    for field_match in _MD_FIELD_RE.finditer(text):
        if field_match.group("key").strip().lower() == "status":
            return field_match.group("value").strip().lower()
    return ""


def _is_archived(path: Path) -> bool:
    """True when *path* sits under a ``_archive`` directory anywhere in its parts.

    Review finding R-03: ``rglob`` over ``backlog/``, ``bugs/``, and ``audits/`` must
    never include their ``_archive/`` subtrees — archived items are historical record,
    not live corpus, and dumping them wastes the prompt budget on content nobody asked
    the step to reason over.
    """
    return "_archive" in path.parts


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FileRef:
    """A resolved file with a stable, host-independent ref identifier."""

    path: Path
    ref: str


# Batch-selector bounds (review R-01/R-02/R-06/R-07). Kept as named module constants
# rather than magic numbers so the cap is a single, greppable, deliberately-changed
# decision.
_ITEM_CAP = 8
"""Max full-text items a capped batch selector (backlog/bugs/audits) renders before
degrading the remainder to one-line pointers."""

_RELEVANT_ATOM_CAP = 5
"""Max memory atoms :meth:`ContextSelector.sel_relevant_product_atoms` renders in full."""

_RECENT_HANDOFF_CAP = 3
"""Max historical handoffs :meth:`ContextSelector._render_handoffs` renders (chronological,
most-recent-first) outside the ``previous-handoff-only`` single-handoff policy."""

_SOURCE_TREE_MAX_DEPTH = 2
"""Directory-recursion depth bound for :meth:`ContextSelector.sel_source_summary`."""

_SOURCE_TREE_MAX_ENTRIES = 100
"""Entry-count bound for :meth:`ContextSelector.sel_source_summary`."""


class ContextSelector:
    """Resolve named dynamic inputs into bounded, auditable content."""

    def __init__(
        self,
        context: SpecContext,
        *,
        cli_anchors: frozenset[str] = frozenset(),
        diff_provider: Callable[[], str] | None = None,
        test_output_provider: Callable[[], str] | None = None,
    ) -> None:
        self._ctx = context
        # Pre-derived cli-kind anchor set, threaded in from the composition boundary
        # (FR1b) — only :meth:`sel_backlog_index` uses it (to build the subject registry);
        # this feature never imports ``cli.main``. Empty when the selector never resolves
        # ``backlog_index`` (the default).
        self._cli_anchors = cli_anchors
        # Runtime-evidence providers (review R-04), additive-optional: a zero-arg callable
        # returning real diff / test-output text, injected by the composition root
        # (``container.py``, e.g. ``infrastructure.git_evidence.build_git_diff_provider``).
        # ``None`` (the default) keeps this feature module subprocess-free — unwired
        # selectors return an explicit "not wired" note rather than a silent empty string.
        self._diff_provider = diff_provider
        self._test_output_provider = test_output_provider
        # Per-step selector-identity dedupe state for :meth:`select_all` (review R-05).
        # ``_step_selector_seen`` maps a step label to {underlying selector function ->
        # the first dynamic-input name that resolved it for that step}; a later name in
        # the SAME step batch that resolves the SAME function gets a one-line pointer
        # instead of a second full copy. ``_last_select_all_step`` lets a fresh batch for
        # a step whose bucket already exists (e.g. a retried step, reached again only
        # after at least one *other* step's batch ran in between — the pipeline never
        # interleaves two batches for the same step without an intervening step) start
        # clean rather than inheriting a stale, already-exhausted bucket.
        self._step_selector_seen: dict[str, dict[_SelectorFn, str]] = {}
        self._last_select_all_step: str | None = None

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
        input_policies: dict[str, MaxContextPolicy | str] | None = None,
    ) -> SelectionAudit:
        """Resolve an ordered set of inputs into an auditable batch (v0.1.57 FR3 per-input).

        Each input resolves at *policy* — the fragment-global ``max_context_policy`` — unless
        it is named in *input_policies*, whose per-name override wins for that input only
        (``input_policies`` maps an input name → its own :class:`MaxContextPolicy`). An input
        absent from the map falls back to *policy*. ``input_policies=None`` (the default) is
        byte-identical to the pre-FR3 behaviour — every input resolves at the fragment-global
        policy — so a fragment declaring no ``input_policies`` is unchanged.

        Selector-identity dedupe (review R-05): two dynamic-input *names* can map to the
        very same underlying selector method (e.g. ``task_group`` and ``declared_write_set``
        both resolve :meth:`sel_tasks_draft`). A prompt assembled from a step's main
        fragment plus its shared fragments calls this method once per fragment but with the
        SAME *step* label each time (see ``pipeline._select_context`` /
        ``_fragment_gate._select_context``), so the first name to resolve a given selector
        for *step* renders in full; a later name in a later call for the SAME step that
        resolves the SAME selector renders as a one-line pointer instead of injecting the
        identical content again. The bucket resets whenever *step* differs from the step of
        the immediately-preceding call, so a step reached again later (a retry, always
        preceded by at least one other step's own batch — implementation/QA/security/code
        review never repeats a step back-to-back) gets a clean slate rather than an
        already-exhausted one.
        """
        resolved = MaxContextPolicy.parse(policy) if isinstance(policy, str) else policy
        overrides = {
            name: (MaxContextPolicy.parse(value) if isinstance(value, str) else value)
            for name, value in (input_policies or {}).items()
        }
        if step != self._last_select_all_step:
            self._step_selector_seen[step] = {}
            self._last_select_all_step = step
        seen_for_step = self._step_selector_seen.setdefault(step, {})

        results: list[SelectionResult] = []
        for name in names:
            selector_fn = _SELECTORS.get(name)
            if selector_fn is None:
                valid = ", ".join(sorted(_SELECTORS))
                raise UnknownDynamicInputError(
                    f"no selector registered for dynamic input '{name}'; known inputs: {valid}"
                )
            name_policy = overrides.get(name, resolved)
            first_name = seen_for_step.get(selector_fn)
            if first_name is None:
                seen_for_step[selector_fn] = name
                results.append(selector_fn(self, name, name_policy))
            elif first_name == name:
                # Exact-name repeat within one call (pre-existing, unchanged behaviour):
                # resolve again rather than pointer — a caller that literally lists the
                # same name twice gets it twice, same as before this fix.
                results.append(selector_fn(self, name, name_policy))
            else:
                results.append(
                    SelectionResult(
                        name=name,
                        policy=name_policy,
                        content=(
                            f"(same content as '{first_name}' above — not re-injected; "
                            f"'{name}' and '{first_name}' resolve the same underlying "
                            "selector for this step)"
                        ),
                        refs=(),
                    )
                )
        return SelectionAudit(step=step, results=tuple(results), fragment_ids=fragment_ids)

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

    def _one_line_summary(self, fref: _FileRef) -> str:
        """A single-line frontmatter/first-paragraph summary, used by pointer overflow."""
        text = _read_text(fref.path)
        summary = _frontmatter_summary(text, max_lines=3)
        first_line = summary.splitlines()[0] if summary else ""
        return first_line[:160]

    def _render_capped(
        self,
        name: str,
        policy: MaxContextPolicy,
        refs: tuple[_FileRef, ...],
        *,
        cap: int = _ITEM_CAP,
    ) -> SelectionResult:
        """Render *refs* under *policy*, capping full-text items at *cap* (review R-01).

        The first *cap* refs render exactly as :meth:`_render` would (full text under
        ``exact-files-only``, frontmatter summary under ``summary``, catalog line under
        ``catalog-only``). Beyond the cap, the remaining refs degrade to a one-line
        pointer summary regardless of the requested *policy* — an ``exact-files-only``
        fragment declaration is never a licence for an unbounded corpus dump. Every ref
        (capped or not) is still listed in the result's ``refs`` — the audit trail stays
        complete even when the rendered content is bounded.
        """
        if len(refs) <= cap:
            return self._render(name, policy, refs)
        head, tail = refs[:cap], refs[cap:]
        rendered = self._render(name, policy, head)
        pointer_lines = [f"- {fref.ref}: {self._one_line_summary(fref)}" for fref in tail]
        pointer_block = (
            f"### (+{len(tail)} more, summary only — capped at {cap} full items)\n"
            + "\n".join(pointer_lines)
        )
        content = (
            f"{rendered.content}\n\n{pointer_block}".strip() if rendered.content else pointer_block
        )
        return SelectionResult(
            name=name,
            policy=policy,
            content=content,
            refs=tuple(fref.ref for fref in refs),
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
            if _is_archived(path):
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

    def _relevance_corpus(self) -> str:
        """Lowercased text corpus describing what the active release is about.

        Never rendered to the model — used only to keyword-rank memory atoms by
        relevance (review R-02). Sourced from whatever release-definition evidence
        already exists: the release-scope handoff, open backlog items, open bugs, and
        any release artifacts (SPEC/PLAN/TASKS) already on disk. All of these are the
        exact material the picked-scope steps (``spec_create`` and downstream) already
        reason over, so this adds no new corpus the step could not already see.
        """
        parts: list[str] = []
        for fref in self._handoffs(agent="project-manager"):
            parts.append(self._handoff_digest(fref.path))
        for fref in self._backlog_refs(open_only=True):
            parts.append(_read_text(fref.path))
        for fref in self._bug_refs(open_only=True):
            parts.append(_read_text(fref.path))
        for filename in ("SPEC.md", "PLAN.md", "TASKS.md"):
            path = self._ctx.release_dir / filename
            if path.is_file():
                parts.append(_read_text(path))
        return "\n".join(parts).lower()

    @staticmethod
    def _rank_atoms_by_relevance(
        corpus: str, features: list[dict[str, object]]
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        """Split *features* into ``(matched, rest)`` by keyword hits against *corpus*.

        A feature matches when its slug or any declared tag's text appears in the
        corpus. ``matched`` is capped at :data:`_RELEVANT_ATOM_CAP`, ordered by hit
        count (descending) then original catalog order; ``rest`` is every remaining
        feature, in original catalog order.
        """
        scored: list[tuple[int, int, dict[str, object]]] = []
        for index, feature in enumerate(features):
            slug = str(feature.get("slug", ""))
            tags_value = feature.get("tags", [])
            tags = tags_value if isinstance(tags_value, list) else []
            keywords = {slug.lower()} | {str(tag).lower() for tag in tags if str(tag).strip()}
            score = sum(corpus.count(keyword) for keyword in keywords if keyword)
            scored.append((score, index, feature))
        scored.sort(key=lambda item: (-item[0], item[1]))
        matched = [feature for score, _, feature in scored if score > 0][:_RELEVANT_ATOM_CAP]
        matched_slugs = {str(feature.get("slug", "")) for feature in matched}
        rest = [
            feature for feature in features if str(feature.get("slug", "")) not in matched_slugs
        ]
        return matched, rest

    def _feature_refs(self, features: list[dict[str, object]]) -> tuple[_FileRef, ...]:
        refs: list[_FileRef] = []
        for feature in features:
            path_value = feature.get("path")
            if isinstance(path_value, str):
                path = self._ctx.specs_dir.parent / path_value
            else:
                # Catalog entries conventionally live at memory/product/<slug>.md;
                # a feature with no explicit path derives it from its slug.
                slug = str(feature.get("slug", "")).strip()
                if not slug:
                    continue
                path = self._ctx.specs_dir / "memory" / "product" / f"{slug}.md"
            if path.is_file():
                refs.append(_FileRef(path=path, ref=self._specs_ref(path)))
        return tuple(refs)

    def sel_relevant_product_atoms(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        """Select memory atoms relevant to the active release, capped at N=5 full atoms.

        Review R-02: the naive version dumped every atom under ``memory/product`` in
        full regardless of relevance. Relevance is a keyword match between each
        catalog feature's slug/tags and :meth:`_relevance_corpus` (the release-scope
        handoff, open backlog/bug items, and any existing SPEC/PLAN/TASKS). Matched
        atoms render in full, bounded by *policy* exactly like any other file-backed
        selector; every other catalog entry renders as a one-line ``slug: tldr``
        pointer so the step still knows the feature exists without paying its
        full-body cost. When nothing matches yet (no evidence names a feature — e.g.
        the very first release-definition step), this falls back to the catalog's own
        rank order so the step still gets concrete atoms rather than nothing. Falls
        back further to every atom on disk (pre-fix behaviour) only when there is no
        catalog to rank against at all.
        """
        features = self._catalog_features()
        if not features:
            return self._render(name, policy, self._dir_files("memory/product"))
        corpus = self._relevance_corpus()
        matched, rest = self._rank_atoms_by_relevance(corpus, features)
        if not matched:
            matched, rest = features[:_RELEVANT_ATOM_CAP], features[_RELEVANT_ATOM_CAP:]
        rendered = self._render(name, policy, self._feature_refs(matched))
        pointer_lines = [
            f"- {feature.get('slug', '')}: {feature.get('tldr', '')}".rstrip() for feature in rest
        ]
        if not pointer_lines:
            return rendered
        pointer_block = "### other catalog atoms (tldr only — not injected in full)\n" + "\n".join(
            pointer_lines
        )
        content = (
            f"{rendered.content}\n\n{pointer_block}".strip() if rendered.content else pointer_block
        )
        return SelectionResult(name=name, policy=policy, content=content, refs=rendered.refs)

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
        # NOT DEAD (v0.1.57 FR3 / A4). ``sel_constitution`` has no *direct* fragment
        # ``dynamic_inputs`` consumer, but is reached two ways at runtime, so it stays
        # registered and must never be pruned as unused:
        #   1. INDIRECT chain — ``write_set_guidance`` (declared by
        #      ``release_definition.tasks_create``) → :meth:`sel_write_set_guidance` →
        #      :meth:`sel_constitution`.
        #   2. DIRECT static-input — ``spec_create`` declares ``specs/constitution.md`` in its
        #      fragment ``static_inputs``, resolved via :meth:`resolve_static_input`.
        # The FR3 decision KEEPS it registered + both paths canonical; no removal, no new
        # consumer, and constitution is deliberately NOT added to the FR2 role→atom baseline.
        path = self._ctx.specs_dir / "constitution.md"
        if not path.is_file():
            return SelectionResult(name=name, policy=policy, content="", refs=())
        return self._render(name, policy, (_FileRef(path=path, ref=self._specs_ref(path)),))

    # ---- backlog / bugs / audits --------------------------------------

    _CLOSED_BACKLOG_STATUSES = frozenset(
        {"deferred", "rejected", "closed", "done", "shipped", "superseded"}
    )

    def _backlog_refs(self, *, open_only: bool) -> tuple[_FileRef, ...]:
        refs = self._dir_files("backlog")
        if not open_only:
            return refs
        kept: list[_FileRef] = []
        for fref in refs:
            status = _backlog_status(_read_text(fref.path))
            if status in self._CLOSED_BACKLOG_STATUSES:
                continue
            kept.append(fref)
        return tuple(kept)

    def sel_candidate_backlog(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_capped(name, policy, self._backlog_refs(open_only=True))

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
        """Open backlog items only, capped (review R-01).

        Previously ``open_only=False`` dumped every backlog item ever filed — live and
        archived alike — in full text (26 files at review time; ``_archive/`` alone
        accounted for 24 of them, see R-03). A release's scope handoff has already
        picked the exact items in play; until that pick is threaded through as an
        explicit relevance hint, "every currently-open (non-archived, non-closed) item,
        item-capped" is the honest, bounded default — never the full historical
        corpus regardless of the fragment's declared ``max_context_policy``.
        """
        return self._render_capped(name, policy, self._backlog_refs(open_only=True))

    _CLOSED_BUG_STATUSES = frozenset({"closed", "resolved", "deferred", "rejected", "superseded"})

    def _bug_refs(self, *, open_only: bool) -> tuple[_FileRef, ...]:
        refs = self._dir_files("bugs")
        if not open_only:
            return refs
        kept: list[_FileRef] = []
        for fref in refs:
            status = _bug_status(_read_text(fref.path))
            if status in self._CLOSED_BUG_STATUSES:
                continue
            kept.append(fref)
        return tuple(kept)

    def sel_open_bugs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_capped(name, policy, self._bug_refs(open_only=True))

    def sel_selected_bugs(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        # Same open-only + capped discipline as sel_selected_backlog_items (R-01,
        # applied by symmetry — the identical open_only=False defect shape).
        return self._render_capped(name, policy, self._bug_refs(open_only=True))

    def _audit_refs(self) -> tuple[_FileRef, ...]:
        directory = self._ctx.specs_dir / "audits"
        if not directory.is_dir():
            return ()
        refs: list[_FileRef] = []
        for path in sorted(directory.rglob("index.md")):
            if _is_archived(path):
                continue
            refs.append(_FileRef(path=path, ref=self._specs_ref(path)))
        return tuple(refs)

    def sel_open_audits(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_capped(name, policy, self._audit_refs())

    def sel_selected_audit_findings(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        return self._render_capped(name, policy, self._audit_refs())

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
        """Render handoff digests, capped to the most recent ones (review R-06).

        ``_handoffs`` returns matches sorted by filename, which is date-prefixed, so
        chronological order — ``refs[-1]`` is the most recent. ``previous-handoff-only``
        already bounds to exactly that one; every other policy is now bounded to the
        most recent :data:`_RECENT_HANDOFF_CAP` instead of the full historical ledger
        (previously ALL matching handoffs rendered, unbounded, for any other policy).
        """
        if policy is MaxContextPolicy.PREVIOUS_HANDOFF_ONLY and refs:
            refs = (refs[-1],)
        elif len(refs) > _RECENT_HANDOFF_CAP:
            refs = refs[-_RECENT_HANDOFF_CAP:]
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

    _TREE_SKIP_NAMES = frozenset(
        {
            "__pycache__",
            ".git",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".import_linter_cache",
        }
    )

    def _bounded_file_tree(
        self,
        root: Path,
        *,
        max_depth: int = _SOURCE_TREE_MAX_DEPTH,
        max_entries: int = _SOURCE_TREE_MAX_ENTRIES,
    ) -> list[str]:
        """Depth- and entry-bounded file tree under *root* (review R-07).

        Walks up to *max_depth* directory levels (the immediate children of *root* are
        depth 1), skipping dunder/cache directories and dotfiles, and stops collecting
        once *max_entries* have been recorded — the remainder is summarized with a
        single overflow line rather than continuing unbounded. This replaces a bare
        single-level ``root.iterdir()`` name dump with an actually-informative,
        still-cheap tree.
        """
        if not root.is_dir():
            return []
        entries: list[str] = []
        overflow = 0

        def walk(dir_path: Path, depth: int, prefix: str) -> None:
            nonlocal overflow
            try:
                children = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except OSError:
                return
            for child in children:
                if child.name in self._TREE_SKIP_NAMES or child.name.startswith("."):
                    continue
                if len(entries) >= max_entries:
                    overflow += 1
                    continue
                entries.append(f"{prefix}{child.name}{'/' if child.is_dir() else ''}")
                if child.is_dir() and depth < max_depth:
                    walk(child, depth + 1, prefix + "  ")

        walk(root, 1, "")
        if overflow:
            entries.append(f"... ({overflow} more entries not shown, capped at {max_entries})")
        return entries

    def _changed_paths_from_diff(self) -> list[str]:
        """Extract the ``Changed files:`` block's paths from the wired diff provider.

        Returns ``[]`` when no provider is wired, the provider raises, or its output
        does not carry the ``- <path>`` leading-block shape
        (:func:`dadaia_workspace.infrastructure.git_evidence.git_diff_text` produces
        it; an arbitrary custom provider that doesn't is simply not usable for this,
        and :meth:`sel_source_summary` falls back to the bounded file tree).
        """
        if self._diff_provider is None:
            return []
        try:
            diff_text = self._diff_provider()
        except Exception:  # noqa: BLE001 — evidence is best-effort, never fatal
            return []
        paths: list[str] = []
        for line in diff_text.splitlines():
            if line.startswith("- "):
                paths.append(line[2:].strip())
            elif paths:
                # The leading "- path" block ends at the first non-matching line.
                break
        return paths

    def sel_source_summary(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        """A bounded source overview — changed-paths-focused when diff evidence is
        wired, else a depth<=2, entry-capped file tree (review R-07).

        Previously a bare single-level ``ls`` of ``dadaia_workspace/`` (the package's
        top-level dirs only — not informative and not depth-bounded by design, just
        incidentally shallow). When a ``diff_provider`` is wired (see
        :meth:`ContextSelector.__init__`), the step almost always cares about what
        changed, not the whole tree, so this prefers the diff's changed-files list;
        it falls back to the bounded tree when no diff evidence is wired or the
        working tree has no changes.
        """
        root = self._ctx.specs_dir.parent / "dadaia_workspace"
        changed = self._changed_paths_from_diff()
        if changed:
            content = "source summary (changed paths — diff evidence wired):\n" + "\n".join(
                f"- {path}" for path in changed
            )
            return SelectionResult(
                name=name, policy=policy, content=content, refs=(root.as_posix(),)
            )
        entries = self._bounded_file_tree(root)
        if not entries:
            return SelectionResult(
                name=name, policy=policy, content="source summary: (none)", refs=()
            )
        content = (
            f"source summary (depth<={_SOURCE_TREE_MAX_DEPTH}, capped at "
            f"{_SOURCE_TREE_MAX_ENTRIES} entries):\n" + "\n".join(f"- {entry}" for entry in entries)
        )
        return SelectionResult(name=name, policy=policy, content=content, refs=(root.as_posix(),))

    def sel_git_diff(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        """Real diff evidence when a ``diff_provider`` is wired (review R-04).

        See :meth:`ContextSelector.__init__`. Without a wired provider this returns an
        explicit "no diff evidence wired" note rather than a silent empty string, so a
        reviewer reading the assembled prompt can tell "evidence was never connected"
        apart from "there happen to be no changes" (the latter is the provider's own
        honest message — see
        :func:`dadaia_workspace.infrastructure.git_evidence.git_diff_text`). The result
        always carries ``DIFF_ONLY`` policy regardless of the requested *policy* — diff
        evidence is inherently diff-shaped, independent of the fragment's declared
        ``max_context_policy``.
        """
        if self._diff_provider is None:
            content = "no diff evidence wired: ContextSelector.diff_provider is not set"
        else:
            try:
                content = self._diff_provider() or "no diff evidence: provider returned no content"
            except Exception as exc:  # noqa: BLE001 — evidence is best-effort, never fatal
                content = f"no diff evidence: provider raised {exc.__class__.__name__}"
        return SelectionResult(
            name=name, policy=MaxContextPolicy.DIFF_ONLY, content=content, refs=()
        )

    def sel_test_output(self, name: str, policy: MaxContextPolicy) -> SelectionResult:
        """Real test-output evidence when a ``test_output_provider`` is wired (review R-04).

        Mirrors :meth:`sel_git_diff`. Without a wired provider this returns an
        explicit one-liner instead of the previous literal ``"test output: pending"``,
        which read as "forthcoming" rather than "never connected".
        """
        if self._test_output_provider is None:
            return SelectionResult(
                name=name,
                policy=policy,
                content="no test-output evidence wired: ContextSelector.test_output_provider is not set",
                refs=(),
            )
        try:
            content = (
                self._test_output_provider()
                or "no test-output evidence: provider returned no content"
            )
        except Exception as exc:  # noqa: BLE001 — evidence is best-effort, never fatal
            content = f"no test-output evidence: provider raised {exc.__class__.__name__}"
        return SelectionResult(name=name, policy=policy, content=content, refs=())


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
    # implementation_reviews vocabulary. These aliases deliberately reuse the
    # canonical release/diff/handoff selectors so fragment language does not create
    # a second data-access implementation.
    "task_group": ContextSelector.sel_tasks_draft,
    "declared_write_set": ContextSelector.sel_tasks_draft,
    "spec_criteria": ContextSelector.sel_approved_spec,
    "plan_slice": ContextSelector.sel_approved_plan,
    "plan_test_strategy": ContextSelector.sel_approved_plan,
    "relevant_source_files": ContextSelector.sel_source_summary,
    "change_diff": ContextSelector.sel_git_diff,
    "changed_paths": ContextSelector.sel_git_diff,
    "dependency_changes": ContextSelector.sel_git_diff,
    "test_evidence": ContextSelector.sel_test_output,
    "verification_commands": ContextSelector.sel_test_output,
    "implementation_result": ContextSelector.sel_prior_handoffs,
    "release_artifacts": ContextSelector.sel_prior_handoffs,
    "review_evidence": ContextSelector.sel_prior_handoffs,
    "current_memory": ContextSelector.sel_memory_atoms,
    # Shared-fragment vocabulary.
    "available_evidence": ContextSelector.sel_source_summary,
    "grill_subject": ContextSelector.sel_source_summary,
    "selected_memory_atoms": ContextSelector.sel_memory_atoms,
}


def known_dynamic_inputs() -> tuple[str, ...]:
    """Return every dynamic input name the selector can resolve."""
    return tuple(sorted(_SELECTORS))
