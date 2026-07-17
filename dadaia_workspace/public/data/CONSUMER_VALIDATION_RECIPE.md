# Consumer Validation Recipe — dadaia-workspace

**Contract.** The canonical end-to-end validation matrix a consumer-side agent runs
against EVERY candidate wheel before deploy. Ships inside the package so recipe and
version never drift — always read the copy from the INSTALLED candidate. Verdict is
exactly one of **APROVADA / BLOQUEADA / APROVADA COM EXCEÇÃO EXPLÍCITA**.

## How to judge each statement (read first)

Each `F-NN` below is one feature with an explicit, binary **PASS assertion**. Run the
listed commands in the listed setup, capture command+exit+output as evidence, then mark:

- **PASS** — the PASS assertion is objectively true from the captured output.
- **FAIL** — the assertion is false (a real defect). Register a `dadaia bugs append`.
- **EXCEPTION** — the assertion cannot run because the validation environment lacks a
  prerequisite the wheel does not own (e.g. no Layer-2 model/harness reachable for a
  live workflow). Record why; an EXCEPTION is NOT a FAIL and does not block on its own.

Do NOT mark FAIL for "not fully demonstrated": every statement here has a crisp
assertion — if the commands ran and the assertion holds, it is PASS. If a command uses
a flag/subcommand that does not exist, THAT is a real FAIL (contract/CLI mismatch).

**Sweep the whole matrix, never one bug per cycle.** A validation run is a FULL sweep:
run EVERY statement every time, never stop at the first FAIL, and report ALL failures
of the run in one batch (one bug event each, full evidence). When a defect is found,
immediately probe the SAME defect class across every sibling surface in the SAME run —
e.g. a worker-step defect in `backlog-definition` means you also probe
`release-definition`, `audit`, and `implementation-reviews` for that class before
reporting — so the operator fixes a CLASS, not an instance, and the next candidate does
not fail on the sibling you never tried. A run that reports one bug and stops is an
incomplete validation, not a verdict.

Setup once:

```bash
python3 -m venv /tmp/val-venv && /tmp/val-venv/bin/pip install <wheel>
export DADAIA_BOOTSTRAP_PACKAGE=<wheel>   # REQUIRED for a candidate wheel
D=/tmp/val-venv/bin/dadaia
```

`DADAIA_BOOTSTRAP_PACKAGE` makes every workspace-venv bootstrap (`init`, `certify`,
`reconcile`) install the CANDIDATE wheel itself instead of pinning the version from
PyPI — the fast path for a candidate under validation. The bootstrap also
self-heals WITHOUT the export by re-packing the running installed distribution as a
local wheel when the index cannot resolve the exact version — F-25 asserts that path
deliberately unset. Destructive statements use
throwaway dirs under `/tmp` — never the production workspace. Where a statement needs
an initialized workspace, create it:
`mkdir -p /tmp/f<NN> && cd /tmp/f<NN> && $D init --harness all`.

---

### F-01 — Version & identity
- Run: `$D --version`; `$D capabilities --json`.
- **PASS if:** `$D --version` exits 0 and prints the candidate version; and
  `capabilities` JSON `.provider.distribution_version` equals that same version.

### F-02 — Reconcile with legacy quarantine
- Setup: an initialized workspace that also contains legacy `.dadaia/bugs/` and
  `.dadaia/src/` dirs (create them with a file inside).
- Run: `$D reconcile --expect-version <candidate> --json`.
- **PASS if:** exit 0, result `.ok == true`, `.steps` contains `legacy-dir-quarantine`,
  and `.dadaia/tmp/legacy-quarantine/<run>/manifest.json` exists while `.dadaia/bugs`
  and `.dadaia/src` are gone (moved, not deleted — content present under quarantine).

### F-03 — Certify agrees with reconcile AND proves the workflow chain
- Run: `$D certify --json`.
- **PASS if:** exit 0 and all checks report pass; the verdict does not contradict F-02
  (certify-green while reconcile-red, or vice versa, is a FAIL); AND the check ledger
  proves a COMPLETE chain, not gate reachability: `workflow-backlog-definition`,
  `workflow-release-definition`, `workflow-audit`, and
  `workflow-implementation-reviews` all PASS with `completed` detail (a certification
  that reports ok:true while its workflow checks only reached deterministic blocks is a
  FAIL of this statement), plus the honest-failure canaries
  (`workflow-audit-undefined-release-refused`, `workflow-completed-run-rerun-refused`)
  PASS with "no traceback".

### F-04 — Doctors
- Run in an initialized workspace: `$D doctor`; `$D public doctor`; and a specs tree
  INSIDE a repo: `mkdir -p repos/valproj && $D specs init --specs-dir
  repos/valproj/specs && $D specs doctor --specs-dir repos/valproj/specs`.
- Also assert coherence: bare `$D specs init` AT the workspace root must REFUSE
  (Root Law — init must not create what doctor refuses), exit non-zero, no `specs/`
  created.
- **PASS if:** doctor/public-doctor/specs-doctor exit 0 on the clean tree, the root
  `specs init` refusal holds, and seeding one violation (`mkdir .dadaia/nonsense`)
  makes `$D doctor` exit non-zero naming ROOT-4. Evidence discipline for the ROOT-4
  probe: capture the `mkdir`, the `pwd`, and the doctor invocation in the SAME log —
  the seeded dir and the doctor run must share the workspace root (a doctor run from
  another cwd resolves a different workspace and proves nothing), and assert the exit
  code directly, never through a pipe.

### F-05 — Projections
- Run: `$D public stage`; `$D public install --target all`; `$D public doctor`.
- **PASS if:** stage+install exit 0 and `public doctor` reports every asset `[ok]`
  (no `[drift]`/`[missing]`), exit 0.

### F-06 — Context lifecycle
- Setup: a local source repo (`git init --bare /tmp/f06/src.git`).
- Run: `$D context create alpha --repo alpha --url file:///tmp/f06/src.git`;
  `$D context list --json`; `$D context show alpha --json`; `$D context alive alpha`;
  `$D context dead alpha`.
- **PASS if:** create→list shows alpha `state:"dead"`; `alive` clones, scaffolds AND
  commits its own scaffold (repo left clean — `git status --porcelain` empty of
  tool-created files); the freshly-scaffolded context is doctor-clean —
  `$D specs doctor --context alpha` reports **0 errors AND 0 warnings** (a supported
  init path must reach a fully clean tree, with `ACTIVE.md`, catalog, and no raw
  placeholder atom — a fresh context that doctor rejects is a FAIL); `dead` flips back
  WITHOUT the untracked-consent refusal (the tool must never refuse its own scaffold);
  and a guard fails cleanly (`$D context dead ghost` exits non-zero with a clear
  message, no traceback).

### F-07 — Bind & session identity
- Setup: initialized workspace with one alive context `beta`; export a STABLE id:
  `export DADAIA_SESSION_ID=f07-fixed`.
- Run: `$D context show --json` (no bind yet); `$D context bind beta --mode
  implementation --release r1`; `$D context bind beta --mode implementation --release
  r1` (again); `ls .dadaia/sessions/*.json | wc -l`.
- **PASS if:** the unbound `show --json` prints `{"context": null}` exit 0 (no
  traceback); both binds print the SAME session id (`f07-fixed`); and exactly ONE
  session record exists after the two binds.

### F-08 — SDD gate & chokepoints
- Run the projected pre-gate hook directly with JSON payloads (no workflow needed).
  IMPORTANT: path-class payloads use IN-REPO paths (`repos/valproj/specs/...`) — a
  bare root `specs/...` write is intercepted FIRST by the root-whitelist (that is a
  separate, correct decision, asserted on its own):
  - `repos/valproj/specs/bugs/x.md` (ADDITIVE) → expect `allow`;
  - `repos/valproj/specs/_archive/x.md` (FROZEN) → expect `block`;
  - `.dadaia/sessions/x` (PROTECTED) → expect `block`;
  - `newdir/x.md` (new top-level root entry) → expect `block` naming the root
    whitelist.
- **PASS if:** all four decisions match. (Each is one deterministic hook invocation —
  that IS the demonstration.)

### F-09 — Bugs ledger
- Setup: an in-repo specs tree (`mkdir -p repos/vp && $D specs init --specs-dir
  repos/vp/specs`). `bugs` resolves its specs tree from `--specs-dir` OR a bound context —
  pass `--specs-dir` on EVERY `bugs` call (append AND status), the same way F-04/F-10/F-15
  do; a `bugs status` with no `--specs-dir` and no bind correctly errors with guidance
  ("Pass --specs-dir or bind a context"), which is expected, not a FAIL.
- Run the complete append with EVERY required `reported` field —
  `--event reported --bug-id valbug --reported-by selfrun --title t --severity LOW
  --surface s --component c --context vp --tag x --symptom sy --repro rp --expected ex
  --notes no --specs-dir repos/vp/specs`; then `$D bugs status --specs-dir repos/vp/specs`;
  then an INCOMPLETE append `$D bugs append --event reported --bug-id x --specs-dir
  repos/vp/specs` (omitting the fields above).
- **PASS if:** the complete append exits 0 and appears in `bugs status --specs-dir
  repos/vp/specs`; the incomplete one exits non-zero and writes nothing.

### F-10 — Backlog governance
- Run against the IN-REPO specs tree from F-04: `$D specs doctor --json --specs-dir
  repos/valproj/specs` (must be valid JSON); add a backlog item missing `intents[]` at
  status `candidate` under `repos/valproj/specs/backlog/`, then run the backlog-specific
  doctor — `$D backlog doctor --specs-dir repos/valproj/specs` (NOT `specs doctor`, which
  validates candidates.md format; BL-SCHEMA is the `backlog doctor` path). Assert its exit
  code directly, not through a pipe.
- **PASS if:** `specs doctor --json` emits parseable JSON exit 0; and `backlog doctor`
  flags the malformed item `[ERROR] BL-SCHEMA` and exits non-zero.

### F-11 — Lifecycle workflows present & gated
- Run: `$D lifecycle --help` and each of `backlog-definition|release-definition|
  implementation-reviews|audit --help`.
- Also assert the **undefined-input guards** (deterministic, no live worker needed):
  in a context whose `specs/releases/` has NO `<bogus-id>` dir, run
  `$D lifecycle audit --context <ctx> --release-id <bogus-id> --harness codex` and
  `$D lifecycle implementation-reviews --context <ctx> --release-id <bogus-id> --harness
  fake`. Each MUST exit non-zero and MUST NOT create `specs/releases/<bogus-id>/` — a
  lifecycle verb must reject an undefined release, never synthesize a release tree for it
  (audit runs against an EXISTING release). Check the exit code directly, not through a pipe.
- Also assert a **live worker step executes** (not just the deterministic guards): in a
  context with an EXISTING release dir, run `$D lifecycle audit --context <ctx>
  --release-id <existing> --harness codex`. The Codex worker must actually run its
  `audit_report` step (`"runtime":"codex_exec"`, step `accepted`) — the workflow then
  completes or blocks honestly at a gate. In a nested/unprivileged container, set
  `DADAIA_CODEX_SANDBOX=danger-bypass` so codex runs without a sandbox namespace (the outer
  container is the trust boundary); a `bwrap`/"No permissions to create a new namespace"
  failure is now a **FAIL**, not an EXCEPTION — dadaia's adapter supports the bypass.
- **PASS if:** all four subcommands exist and their help renders (options, purpose); the
  two undefined-release invocations are rejected (non-zero) with no synthesized release
  dir; AND the live Codex `audit_report` step executes (no sandbox namespace error). Mark
  **EXCEPTION** for the live-run portion ONLY if NO Layer-2 harness is installed at all
  (no codex and no pi binary) — never for a sandbox-namespace failure, which the
  `danger-bypass` mode fixes.

### F-12 — Reports & handoffs
- Setup: run inside an INITIALIZED workspace (`reports validate` resolves workspace state);
  write a minimal VALID `handoff-v1.2` JSON to a file. Minimal valid = these keys:
  `schema_version:"handoff-v1.2"`, `agent`, `context`, `produced_at` (UTC ISO),
  `scope`, `metrics:{}`, `self_pull:{"refs":[<one ref that EXISTS on disk, e.g. "AGENTS.md">]}`,
  `artifact:{"type":"other"}`, `findings:[]`, `verdict:"APPROVED"`,
  `next_handoff:{"agent":"human","context":<ctx>,"expected_artifact_type":"other"}`.
  Also write a tampered copy (e.g. `schema_version:"handoff-BOGUS"` and drop `agent`).
- Run: `$D reports validate <good>.handoff.json`; `$D reports validate <bad>.handoff.json`.
- **PASS if:** the valid file validates (exit 0) and the tampered one is rejected
  (non-zero, names the failure).

### F-13 — Panel
- Run: `$D panel --no-open --port <p>` in the background; hit the port with an HTTP GET;
  `$D server list` WHILE the panel is up; then stop the panel. Use whatever HTTP client
  the env has — `curl -fsS localhost:<p>/`, or, since `curl` is not guaranteed, the always
  available stdlib: `python -c "import urllib.request as u; print(u.urlopen('http://localhost:<p>/').status)"`.
- **PASS if:** HTTP 200; `server list` shows port `<p>` registered to `dadaia-panel`
  while running (the panel self-registers per the dev-server-registry law); and the
  entry is released after a clean stop. Only if the env cannot bind ANY port at all, mark
  **EXCEPTION** — a missing `curl` is not an EXCEPTION (use the stdlib client above).

### F-14 — Server registry
- Run: `$D server register --port <p> --project val`; `$D server list`; then re-register
  the SAME port for the SAME project (`--project val`); then register the same port for a
  DIFFERENT project (`--project other`).
- **PASS if:** first register + list round-trip; the same-project re-register is an
  idempotent no-op (exit 0 — a dev server re-registering its own port on restart must not
  be refused); and the different-project registration is REFUSED with guidance (non-zero,
  names the owning project). Assert exit codes directly — do not read them through a pipe,
  which masks them.

### F-15 — Memory & injection
- Setup: an in-repo scaffolded specs tree `S` (`S=repos/vp/specs`; `mkdir -p repos/vp &&
  $D specs init --specs-dir S`) that is doctor-clean — confirm `$D specs doctor
  --specs-dir S` reports **0 errors AND 0 warnings**.
- Run: `$D memory product add <slug> --specs-dir S`; `$D memory catalog generate
  --specs-dir S`; then `$D specs doctor --specs-dir S` again.
- **PASS if:** the verbs exist and exit 0; the atom is registered in the catalog; and the
  supported "add a feature" path leaves `specs doctor` at **0 errors AND 0 warnings** —
  the atom emitted by `memory product add` must lint clean out of the box (its template
  headings are allowlisted). A LINT-1 unknown-heading warning on a freshly added atom is a
  FAIL: the tool's own template must not violate its own linter.

### F-16 — Portability
- Run: `$D export --output /tmp/f16/` (note: `--output/-o`, not positional); then import
  the archive into a NEW destination — the archive is positional and the destination is
  `--workspace/-w` (default cwd), so either `$D import <archive> --workspace /tmp/f16b`
  or `cd /tmp/f16b && $D import <archive>`. (There is no `--into`; confirm the real flags
  with `$D import --help`.)
- **PASS if:** export produces an archive exit 0 and import reconstructs a workspace at the
  destination that passes `$D doctor`.

### F-17 — Migrations
- Setup: seed an older specs tree (lower pattern version) in a throwaway dir.
- Run: `$D migrate --help` then the relevant migrate verb (`migrate tree-v2 -y`);
  `$D specs doctor` after.
- **PASS if:** the migrate verb upgrades losslessly (legacy content relocated under
  `releases/legacy/`, nothing dropped) and `specs doctor` exits 0 with **0 errors**
  afterwards; re-running the migrate verb is a no-op. A SPEC-DOC-027 **WARNING** on the
  sanctioned `releases/legacy/` holding dir is EXPECTED, not a FAIL — it is the migration's
  own destination, preserved-until-renamed by design (doctor exits 0 on warnings). Judge
  on errors + exit code, not on the presence of that warning.

### F-18 — Init / onboarding (bootstrap INTEGRITY, not just exit 0)
- Run in an empty dir, with fail-fast shell discipline (`set -euo pipefail`, explicit
  `cd` into the target workspace, exit codes asserted directly — never through a pipe):
  `$D init --harness all` with `DADAIA_BOOTSTRAP_PACKAGE` UNSET for this statement.
- **PASS if ALL of:**
  1. exit 0 and `.dadaia/` bootstrapped (venv + projections), `$D doctor` green after;
  2. the captured init output contains NO raw installer error (`ERROR:`/`Traceback`) —
     an index miss handled by the re-pack fallback announces itself in one clean
     `[bootstrap]` line instead;
  3. the GENERATED venv stands alone: run
     `env -i PATH="$PATH" <ws>/.dadaia/.venv/bin/python -c "import dadaia_workspace, importlib.metadata as m; print(m.version('dadaia-workspace'))"`
     — it must import WITHOUT inherited PYTHONPATH/parent-workspace resolution and
     print EXACTLY the candidate version. A version mismatch or import failure is a
     FAIL even when init exited 0 (bug init-succeeds-after-provider-bootstrap-failure
     class: a bootstrap that only works through inherited runtime paths is broken).
  (Init may reach an index — if egress is fully blocked AND the fallback cannot apply,
  mark EXCEPTION with the network cause, else FAIL.)

### F-19 — Plugins
- Run in an initialized workspace: `$D plugin list`.
- **PASS if:** it lists installed packs (empty set on a fresh workspace is a valid
  answer — exit 0, "no plugins", NOT an error). Then install one of the two in-package
  packs — `$D plugin install frontend-design` (or `devops`) — which records the ledger and
  leaves doctor green. `plugin list` in an UNINITIALIZED dir returning a clean "run init
  first" message (non-zero) is acceptable, not a FAIL.

### F-20 — Academy
- Run: `$D academy --help` and a read verb.
- **PASS if:** the academy verbs exist and read without touching governed paths.

### F-21 — CI preflight
- Run inside a git repo working tree with the wheel installed: `$D ci preflight` (it
  gates format/lint/type/tests). Consult `$D ci preflight --help` for required context.
- **PASS if:** it runs the gate and its exit code truthfully reflects pass/fail. Running
  it OUTSIDE a repo returning a clear usage error is expected, not a FAIL — run it in a
  prepared repo to demonstrate the gate.

### F-22 — Help & docs quality
- Run `--help` on every top-level verb.
- **PASS if:** each states purpose + usage, and NO invocation in this whole matrix
  produced a raw Python traceback (a traceback anywhere is a FAIL of this statement).

### F-23 — Harness canaries
- Run the projected hooks directly: pre-gate with the F-08 payload set (in-repo paths,
  same expected decisions) and ctx-inject SessionStart with a JSON payload.
- **PASS if:** the hooks execute exit 0 and the pre-gate reproduces the F-08 decisions.
  On a fresh unbound session ctx-inject prints the GENERIC dispatcher preflight and
  NO context memory — that non-empty generic output is the CORRECT result (injection
  is bind-driven). FAIL only if it injects a context's memory without a bind, or
  crashes.

### F-24 — Workflow chain E2E (fake harness, disposable context)
- Setup: a clean disposable context `chain` (create + alive + baseline as in F-06),
  bound with a release id `v0.0.1`.
- Run, in order, each with `--harness fake --json` and a fresh `--run-id`:
  1. `$D lifecycle backlog-definition --context chain --release-id v0.0.1 --demand "chain canary"`
  2. `$D lifecycle release-definition --context chain --release-id v0.0.1`
  3. `$D lifecycle audit --context chain --release-id v0.0.1`
  4. commit the specs tree, then
     `$D lifecycle implementation-reviews --skip-preflight --context chain --release-id v0.0.1`
- **PASS if:** ALL four runs exit 0 with `"completed": true`; step (1) materialized a
  new/changed item under `specs/backlog/`; after (2) `SPEC.md` and `PLAN.md` carry
  `**Status:** Aprovado`, `TASKS.md` exists, and `releases/ACTIVE.md` points at the
  release in IMPLEMENTATION; after (4) `releases/v0.0.1/CLOSURE.md` exists. The
  documented fake path walks the WHOLE user flow — any deterministic block in this
  chain is a FAIL (the former "honest block" behavior is retired). Also: re-running
  ANY of the four steps with its SAME completed `--run-id` must be REFUSED cleanly —
  non-zero exit, one line naming the refusal (`already COMPLETED`, fresh --run-id
  guidance), no traceback, and NO re-execution of the ladder (probe at least steps (1)
  and (4); the refusal is a shared engine guard, so a sibling that re-executes is a
  FAIL of this statement).

### F-25 — Disposable bootstrap without index or env override
- Setup: an initialized workspace with the candidate installed. UNSET the override:
  `unset DADAIA_BOOTSTRAP_PACKAGE` for this statement only.
- Run: `$D certify --json`.
- **PASS if:** certification bootstraps its disposable workspace with the EXACT
  installed provider version even though the index does not serve it — the venv
  bootstrap re-packs the running installed distribution as a local wheel
  (`workspace-init-all-harnesses` and `exact-version-reconciliation` PASS). "pip could
  not resolve dadaia-workspace==<candidate>" surfacing to the operator is a FAIL: an
  unpublished candidate is the validation norm and must bootstrap with no env var.

### F-26 — Live authoring canary (Codex materializes a real artifact)
- Setup: a disposable canary context, bound; codex harness reachable
  (`DADAIA_CODEX_SANDBOX=danger-bypass` in a nested container).
- Run: `$D lifecycle backlog-definition --context <canary> --release-id <rid>
  --run-id <fresh> --demand "<bounded fictional demand>" --harness codex --json`.
- **PASS if:** the author step's prompt supplied the canonical anchor set (the item's
  `intents[]` refs resolve through `dadaia backlog subjects` — an authored item whose
  ref no canonical anchor resolves means the workflow failed to hand the author its
  anchors, bug backlog-author-missing-canonical-subject-input class); and EITHER the
  run completes with a real new/changed `specs/backlog/` item
  (the worker authored a real deliverable), OR it blocks AT `backlog_author` with
  reason "no deliverable in the step's declared zone" and a persisted worker
  diagnostic (the blocked detail references the diagnostic; the payload is never a
  bare "codex exec completed" that sails through to fail later at
  `backlog_review_gate` with no worker trace). Blocking at `backlog_review_gate` with
  an empty-payload author step marked `accepted` is a FAIL of this statement. Mark
  **EXCEPTION** only if no codex binary/credentials exist in the environment.

---
**Verdict line (Telegram-short, last line of output):**
`<version> — <APROVADA|BLOQUEADA|APROVADA COM EXCEÇÃO EXPLÍCITA> — <N> PASS / <M> FAIL / <K> EXCEPTION — bugs: <ids|nenhum> — evidência: <path>`

APROVADA requires 0 FAIL. EXCEPTIONs are listed but do not block; note each so the
operator can decide. Persist per-statement evidence; register every FAIL as a bug
before the run ends.
