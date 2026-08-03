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
  prerequisite the wheel does not own (e.g. no harness CLI reachable for a
  live authoring statement). Record why; an EXCEPTION is NOT a FAIL and does not block on its own.

Do NOT mark FAIL for "not fully demonstrated": every statement here has a crisp
assertion — if the commands ran and the assertion holds, it is PASS. If a command uses
a flag/subcommand that does not exist, THAT is a real FAIL (contract/CLI mismatch).

**State the identity you verified, by hash, or the run is void.** Before the first
statement, hash the candidate wheel and at least one installed `.py` file, and print those
hashes in the report. Never copy an identity from a previous run's evidence files: a run
that reports a sha which does not match the artifact under test proves nothing about that
artifact, however green it reads. If you resume or reuse earlier evidence, re-verify the
identity first and say which statements came from the earlier run.

**Cover the whole surface, not the statements you happen to like.** The product is the
23 CLI groups — `init export import capabilities certify reconcile clean context ci repos
public doctor academy plugin reports specs server migrate panel memory release backlog
bugs`. Before you write the verdict, list every group and say which statement exercised
it. A group no statement touched is reported under `COBERTURA` as untested — silence is
not a pass, and "the matrix didn't ask" is exactly how a feature ships broken.

**Sweep the whole matrix, never one bug per cycle.** A validation run is a FULL sweep:
run EVERY statement every time, never stop at the first FAIL, and report ALL failures
of the run in one batch (one bug event each, full evidence). When a defect is found,
immediately probe the SAME defect class across every sibling surface in the SAME run —
e.g. a path-resolution defect in `backlog consume` means you also probe `specs release
open`, `specs doctor`, and `backlog remove-consumed` for that class before reporting — so the operator fixes a CLASS, not an instance, and the next candidate does
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

### F-03 — Certify agrees with reconcile AND proves the SDD chain
- Run: `$D certify --json`.
- **PASS if:** exit 0, `ok:true`, and every check PASSes; the verdict does not contradict
  F-02 (certify-green while reconcile-red, or vice versa, is a FAIL); AND the ledger proves
  the SDD contract end to end, not merely that verbs exist:
  `sdd-backlog-item-materializes`, `sdd-release-opens-with-active-repointed`,
  `sdd-approved-artifacts-stay-doctor-clean`, `sdd-task-markers-round-trip`,
  `sdd-audit-without-disposition-is-reported`, `sdd-tree-stays-doctor-clean`, and the
  honest-failure canaries (`sdd-release-new-no-clobber-refused`,
  `sdd-backlog-bad-slug-refused`, `sdd-release-open-does-not-rewind-active`) all PASS.
- A check whose name still contains `workflow-` is a FAIL: the engine is gone, and a gate
  that names it is a gate validating something that no longer exists (bug
  certify-invokes-deleted-lifecycle-verb — the gate shipped broken while the unit suite
  stayed green, because certification checks do not run in-process).

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

### F-06 — Context lifecycle, and DEAD as a safe promise
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

**DEAD is a promise: commit → push → remove.** Removing the working copy is only safe
because a remote holds the pushed commits. Assert BOTH halves separately:
- **The promise is kept.** After `dead alpha` succeeds: `repos/alpha/` is GONE from disk,
  and the bare remote contains the commits (`git --git-dir=/tmp/f06/src.git log --oneline`
  is non-empty and includes the scaffold commit). A DEAD that leaves the directory behind
  is a FAIL; so is one whose work never reached the remote.
- **The promise is never silently degraded.** Create a second context whose repo has NO
  remote, make its tree dirty, and run `$D context dead`. It MUST refuse — non-zero exit,
  one clean line naming the missing remote, `repos/<slug>/` still on disk, and the context
  still ALIVE. Passing `--no-remote` then completes the removal as explicit consent.
  Exit 0 with the directory deleted and nothing pushed is a **CRITICAL FAIL**: the only
  copy of the operator's work was destroyed by a command that reported success (bug
  dead-removes-repo-with-no-remote).

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

### F-11 — SDD lifecycle verbs present & gated
There is no workflow engine and no `dadaia lifecycle` command. Ordered lifecycle work is a
persona operating these verbs; what the PRODUCT owns — and what this statement asserts — is
that the verbs exist, refuse bad input cleanly, and never fabricate state.
- Run: `$D backlog new --help`, `$D release new --help`, `$D specs release open --help`,
  `$D specs segment open --help`, `$D specs doctor --help`, `$D backlog consume --help`,
  `$D backlog remove-consumed --help`, `$D bugs append --help`.
- Assert the **undefined-input guards** (deterministic, no model needed), checking exit
  codes directly and never through a pipe:
  1. `$D backlog new "Not A Slug"` → non-zero, no file written.
  2. `$D release new <id>` twice → the second is refused (documented no-clobber), and the
     first SPEC.md is unchanged.
  3. `$D specs release open <existing-id>` on a live release → refused, naming
     `specs segment open`, with `releases/ACTIVE.md` byte-identical afterwards. Exit 0 here
     is a FAIL: it rewinds `phase:` back to `SPEC` on a release already in IMPLEMENTATION,
     losing lifecycle state with no trace (bug release-open-rewinds-active-phase).
  4. `$D backlog consume --release-id <id>` where the SPEC declares no `**Consumes:**`
     line → refused or an explicit empty result; never a silent `OK` over nothing.
- **PASS if:** every verb's help renders (options + purpose), all four guards refuse
  cleanly with no traceback and no side effect on disk. A verb that does not exist is a
  FAIL (contract/CLI mismatch), NOT an EXCEPTION.
- If ANY block in this recipe still tells you to run `dadaia lifecycle …`, that is a FAIL
  of the recipe itself — report it as a documentation defect, do not mark EXCEPTION.

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

**The panel must be usable by an AGENT, not only by a human with a browser.** An agent has
no eyes: it reads JSON and it acts. Assert that path explicitly:
- Every read the panel renders is reachable as machine-readable JSON without a browser
  (`GET /api/...`), and the payload parses with `json.loads` — an endpoint that only ever
  returns HTML is a FAIL of this statement.
- The state an agent needs to act is present in those payloads: the contexts and their
  states, the reports/handoffs index, the server registry, and the agent-model policy.
- A write surface the panel exposes (e.g. `PUT /api/agent-model-policy`) is drivable from
  a plain HTTP client and its effect is visible on DISK afterwards — never only in the UI.
- Starting the panel must never require an interactive terminal: `--no-open` runs
  headless, and nothing prompts. A panel that blocks waiting for a human is unusable by
  the agent that operates this workspace, which is a FAIL.

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

### F-24 — SDD chain E2E, deterministic, in a disposable context
The whole flow with no model in the loop, so it can run anywhere, every time, for free.
- Setup: a clean disposable context `chain` (create + alive as in F-06).
- Run, in order, asserting each on DISK:
  1. `$D backlog new chain-canary --specs-dir repos/chain/specs` → the item exists.
  2. `$D specs release open v0.0.1 --specs-dir repos/chain/specs` → `alpha-1/` carries
     SPEC.md, PLAN.md, TASKS.md and `ACTIVE.md` names release + segment + phase.
  3. Flip each artifact's `**Status:** Draft` to `**Status:** Aprovado` (the canonical
     token — never translate it) → `$D specs doctor` stays 0 errors / 0 warnings.
  4. Add one task line, advance its marker `[ ]` → `[-]` → `[x]`, running
     `$D specs doctor` after EACH transition → clean at every state.
  5. Write `CLOSURE.md` for the release → `$D specs doctor` clean.
  6. `$D backlog doctor --specs-dir repos/chain/specs` → clean (exit 0).
- **PASS if:** every step's disk assertion holds AND both doctors are clean at the END of
  the chain, not only inside each step. A tree that each step declares good but the
  doctors reject afterwards is the exact failure this statement exists to catch — an
  internal gate reading green while a validator finds real defects is itself a defect.

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

### F-26 — Live authoring canary (a real harness materializes a real artifact)
- Setup: a disposable canary context, bound; one Layer-1 harness CLI reachable
  (`claude`, `kimi`, or `codex`). In a nested container export
  `DADAIA_CODEX_SANDBOX=danger-bypass` before driving codex.
- Drive the harness with a bounded fictional demand: "author ONE backlog item in context
  <canary> using `dadaia backlog new`, fill its frontmatter and acceptance criteria, then
  prove it with `dadaia backlog doctor`."
- **PASS if:** a NEW or CHANGED `specs/backlog/*.md` exists on disk afterwards, its
  `intents[]` refs resolve through `$D backlog subjects`, and `backlog doctor` exits 0.
  An agent that reports success with no delta on disk is a FAIL — the deliverable is the
  file, never the final message.
- Mark **EXCEPTION** only if NO harness CLI is installed at all. A sandbox-namespace
  failure is a FAIL, not an EXCEPTION: `danger-bypass` fixes it.

### F-27 — The groups nobody remembers: `clean` and `repos`
Written because the coverage law above caught these two with no statement at all — which
is precisely how a group ships broken while a 50-statement matrix reports APROVADA.
- Run: `$D clean --help` and every subcommand's `--help`; then exercise a reclaim on a
  disposable workspace after seeding a stale file under a `.dadaia/` ephemeral zone
  (`.dadaia/tmp/…`).
- **PASS if:** the seeded stale file is gone afterwards, and nothing outside the ephemeral
  zones was touched — assert a canary file under `.dadaia/states/` still exists. A clean
  that reclaims live state is a CRITICAL FAIL.
- Run: `$D repos list` in a workspace with no catalog present.
- **PASS if:** it refuses or reports empty as ONE clean line naming what it expected —
  never a traceback, never a silent empty success that looks like "no repos exist".

## Real-use matrix — the hermes day-to-day contract (v0.2.9)

**This section is the release gate's second half.** The deterministic matrix above
(F-01…F-27 + the structural certification) proves components in isolation; it is
**never sufficient to approve a release alone**. A candidate is green only when the
real-use statements below — built from the hermes agent's actual day-to-day
inventory — ALL pass with artifact-level evidence (bug
certification-misses-live-codex-backlog-regression-040: a green certification that
never exercised the live backlog path was false confidence).

### R-01 — Live agent chain, end to end, with per-link artifact proofs

- Setup: a clean disposable context on the candidate; one Layer-1 harness reachable
  (`DADAIA_CODEX_SANDBOX=danger-bypass` in nested containers); a bounded real demand.
- Drive the harness through the SDD sequence, one dispatch per link: author a backlog item
  → open and author the release (SPEC/PLAN/TASKS, `Aprovado`) → implement one task under
  marker discipline → close it → audit the result.
- **PASS if ALL of:**
  1. the authored backlog item EXISTS on disk as a NEW or CHANGED `specs/backlog/*.md` —
     an agent that reports "authored" with no delta is a FAIL;
  2. `SPEC.md`/`PLAN.md`/`TASKS.md` exist and carry `**Status:** Aprovado`, and
     `ACTIVE.md` is repointed — never a success report over missing artifacts;
  3. the implemented task's marker reached `[x]` and the change is inside the task's
     declared write set;
  4. the audit produced a report whose findings each carry a disposition;
  5. every produced handoff validates (`$D reports validate`).
- Each link is asserted from DISK, never from the agent's own summary.

### R-02 — Real-demand backlog is canonical and consumable

- Author a backlog item from a real capture demand (`dadaia backlog new`, then fill its
  frontmatter and acceptance) on a real or disposable context, then validate with
  `dadaia backlog doctor --specs-dir <ctx>/specs`.
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
- **PASS if:** `backlog doctor` reports clean AND `dadaia backlog consume` binds the item
  from a SPEC that declares it (the ledger names the canonical `specs/backlog/<slug>.md`
  path — never a bare "done" summary).
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

### R-10 — A refined backlog item is visible on disk, not just claimed

- Author a backlog item, then refine the SAME item's body/acceptance without touching
  its `intents[]`.
- **PASS if:** the refinement is present in the file on disk and `backlog doctor` still
  passes. An agent that reports "updated" while writing NOTHING is a FAIL — the
  deliverable is the file, never the final message
  (bug backlog-dedupe-updated-payload-not-gate-visible-043).

### R-12 — New-surface backlog intents classify by their own identity

- Author two independent NEW CLI-command items (e.g. `hello`, then `version`) using
  `subject: { kind: cli, ref: <name>, surface: new }`.
- **PASS if ALL of:** both items materialize with DISTINCT anchors (two independent new
  CLI surfaces must not collapse onto one shared coarse anchor — bug
  backlog-independent-cli-items-false-conflict-044); a `surface: new` ref that ALREADY
  resolves through `dadaia backlog subjects` is refused with the exact remedy; and an
  unresolved EXISTING ref is refused naming both recoveries (`dadaia backlog subjects` /
  `surface: new`) AND a pasteable command that performs the fix
  (bug backlog-cli-intent-hallucinated-anchor-045 — no refusal is a dead end).

### R-13 — Producers pass their own validators (scaffold / fake / baseline)

- `specs release open v0.1.0` then `specs doctor`; `specs segment open alpha-2` then
  doctor again; `backlog new <slug>` then `backlog doctor`;
  fresh context: `context create` → `alive` → `specs init` → `context baseline`.
- **PASS if ALL of:** both doctors report 0 errors AND 0 warnings on the fresh
  scaffold (Draft + phase SPEC is the legitimate authoring state — bug
  fresh-release-scaffold-emits-spec-doctor-warnings-042); the fake-materialized item
  the generated item is BL-SCHEMA-valid — a scaffolder that emits what its own doctor
  rejects is a FAIL (bug fake-backlog-workflow-materializes-doctor-invalid-status-042);
  and baseline COMPLETES after the official scaffold follow-up while still refusing a
  tree carrying operator files (bug context-baseline-rejects-official-scaffold-followup).
- **A GATE is a validator too** (bug r4g-backlog-surface-new-existing-accepted): take
  what a verb's own guard ACCEPTED and run the matching doctor over it. A command that
  exits 0 while `backlog doctor` / `specs doctor` rejects its output is a FAIL — the
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
- **PASS if ALL of the above hold.** A registry-derived allowlist narrowing (e.g. a
  provider-qualified PI id that no longer maps) must fail LOUDLY at load with a
  message naming the rejected id — never silently accept an unmapped model.

### R-16 — Every prescribed remedy actually WORKS (no contradiction loops)

A block that names a command which cannot run is worse than a block with no advice:
the operator burns a cycle proving the tool wrong. This class keeps recurring — most
recently `r6-release-open-guard-remedy-placeholder-not-pasteable`, where a refusal
prescribed `segment open <alpha-N|rc-N>` and the literal placeholder failed — so it gets
its own sweep.

- For every refusal you can reach in this run — a doctor, a gate, a guard, a chokepoint —
  take the command its message prescribes and **execute it verbatim**.
- **PASS if ALL of:** the prescribed command is executable as written (the verb and flags
  it cites exist), and it changes the state or explains precisely why it cannot; no
  prescribed remedy raises a raw traceback; and a refusal that has NO mechanical remedy
  says so in-band rather than naming a command that cannot help.

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
N backlog items authored, consumed by ONE release, then implemented and closed — driven by
an AGENT operating the CLI, which is what the workspace is for. Run it in a FRESH consumer
workspace. Every step is asserted on DISK, never from the agent's summary:

1. `init` a fresh workspace, `context create` + `context alive` a scratch context, `bind` it.
2. Author **THREE** backlog items from three distinct demands (`backlog new` ×3, each with
   its own `ref:` anchor and acceptance criteria). **PASS if:** `specs/backlog/` gains
   THREE items with THREE distinct anchors. One item, or three sharing one anchor, is a
   FAIL — an agent that reports success while overwriting its previous deliverable is the
   exact class this recipe exists to catch.
3. Open ONE release and author its SPEC declaring `**Consumes:** slug-a, slug-b, slug-c`.
   Run `$D backlog consume --release-id <id>`. **PASS if:** it names ALL THREE slugs, binds
   all three anchors, and `specs/_archive/<id>/consumed_backlog.json` EXISTS on disk. An
   empty consumed set reported as `OK` is a FAIL, not a no-op.
4. **Assert the negative too:** drop one slug from `**Consumes:**` and re-run consume —
   it must FAIL naming the dropped slug. A verification that cannot fail is not a
   verification.
5. Implement the release under marker discipline (`[ ]`→`[-]`→`[x]`), then close it and run
   `$D backlog remove-consumed --release-id <id>`. **PASS if:** all three items leave the
   live SET (a copy archived first) and `$D backlog doctor` reports zero BL-STALE.
6. Run an audit against the release and disposition every finding. **PASS if:** the report
   exists, each finding carries `fixed`/`superseded`/`deferred`/`rejected` with a reason,
   and `$D specs doctor` does not report an undispositioned audit.

Report each numbered step's verdict separately with the disk evidence you checked. A FAIL
anywhere here outranks every F-statement: it means the product cannot do the one thing it
exists to do.

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

### R-23 — Every block is a command you can paste, not advice about one

Provoke a refusal on each surface that prescribes a command — the doctors, the gate, the
git chokepoints, the backlog/release guards.

**The test is: copy the line verbatim into the shell and it runs and does the whole fix.**
Nothing else. Judge it by that and not by how it looks.

**PASS if** every command printed in a refusal carries the real context/paths it applies
to and pasting it verbatim runs. Two shapes are explicitly legal and must not be reported
as failures:

- a leading `NAME=value` environment assignment (e.g.
  `DADAIA_CODEX_SANDBOX=danger-bypass dadaia …`) — when the refusal was caused by the
  environment, the escape hatch is *part of* the command, and a remedy that made the
  operator remember to prepend it would be exactly the omission this item exists to catch;
- a trailing `  # note` explaining what the command re-executes — the shell ignores it.

**FAIL if** any of them reads like instructions ("re-run it with …", "re-author the
artifact that …", "inspect …"), names a `<placeholder>`, omits a field you would have
to remember, **or hides a second command inside the trailing comment** — pasting that line
runs only the first half and says nothing about the rest, so the operator believes they
followed the remedy when they did not.

> An earlier wording of this item demanded that the command "begin with `dadaia `", which
> contradicted the environment-prefix requirement in the same round and manufactured a
> false FAIL. Begins-with was never the property that mattered; runs-when-pasted is.

This has now been reported five times on five different routes. When you find one, do not
stop at it: grep the whole output of the round for `re-run`, `inspect`, and `re-execute`
and report every occurrence together — a class fixed one instance at a time is a class
that survives.

### R-24 — A malformed artifact is diagnosed where it is WRITTEN

Hand-write a broken backlog item, one variant per run: frontmatter that opens and never
closes; frontmatter with keys and a closing `---` but no opening one; and unparseable YAML
inside a well-formed block. Then run `dadaia backlog doctor`. **PASS if** each is refused
naming the actual defect ("unterminated", "missing its opening delimiter", the YAML error
with line/column). **FAIL if** any is allowed through and surfaces later as a missing
status or absent intents — a diagnosis that names the wrong thing, about a file the
operator will
then inspect looking for the wrong problem.

Guard the other way too: a normal item containing a Markdown horizontal rule (`---` after
prose) must NOT be called malformed. A false positive here is worse than the defect,
because nothing the operator changes will make it go away.

### R-25 — An artifact may not say two different things about its own status

After ANY live release definition completes, open SPEC.md, PLAN.md and TASKS.md and read
them the way a human does. **PASS if** each declares its status exactly once and that
declaration is `> **Status:** Aprovado`. **FAIL if** a file carries a second status
declaration in any decorated form — a heading (`## Status: Draft`), a bullet, a
blockquote — alongside the canonical line, or if the release was moved into
IMPLEMENTATION while any artifact still reads Draft to a reader.

This is the shape that produced a false completed definition on R23/F-26: the single-
writer normalization enumerated the prefixes workers had used so far, a live model wrote
the status as a Markdown heading, and Python inserted its canonical line ALONGSIDE it. The
gate saw Aprovado, the human saw Draft, and the release entered IMPLEMENTATION.

Generalize while you sweep: wherever the product NORMALIZES worker-authored text to a
canonical form, try the ordinary variants a model actually writes — headings, bold, bullets,
extra whitespace, a missing accent — and check the result declares itself exactly once. Any
normalizer written as a list of known shapes is one live worker behind.

### R-27 — A gate must name the defect it actually found

The lesson of round 24. A PLAN lint refused a live artifact twice with *"every validation
dependency row must contain all five non-empty cells"* — while not one cell was empty. The
real defect was a `|` inside an `rg` command in the "Direct validation" column, which the
lint split into extra cells. The author, told nothing true, rewrote the same correct table
and the definition went nowhere.

A wrong diagnosis is worse than a strict gate, because a retry loop can only converge on
what it is told. Drive each deterministic gate — the plan dependency lint, the frontmatter
parser, the status normalizer, the terminal semantic gate — into failure **and then read
the message as if you were the one who had to fix it**. **PASS if** the message names the
offending artifact, the offending row/line, and what is wrong with it, such that a second
attempt written only from that message would pass. **FAIL if** the message asserts
something that is not true of the artifact, names a different defect than the one present,
or describes the rule without pointing at the violation.

Then check the other side: feed each gate the artifact shape a competent author would
naturally write — a validation column holding a real shell command with a pipe in it, a
backlog item containing a Markdown horizontal rule, a localized heading — and confirm it
is accepted. A gate that rejects the honest answer to its own question has no correct
input, and no operator can escape it.

---

## Harness parity audit — H-01..H-06 (audit, never alteration)

dadaia defines each capability abstractly — a persona, a deterministic behaviour, a rule,
a skill — and every entry harness derives its own entity from it. That claim is only worth
anything if the derived entities actually WORK in each harness. This section is an
**audit**: you observe and report. **Do not repair, re-project, or hand-edit any harness
entity during it** — a fix inside the check destroys the evidence, and a projection you
healed is a projection you can no longer say was broken.

Run the whole section **twice**, once per harness: `claude-code` and `kimi-code`. Report
each statement per harness, and report the DELTA between them explicitly — parity is the
subject, so "both PASS" and "both FAIL identically" are different findings from "one PASS,
one FAIL", and only the last one means the abstraction leaked.

### H-01 — The harness projects, from one install
- Run `$D init --harness <harness>` in a disposable dir (for kimi, export a throwaway
  `KIMI_CODE_HOME` first), then `$D public doctor`.
- **PASS if:** the harness's own tree exists (`.claude/` / `.kimi-code/` plus its
  user-level wiring), `public doctor` reports every asset `[ok]` with exit 0, and no asset
  is `[drift]`/`[missing]` on a profile scoped to that harness alone.

### H-02 — Hooks fire, and decide the same way in both harnesses
- Drive the projected pre-gate entrypoint for that harness directly with the four F-08
  payloads (ADDITIVE allow, FROZEN block, PROTECTED block, root-whitelist block).
- **PASS if:** all four decisions match F-08 **and match the other harness's decision for
  the same payload**. A path class allowed in one harness and blocked in the
  other is a parity FAIL, and it is the most serious finding this section can produce: the
  gate is the safety boundary, and a boundary that depends on which CLI you launched is
  not a boundary.
- Also assert the envelope contract per harness (F-08): Claude Code's PreToolUse schema on
  one side, the kimi shim's string-matching contract on the other. An envelope that
  satisfies one and breaks the other is a FAIL even when the DECISION is identical.

### H-03 — Context injection reaches the session
- `$D context bind <ctx>` in a session of that harness, then trigger the injection path
  the harness uses (session start / next prompt / post-compact).
- **PASS if:** the context's memory is injected exactly ONCE per bind epoch, an unbound
  session receives generic preflight and NO context memory, and a re-bind re-injects.
  Injection that never fires, or fires on every prompt, are both FAILs.
- **Compaction is a legitimate second trigger, not a double-injection.** A harness that
  compacts its context has DROPPED the memory, so re-injecting exactly once on the next
  prompt is the contract, not a defect — check each harness's own documented compaction
  behaviour before calling it a FAIL. The bug shape is re-injecting *more than once* for
  a single compaction, or never re-injecting after one.

### H-04 — Sub-agents exist and are dispatchable
- List the harness's agent entities and compare them to the persona roster (the nine core
  personas plus the three install-gated plugin stubs).
- **First establish whether the harness can express a custom agent at all.** Some entry
  harnesses have no project-level agent surface; for those, "zero persona entities" is a
  documented platform limitation, NOT a projection defect. Report it under `PARIDADE` as a
  **capability gap** with the evidence (the harness CLI has no such command, and dadaia's
  own scoped `AGENTS.md` for that harness says so) — never as a FAIL. A FAIL here means a
  harness that CAN express agents and still has none, or has one with no persona behind it.
- **PASS if:** for every harness that supports custom agents, each entity maps to a persona
  and each persona has an entity — no orphan entity, no persona without a projection. Then
  DISPATCH one leaf specialist in that harness with a trivial bounded task and confirm it
  runs and returns.
- A stub plugin persona must answer with the `[PLUGIN REQUIRED]` line, not attempt the
  work. An entity whose declared authority contradicts its persona's is a FAIL — report
  the contradiction, do not fix it.

### H-05 — Skills load and rules bind
- In each harness, confirm the universal skills are present and loadable
  (`.agents/skills/**`), and that the scoped `AGENTS.md` files are read where they apply.
- **PASS if:** the same skill body is available in both harnesses (skills are harness-
  universal by definition — a skill present in one and absent in the other is a
  projection defect), and a rule that forbids an action actually surfaces when the action
  is attempted in a session.
- Read the always-loaded root law in each harness and confirm it does not prescribe a
  command that does not exist. Instruction that cannot be followed is a defect of the
  same severity as code that cannot run.

### H-06 — What the harnesses may NOT share
- **PASS if:** each harness's entities live only under its own tree, and nothing in one
  harness's projection names or edits another's. Harnesses know nothing about each other;
  a cross-harness reference is a FAIL.
- Report — never repair — any hand-edited (locally diverged) projected file you find:
  name the file and the drift. Repair is the operator's call, after the audit.

**Report for this section:** one table, statements as rows, `claude-code` and `kimi-code`
as columns, plus a `PARIDADE` line naming every statement whose two verdicts differ.

**Verdict line (Telegram-short, last line of output):**
`<version> — <APROVADA|BLOQUEADA|APROVADA COM EXCEÇÃO EXPLÍCITA> — <N> PASS / <M> FAIL / <K> EXCEPTION — paridade: <ok|N divergências> — grupos sem cobertura: <lista|nenhum> — bugs: <ids|nenhum> — evidência: <path>`

APROVADA requires 0 FAIL. EXCEPTIONs are listed but do not block; note each so the
operator can decide. Persist per-statement evidence; register every FAIL as a bug
before the run ends.
