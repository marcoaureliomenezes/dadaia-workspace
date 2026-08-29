"""The v5 fold adapter — deletable at 0.6.0 (v0.5.0 FR2/A2.5, AR-1 ruling answer (a),
amended by the S1 FR23 firing, `specs/releases/0.5.0/reviews/S1-FR23-firing.md` A1/A2).

**``read_ledger`` is DELETED (A1).** It used to be the permanent
``features/bugs/service.py``'s ONLY read path — a second, independently-maintained
tolerant-JSON loop beside the injected
:class:`~dadaia_workspace.core.protocols.record_store.RecordStore`, reaching around the
store to its raw file. The live ledger has zero v5 lines (the migration this module's
own scope name promises physically ran at T-050-10); every permanent read now goes
through ``self._record_store.iter_records()`` directly. ``parse_ledger_lines`` (the
raw-text tolerant split this docstring used to describe as "still useful to a one-shot
migration runner") is DELETED at v0.5.1 K5 — it had zero callers, inside this module
or out (``run_migration`` never called it either); what survives here is the fold/
mining pieces below, reached only through :func:`build_migrated_record`/
:func:`run_migration`.

**``classify_ledger_line`` MOVED to ``core/bug_provenance.py`` and is PERMANENT there
(A2), not deletable with this module.** The first reading of A2.5 called it "deletable
with the migration module" — wrong: this repository's git history is v5-shaped for
hundreds of commits forever, and FR8's resolver
(``BugService.resolved_commit``)/FR14's pillar-1 audit both need to decode that history
permanently. Import it from :mod:`dadaia_workspace.core.bug_provenance` instead.

**Deliberately minimal — no git, no cause-mining (T-050-08 scope).**
``registration_commit``/``resolved_commit``/``registration_granularity``/
``resolution_granularity``/``cause``/``caused_by``/``lineage_source`` all stay ``None``
in the raw v5 fold: deriving them from git history (FR3, ``core/bug_provenance.py``) and
mining ``cause`` from free prose are :func:`build_migrated_record`'s job.

**T-050-09 extends this module with the pieces FR3 names as "the migration module"'s
own job (A2.5), never the pure derivation itself.**
:data:`LEGACY_SURFACE_MAP`/:func:`map_legacy_surface` are FR3 step 6d's "table in the
migration module"; :func:`run_migration` is the one-shot runner **scaffolding** that
composes a caller-supplied
:class:`~dadaia_workspace.core.protocols.git_history_reader.GitHistoryReader` with
:func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line` and
:func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance`. Every function in
this module consumes RAW ``dict``/``Mapping`` v5-event shapes, never
:class:`~dadaia_workspace.core.models.bugs.BugEvent` (deleted, S1 FR23 firing A3 — the
model has no writer left to justify it).

Deleted whole at 0.6.0, once no consumer needs the v5 fold at all — a contract test
(T-050-09, A3.10) asserts no PERMANENT module imports this one; its tests are marked
``Intent: SCAFFOLD — T-050-09 — expires: 0.6.0`` (qa-engineer amendment 10), distinct
from ``core/bug_provenance.py``'s own ``CONTRACT`` tests, which outlive this module.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import replace
from pathlib import Path

from dadaia_workspace.core.bug_provenance import (
    DerivedBugProvenance,
    classify_ledger_line,
    derive_commit_provenance,
)
from dadaia_workspace.core.models.bugs import (
    TERMINAL_EVENTS,
    BugEventKind,
    BugRecord,
)
from dadaia_workspace.core.protocols.git_history_reader import GitHistoryReader

__all__ = [
    "LEGACY_SURFACE_MAP",
    "build_bug_id_matcher",
    "build_migrated_record",
    "map_legacy_surface",
    "mine_cause",
    "mine_caused_by",
    "run_migration",
]

_LOG = logging.getLogger(__name__)


def _str_field(event: Mapping[str, object], key: str) -> str | None:
    """Best-effort ``str``-or-``None`` extraction from a raw v5 event dict."""
    value = event.get(key)
    return value if isinstance(value, str) else None


def _fold_v5_events(events: list[dict[str, object]]) -> dict[str, BugRecord]:
    """Fold a raw v5 event-dict stream into one :class:`BugRecord` per ``bug_id`` (see
    module docstring for the exact semantics carried over from the pre-T-050-08 fold).
    """
    records: dict[str, BugRecord] = {}
    for event in events:
        bug_id = _str_field(event, "bug_id")
        kind = _str_field(event, "event")
        if bug_id is None or kind is None:
            continue
        if kind == BugEventKind.REPORTED.value:
            records[bug_id] = BugRecord(
                id=bug_id,
                ts=_str_field(event, "ts") or "",
                reported_by=_str_field(event, "reported_by") or "",
                title=_str_field(event, "title") or "",
                severity=_str_field(event, "severity") or "",
                surface=_str_field(event, "surface") or "",
                component=_str_field(event, "component") or "",
                context=_str_field(event, "context") or "",
                symptom=_str_field(event, "symptom") or "",
                repro=_str_field(event, "repro") or "",
                expected=_str_field(event, "expected") or "",
                status="open",
            )
            continue
        if kind not in TERMINAL_EVENTS:
            continue  # `picked`/`archived`: contribute nothing to the record (FR2).
        current = records.get(bug_id)
        if current is None:
            # Terminal-without-reported is incoherent history (the doctor's own
            # SPEC-DOC-033 finding) — this adapter never synthesizes a phantom record
            # for it; there is nothing to fold onto.
            continue
        records[bug_id] = replace(
            current,
            status=kind,
            superseded_by=(
                _str_field(event, "superseded_by")
                if kind == BugEventKind.SUPERSEDED.value
                else None
            )
            or current.superseded_by,
            evidence_loop=_str_field(event, "evidence_loop") or current.evidence_loop,
            evidence_seam=_str_field(event, "evidence_seam") or current.evidence_seam,
            evidence_diff=_str_field(event, "evidence_diff") or current.evidence_diff,
        )
    return records


#: Legacy free-text ``surface``/``component`` values observed on a v5 ``reported``
#: event, mapped onto ``bug-record-v1.schema.json``'s closed ``surface`` enum (FR3 step
#: 6d, SA-Q5: "the enum derives from the feature-package list the independence contract
#: uses ... the forensic's normalizer becomes FR3's legacy mapping table"). **T-050-10
#: full pass** (2026-08-27, 496 bug ids / 405 distinct raw ``surface`` strings): every
#: row below is a literal, SINGLE-topic match reviewed by hand against the full
#: frequency list — a raw string naming two or more different systems (joined by
#: ``" / "``/``" vs "``/``" + "``), or naming ONLY the retired lifecycle/workflow-engine
#: subsystem (no current ``features/`` package owns it — see the module docstring's
#: A2.5/SPEC AS-14 cross-reference), is deliberately left UNMAPPED rather than guessed
#: (FR3 step 6: "nothing is guessed"); mapping the whole 496-record corpus this way
#: reaches 231/496 (46.6 %) mapped, 265/496 (53.4 %) ``unknown`` — recorded honestly in
#: the migration report per A3.11 rather than forced under the 10 % guideline by
#: fabricating a package for a demolished subsystem. One row per legacy string, exact
#: match, case-sensitive — no fuzzy/guessed mapping (FR3: "nothing is guessed and
#: nothing is dropped").
LEGACY_SURFACE_MAP: Mapping[str, str] = {
    "gate": "chokepoints",
    "dadaia certify": "certification",
    # public
    "dadaia public doctor": "public",
    "dadaia public install --target all": "public",
    "dadaia public install --target claude / dadaia public doctor": "public",
    "dadaia public install --target claude": "public",
    "dadaia public doctor / FileSystemPublicAssetManager.doctor": "public",
    "dadaia public doctor / public-privacy": "public",
    "dadaia public install --target kimi-code / dadaia public doctor": "public",
    "public install / law-file projection (Claude Code)": "public",
    "dadaia public install (codex target) — runtime_config.codex_config()": "public",
    "dadaia public doctor D-CX-9 / .codex/hooks.json generated command paths": "public",
    "install_helpers.install_codex_agents + runtime_transforms/codex.transform_for_codex + codex_doctor D-CX-4": "public",
    "codex_doctor.lint_legacy_software_engineer (T-35 lint)": "public",
    # public-assets
    "dadaia_workspace/public/data/dadaia-AGENTS.md (projected to .dadaia/AGENTS.md)": "public-assets",
    "dadaia-cli skill": "public-assets",
    "dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md": "public-assets",
    "AI-entity surface (agent skills: frontmatter)": "public-assets",
    "dadaia_workspace/public/agents/**, dadaia_workspace/public/skills/**": "public-assets",
    # spec_context
    "dadaia context bind": "spec_context",
    "dadaia context show --json": "spec_context",
    "dadaia context create": "spec_context",
    "dadaia context alive / dadaia context dead": "spec_context",
    "dadaia context show --json (and resolve_specs_dir_for_cli)": "spec_context",
    "cli/commands/context.py bind (FR-R4-02 harness-real mode path)": "spec_context",
    "dadaia context alive -> context baseline": "spec_context",
    "dadaia context bind — mandatory --mode option / bind ergonomics": "spec_context",
    "dadaia context bind / context show --json": "spec_context",
    "dadaia context create + spec_context dead": "spec_context",
    "dadaia context show": "spec_context",
    "context dead()": "spec_context",
    "context dead() push": "spec_context",
    "dadaia context delete + bind-resolved commands (bugs status)": "spec_context",
    "dadaia context heartbeat": "spec_context",
    "dadaia context heartbeat / context show --json": "spec_context",
    "dadaia context list / dadaia context list --json": "spec_context",
    "dadaia context list --json": "spec_context",
    "dadaia context release / context dead / PostToolUse heartbeat hook": "spec_context",
    "dadaia context repo add + spec_context dead": "spec_context",
    "dadaia context create/alive/dead (repo_url lifecycle)": "spec_context",
    "dadaia context dead (commit_all)": "spec_context",
    "dadaia context alive": "spec_context",
    "sdd-spec-gate.sh — CONTEXT_SLUG resolution + MUTATING lease acquire": "spec_context",
    "dadaia context bind (kimi-code runtime)": "spec_context",
    "context bind / lease.adopt_if_own_lineage / pre-gate lease acquire": "spec_context",
    "sdd-spec-gate.sh (single-session lease check) / context resolution": "spec_context",
    "features/spec_context/lease.py acquire() + hooks/sdd_gate.py (WS-R2 FR-R2-03 pid veto)": "spec_context",
    "hooks/sdd_gate.py + spec_context/gate_policy.py + spec_context/lease.py heartbeat model": "spec_context",
    "dadaia context alive/dead/create/update/delete/bind/release and pre-commit advisory": "spec_context",
    "dadaia context bind --mode spec": "spec_context",
    "dadaia context bind / preflight lease probe": "spec_context",
    "dadaia context release": "spec_context",
    "dadaia doctor": "spec_context",
    "dadaia doctor --fix": "spec_context",
    "dadaia doctor ROOT-1 / ROOT-3": "spec_context",
    "dadaia doctor ROOT-4 (_DADAIA_ALLOWED_SUBDIRS)": "spec_context",
    "dadaia doctor with a file:// bare remote": "spec_context",
    "dadaia doctor (ROOT-4 check)": "spec_context",
    # bugs
    "dadaia bugs append": "bugs",
    "bugs ledger": "bugs",
    "dadaia_workspace/core/models/bugs.py": "bugs",
    "dadaia bugs append --resolution-evidence / BugEvent.redact": "bugs",
    "dadaia bugs append (default specs-dir resolution)": "bugs",
    "dadaia bugs store (migrated events)": "bugs",
    "dadaia bugs append / specs/bugs layout": "bugs",
    "specs/bugs/bugs.jsonl": "bugs",
    "git tracking of specs/bugs/": "bugs",
    # specs
    "dadaia specs doctor": "specs",
    "memory catalog regeneration": "specs",
    "dadaia specs doctor SPEC-DOC-016/027": "specs",
    "dadaia specs release open / specs segment open -> specs doctor": "specs",
    "dadaia memory catalog generate (features/specs/catalog.py)": "specs",
    "specs doctor memory": "specs",
    "dadaia memory catalog generate (index.md renderer)": "specs",
    "dadaia specs upgrade (agent-tier-frontmatter migration)": "specs",
    "specs upgrade (migration steps)": "specs",
    "release CLOSURE protocol (dadaia-release-closure skill) + specs doctor": "specs",
    "dadaia release new (release-id validator) vs dadaia specs doctor (SPEC-DOC-027 naming canon)": "specs",
    "specs/releases/v0.4.4/reviews/S2-qa-close.md:44": "specs",
    "specs upgrade / specs doctor --fix / memory catalog generate / baseline / specs init --force": "specs",
    "specs doctor SPEC-DOC-029 (retired)": "specs",
    "dadaia specs doctor / context resolution": "specs",
    "dadaia specs doctor (features/specs/doctor.py + memory lint output)": "specs",
    "dadaia specs doctor (SPEC-DOC-016) + tests/e2e/test_lifecycle_engine_smoke.py": "specs",
    "cli/specs doctor context resolution": "specs",
    "dadaia specs doctor / memory atom authoring contract": "specs",
    "dadaia specs doctor (TREE-5M check message)": "specs",
    "dadaia specs init / dadaia specs doctor": "specs",
    "dadaia specs upgrade (post-migration doctor comparison)": "specs",
    "dadaia specs upgrade (agent-tier-frontmatter step)": "specs",
    "dadaia specs upgrade (cli/commands/specs.py upgrade())": "specs",
    "specs upgrade / specs doctor --fix": "specs",
    "projected lint-memory-atoms.py": "specs",
    # backlog
    "dadaia backlog doctor": "backlog",
    "pre-commit backlog doctor (BL-SCHEMA) / features.backlog.subject_registry": "backlog",
    "dadaia backlog doctor (CLI default --alias-map resolution) / features/backlog": "backlog",
    "dadaia backlog doctor (BL-SCHEMA)": "backlog",
    ".gitignore specs opt-ins / pre-commit backlog-doctor scope / CI backlog-doctor job": "backlog",
    "dadaia backlog new / projected specs/backlog/README.md / dadaia backlog doctor": "backlog",
    "sdd-spec-gate.sh (backlog-ownership branch) + dadaia backlog CLI": "backlog",
    "dadaia backlog subjects / backlog doctor fail-closed classifier": "backlog",
    "backlog README": "backlog",
    "pre-commit hook (backlog doctor / BL-SCHEMA gate)": "backlog",
    # certification ("dadaia certify" itself is the seed row above)
    "dadaia certify --json": "certification",
    "features/certification/service.py::_codex_environment_unavailable_reason + _codex_live_probe_detail": "certification",
    "dadaia certify --json (workflow-* checks)": "certification",
    "dadaia certify from an installed candidate wheel": "certification",
    # ci_preflight
    "test-suite/CI": "ci_preflight",
    "dadaia ci preflight / features/ci_preflight/service.py check argv": "ci_preflight",
    "dadaia ci preflight (features/ci_preflight/service.py)": "ci_preflight",
    "dadaia ci preflight (run from a consumer repo) and the projected pre-push-ci-gate.sh": "ci_preflight",
    "CI workflow": "ci_preflight",
    "test-suite/pre-push gate (dadaia ci preflight, full mode)": "ci_preflight",
    "ci-workflow": "ci_preflight",
    "CI (Unit fast, Contract coverage) windows-latest": "ci_preflight",
    "ci": "ci_preflight",
    "CI Unit fast (Windows/macOS) windows-latest": "ci_preflight",
    # chokepoints
    "test-suite/pre-push gate": "chokepoints",
    "features/chokepoints/service.py push_gate_decision denylist range scan (first push of feature/{M.m.p})": "chokepoints",
    "pre-push-ci-gate.sh (.git/hooks/pre-push runner detection)": "chokepoints",
    "pre-push-ci-gate.sh / ci.yml": "chokepoints",
    "pre-push chokepoint (push-range denylist scan) vs the packaged privacy baseline's email-address carve-out": "chokepoints",
    "dadaia_workspace/features/chokepoints/denylist_scan.py": "chokepoints",
    "pre-push chokepoint (push-range denylist scan) vs privacy-baseline positive fixtures": "chokepoints",
    "pre-push chokepoint: dadaia ci push-gate-check (range-scoped denylist scan, commit-body layer)": "chokepoints",
    # reconcile
    "dadaia reconcile": "reconcile",
    # reports
    "dadaia reports validate": "reports",
    "reports_validation (handoff-v1.1 schema + artifact path resolver)": "reports",
    "dadaia reports validate (features/reports_validation/service.py)": "reports",
    'dadaia reports validate (CLI) vs root AGENTS.md "Reports and Panel" contract': "reports",
    "handoff emission / .dadaia root resolution when cwd is inside a repo": "reports",
    # tests
    "tests/integration/test_repo_self_scan.py": "tests",
    "tests/unit/features/specs/test_migration_symlink_hardening.py": "tests",
    "tests/contract/test_rules_skills_map.py::test_every_cited_path_exists on CI": "tests",
    "tests/contract/test_rules_skills_map.py mutation fixtures 9/10/11 on windows-latest": "tests",
    "tests/integration/features/certification/test_codex_live_probe_live.py + features/certification/service.py::_codex_live_probe_detail": "tests",
    "tests/unit/features/certification/test_service_codex_live_probe.py": "tests",
    "tests/e2e/panel/workflow-policy-harness-toggle.spec.ts (GHA e2e-panel leg)": "tests",
    "tests/contract/test_frozen_clock_aging_ratchet.py": "tests",
    "tests/integration/scripts/test_run_mutation_baseline_wiring.py": "tests",
    "tests/ (contract coverage)": "tests",
    "tests/e2e/features/test_opencode_parity_hardening.py": "tests",
    "tests/performance/test_lifecycle_hygiene_scan.py": "tests",
    "tests/integration/cli/test_lifecycle_pipeline_cli.py::test_pipeline_runs_first_step_on_pi_harness_end_to_end (and any executed-path test following the same monkeypatch pattern for pi/codex)": "tests",
    "tests/integration/cli/test_lifecycle_pipeline_cli.py (PiHeadlessAdapter executed-path tests)": "tests",
    "tests/unit/hooks/test_post_gate_reconciler.py::test_throttle_skip_and_expiry, ::test_dirty_mutating_emits_flag_advisory_only": "tests",
    "tests/scripts/check_skill_orphans.py": "tests",
    "tests/integration/test_repo_self_scan.py (push-range denylist self-scan)": "tests",
    "tests/unit/features/lifecycle/test_retention_sweep.py (D5 retention sweep)": "tests",
    "tests/contract/test_public_source_hygiene.py (full-suite run) + public/scripts/*.py bytecode guard": "tests",
    "pytest full repository collection": "tests",
    "pytest suite / ci_preflight real-mypy test": "tests",
    "tests/integration/test_repo_self_scan.py::test_no_hit_outside_the_shrink_only_baseline": "tests",
    "tests/integration/test_public_assets.py": "tests",
    "tests/e2e/features/test_public_pipeline.py": "tests",
    "tests/unit/features/tmp_gc/test_tmp_gc_service.py": "tests",
    "tests/contract/cli/test_cli_context.py + tests/unit/hooks/test_sdd_post_gate.py (v0.1.10 in-progress working tree)": "tests",
    "full pytest projection and architecture contracts": "tests",
    "pytest suite": "tests",
    # hooks
    "runtime_config.claude_settings / hooks.ctx_inject": "hooks",
    "hooks.pre_gate / hooks._common emit_allow+emit_block": "hooks",
    ".codex/hooks.json command execution on Codex VPS/VS Code surface": "hooks",
    "hooks/ctx_inject.py context resolution (UserPromptSubmit/SessionStart injection)": "hooks",
    "hooks/ctx_inject (UserPromptSubmit/SessionStart context-memory injection)": "hooks",
    "dadaia-kimi-post-compact.sh stdout": "hooks",
    "dadaia-kimi-post-compact.sh stdout after bind without prior prompt": "hooks",
    "kimi pre-gate shim": "hooks",
    "Codex hook wrappers, Claude hook commands, and PI hook subprocesses": "hooks",
    "hooks._common emit_allow / pre_gate PreToolUse stdout": "hooks",
    "PreToolUse pre_gate (merged)": "hooks",
    "pre_gate root-whitelist block reason": "hooks",
    "hooks.root_whitelist (PreToolUse root-whitelist policy)": "hooks",
    "SDD artifact post-write linter (editing specs/releases/<id>/{SPEC,PLAN,TASKS}.md via file tools)": "hooks",
    "dadaia_workspace/hooks/_common.py target_path() (SDD gate path classification on Codex)": "hooks",
    "PreToolUse SDD gate (dadaia_workspace.hooks.pre_gate -> sdd_gate -> gate_policy)": "hooks",
    "dadaia_workspace.hooks.sdd_gate (lease identity + heartbeat renewal)": "hooks",
    "sdd-spec-gate.sh (FPATH classification)": "hooks",
    # infrastructure
    "codex_runtime._structured_from_payload": "infrastructure",
    "runtime_transforms/codex.transform_for_codex + model_mapping.MODEL_MAP (persona-body model guidance)": "infrastructure",
    "infrastructure/runtime_config.py codex_hooks() PostToolUse matcher (+ ai-harness-codex skill claim)": "infrastructure",
    "dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py / .codex/agents/*.toml": "infrastructure",
    "codex_assets (generated .codex/rules/dadaia-command-policy.rules)": "infrastructure",
    "dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py / .codex/rules/dadaia-command-policy.rules": "infrastructure",
    "infrastructure/json_workflow_model_policy_store.py WorkflowModelPolicyOverlay.to_dict": "infrastructure",
    "infrastructure/pi_runtime.py PiHeadlessAdapter._command": "infrastructure",
    # telemetry
    "telemetry aggregator / codex liveness": "telemetry",
    # migrate
    "dadaia_workspace/features/migrate/frontmatter_keys.py": "migrate",
    # tmp_gc
    "tmp-file-guardrail": "tmp_gc",
    # panel
    "dadaia panel — Agents tab model picker": "panel",
    "features/panel/views/kanban.py + assets/js/kanban.js (GET /api/kanban)": "panel",
    "panel auth architecture (features/panel/{auth,handler}.py + views/assets/js/core.js)": "panel",
    "features/panel (index.py inline mermaid script + CSP) / tests/e2e/panel (ops-tab OPS-02) / ci preflight scope": "panel",
    "panel Projects tab memory feed (views/index.py chips, views/memory.py root, handler route classes)": "panel",
    "panel workflow model-governance editor (workflow_policy.py / workflow_model_policy overlay / policy_resolver)": "panel",
    # workspace
    "dadaia init from an unpublished wheel": "workspace",
    "dadaia init / features.workspace.service initialize": "workspace",
    "dadaia init --skip-assets": "workspace",
    "dadaia init / workspace venv bootstrap": "workspace",
    "dadaia init / doctor VENV-1 / infrastructure.python_env": "workspace",
    "workspace init and CLI exception reporting": "workspace",
    "dadaia init": "workspace",
    "workspace venv (.dadaia/.venv)": "workspace",
    # cli
    "cli": "cli",
    "dadaia CLI (plugin subcommand) vs plugin-scope rule": "cli",
}


def map_legacy_surface(
    raw_surface: str, canonical_surfaces: AbstractSet[str]
) -> tuple[str, str | None]:
    """Map one legacy free-text ``surface`` value onto the closed enum.

    *canonical_surfaces* is the caller-supplied enum member set (T-050-29 is the task
    that publishes the single Python-side source for it, per A2.12's "one source, two
    consumers" rule — this module does not hardcode a second, independently-maintained
    copy of that 30-member list; it takes the set as a parameter, exactly like
    :func:`derive_commit_provenance` takes its classifier). Returns
    ``(mapped_surface, original_if_unmapped)``: when *raw_surface* is already a
    canonical member, or :data:`LEGACY_SURFACE_MAP` maps it onto one, the pair is
    ``(surface, None)``; otherwise the pair is ``("unknown", raw_surface)`` — the
    original is preserved (never dropped) for the migration report's ``unknown`` list
    (FR3 step 6d, A3.11).
    """
    mapped = LEGACY_SURFACE_MAP.get(raw_surface, raw_surface)
    if mapped in canonical_surfaces:
        return mapped, None
    return "unknown", raw_surface


def run_migration(
    repo: Path,
    pathspec: str,
    history_reader: GitHistoryReader,
) -> dict[str, DerivedBugProvenance]:
    """The one-shot runner **scaffolding** (T-050-09) — composes an injected
    :class:`~dadaia_workspace.core.protocols.git_history_reader.GitHistoryReader` with
    :func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line` (permanent, S1
    FR23 firing A2) and
    :func:`~dadaia_workspace.core.bug_provenance.derive_commit_provenance` to derive
    every bug id's commit provenance from *repo*'s real history over *pathspec*.

    **Scaffolding, not the migration.** This function performs no ledger write, no
    report, no CLI wiring — T-050-10 is the task that runs the full FR3 migration
    (rewrites ``bugs.jsonl`` -> ``BUGS.jsonl``, writes the migration report, wires a CLI
    verb) and it is EXPECTED to call something shaped like this, but this task never
    invokes it against the real ``specs/bugs/`` history (per its own instructions) —
    only fixture tests, with a fake :class:`GitHistoryReader`, exercise it. No
    ``infrastructure``/``subprocess`` import here: *history_reader* arrives already
    constructed (``container.build_git_history_reader()`` in production), matching
    `features-no-infrastructure`/`features-no-subprocess` — this module never imports
    either directly, even for its own runner.
    """
    commits = history_reader.log_added_lines(repo, pathspec)
    return derive_commit_provenance(commits, classify_ledger_line)


#: FR3 step 6's cause-mining trigger — a case-insensitive ``cause`` substring, matched
#: with a leading word boundary so "be-CAUSE" never qualifies (there is no boundary
#: between "be" and "cause" inside that word) while "cause"/"caused"/"causing"/"root
#: cause" all do. Deliberately a SUBSTRING search, never a whole-word one: "root cause:"
#: and "caused by" both need to match and neither is the bare word "cause".
_CAUSE_MARKER_RE = re.compile(r"\bcause", re.IGNORECASE)

#: `evidence_diff`'s own schema pattern (``bug-record-v1.schema.json``) already
#: anchors one of these three tokens at the START of the string — `diff_direction`
#: (FR3 step 6d) is that SAME token, read out as its own closed-enum field rather than
#: re-parsed from `evidence_diff` by every consumer (FR14 metric 3).
_DIFF_DIRECTION_RE = re.compile(r"^(net-negative|net-neutral|net-positive):")


def mine_cause(events_for_id: Sequence[Mapping[str, object]]) -> str | None:
    """FR3 step 6: ``cause`` copied VERBATIM from the record's own v5 ``evidence_diff``
    or ``notes`` text — only where that text literally states one
    (:data:`_CAUSE_MARKER_RE`). Checked on the LAST terminal event in *events_for_id*
    only (the same event :func:`_fold_v5_events` reads ``status`` from) — a
    ``reported`` event's own ``notes`` is legacy narrative describing the bug ITSELF,
    not the fix's own statement of cause the schema's ``cause`` field documents.
    ``evidence_diff`` is checked first (concise, structured, FR23-restored), ``notes``
    second. Returns the verbatim source field, never a paraphrase — this makes A3.5's
    "zero records carry a cause string that is not literally present in the source
    record's text" hold by construction. ``None`` when there is no terminal event, or
    neither field mentions a cause — "nothing is guessed" (FR3 step 6).

    *events_for_id* carries raw v5 event dicts (S1 FR23 firing A3: ``BugEvent`` is
    deleted; :func:`parse_ledger_lines` already produces this shape).
    """
    terminal: Mapping[str, object] | None = None
    for event in events_for_id:
        if _str_field(event, "event") in TERMINAL_EVENTS:
            terminal = event  # last one wins — mirrors _fold_v5_events' status rule.
    if terminal is None:
        return None
    for candidate in (_str_field(terminal, "evidence_diff"), _str_field(terminal, "notes")):
        if candidate and _CAUSE_MARKER_RE.search(candidate):
            return candidate
    return None


def build_bug_id_matcher(bug_ids: AbstractSet[str]) -> re.Pattern[str]:
    """One compiled alternation over every *bug_ids* member, longest-first (so a short
    id can never shadow-match inside a longer one that starts the same way) and
    hyphen/alnum-bounded on both sides (so a match can only be a WHOLE id token, never
    a partial hit inside a longer hyphenated string). Built once per migration run and
    reused across every record — :func:`mine_caused_by`'s own O(ids) argument.
    """
    ordered = sorted(bug_ids, key=len, reverse=True)
    alternation = "|".join(re.escape(bug_id) for bug_id in ordered)
    return re.compile(rf"(?<![A-Za-z0-9-])(?:{alternation})(?![A-Za-z0-9-])")


#: Every free-text field a raw v5 event dict carries that could name another bug id
#: in prose (title/symptom/repro/expected describe the bug itself; notes/evidence*/
#: reason are where a fixer's cross-reference — a ``[[wikilink]]`` or a bare mention —
#: actually shows up in this corpus, per the T-050-10 forensic scan).
_CAUSED_BY_TEXT_FIELDS: tuple[str, ...] = (
    "title",
    "symptom",
    "repro",
    "expected",
    "notes",
    "evidence",
    "evidence_loop",
    "evidence_seam",
    "evidence_diff",
    "reason",
)


def mine_caused_by(
    bug_id: str, events_for_id: Sequence[Mapping[str, object]], matcher: re.Pattern[str]
) -> str | None:
    """FR3 step 6: ``caused_by`` populated ONLY where the record's OWN text — every
    field in :data:`_CAUSED_BY_TEXT_FIELDS` on EVERY one of its own events, reported
    and terminal alike — literally names ONE other bug id already present in the
    ledger. A ``[[wikilink]]`` and a bare mention both qualify through the SAME
    whole-token match (*matcher*, :func:`build_bug_id_matcher`) — FR3 step 6 requires
    only that the text "names another existing bug id", never a causation verb next to
    it (that is exactly why every populated value carries ``lineage_source:
    "text-reference"`` — the caller marks it inferred, not asserted). Returns ``None``
    (never a guess) when zero, or MORE THAN ONE, distinct other id is named in *this*
    record's own text — an ambiguous multi-reference is not resolved by picking one
    (AS-2/A3.5: every populated value is unambiguous or absent, never invented).

    *events_for_id* carries raw v5 event dicts (S1 FR23 firing A3).
    """
    found: set[str] = set()
    for event in events_for_id:
        for field_name in _CAUSED_BY_TEXT_FIELDS:
            value = _str_field(event, field_name)
            if not value:
                continue
            found.update(m for m in matcher.findall(value) if m != bug_id)
    if len(found) == 1:
        return next(iter(found))
    return None


def build_migrated_record(
    folded: BugRecord,
    events_for_id: Sequence[Mapping[str, object]],
    provenance: DerivedBugProvenance | None,
    canonical_surfaces: AbstractSet[str],
    matcher: re.Pattern[str],
) -> tuple[BugRecord, str | None]:
    """Compose ONE fully-migrated v6 :class:`BugRecord` (FR3 step 6/6d) — the function
    T-050-10's runner calls once per bug id.

    *folded* is the v5-event fold :func:`_fold_v5_events` already produces for this id
    (immutable core + ``status`` + the FR23 evidence triple carried onto the record's
    own write-once fields — that half needs no re-derivation here). *events_for_id* is
    this id's raw v5 events in file order (:func:`parse_ledger_lines`), the free-text
    source :func:`mine_cause`/:func:`mine_caused_by` read (``notes``/``reason`` have no
    field on :class:`BugRecord`, so the fold alone cannot supply them). *provenance* is
    this id's :class:`~dadaia_workspace.core.bug_provenance.DerivedBugProvenance`, or
    ``None`` when the walked git history never adds a line for it (not expected on this
    corpus — defensive only, matches FR3 step 5's ``migration_note`` case).
    *canonical_surfaces*/*matcher*: see :func:`map_legacy_surface`/
    :func:`build_bug_id_matcher`.

    Returns ``(record, unknown_original_surface)`` — the second element is the RAW
    ``surface`` string when :func:`map_legacy_surface` returned ``unknown`` for it
    (for the caller's migration-report ``unknown`` list, A3.11), else ``None``.
    """
    mapped_surface, original_surface = map_legacy_surface(folded.surface, canonical_surfaces)
    component = folded.component
    if original_surface is not None:
        # FR3 step 6d: "the original preserved in component" — never destroying the
        # component free text that is already there (its own, independently useful
        # `path#symbol` precision), only ever ADDING the raw surface value to it.
        if not component:
            component = original_surface
        elif original_surface not in component:
            component = f"{original_surface} | {component}"

    cause = mine_cause(events_for_id)
    caused_by = mine_caused_by(folded.id, events_for_id, matcher)
    lineage_source = "text-reference" if caused_by is not None else None

    diff_direction: str | None = None
    if folded.evidence_diff:
        match = _DIFF_DIRECTION_RE.match(folded.evidence_diff)
        if match:
            diff_direction = match.group(1)

    record = replace(
        folded,
        surface=mapped_surface,
        component=component,
        cause=cause,
        caused_by=caused_by,
        lineage_source=lineage_source,
        diff_direction=diff_direction,
        registration_commit=provenance.registration_commit if provenance else None,
        registration_granularity=provenance.registration_granularity if provenance else None,
        resolved_commit=provenance.resolved_commit if provenance else None,
        resolution_granularity=provenance.resolution_granularity if provenance else None,
        migration_note=provenance.migration_note if provenance else None,
    )
    return record, original_surface
