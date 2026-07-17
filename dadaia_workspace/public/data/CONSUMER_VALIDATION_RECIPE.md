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

Setup once:

```bash
python3 -m venv /tmp/val-venv && /tmp/val-venv/bin/pip install <wheel>
export DADAIA_BOOTSTRAP_PACKAGE=<wheel>   # REQUIRED for a candidate wheel
D=/tmp/val-venv/bin/dadaia
```

`DADAIA_BOOTSTRAP_PACKAGE` makes every workspace-venv bootstrap (`init`, `certify`,
`reconcile`) install the CANDIDATE wheel itself instead of pinning the version from
PyPI — an unpublished candidate is the validation norm, and without this export every
`init` fails with "No matching distribution found". Destructive statements use
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
- **PASS if:** exit 0 and all checks report pass; and this verdict does not contradict
  F-02 (certify-green while reconcile-red, or vice versa, is a FAIL of this statement).

### F-04 — Doctors
- Run in an initialized workspace: `$D doctor`; `$D public doctor`; and a specs tree
  INSIDE a repo: `mkdir -p repos/valproj && $D specs init --specs-dir
  repos/valproj/specs && $D specs doctor --specs-dir repos/valproj/specs`.
- Also assert coherence: bare `$D specs init` AT the workspace root must REFUSE
  (Root Law — init must not create what doctor refuses), exit non-zero, no `specs/`
  created.
- **PASS if:** doctor/public-doctor/specs-doctor exit 0 on the clean tree, the root
  `specs init` refusal holds, and seeding one violation (`mkdir .dadaia/nonsense`)
  makes `$D doctor` exit non-zero naming ROOT-4.

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
  repos/valproj/specs` (must be valid JSON); add a backlog item missing `intents[]`
  under `repos/valproj/specs/backlog/` and run the backlog doctor path.
- **PASS if:** `specs doctor --json` emits parseable JSON exit 0; the malformed backlog
  item is flagged BL-SCHEMA.

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
- Setup: write a minimal VALID `handoff-v1.2` JSON to a file. Minimal valid = these keys:
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

### F-18 — Init / onboarding
- Run in an empty dir: `$D init --harness all`.
- **PASS if:** exit 0, `.dadaia/` bootstrapped (venv + projections), and `$D doctor`
  green afterward. (Init builds a venv — the env must allow PyPI; if egress is blocked
  mark EXCEPTION with the network cause, else FAIL.)

### F-19 — Plugins
- Run in an initialized workspace: `$D plugin list`.
- **PASS if:** it lists installed packs (empty set on a fresh workspace is a valid
  answer — exit 0, "no plugins", NOT an error). Then `$D plugin install <pack>` records
  the ledger and doctor stays green. `plugin list` in an UNINITIALIZED dir returning a
  clean "run init first" message (non-zero) is acceptable, not a FAIL.

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

---
**Verdict line (Telegram-short, last line of output):**
`<version> — <APROVADA|BLOQUEADA|APROVADA COM EXCEÇÃO EXPLÍCITA> — <N> PASS / <M> FAIL / <K> EXCEPTION — bugs: <ids|nenhum> — evidência: <path>`

APROVADA requires 0 FAIL. EXCEPTIONs are listed but do not block; note each so the
operator can decide. Persist per-statement evidence; register every FAIL as a bug
before the run ends.
