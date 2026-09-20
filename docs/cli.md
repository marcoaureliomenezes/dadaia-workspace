<!-- derived-from: dadaia help tree — regenerate: `dadaia help tree > docs/cli.md` -->

# dadaia CLI digest (v0.4.7 — derived from the live command tree; authoritative help: `dadaia <group> --help`)

## dadaia audit — Audit finding and archive commands.
- audit close — Archive one fully dispositioned audit: the histo record is appended LAST, then
- audit disposition — Rewrite one finding's disposition, release and reason, in place.

## dadaia backlog — Backlog entry management commands.
- backlog exit — Retire <slug> out of active[] and append its one backlog_histo record.
- backlog new — Append one ``active[]`` entry for <slug> to specs/backlog/BACKLOG.json.
- backlog subjects — List the live canonical-subject anchors, or resolve one proposed subject (read-only).

## dadaia capabilities — Describe public dadaia-workspace features supported by this installation.

## dadaia certify — Certify assembled public features in a disposable local workspace.

## dadaia ci — Local CI-equivalent preflight gate + git-hook chokepoints.
- ci install-hook — Install the pre-push CI/security gate.
- ci preflight — Run ruff + mypy --strict + pytest locally; exit non-zero if any fail.
- ci push-gate-check — Pre-push gate: branch-name validation + the range-scoped denylist scan.

## dadaia context — Manage Spec Context Projects.
- context alive — Transition a context to ALIVE; clone repo if absent. Idempotent if already ALIVE.
- context baseline — Create the explicit initial scaffold commit for an unborn repository.
- context bind — Bind this shell session to a context.
- context create — Create a new Spec Context Project in state 'dead'.
- context dead — Transition a context to DEAD; git sync + remove repo from disk.
- context delete — Delete a context. Context must be dead.
- context list — List all Spec Context Projects.
- context repo <add, list, remove> — Manage a context's associated repos (main repo excluded).
- context show — Show details of a context.
- context update — Repair a context's repo URL (FR-W2-03 c / T-011-08).

## dadaia doctor — Diagnose and repair workspace, specs and ledger compliance.

## dadaia export — Write `.dadaia/dist/spec-contexts.json` — one record per spec context.

## dadaia help — Derived help surfaces (docker-style; generated, never transcribed).
- help tree — Print the compact CLI digest derived from the live command tree.

## dadaia import — Register every context of a `dadaia export` file this workspace does not know as DEAD.

## dadaia init — Bootstrap a dadaia workspace: creates .dadaia/ and projects agent assets for the chosen harness set (default all: .agents/, .claude/, .codex/).

## dadaia memory — Memory catalog management commands.
- memory catalog <generate> — Catalog JSON generation commands.
- memory product <add> — Product memory catalog commands.

## dadaia migrate — Migration helpers for dadaia workspace and spec trees.

## dadaia public — Manage distributed public agent assets.
- public doctor — Diagnose drift between package source, staging, and runtime projections.
- public install — Install staged public assets into runtime projections.
- public stage — Stage packaged public assets into .dadaia/agentic/.

## dadaia reconcile — Reconcile state and projections after installing an exact candidate wheel.

## dadaia release — Release management commands.
- release archive — Ship the live release: one transactional promote verb (0.4.7 FR3).
- release fold — Fold a wrongly archived release into rc-N/ of the version that published it.
- release new — Create specs/releases/<id>/ with its SPEC.md stub and _RELEASE.json state.
- release phase — Move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone.
- release rc-archive — Archive the live release's completed candidate trio into the next rc-N/.

## dadaia reports — Validate agent handoff reports.
- reports validate — Validate one or more agent handoff JSON files.

## dadaia specs — SDD release-lifecycle structural checks and helpers.
- specs init — Bootstrap a SDD release-lifecycle specs/ directory structure.
- specs upgrade — Upgrade a specs/ tree to the canonical pattern version.
