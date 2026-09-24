<!-- derived-from: dadaia help tree — regenerate: `dadaia help tree > docs/cli.md` -->

# dadaia CLI digest (derived from the live command tree; authoritative help: `dadaia <group> --help`)

## dadaia capabilities — Describe public dadaia-workspace features supported by this installation.

## dadaia certify — Certify assembled public features in a disposable local workspace.

## dadaia ci — Local CI-equivalent preflight gate + git-hook chokepoints.
- ci install-hook — Install the pre-push CI/security gate.
- ci preflight — Run the five local CI checks; exit non-zero if any fail.
- ci push-gate-check — Pre-push gate: branch-name validation + the range-scoped denylist scan.

## dadaia context — Manage Spec Context Projects.
- context alive — Transition a context to ALIVE; clone repo if absent. Idempotent if already ALIVE.
- context baseline — Create the explicit initial scaffold commit for an unborn repository.
- context bind — Bind this shell session to a context.
- context create — Clone (or adopt) every repo, install the pre-push hook, make the context ALIVE and
- context dead — Transition a context to DEAD; git sync + remove repo from disk.
- context delete — Delete a context. Context must be dead.
- context list — List all Spec Context Projects.
- context repo <add, remove> — Manage a context's associated repos (main repo excluded).
- context show — Show details of a context.

## dadaia doctor — Diagnose and repair workspace, specs and ledger compliance.

## dadaia export — Write `.dadaia/dist/spec-contexts.json` — one record per spec context.

## dadaia harness — Register and inspect the workspace's agent runtimes (harnesses).
- harness add — Register a harness and project its runtime set into this workspace.
- harness list — Show the harnesses registered in this workspace's profile.

## dadaia help — Derived help surfaces (docker-style; generated, never transcribed).
- help tree — Print the compact CLI digest derived from the live command tree.

## dadaia import — Register every context of a `dadaia export` file this workspace does not know as DEAD.

## dadaia init — Bootstrap a dadaia workspace in DIR for one harness: .dadaia/, the law, and that harness's projection.

## dadaia migrate — Migration helpers for dadaia workspace and spec trees.

## dadaia public — Manage distributed public agent assets.
- public doctor — Diagnose drift between package source, staging, and runtime projections.
- public install — Install staged public assets into runtime projections.
- public stage — Stage packaged public assets into .dadaia/agentic/.

## dadaia reconcile — Reconcile state and projections after installing an exact candidate wheel.

## dadaia reports — Validate agent handoff reports.
- reports validate — Validate one or more agent handoff JSON files.

## dadaia specs — SDD release-lifecycle structural checks and helpers.
- specs init — Bring a repo's specs/ to the canon, never committing.
- specs upgrade — Upgrade a specs/ tree to the canonical pattern version.
