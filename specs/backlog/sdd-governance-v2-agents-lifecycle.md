---
name: sdd-governance-v2-agents-lifecycle
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/gate_policy.py#classify_path" }
    change: "specs taxonomy: classify specs/backlog/_archive, specs/audits/_archive, specs/bugs/_archive as FROZEN for file-write tools (archive moves via git mv)"
  - subject: { kind: cli, ref: "bug new" }
    change: "event-sourced JSONL bug telemetry: add `dadaia bugs append|status|stats` over append-only specs/bugs/<ts>.jsonl with a shipped event schema + migration from *.md"
  - subject: { kind: catalog, ref: "sdd-bug-backlog-governance" }
    change: "audit-disposition law: first release after an audit dispositions every finding (fixed|superseded|deferred/rejected); archive to audits/_archive only when fully dispositioned"
---

# EPIC — SDD Governance v2 (residual): roster/taxonomy + JSONL bug-events + audit-disposition law

**ID:** FEAT-GOV-V2-01
**Reported:** 2026-06-12 (operator long-prompt + grill `fc45dd8c`).
**Owner:** project-manager (curates) → product-engineer (release definition after grill).
**Status:** PARTIALLY CONSUMED — v0.1.15 shipped the Codex deterministic lifecycle
foundation slice. Residual = the three governance-v2 pillars below.

> **Scope correction (2026-06-26):** OpenCode was removed entirely in v0.1.24 (both
> layers). All OpenCode-enforcement / OpenCode-projection-parity scope is **dead** and has
> been stripped from this entry. The Layer-1 harness set is `{claude, codex, pi}`.

---

## 1. Thesis (residual)

Three governance pillars remain open after v0.1.15:

1. a canonical **specs taxonomy** with archive flows + path-class gate changes for every
   artifact class (`specs/backlog/_archive/`, `specs/audits/_archive/`,
   `specs/bugs/_archive/` classified FROZEN; consumed-backlog and undisposed-audit doctor
   invariants);
2. append-only **event-sourced bug telemetry** (JSONL);
3. an **audit-disposition law** (disposition-complete, not solve-all).

The roster/lifecycle-ladder work this entry once carried has been overtaken by the
two-layer shift (v0.1.15 gate ladder + v0.1.24 Python lifecycle); only the taxonomy,
bug-events, and audit-disposition pillars are genuinely residual.

## 2. Bugs: event-sourced JSONL

- **Format:** `specs/bugs/<YYYYMMDDTHH>Z.jsonl`; append-only; rotate at 1000 rows.
- **Event schema** (shipped under `.dadaia/agentic/schemas/`): required `bug_id`, `event`
  (`reported|resolved|superseded|deferred|rejected|archived`), `ts`, `reported_by`.
  `reported` carries `title`, `severity`, `surface`, `component`, `context`, `tags[]`,
  `symptom`, `repro`, `expected`, `notes` (redacted); `resolved` carries `release`;
  `superseded` carries `superseded_by`; `deferred`/`rejected` carry `reason`.
- **CLI:** `dadaia bugs append | status | stats`. Doctor invariant: JSONL schema +
  rotation + event coherence (`resolved` with no prior `reported` = error).
- **Migration:** one-time converter for the existing `specs/bugs/*.md` files →
  `reported` (open) / full event history (closed) + `git mv` to `specs/bugs/_archive/`;
  shipped as a `dadaia specs upgrade` step for consumers.
- **Law:** rewrite the `bug-registration-guardrail` rule format section for JSONL events;
  registration stays ADDITIVE for every agent.

## 3. Specs taxonomy + archive gate classes

- Create `specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/`
  (workspace + scaffold + consumer-onboarding paths).
- Gate (`features/spec_context/gate_policy.py`): classify the three `_archive` dirs as
  **FROZEN** for file-write tools; archive moves happen via `git mv` outside the gate
  envelope.
- Backlog archive flow: CLOSURE moves a consumed backlog entry to `specs/backlog/_archive/`.
- Doctor: `_archive` dirs exist per class; consumed-but-unarchived backlog detection;
  audit-without-disposition detection (an archived audit must reference its disposing
  release).

## 4. Audit-disposition law

One audit report always generates a release; the first release after an audit must give
EVERY finding an explicit disposition (`fixed` | `superseded` | `deferred`/`rejected` with
reason → backlog). An audit archives to `specs/audits/_archive/` only when all findings are
dispositioned and the release is approved. Open bugs + open audits outrank plain backlog at
release-definition pick. `project-auditor` owns the bug-trend audit that gates bug archiving
(clusters recurring root causes from JSONL history).

## 5. Out of scope

- OpenCode enforcement / projection parity — **dead** (OpenCode removed v0.1.24).
- The alpha-N/rc-N ↔ gate-ladder change — shipped v0.1.15.
- Python lifecycle workflow bodies — owned by `lifecycle-prompt-fragments-ai-surface-dehydration`.
- Panel bug-analytics UI beyond minimal stats rendering.
