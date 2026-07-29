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
- **AND — the version string is NOT identity.** Two candidates built 41 commits apart
  both print `0.4.2`; a validation venv installed from an earlier wheel therefore looks
  correct and silently validates dead code (this happened, and cost two days of a matrix
  run re-finding already-fixed bugs). So compare CONTENT, not the label: for every
  `dadaia_workspace/**/*.py` inside the candidate wheel being validated, the file
  installed in the venv under test must have the SAME sha256.

  ```bash
  python3 - "$WHEEL" "$(dirname "$D")/../lib" <<'EOF'
  import hashlib, pathlib, sys, zipfile
  wheel, libroot = sys.argv[1], pathlib.Path(sys.argv[2])
  site = next(libroot.glob("python*/site-packages"))
  z = zipfile.ZipFile(wheel)
  bad = []
  for n in z.namelist():
      if n.startswith("dadaia_workspace/") and n.endswith(".py"):
          inst = site / n
          if not inst.exists() or hashlib.sha256(inst.read_bytes()).digest() != \
             hashlib.sha256(z.read(n)).digest():
              bad.append(n)
  print("MISMATCH", len(bad), bad[:5]) if bad else print("IDENTITY OK")
  sys.exit(1 if bad else 0)
  EOF
  ```

  A mismatch is a **hard stop**: rebuild the validation venv from the candidate wheel and
  restart the round. Never reuse a venv across candidates, and never trust a `--version`
  that agrees.

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
- **Envelope contract (bugs claude-pre-gate-envelope-contract +
  pre-gate-allow-envelope-fails-claude-schema):** each verdict must be a single JSON
  envelope that validates against the Claude Code PreToolUse output schema (top-level
  `decision` enum is `["approve", "block"]` — nothing else may appear there) while
  staying readable by codex/kimi —
  - block: top-level `"decision": "block"` AND
    `hookSpecificOutput.permissionDecision == "deny"` with `hookEventName ==
    "PreToolUse"` and `permissionDecisionReason` equal to the top-level `reason`,
    which must be the LAST key (the kimi shim's sed capture depends on it);
  - allow: a non-empty JSON envelope carrying NO permission verdict of any kind —
    exactly `{"continue": true, "hookSpecificOutput": {"hookEventName": "PreToolUse"}}`.
    A top-level `"decision": "allow"` is a FAIL (invalid enum value — the harness
    rejects the whole envelope, "Hook JSON output validation failed", on every allowed
    call). `permissionDecision: "defer"` is a FAIL (print-mode only; interactive
    sessions warn and ignore it). `"approve"`/`permissionDecision: "allow"` are a FAIL
    (they would bypass the operator's permission prompts). The literal
    `"decision": "block"` must NOT appear (the kimi shim greps it).
  A bare legacy block envelope (`hookSpecificOutput` family missing) is a FAIL.

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
  `scope`, `metrics:{}`, `self_pull:{"refs":[<the agent's ROLE-MAPPED memory atom>, ...]}`,
  `artifact:{"type":"other"}`, `findings:[]`, `verdict:"APPROVED"`,
  `next_handoff:{"agent":"human","context":<ctx>,"expected_artifact_type":"other"}`.
  `self_pull.refs` MUST list the memory atom the agent's role maps to, or the validator
  rejects it — correctly: an agent's handoff has to show it read its own memory. For
  `agent:"qa-engineer"` that is `specs/memory/quality-assurance.md` (context-relative, and
  it exists in any scaffolded context). A ref like `AGENTS.md` alone is NOT enough
  (bug recipe-f12-minimal-valid-handoff-is-invalid: the earlier wording prescribed exactly
  that, so following the recipe verbatim produced a FAIL against a healthy product).
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
     print EXACTLY the candidate version; and the venv carries the promised CI
     toolchain — `<ws>/.dadaia/.venv/bin/python -m pytest --version` exits 0 (without
     it, `ci preflight` and the executed-test closure gate are unusable). A version mismatch or import failure is a
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

### F-21 — CI preflight (scope-aware)
- Run `$D ci preflight` from a git repo that is NOT the dadaia-workspace source tree
  (any consumer Spec Context repo will do).
- **PASS if:** it refuses in ONE clear line saying the gate targets the dadaia-workspace
  source repo, exit non-zero, no traceback — and it does NOT report a lint failure or
  blame a missing `poetry`. The gate's checks lint and type-check the library's own
  paths (`dadaia_workspace/`, `tests/`, this repo's `setup.cfg`), which do not exist in a
  consumer repo, and a consumer venv carries no ruff/mypy — so the old behaviour reported
  `[FAIL] ruff format --check` / `command not found: poetry` and sent the operator to
  install a tool that would not have helped
  (bug ci-preflight-unusable-outside-the-source-repo).
- Running it OUTSIDE any git repo returning a clear usage error is also expected.
- The in-source-repo path (where the gate actually runs format/lint/type/tests) is not
  reachable from a consumer validation workspace; mark it **EXCEPTION** with that reason
  rather than installing the library source just to exercise it.

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
- **Compact re-injection (bug claude-compact-reinjection-missing):** the projected
  `.claude/settings.json` must register `SessionStart` entries with matchers `compact`
  AND `clear` pointing at `dadaia_workspace.hooks.ctx_inject`. Drive ctx-inject with a
  Claude SessionStart payload (`{"hook_event_name": "SessionStart", "source":
  "compact", "session_id": ...}`) on a session whose sentinel records a bound slug:
  the bootstrap must re-emit AT THE EVENT and the NEXT UserPromptSubmit must stay
  silent (exactly-once — no compact marker left behind). A missing SessionStart block
  in settings.json, silence at the event, or a double injection is a FAIL.

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
  an empty-payload author step marked `accepted` is a FAIL of this statement.
  **Chain continuation:** when the live backlog run COMPLETES, the pick must be
  CONSUMABLE — inspect the promoted `backlog_author` ledger payload (it must carry a
  `specs/backlog/` path, e.g. `authored_backlog_paths`; a bare "codex exec completed"
  payload is a FAIL — bug backlog-author-bare-payload-breaks-release-handoff class)
  and then run `release-definition` for the same context/release: it must ACCEPT the
  authoritative pick (never refuse with "produced no exact specs/backlog artifact
  path") AND drive the live definition to APPROVAL in the fresh context — SPEC and
  PLAN flipped to `**Status:** Aprovado`, TASKS authored. A fresh (greenfield)
  context's embryonic memory is NEVER a valid rejection reason at `definition_review` (bug
  live-release-definition-rejects-fresh-context class): the SPEC itself is the
  founding structural reference there. **Closure integrity:** when the release's
  TASKS/write set declare test paths, `implementation-reviews` may reach CLOSURE only
  with an EXECUTED, green test run — the deterministic close gate runs pytest itself.
  A closure whose final payload lists validation commands as "planned / not run", or
  a CLOSURE.md produced without an executed green suite, is a FAIL (bug
  implementation-review-approves-unexecuted-validation class). **Anchor stability:**
  after CLOSURE (memory/catalog updates included), every intent of the consumed
  backlog item must STILL resolve via `dadaia backlog subjects` — a regeneration that
  renames/destroys a canonical heading anchor is a FAIL (bug
  closure-breaks-canonical-backlog-anchor class). **Post-closure coherence:** after
  the live cycle closes, `dadaia specs doctor` on the context must report 0 errors —
  in particular no CAT-1 (catalog entry without its memory atom; the catalog is
  derived and regenerated at closure — bug
  closure-catalog-references-missing-memory-atom class). Also post-closure: the
  context repo contains NO cache dirs (`__pycache__`, `.pytest_cache`, … — swept at
  closure; bug lifecycle-workflows-leave-python-bytecode-in-repo class), memory atoms
  are lint-clean (no LINT-1 warnings; bug closure-allows-memory-doctor-warnings
  class), and a BLOCKED implementation run resumes with
  `implementation-reviews --resume-from <step>` keeping upstream ledger payloads (bug
  implementation-reviews-resume-token-without-cli-resume class — a published resume
  token without a working resume command is a FAIL). **Release-id canon:** every
  lifecycle verb refuses a noncanonical `--release-id` up front (canonical:
  `vMAJOR.MINOR.PATCH[-suffix]`) — use e.g. `v0.1.0` for the live cycle; an accepted
  noncanonical id that later breaks closure is a FAIL. **Blocked-close transaction:**
  a close that BLOCKS must leave no half-written state — no CLOSURE.md, no memory
  mutation, ACTIVE.md still pointing at the release (resume must work). **Runnable
  product proof:** the game evidence must come from the DECLARED entrypoint
  invocation (e.g. `python -m <pkg>.cli` with scripted moves producing real output),
  not only direct function calls — an approved CLI that exits 0 with no I/O is a
  FAIL (bug implementation-review-misses-nonrunnable-cli-entrypoint class).
  **Closure commit:** a completed cycle leaves the context repo COMMITTED
  (`git status --porcelain` empty apart from operator files; the closure commit is
  Python-owned — bug implementation-closure-leaves-uncommitted-release-tree class).
  **Validator setup hint:** create the disposable bare remote OUTSIDE the workspace
  root (e.g. a sibling dir) — a `src.git` at the root is a ROOT-1 finding of the
  validator's own setup, not a candidate defect. Mark **EXCEPTION** only if no codex binary/credentials exist in the
  environment.

---

## Real-use matrix — the hermes day-to-day contract (v0.2.9)

**This section is the release gate's second half.** The deterministic matrix above
(F-01…F-26 + the structural certification) proves components in isolation; it is
**never sufficient to approve a release alone**. A candidate is green only when the
real-use statements below — built from the hermes agent's actual day-to-day
inventory — ALL pass with artifact-level evidence (bug
certification-misses-live-codex-backlog-regression-040: a green certification that
never exercised the live backlog path was false confidence).

### R-01 — Live Codex chain, end to end, with per-link artifact proofs

- Setup: a clean disposable context on the candidate; `DADAIA_CODEX_SANDBOX=danger-bypass`
  in nested containers; a bounded real demand.
- Run the chain IN ORDER: `lifecycle backlog-definition` → `lifecycle
  release-definition` → `lifecycle implementation-reviews` → `lifecycle audit`.
- **PASS if ALL of:**
  1. backlog-definition COMPLETES and the authored item EXISTS on disk as a NEW or
     CHANGED `specs/backlog/*.md` (bug codex-backlog-author-no-materialization: a
     worker accepted with no delta is a FAIL, and it must now block AT the author
     step with the retry, not later at the review gate);
  2. release-definition COMPLETES with SPEC.md/PLAN.md/TASKS.md written AND
     review-flipped to `**Status:** Aprovado`, ACTIVE.md repointed — never a
     success report over missing artifacts (bug release-define-stalls-before-worker
     class);
  3. implementation-reviews reaches an honest terminal state (completed, or blocked
     with a surfaced reason — a silent/empty terminal is a FAIL);
  4. audit COMPLETES (or blocks honestly at a named gate) with the `audit-report-v1`
     payload validating;
  5. every produced handoff validates (`dadaia reports validate`).

### R-02 — Real-demand backlog is canonical and consumable

- Run a B3/CVM-style real capture demand through backlog-definition on a real or
  disposable context, then validate with `dadaia backlog doctor --specs-dir <ctx>/specs`.
- **The authority is `backlog doctor`, NOT eyeballing `backlog subjects`.** `backlog
  subjects` lists the canonical registry (the anchors that exist) and always exits 0; it
  never reports an item's unresolved refs. Reading a ref's absence from that list as
  "UNRESOLVED" is a validator error, and it produced a false FAIL on R9/R-02 — the very
  first version of this item told you to do exactly that.
- **A `surface: new` ref is SUPPOSED to be absent from the registry.** That is what
  declaring a new surface means: the intent binds by declared identity
  (`new:<kind>:<ref>`) instead of registry resolution. Demanding that *every* ref resolve
  contradicts the mechanism shipped for bugs `backlog-independent-cli-items-false-conflict-044`
  and `backlog-cli-intent-hallucinated-anchor-045`.
- **PASS if:** `backlog doctor` reports clean AND release-definition's authoritative pick
  consumes the item (the promoted payload carries the canonical
  `specs/backlog/<slug>.md` path — never a bare "codex exec completed" summary).
- **Both error directions must still be caught — prove them, do not assume:**
  - an intent WITHOUT `surface: new` whose ref resolves to nothing ⇒ doctor MUST fail with
    `BL-SCHEMA … resolves to no known anchor`;
  - an intent WITH `surface: new` whose ref DOES already resolve ⇒ doctor MUST fail with
    `… is declared 'surface: new' but already resolves to existing anchor …`.

  A green run that never exercised these two is not evidence — plant each one and confirm
  the failure before accepting the PASS.

### R-03 — Fresh specs tree is doctor-clean with no manual edits

- Run `$D specs init --specs-dir /tmp/r03/specs`; then `$D specs doctor --specs-dir
  /tmp/r03/specs`.
- **PASS if:** doctor reports 0 errors AND 0 warnings out of the box (no
  placeholder atom requiring manual repair — the scaffold emits only valid atoms).

### R-04 — Old tree with a placeholder atom is repaired by BOTH verbs

- Seed `/tmp/r04/specs` (fresh init) + a raw `memory/product/feature.md` carrying
  `SLUG_PLACEHOLDER`/`TITLE_PLACEHOLDER`/`RELEASE_PLACEHOLDER`.
- Run `$D specs doctor --fix --specs-dir /tmp/r04/specs`; then re-seed and run `$D
  specs upgrade --specs-dir /tmp/r04/specs -y`; also `$D specs upgrade --dry-run`.
- **PASS if:** `doctor --fix` removes the atom and leaves doctor 0/0; `upgrade`
  repairs even an already-current tree (dry-run reports without deleting);
  filled atoms are never touched (bug
  scaffold-repair-cannot-remediate-invalid-placeholder-atom).

### R-05 — release-definition on a real context advances to a terminal state

- On a repaired real context (or a faithful replica), run `lifecycle
  release-definition --release-id v0.1.0 --harness codex` with a bounded demand.
- **PASS if:** the run reaches an honest terminal state with persisted evidence —
  never a `running` cursor with empty `workflow_steps` plus a success report (bug
  lifecycle-release-define-stalls-before-worker class). A blocked run must surface
  its reason and resume with `--resume-from`.

### R-06 — Bug ledger round-trip

- Register a synthetic bug (`bugs append` with every required field), fix-and-mark
  it (`resolved` with evidence), and query `bugs status`.
- **PASS if:** the events validate, stream order stays coherent (reported before
  resolved), and status reflects the resolution.

### R-07 — Fake-chain honesty (scope note, not a run)

- The fake chain is evidence for DETERMINISTIC gates only. **PASS if:** every place
  this recipe (or a verdict) cites a fake-chain run, it is labeled as gate evidence
  — never as user-flow proof. A verdict that leans on fake flows for real-user
  behavior is a FAIL of the verdict, not of the product.

### R-08 — Kimi Code harness end to end (v0.2.8 surface)

- Setup: `export KIMI_CODE_HOME=<throwaway>`; `$D init --harness kimi-code` in a
  disposable dir.
- **PASS if ALL of:** `.kimi-code/AGENTS.md` exists; the managed `[[hooks]]` block
  and four `dadaia-kimi-*` shims exist under `$KIMI_CODE_HOME`; the pre-gate shim
  allows a normal write (exit 0) and blocks a root-law violation (exit 2 + stderr
  reason naming `.kimi-code/` among allowed entries); ctx-inject injects after
  `dadaia context bind`; the post-compact shim stamps `ctx-compact-<sid>` AND
  re-emits the bootstrap on stdout, and the next prompt re-injects exactly once;
  `dadaia public doctor` is green (incl. `dadaia:scripts/*` on a kimi-only profile);
  `dadaia public doctor` flags a tampered shim/block and `install` heals it.

### R-09 — Resume of a sandbox-blocked run completes (echo-classification class)

- Force a codex backlog/definition run to block on the sandbox signature (no bypass),
  then run the PRESCRIBED remedy: same run-id, `--resume-from <blocked step>`, with
  `DADAIA_CODEX_SANDBOX=danger-bypass`.
- **PASS if:** the resumed run persists `completed` in `.dadaia/states/lifecycle/` AND
  downstream consumption works (`release-definition --backlog-run-id <id>` accepts it).
  A resumed run re-blocked with the OLD sandbox reason while its deliverables landed on
  disk is the bug class (real-codex-resume-output-not-committed-to-ledger-042: the
  prompt's own block digest echoed into stderr must never re-classify a bypass run).

### R-10 — Dedupe EDIT path is gate-visible (disk truth, not anchors only)

- Run backlog-definition twice over the same demand: the second run's worker refines
  the existing item's BODY/acceptance without touching `intents[]`.
- **PASS if:** the run COMPLETES (the review gate detects the content-hash change);
  and a worker that claims 'updated' while writing NOTHING blocks at the author step
  with the worker diagnostic — never an accepted-then-unexplained gate block (bug
  backlog-dedupe-updated-payload-not-gate-visible-043).

### R-11 — Resume never collides with its own leftovers (ledger-owned immutability)

- **Do NOT try to reach a "spent-review-budget block" — it does not exist by design.**
  An earlier version of this item required driving a review to REJECT twice and then
  resuming from a block. The product deliberately makes a post-budget REJECTED review
  **advisory**: the step proceeds carrying the rejection as a warning, precisely so a
  model verdict can never deadlock a release (`_fragment_gate`, "a model verdict is
  advisory, never terminal"). The shipped CLI also has no deterministic rejection
  injector, so the scenario is unreachable AND contradicts the intended semantics.
  Requiring it produced a FAIL against correct behaviour on R17.
- Instead: interrupt a run between payload write and state save (or plant a stray
  `<step>-attempt-0.step-payload.json` with no ledger record) and resume from the
  prescribed step on the SAME run-id.
- **PASS if:** every prescribed resume executes — no `already recorded step ...
  (immutable payload ...)` error ever surfaces on a path the error text itself
  prescribed (bug release-definition-retry-collides-with-immutable-tasks-payload).

### R-12 — New-surface backlog intents classify by their own identity

- Author two independent NEW CLI-command items (e.g. `hello`, then `version`) using
  `subject: { kind: cli, ref: <name>, surface: new }`.
- **PASS if ALL of:** both runs complete (no DIVERGENT_CONFLICT over a shared coarse
  anchor — bug backlog-independent-cli-items-false-conflict-044); a `surface: new`
  ref that ALREADY resolves blocks with the exact remedy; an unresolved EXISTING ref
  blocks with a reason naming both recoveries (`dadaia backlog subjects` /
  `surface: new`) AND a non-null `operator_command` naming the resume invocation
  (bug backlog-cli-intent-hallucinated-anchor-045 — no gate block is a dead end).

### R-13 — Producers pass their own validators (scaffold / fake / baseline)

- `specs release open v0.1.0` then `specs doctor`; `specs segment open alpha-2` then
  doctor again; `lifecycle backlog-definition --harness fake` then `backlog doctor`;
  fresh context: `context create` → `alive` → `specs init` → `context baseline`.
- **PASS if ALL of:** both doctors report 0 errors AND 0 warnings on the fresh
  scaffold (Draft + phase SPEC is the legitimate authoring state — bug
  fresh-release-scaffold-emits-spec-doctor-warnings-042); the fake-materialized item
  is BL-SCHEMA-valid (bug fake-backlog-workflow-materializes-doctor-invalid-status-042);
  and baseline COMPLETES after the official scaffold follow-up while still refusing a
  tree carrying operator files (bug context-baseline-rejects-official-scaffold-followup).
- **A GATE is a validator too** (bug r4g-backlog-surface-new-existing-accepted): take
  what a workflow's own gate ACCEPTED and run the matching doctor over it. A run that
  completes while `backlog doctor` / `specs doctor` rejects its output is a FAIL — the
  gate and the doctor must never hold two opinions. Probe the degenerate inputs
  specifically: an item with NO `intents[]` at `candidate` status (must block; `idea`
  stays exempt), and an empty/absent field where the gate's checks could be *vacuously*
  satisfied rather than actually passed.

### R-14 — Live foreign presence is SURFACED on the allowed write

- Bind two sessions in implementation mode on one context; drive a real `pre_gate`
  MUTATING write payload for each.
- **PASS if:** the second write is ALLOWED and its hook output visibly carries the
  throttled `[PRESENCE]` advisory naming the other session (id, runtime, heartbeat
  age) — in the allow envelope's `systemMessage` and on stderr; a neutral allow with
  live foreign presence is the bug (pre-gate-drops-live-presence-advisory-042).
  Repeat writes inside the throttle window stay quiet (at most one advisory).

### R-15 — L1 agent-model roster resolves, projects and RUNS on the mapped models

The L1 roster is data (`core/agent_model_templates.py` + `core/model_registry.py`)
rendered at projection time into BOTH harness surfaces. A remap that resolves and
renders cleanly can still name a model the runtime cannot reach — a class internal
gates cannot catch, because they never call the model.

- **Reachability (the load-bearing check):** for every DISTINCT `model` string in
  `.codex/agents/*.toml`, run one minimal `codex exec --model <id>` and require
  exit 0. A projected model that 403s/404s at runtime is a FAIL even when every
  doctor is green.
- **Lockstep:** with no overlay, `.claude/agents/<a>.md` frontmatter (`model`,
  `effort`) and `.codex/agents/<a>.toml` (`model`, `model_reasoning_effort`) must
  render from the SAME resolved roster for all 9 core agents; the codex effort is
  the D-3 clamp of the claude effort (`xhigh` → `high`).
- **Overlay round-trip:** apply a template + a per-agent override through the panel
  API (`PUT /api/agent-model-policy`), re-install, and confirm BOTH surfaces moved
  together; `GET /api/agent-model-templates` offers every registry `claude_id` as a
  selectable model and the full effort vocabulary.
- **Tier invariants:** `dadaia public doctor` reports `[ok] model-resolution`; each
  registry tier resolves to exactly ONE codex id, and no two tiers collapse to an
  identical `(codex_id, reasoning_effort)` pair.
- **G-1 stands:** `claude-fable-5` is NEVER the resolved model for
  `security-reviewer`, under any template or override.
- **Layer-2 is NOT collateral:** the four lifecycle workflows keep running on their
  own profiles (`features/lifecycle/model_profiles.py`) — an L1 remap must not
  change which model a workflow worker runs, and must not drop a Layer-2 id the
  operator overlay depends on (credit-exhaustion escape hatch).
- **PASS if ALL of the above hold.** A registry-derived allowlist narrowing (e.g. a
  provider-qualified PI id that no longer maps) must fail LOUDLY at load with a
  message naming the rejected id — never silently accept an unmapped model.

### R-16 — Every prescribed remedy actually WORKS (no contradiction loops)

A block that names a command which cannot run is worse than a block with no advice:
the operator burns a cycle proving the tool wrong. This class has now appeared twice
(bug release-definition-retry-collides-with-immutable-tasks-payload, bug
r4d-resume-preflight-invalid-step-traceback), so it gets its own sweep.

- For every BLOCKED state you can reach in this run, take its `operator_command` (and
  any command named in `reason`) and **execute it verbatim**.
- **PASS if ALL of:** the prescribed command is executable as written — the step it
  names exists in that workflow's sequence, the run-id/flags it cites are valid, and it
  changes the state (or explains precisely why it cannot); no prescribed remedy raises a
  raw traceback; and a gate that is NOT resumable says so in-band rather than reporting
  a `blocked_at_step` that invites `--resume-from <gate>` (preflight is the known case).
- Probe an INVALID `--resume-from <unknown-step>` on each of the three workflows that
  accept it: each must fail as ONE clean `DadaiaError` line naming the VALID steps —
  never a raw `ValueError`.

### R-17 — Bootstrap survives a hostile filesystem, cleanly

- Point `init` (and `import`, if exercised) at a target on a **noexec** mount — `/tmp` is
  mounted this way on many hardened hosts and containers, including this worker.
- **PASS if:** exit code is non-zero, output is ONE actionable line naming the path and
  the likely cause, and there are ZERO traceback lines (bug
  r3b-portability-import-venv-permission). The filesystem limit is legitimate and not the
  product's to fix; crashing on it is.
- **Also assert the success path did not regress:** a normal bootstrap on an exec-capable
  filesystem still creates the venv and installs the distribution, with and without
  `DADAIA_BOOTSTRAP_PACKAGE`. An error-path fix that starts swallowing legitimate
  failures, or that breaks valid bootstrap, is its own FAIL.

### R-18 — F-22 holds as a BOUNDARY: no verb tracebacks, for ANY failure

F-22 ("no raw traceback from any CLI verb") was long enforced as a *whitelist*: the entry
point caught only `DadaiaError`, so the contract held only for raises that happened to be
inside that hierarchy — and the package raises ~138 bare builtin exceptions. It leaked one
verb at a time (`WorkspaceVenvBootstrapError`, then a dangling `DADAIA_BOOTSTRAP_PACKAGE`).
Probe the boundary directly, not just the verbs you happen to know about:

- Provoke a NON-`DadaiaError` failure through the real console entry point. The
  reproducible one: export `DADAIA_BOOTSTRAP_PACKAGE=/does/not/exist.whl` and run `init`.
  **PASS if:** exit non-zero, ZERO traceback lines, the message names the offending value
  and what is required of it, and — for an unexpected defect — names the exception type
  and how to get a traceback.
- Assert the debug escape hatch works: the SAME command with `DADAIA_TRACEBACK=1` DOES
  print the traceback. A boundary that removes all debuggability is its own defect.
- Assert the boundary did not swallow normal exits: `--help` exits 0, an unknown option
  exits non-zero with usage (not a "defect" line), and neither is relabeled.
- **Sweep, do not spot-check:** run every top-level verb with a deliberately invalid
  argument and grep the combined output for `Traceback (most recent call last)`. Any hit
  is a FAIL, regardless of which verb produced it.

### R-19 — THE FULL DEVELOPMENT LIFECYCLE (mandatory; the flow the workspace exists for)

Everything else in this recipe validates parts. This statement validates the whole product:
N backlog items authored, consumed by ONE release, then implemented — driven entirely by the
dadaia-workflows. Run it in a FRESH consumer workspace with `--harness fake` (deterministic,
zero credits). Every step below must be asserted on DISK, never from the run's own summary:

1. `init` a fresh workspace, `context create` + `context alive` a scratch context.
2. Run `lifecycle backlog-definition` **THREE times** with three DISTINCT `--run-id` and
   three distinct `--demand`. **PASS if:** all three complete AND `specs/backlog/` gains
   **THREE** items, each with its own `ref:` anchor. One item, or three items sharing one
   anchor, is a FAIL (bug fake-backlog-canary-fixed-slug-blocks-multi-item-release-flow):
   a run that reports success while overwriting a previous run's deliverable is the exact
   class this recipe exists to catch.
3. Run `lifecycle release-definition` ONCE for the same release id, with NO
   `--backlog-run-id`. **PASS if:** it completes without demanding you pick one producer,
   and `post_step.consumed_slugs` names **ALL THREE** items, `post_step.shipped_anchors`
   names all three anchors, and the `consumed_backlog.json` ledger EXISTS on disk
   (bugs release-definition-refuses-multiple-backlog-producers and
   release-definition-consumes-nothing-while-scope-declares-items). An empty
   `consumed_slugs` with `status: OK` is a FAIL, not a no-op.
4. Assert the negative too: hand-edit the SPEC to drop one slug from `**Consumes:**`, re-run
   the post-step path, and confirm it FAILS naming the dropped slug. A verification that
   cannot fail is not a verification.
5. Run `lifecycle implementation-reviews`. If preflight blocks with `context is not bound`,
   run its `operator_command` verbatim and re-run — that prescribed remedy MUST work (R-16).
   **PASS if:** it completes, `final_phase` is `closure`, and `closure_gate.removed` names
   ALL THREE consumed items.
6. Run `lifecycle audit` against the release. **PASS if:** it completes and writes its
   report.

Report each numbered step's verdict separately with the disk evidence you checked. A FAIL
anywhere here outranks every F-statement: it means the product cannot do the one thing it
exists to do.

### R-20 — The workflow is SIMPLE and cannot deadlock (v0.2.x re-architecture)

Four architectural defects were fixed together; this statement is how you prove them, and
it replaces any earlier expectation of a 7-step release definition.

- **Three steps, not seven.** `release-definition` runs exactly
  `definition_draft` → `definition_review` → `definition_commit_gate`. Assert the step
  labels from the `--json` output. TWO model calls, not six: a longer sequence is a FAIL of
  this statement, because the whole point is context and cost.
- **A model verdict can never stop a run.** Drive a release whose review REJECTS every
  time. **PASS if:** the run still reaches a terminal state (it does not sit blocked on the
  verdict), and the objection appears in `warnings[]` — accepted is never silent. A run
  that blocks forever on a reviewer is the deadlock this removed.
- **Deterministic gates DID stay terminal.** A definition whose SPEC never lands on disk,
  or whose PLAN omits the `## Validation Dependency Table`, or whose TASKS carry a `pytest`
  without `-p no:cacheprovider`, must still BLOCK — with a remedy naming
  `--resume-from definition_draft`. If any of these now passes, the fix went too far and
  that is a FAIL.
- **Prompt and validator agree.** For every rule Python enforces, the fragment teaches it:
  `**Consumes:**`, the contract bindings, the pytest flag, the dependency table. Grep the
  two shipped fragments (`definition_draft`, `definition_review`) and confirm each is
  taught. A rule enforced but never taught is the bug class that cost weeks.
- **Only two fragments ship** for `release_definition`. Any leftover `spec-create` /
  `plan-create` / `tasks-create` / `*-review` fragment is dead weight and a FAIL.

---
### R-21 — An unrepairable environment limit is never reported as repairable drift

A status carries a promised remedy. `[drift]`/`[missing]` mean "re-run
`dadaia public install`"; if install cannot possibly repair the condition, that status is a
lie that sends the consumer into an infinite repair loop and fails `reconcile` with
`rollback_required`. Two known limits, both real on hardened hosts:

- **A `noexec` `KIMI_CODE_HOME`.** Point `KIMI_CODE_HOME` at a directory on a `noexec`
  mount (a tmpfs `/tmp` is the common case), run `dadaia public install --target kimi-code`,
  then `dadaia public doctor`. **PASS if:** the four `kimi-code:hooks/*.sh` lines are
  `[unsupported]`, name the `noexec` mount as the cause and `KIMI_CODE_HOME` as the remedy,
  `public doctor` exits 0, and `dadaia reconcile --expect-version <ver>` succeeds. **FAIL
  if** any line reads `[drift]`/`[missing]`, or `reconcile` reports `rollback_required` —
  reinstalling cannot clear a mount flag, so the run would never converge.
- **The repairable boundary must survive.** `chmod 0o644` one shim on a NORMAL filesystem
  and re-run the doctor. **PASS if** it reads `[drift] … (not executable)` and a plain
  `dadaia public install --target kimi-code` clears it. Turning every executability failure
  into `[unsupported]` is the opposite defect and also a FAIL.

Generalize while you sweep: any doctor/gate line that prescribes a remedy must be a remedy
that WORKS. Apply the prescribed command literally; if it cannot resolve the condition it
names, that is a product FAIL of this statement (see also R-16).

### R-22 — A resume is a way BACK IN, never a way PAST a gate

Interrupt a real release-definition (kill the driver), then run the recovery
`lifecycle status` prints — which resumes at or after the terminal gate. **The pass
condition depends on which precondition is missing, and both are correct outcomes.** The
first wording of this statement demanded `--resume-from definition_review`
unconditionally and produced a false FAIL on R23, because it described an outcome the CLI
cannot reach from a killed run: two independent barriers guard the gate and the ledger one
is hit first.

- **Incomplete step ledger** (the killed-driver case: the draft step wrote no payload).
  **PASS if** the block reads `workflow-step graph incomplete: step 'definition_draft' …`
  and prescribes `--resume-from definition_draft` — the step that must produce the missing
  payload. **FAIL if** it prescribes `--resume-from definition_commit_gate`, i.e. the gate
  that detected the hole: pasting that re-runs the gate, which re-detects the hole, and the
  remedy reproduces its own condition.
- **Complete ledger, unapproved artifacts** (reachable when the draft payload exists and
  the review never ran). **PASS if** the commit gate names PLAN.md and TASKS.md as not
  `Aprovado` and prescribes `--resume-from definition_review`. **FAIL if** it completes and
  ACTIVE.md is repointed to IMPLEMENTATION, leaving the release stuck because
  implementation preflight correctly refuses artifacts the definition never approved.

In every case the remedy must name a step that can actually FIX the stated cause. That is
the invariant; which step it is follows from the cause.

**And the remedy must be SELF-CONTAINED, including the environment.** A block whose cause
is environmental — the Codex sandbox namespace that cannot be created in a nested
container is the standing example — must carry the assignment on the command line
(`DADAIA_CODEX_SANDBOX=danger-bypass dadaia lifecycle …`), not only in the prose that
explains it. **FAIL if** pasting the printed command verbatim reproduces the same failure
because a variable named in the reason was not on the line. Test this by literally copying
each `operator_command` into the shell with nothing added.

Generalize while you sweep: for EVERY terminal gate, ask whether its checks are scoped to
the steps the current run happened to execute. A gate that asks the run about its
itinerary instead of asking the disk what is there can always be stepped over by resuming
past it. Try each workflow's recovery command as an entry point in its own right, not only
as a continuation.

### R-23 — Every block is a command you can paste, not advice about one

Provoke a block on each of the four workflows — a worker that returns nothing usable is
the easiest (point the harness at a stub), and a killed driver is the other. **PASS if**
every `operator_command` printed anywhere begins with `dadaia ` and carries the run's own
`--context`, `--release-id`, `--run-id` and `--resume-from <real step label>`; copy it
verbatim into the shell and it must run. **FAIL if** any of them reads like instructions
("re-run the workflow with …", "re-run the step that produces …", "inspect …"), names a
placeholder, or omits a field you would have to remember.

This has now been reported five times on five different routes. When you find one, do not
stop at it: grep the whole output of the round for `re-run`, `inspect`, and `re-execute`
and report every occurrence together — a class fixed one instance at a time is a class
that survives.

### R-24 — A malformed artifact is diagnosed where it is WRITTEN

Have the author step of `backlog-definition` produce a broken item, one variant per run:
frontmatter that opens and never closes; frontmatter with keys and a closing `---` but no
opening one; and unparseable YAML inside a well-formed block. **PASS if** each blocks at
`backlog_author` naming the actual defect ("unterminated", "missing its opening
delimiter", the YAML error with line/column). **FAIL if** any is allowed through and
surfaces later at `backlog_review_gate` as a missing status or absent intents — a
diagnosis that names the wrong thing, at the wrong step, about a file the operator will
then inspect looking for the wrong problem.

Guard the other way too: a normal item containing a Markdown horizontal rule (`---` after
prose) must NOT be called malformed. A false positive here is worse than the defect,
because nothing the operator changes will make it go away.

### R-25 — An artifact may not say two different things about its own status

After ANY live release-definition completes, open SPEC.md, PLAN.md and TASKS.md and read
them the way a human does. **PASS if** each declares its status exactly once and that
declaration is `> **Status:** Aprovado`. **FAIL if** a file carries a second status
declaration in any decorated form — a heading (`## Status: Draft`), a bullet, a
blockquote — alongside Python's canonical line, or if the workflow reported
`final_phase: implementation` while any artifact still reads Draft to a reader.

This is the shape that produced a false completed definition on R23/F-26: the single-
writer normalization enumerated the prefixes workers had used so far, a live model wrote
the status as a Markdown heading, and Python inserted its canonical line ALONGSIDE it. The
gate saw Aprovado, the human saw Draft, and the release entered IMPLEMENTATION.

Generalize while you sweep: wherever the product NORMALIZES worker-authored text to a
canonical form, try the ordinary variants a model actually writes — headings, bold, bullets,
extra whitespace, a missing accent — and check the result declares itself exactly once. Any
normalizer written as a list of known shapes is one live worker behind.

**Verdict line (Telegram-short, last line of output):**
`<version> — <APROVADA|BLOQUEADA|APROVADA COM EXCEÇÃO EXPLÍCITA> — <N> PASS / <M> FAIL / <K> EXCEPTION — bugs: <ids|nenhum> — evidência: <path>`

APROVADA requires 0 FAIL. EXCEPTIONs are listed but do not block; note each so the
operator can decide. Persist per-statement evidence; register every FAIL as a bug
before the run ends.
