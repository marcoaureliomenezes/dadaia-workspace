---
release: none
phase: none
---

# Active release: none

**v0.1.32** — *harden real-worker workflows (coherent worker-output contract + live review
path)* — is **CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.32/` (CLOSURE.md). The
Layer-2 worker-output contract is now coherent by design — one transport schema
(`schema: agent-run-result-v1`) in a single field, a step-kind-aware "Required output"
instruction across all THREE prompt surfaces (`build_fragment_suffix`,
`pipeline._generic_prompt`, CLI `_run_phase_step`), and single-sourced strict-primary
result extraction (structural fallback as defence-in-depth) shared by the pi and codex
adapters. The **review/verdict path is proven live**: a real `pi` (gpt-5.5, software-architect)
emitted `verdict: APPROVED`, accepted via the **STRICT** path. All tasks `[x]`;
code/security/qa reviews APPROVE; `specs doctor` 0 errors; `public doctor` `[ok]`.

Bug `lifecycle-prompt-names-two-schemas-confusing-real-workers` is Closed with evidence.
Follow-ups left Open: `subagent-handoff-resolves-dadaia-inside-repo-cwd` (MEDIUM — subagents
running with cwd=repo write `.dadaia/` into the repo) plus two minor code-review items noted
in the v0.1.32 CLOSURE (LOW: `output-handoff.md` table lacks an `artifact_refs` row; INFO:
pi vs codex `structured_output` flatten asymmetry).

**Stacked unpushed releases:** `feature/v0.1.32` → `feature/v0.1.31` → `feature/v0.1.30`,
all NOT pushed / NOT merged (operator: no push). Ship path when ready: re-stamp a
`security-reviewer` APPROVE on the final HEAD sha, push, watch CI until every job is green
(incl. the GH-only `e2e-panel` job), PR → squash-merge to `main` — sequencing the three
stacked releases (or rebasing them into one).

No release is currently active. Open the next release with `dadaia release new` when work is
picked.

Pre-existing drift (not in scope): `specs/releases/v0.1.23/` remains unarchived on `main`
(an `Aprovado` SPEC with no CLOSURE) — a future cleanup.
