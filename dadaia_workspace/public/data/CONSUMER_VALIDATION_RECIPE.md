# Consumer Validation Recipe — dadaia-workspace

**Contract.** This is the canonical end-to-end validation matrix a consumer-side
validation agent runs against EVERY candidate version, before deploy. It ships with
the package so recipe and product version never drift. The verdict is exactly one of
**APROVADA / BLOQUEADA / APROVADA COM EXCEÇÃO EXPLÍCITA**, with persisted evidence
(command, exit code, output) per feature statement. A green internal gate (`certify`
included) is never, by itself, validation. Every failure becomes a `dadaia bugs
append` report (redacted) — a failed statement is a product bug, not a local quirk.

Run everything from the workspace root, with the workspace venv binaries
(`.dadaia/.venv/bin/dadaia`). Statements marked **[destructive]** run in a throwaway
copy or a dedicated test context, never against production contexts.

## F-01 — Install & identity
The candidate wheel installs cleanly; `dadaia capabilities` reports schema
`dadaia-capabilities-v1` and `provider.distribution_version` == the candidate version;
`dadaia --version`/help render without traceback.

## F-02 — Reconcile (exact-version convergence)
`dadaia reconcile --expect-version <v>` exits 0 on this real, long-lived workspace:
steps provider-version → state-schema-v2 → legacy-dir-quarantine → public-stage →
public-install → public-doctor → workspace-doctor → capability-canary all `[ok]`.
Legacy `.dadaia/bugs`/`.dadaia/src` (if present) end up under
`.dadaia/tmp/legacy-quarantine/<run>/` with `manifest.json` — moved, never deleted.
Version mismatch (`--expect-version 9.9.9`) fails cleanly with rollback guidance,
no state corruption.

## F-03 — Certification battery
`dadaia certify` all PASS — and its verdict must AGREE with F-02 (a certify-green /
reconcile-red divergence is itself a HIGH bug).

## F-04 — Doctors
`dadaia doctor`, `dadaia specs doctor`, `dadaia public doctor` each: exit 0 on a
healthy tree; non-zero with actionable, specific messages on a seeded violation
**[destructive]** (e.g. stray root file → ROOT-1; unknown `.dadaia` dir → ROOT-4;
hand-edited projection → drift). No false positives on the canonical layout.

## F-05 — Projections (public assets)
`dadaia public stage` + `dadaia public install --target all` project byte-identical
assets to `.claude/`, `.codex/`, `.agents/`, `.pi/`; manifest tracks them; plain
`install` propagates a source edit (hash mismatch) without `--force`; `public doctor`
flags `[drift]`/`[missing]` correctly and exits non-zero on drift.

## F-06 — Context lifecycle **[destructive: use a test context]**
`context create` → `list`/`show --json` (DEAD) → `alive` (clone/scaffold) →
`bind` → `dead` → `delete`. Each transition idempotent where promised, each guard
(dead-requires-alive, duplicate create, unknown names) fails with a clear message.

## F-07 — Bind & session identity
Unbound `context show --json` answers `{"context": null}` exit 0 — no traceback.
Two `bind`s in one session print the SAME session id (harness-native or
`DADAIA_SESSION_ID`) and keep ONE record in `.dadaia/sessions/`; `--mode
implementation|review` requires `--release`; `--print-env` emits eval-safe exports;
`show --json` after bind reflects context/mode/release ("session" block).

## F-08 — SDD gate & chokepoints
File-tool write to `specs/bugs|backlog|audits/` always flows (ADDITIVE); write to
`specs/_archive/` blocks (FROZEN); `.dadaia/sessions/` blocks (PROTECTED);
`specs/memory/` blocks outside DEFINITION/CLOSURE (MEMORY); a new non-whitelisted
root entry blocks (root-whitelist); a system `pip`/`dadaia` invocation is corrected
to the venv (venv-guard). Git: commit with a foreign live presence WARNS but ALLOWS
(NO-LOCKS); push without a sha-matching security APPROVE handoff is REJECTED; push
with it passes.

## F-09 — Bugs ledger
`bugs append --event reported` validates schema (missing field ⇒ non-zero, nothing
written) and lands in the ACTIVE context's `specs/bugs/bugs.jsonl` (`--context`
overrides); `resolved` requires `--resolution-evidence`; `bugs status`/`stats`
aggregate correctly.

## F-10 — Backlog governance
Backlog doctor blocks a commit of an item missing bound `intents[]` or with an
unresolvable subject ref; a well-formed item commits.

## F-11 — Lifecycle workflows (the 4 verbs) **[destructive: test context]**
`dadaia lifecycle backlog-definition | release-definition | implementation-reviews |
audit` each: assembles fragment+persona prompts, advances only through its Python
gates, writes step handoffs under the release folder, BLOCKs on a REJECTED review,
resumes with `--resume-from`, and COMPLETEs leaving the promised artifacts on disk
(gates verify disk, not prose).

## F-12 — Reports & handoffs
A generated handoff validates with `dadaia reports validate <file>` (schema
handoff-v1); a tampered `content_hash` fails validation.

## F-13 — Panel
`dadaia panel` serves HTTP 200 on a registered port (server registry entry created
and released); tabs render Workflows/contexts/reports/handoffs from real state; no
JS console errors on load.

## F-14 — Server registry
`dadaia server register/list` round-trips; a second registration of a taken port is
refused with guidance.

## F-15 — Memory & injection
`dadaia memory` verbs read the bound context's atoms; after `context bind`, the next
session turn receives the context memory injection exactly once (bind-epoch), and an
unbound fresh session receives generic preflight only.

## F-16 — Portability **[destructive: throwaway dir]**
`dadaia export` → `dadaia import` round-trips a workspace (contexts, states, specs)
byte-faithfully; `dadaia clean` reclaims only what it names beforehand.

## F-17 — Migrations
`dadaia migrate` helpers upgrade a seeded older tree (specs pattern, bugs JSONL,
state v2) losslessly; `specs doctor` green after; re-run is a no-op.

## F-18 — Init/onboarding **[destructive: empty dir]**
`dadaia init` bootstraps a valid workspace from nothing (root law satisfied, venv,
projections, doctors green).

## F-19 — Plugins
`dadaia plugin install <pack>` records the ledger and replaces stub agents with real
bodies; doctor stays green; uninstalled packs keep stubs that refuse work with the
`[PLUGIN REQUIRED]` message.

## F-20 — Academy
`dadaia academy` verbs create/read the agent's study area without touching governed
paths.

## F-21 — CI preflight
`dadaia ci preflight` runs format/lint/type/tests and blocks on any failure; exit
codes are truthful (no masked pipes).

## F-22 — Help & docs quality (UX gate)
Every top-level verb: `--help` states purpose, args, and at least one usage line;
error messages on misuse name the fix (no raw tracebacks anywhere in the matrix);
README/AGENTS.md instructions reproduce as written.

## F-23 — Harness canaries
Projected assets load in each installed harness (Claude/Codex/PI): rules corpus
readable, hooks fire (PreToolUse gate blocks a seeded violation), ctx-inject
delivers memory after bind.

---
**Discipline:** persist per-statement evidence; register every failure as a bug
before the run ends; the final verdict message stays SHORT (Telegram-sized): version,
verdict, counts (statements pass/fail), bug ids, evidence path.
