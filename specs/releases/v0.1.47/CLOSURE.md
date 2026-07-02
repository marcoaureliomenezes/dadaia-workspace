# CLOSURE — v0.1.47 — Context-Surface Truth + Fragments/Personas Optimization + Audit Remediation

**Branch:** `feature/v0.1.47` · **Base:** `f88f73d1` (v0.1.46 closure)
**Origin:** operator `/goal` directive 2026-07-01 + full audit
`specs/audits/_archive/20260701T201136Z-0bcd6c19/` (overall 7/10) + the v0.1.47
disposition sweep earmarked by the previous ACTIVE.md.
**Consumes:** `specs-truth-realignment-constitution-memory` (fully delivered by W2/W3;
archived copy + ledger sidecar written at close per ADR-C).

## Shipped (by wave; conventional commits on the feature branch)

- **W0 definition** (`d4ff84b8`) — GRILL (QA REJECT→fix→APPROVE) + SPEC/PLAN/TASKS
  `Aprovado`; `.gitignore` now tracks the bug JSONL store + `_archive` and
  GRILL/OQ-DECISIONS (the entire event store entered version control for the first
  time); backlog sanitized pre-branch (8 delivered items archived, 4 dead anchors fixed
  — commits were blocked before this).
- **W1a** (`a6b2cbab`) — codex exec revived (dead `--ask-for-approval` dropped +
  actionable flag-contract error); inert codex config keys removed; pre-commit backlog
  gate scoped to staged backlog paths; `tests/performance` out of the blocking
  preflight; `setup.cfg` import-linter comment truth.
- **W1b** (`caceac0a`) — persona injection on ALL verbs (shared
  `resolve_persona_for_role`, threaded through the 5 workflow bodies + CLI step path +
  pipeline); ctx-inject markers pid-attributed; root-whitelist first-path-component;
  `specs_resolver` persisted-bind fallback; SPEC-DOC-037 (constitution must not
  enumerate the runtime roster) + SPEC-DOC-038 (loose undisposed audits) + `.dadaia/hooks`
  allowed; SPEC-DOC-031 message reconciled with BL-SCHEMA; FAKE-closure smoke =
  intended-contract (not reproducible).
- **W2** (`7e2c2bee`) — constitution lean rewrite 685→224 lines (principle+rationale;
  roster single-sourced to `[[tech-stack]]`; §8 collapsed to invariants; Governance §15
  with constitution semver; no pinned tunables; article numbering preserved);
  `public/data/AGENTS.md` truth fixes (reports-validate = handoff JSON; Workflows tab;
  harness-preference convention); 8 rules swept clean; sanctioned one-time
  `repos/dadaia-workspace/AGENTS.md` sync; e2e live-tree 037 filter removed (guard live).
- **W5** (`2fa24cff` + `e7211ba9` events) — full disposition sweep: bug ledger
  **27 → 0 open** (18 resolved-in/by-this-release, 2 superseded dup pairs, 7
  deferred-with-named-backlog-entry, 1 rejected with 3-run repro evidence); 99 hollow
  migrated events backfilled from `_archive` sources; **15 loose audits archived** each
  with `DISPOSITION.md` naming its disposing release; 10 deferral backlog entries
  landed (backlog doctor clean; fail-closed BL-CONFLICT forced precise code anchors).
- **W4** (`ba2e8a3e`, `e7211ba9`) — fragments + personas de-slopped (targeted: contract
  not enforcement; stale READMEs deleted; closure README trued; ai-engineer reserve
  note; verdict-token alignment; JSONL-era bug-write; conflict_scan no-persona note);
  `dadaia-handoff-emitter` Step-0 workspace-root resolution; projection reinstalled
  (public doctor exit 0, clearing the pre-existing drift); independent content
  sign-off: **APPROVE, 0 MAJOR** (evidence: 8 real prompt-assembly envelope dumps).
- **W1c** (`8424e5b2`) — ancestry-chain bind attribution (marker = nearest-first pid
  chain, cap 8; membership matching in ctx-inject + resolver; live-proven cross-shell);
  `dadaia_catalog` role prose trued to post-D-1 step roles.
- **W3** (`fd956ea5`) — memory canon re-trued end-to-end; `architecture.md` 1028→~290
  lines (13k→4.7k tokens) de-narrated with mechanism extracted to owning atoms; NEW
  `memory/product/harness/{claude-code,codex,pi}.md` (capability · scaffold · isolation
  per harness) and `product/sdd/dadaia-workflows.md` (7 defined / 4 invocable, honest);
  JSONL bug-store atom; catalog + index regenerated (31 features).

## Validations (final, this tree)

- pytest full (minus the CI-only performance dir): **4361 passed, 17 skipped (opt-in live/Windows/LAN), 1 transitional failure = the live-tree SPEC-DOC-024 e2e assertion during DEFINITION→CLOSURE flip, green after the flip (re-run evidence below)**
- ruff format --check: 749 files clean · ruff check: clean · mypy --strict: 0 issues
  (298 files)
- specs doctor: 0 errors after the CLOSURE flip (during DEFINITION the sole error was
  the expected SPEC-DOC-024 phase-vs-markers state); warnings: TREE-5 (sanctioned
  manual sync), 2× SPEC-DOC-027 legacy archive names, 3× SPEC-DOC-031 candidates
  (ADR-6 false-positive class — PM-curated), transient SPEC-DOC-029 leases (GC'd)
- backlog doctor: clean · lifecycle workflow doctor: ok · lint-memory-atoms: 34 atoms
  0/0 · public doctor: exit 0 · dadaia doctor: fixed (ROOT-2 stray cache deleted,
  stale leases/pointers GC'd)
- Acceptance greps: constitution opencode=0, runtime-enum tokens=0; memory
  bearer/token-gated/loopback_bypass = 0/0/0; no CI-enforcement claim for
  import-linter anywhere; 4 backlog code anchors + all catalog/cli anchors RESOLVED.
- Reviews: QA spec checkpoint (REJECT→APPROVE), independent W4 content sign-off
  (APPROVE), security push-gate handoff keyed to the final sha (see push evidence).

## Drifts / residuals (tracked, not dropped)

- 10 named backlog entries own every deferred audit finding (SPEC §W5 list).
- `ProcessAncestry` port exposes no public ppid-walk; the chain builder reaches the
  adapter's `_ppid_of` via a guarded `getattr` (degrades to single-pid) — follow-up
  candidate for `lease-kernel-identity-hardening` or `hygiene-and-dead-code-cleanup`.
- SPEC-DOC-031 trio (`sdd-governance-v2…`, `panel-ux-overhaul`,
  `features-import-…-debt`) left `candidate` deliberately: partially consumed epics,
  PM curation decision.
- Instance-root strays outside the repo (`.git/` empty dir, stray `specs/releases/`
  tree at the WORKSPACE root) flagged to the operator; not auto-deleted (operator
  exception rule).

## Memory updates

All touched atoms stamped `last_updated: 2026-07-01`, `release_origin: v0.1.47` by W3;
catalog/index regenerated last. CLOSURE-phase edits: ACTIVE.md phase flip + this file;
archive move of `specs/releases/v0.1.47/` happens in the closure commit after merge
(v0.1.46 pattern).
