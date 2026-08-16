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
  prerequisite the wheel does not own (e.g. no codex binary reachable for a live
  model-reachability check). Record why; an EXCEPTION is NOT a FAIL and does not block
  on its own.

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

### F-03 — Certify agrees with reconcile
- Run: `$D certify --json`.
- **PASS if:** exit 0 and all checks report pass; the verdict does not contradict F-02
  (certify-green while reconcile-red, or vice versa, is a FAIL); AND the check ledger
  proves the real surface, not just reachability: `capability-contract`,
  `exact-version-reconciliation`, `context-empty-remote-baseline`,
  `context-list-show-json`, `context-bind-heartbeat`, `reports-handoff-validation`,
  `panel-and-server-registry`, and `context-dead-alive-delete-roundtrip` all PASS with
  "no traceback".

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
  repos/valproj/specs` (must be valid JSON); plant the malformed item as an `## ACTIVE`
  subsection directly in `repos/valproj/specs/backlog/BACKLOG.md` (the single source —
  `dadaia backlog new <slug> --specs-dir repos/valproj/specs` creates the document with
  both section headings if it does not exist yet; then edit the new subsection's
  `**Status:**` to `candidate` and leave it with no `**Intents:**` block), then run the
  backlog-specific doctor — `$D backlog doctor --specs-dir repos/valproj/specs` (NOT
  `specs doctor`, which validates the single-source loose-file/consumption invariants
  SPEC-DOC-031/035, not the ACTIVE-subsection schema; BL-SCHEMA is the `backlog doctor`
  path). Assert its exit code directly, not through a pipe.
- **PASS if:** `specs doctor --json` emits parseable JSON exit 0; and `backlog doctor`
  flags the malformed item `[ERROR] BL-SCHEMA` and exits non-zero.

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

---

## Real-use matrix — the consumer day-to-day contract (v0.2.9)

**This section is the release gate's second half.** The deterministic matrix above
(F-01…F-25 + the structural certification) proves components in isolation; it is
**never sufficient to approve a release alone**. A candidate is green only when the
real-use statements below — built from the consumer agent's actual day-to-day
inventory — ALL pass with artifact-level evidence (bug
certification-misses-live-codex-backlog-regression-040: a green certification that
never exercised the live backlog path was false confidence).

### R-02 — Real-demand backlog is canonical and consumable

- Author a B3/CVM-style real capture item as `project-manager`/`product-engineer` would
  (`dadaia backlog new <slug>` then fill in its `**Intents:**` block, the single-source
  ACTIVE subsection — SPEC v0.12.0 FR3, ADR #14), then `dadaia backlog subjects
  --specs-dir <ctx>/specs`.
- **PASS if:** every emitted `intents[].ref` resolves against the live registry (no
  unresolved subjects) AND a release SPEC naming the item under `**Consumes:**` is
  accepted by `specs doctor`, with the declared slug resolving to an `## ACTIVE`
  subsection in `specs/backlog/BACKLOG.md`.

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

### R-08 — Kimi Code harness end to end (v0.2.8 surface)

- Setup: `export KIMI_CODE_HOME=<throwaway>`; `$D init --harness kimi-code` in a
  disposable dir.
- **Binding posture:** kimi-code exposes no session-id env var, so its binding is the
  exported `DADAIA_CONTEXT=<ctx>` at harness launch (the law's rung 1) — `dadaia
  context bind` alone cannot key a kimi session record and warns saying so.
- **PASS if ALL of:** `.kimi-code/AGENTS.md` exists; the managed `[[hooks]]` block
  and four `dadaia-kimi-*` shims exist under `$KIMI_CODE_HOME`; the pre-gate shim
  allows a normal write (exit 0) and blocks a root-law violation (exit 2 + stderr
  reason naming `.kimi-code/` among allowed entries); ctx-inject injects with
  `DADAIA_CONTEXT` exported at launch; the post-compact shim stamps `ctx-compact-<sid>` AND
  re-emits the bootstrap on stdout, and the next prompt re-injects exactly once;
  `dadaia public doctor` is green (incl. `dadaia:scripts/*` on a kimi-only profile);
  `dadaia public doctor` flags a tampered shim/block and `install` heals it.

### R-13 — Producers pass their own validators (scaffold / backlog / baseline)

- `specs release open v0.1.0` then `specs doctor`; `specs segment open alpha-2` then
  doctor again; `backlog new <slug>` then `backlog doctor`; fresh context:
  `context create` → `alive` → `specs init` → `context baseline`.
- **PASS if ALL of:** both doctors report 0 errors AND 0 warnings on the fresh
  scaffold (Draft + phase SPEC is the legitimate authoring state — bug
  fresh-release-scaffold-emits-spec-doctor-warnings-042); the freshly-created ACTIVE
  subsection in `specs/backlog/BACKLOG.md` (the single source, SPEC v0.12.0 FR3, ADR #14)
  is BL-SCHEMA-valid out of the box; and baseline COMPLETES after the official
  scaffold follow-up while still refusing a tree carrying operator files (bug
  context-baseline-rejects-official-scaffold-followup).
- **A GATE is a validator too** (bug r4g-backlog-surface-new-existing-accepted): take
  what `backlog doctor` ACCEPTED and run `specs doctor` over the same tree. A tree that
  passes one while the other rejects it is a FAIL — the two must never hold two
  opinions. Probe the degenerate inputs specifically: an item with NO `intents[]` at
  `candidate` status (must block; `idea` stays exempt), and an empty/absent field where
  the checks could be *vacuously* satisfied rather than actually passed.

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
  provider-qualified model id that no longer maps) must fail LOUDLY at load with a
  message naming the rejected id — never silently accept an unmapped model.

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
names, that is a product FAIL of this statement.

**Verdict line (Telegram-short, last line of output):**
`<version> — <APROVADA|BLOQUEADA|APROVADA COM EXCEÇÃO EXPLÍCITA> — <N> PASS / <M> FAIL / <K> EXCEPTION — bugs: <ids|nenhum> — evidência: <path>`

APROVADA requires 0 FAIL. EXCEPTIONs are listed but do not block; note each so the
operator can decide. Persist per-statement evidence; register every FAIL as a bug
before the run ends.
