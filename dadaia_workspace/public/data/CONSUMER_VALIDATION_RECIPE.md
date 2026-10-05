# Consumer Validation Recipe — dadaia-workspace

- Read first: memory atoms `platform/consumer-agent-support`, `distribution/pypi-distribution` and `QUALITY.md`; they hold the behavior, this file only lists the checks.
- Run every check against the INSTALLED candidate wheel, in throwaway dirs under `/tmp`, never the production workspace; read this copy from that wheel.
- Setup: `python3 -m venv /tmp/val && /tmp/val/bin/pip install <wheel>`; `D=/tmp/val/bin/dadaia`; `export DADAIA_BOOTSTRAP_PACKAGE=<wheel>` except where a check unsets it.
- A workspace: `$D init /tmp/w<NN> --harness claude && cd /tmp/w<NN>`; skill scripts: `S=.agents/skills`.
- Assert every exit code directly, never through a pipe; capture command, exit code and output as evidence.
- Mark each check PASS, FAIL (register it with `python3 $S/dd-bug-resolution/scripts/bugs.py append`) or EXCEPTION (the environment lacks a prerequisite the wheel does not own).
- Sweep the whole list every run; on a FAIL, probe the same defect class on every sibling surface in the same run.
- A cited command or flag that does not exist is a FAIL; check it against live `--help` first.

## Deterministic checks (F-)

- F-01 `$D --version`; `$D capabilities --json` → exit 0; `.provider.distribution_version` equals the candidate version.
- F-02 seed `.dadaia/nonsense` and a 2-day-old file under `.dadaia/tmp/`; `$D doctor` → non-zero, `WS-dadaia-slop` and `WS-tmp-expired` lines; `$D doctor --fix` → slop moved under `.dadaia/reaped/<YYYYMMDD>/`; `$D doctor` → exit 0.
- F-03 `$D certify --json` → exit 0, every check passes: `workspace-init`, `capability-contract`, `exact-version-reconciliation`, `specs-scaffold-and-doctor`, `context-empty-remote-baseline`, `context-list-show-json`, `context-bind`, `context-specs-doctor`, `reports-handoff-validation`, `context-dead-alive-delete-roundtrip`.
- F-04 `$D doctor`; `$D public doctor`; `$D specs init --specs-dir repos/vp/specs` then `$D doctor --specs-dir repos/vp/specs` → exit 0; bare `$D specs init` at the workspace root → non-zero, no `specs/` created.
- F-05 `$D public stage`; `$D public install`; `$D public doctor` → exit 0, every asset `[ok]`.
- F-06 `$D context create alpha --main-repo file:///tmp/f06/src.git`; `$D context list --json`; `$D context show alpha --json`; `$D context dead alpha`; `$D context alive alpha`; `$D doctor --context alpha` → 0 errors, 0 warnings; `$D context dead ghost` → non-zero, no traceback.
- F-07 `export DADAIA_SESSION_ID=f07`; unbound `$D context show --json` → `{"context": null}`; `$D context bind beta` twice → same session id, one session record.
- F-08 pipe PreToolUse JSON payloads into `python -m dadaia_workspace.hooks.pre_gate`: with vp bound, `repos/vp/specs/bugs/BUGS.jsonl` → block, `repos/vp/specs/audits/x/AUDIT.md` → allow, `.dadaia/reports/vp/r.html` → allow; `.dadaia/sessions/x` → block; a new root entry → block; each block carries one `fix:` line that is itself allowed.
- F-09 `python3 $S/dd-bug-resolution/scripts/bugs.py append` with every required field `--specs repos/vp/specs` → exit 0, listed by `bugs.py status --specs repos/vp/specs`; an append missing fields → non-zero, nothing written.
- F-10 `$D doctor --json --specs-dir repos/vp/specs` → parseable JSON, exit 0; a `candidate` entry with no `intents[]` in `BACKLOG.json` → `BL-SCHEMA`, non-zero.
- F-12 `$D reports validate <good>.handoff.json` → exit 0 for a document valid against `.dadaia/agentic/schemas/handoff-v1.schema.json`; a tampered copy → non-zero, names the failure.
- F-14 `python3 $S/dd-cli-library/scripts/registry.py register --port <p> --project val`; re-register → exit 0; `--project other` on the same port → exit 1, names the owner.
- F-15 `python3 $S/dd-spec-navigator/scripts/memory.py catalog generate --specs repos/vp/specs`; `$D doctor --specs-dir repos/vp/specs` → 0 errors, 0 warnings.
- F-16 `$D export` → writes `.dadaia/dist/spec-contexts.json` only; in a new workspace `$D import <file>` → contexts DEAD; `$D context alive <slug>` clones; `$D doctor` → exit 0.
- F-17 `$D migrate --dry-run` then `$D migrate -y` on a v1 `spec_contexts.json` → schema_version 2, a re-run prints nothing to do; `$D specs upgrade --specs-dir <old tree>` → nothing dropped, `$D doctor` 0 errors.
- F-18 `unset DADAIA_BOOTSTRAP_PACKAGE`; `$D init ws --harness claude` → exit 0, no `ERROR:`/`Traceback`; `env -i PATH="$PATH" ws/.dadaia/.venv/bin/python -c "import importlib.metadata as m; print(m.version('dadaia-workspace'))"` prints the candidate version.
- F-22 `--help` on every verb → purpose and usage; no raw traceback anywhere in the run.
- F-23 `.claude/settings.json` registers `SessionStart` matchers `compact` and `clear` on `dadaia_workspace.hooks.ctx_inject`; a `compact` payload on a bound session re-emits the bootstrap once; an unbound session gets only the generic preflight.
- F-25 `unset DADAIA_BOOTSTRAP_PACKAGE`; `$D certify --json` → `workspace-init` and `exact-version-reconciliation` pass for an unpublished candidate.

## Real-use checks (R-) — required with the F- checks, never optional

- R-02 `python3 $S/dd-backlog-definition/scripts/backlog.py new <slug> --specs <specs>`, fill its intents; `$D doctor --specs-dir <specs>` accepts every ref.
- R-03 `$D specs init --specs-dir /tmp/r03/specs`; `$D doctor --specs-dir /tmp/r03/specs` → 0 errors, 0 warnings.
- R-04 a placeholder atom in a fresh tree: `$D doctor --fix --specs-dir <specs>` → 0/0; `$D specs upgrade --specs-dir <specs>` repairs it; filled atoms untouched.
- R-06 `bugs.py append`, then `bugs.py resolve <id>` with its evidence flags, then `bugs.py status` → the record reads resolved; `bugs.py check --specs <specs>` → exit 0.
- R-08 `export KIMI_CODE_HOME=<tmp>`; `$D init ws --harness kimi-code` → `.kimi-code/AGENTS.md` and four `dadaia-kimi-*` shims; the pre-gate shim blocks a root-law write with exit 2; `$D public doctor` → exit 0, a tampered shim flagged and healed by `$D public install`.
- R-13 `python3 $S/dd-release-implementation/scripts/release.py new 0.1.0 --specs <specs>`; `backlog.py new`; `$D context create` → `$D context bind` → `$D specs init --context` → `$D context baseline` → `$D doctor` 0/0 after each; a gate never accepts what the doctor rejects.
- R-15 every distinct `model` in `.codex/agents/*.toml` answers one `codex exec --model <id>`; `.claude/agents/*.md` and `.codex/agents/*.toml` render from one roster; `$D public doctor` → `[ok] model-resolution`.
- R-17 `$D init` on a `noexec` mount → non-zero, one line naming the path and cause, no traceback; an exec-capable mount still bootstraps.
- R-18 `DADAIA_BOOTSTRAP_PACKAGE=/does/not/exist.whl $D init ws` → non-zero, no traceback; with `DADAIA_TRACEBACK=1` → the traceback prints; every verb with an invalid argument → no `Traceback (most recent call last)`.
- R-21 `KIMI_CODE_HOME` on a `noexec` mount: `$D harness add kimi-code`; `$D public doctor` → `[unsupported]` shims, exit 0; `$D reconcile --expect-version <ver>` → succeeds; a `chmod 0644` shim on a normal mount → `[drift]`, cleared by `$D harness add kimi-code`.

## Verdict — the last output line

- `<version> — <APPROVED|BLOCKED|APPROVED WITH EXPLICIT EXCEPTION> — <N> PASS / <M> FAIL / <K> EXCEPTION — bugs: <ids|none> — evidence: <path>`
- APPROVED requires 0 FAIL; list every EXCEPTION; register every FAIL before the run ends.
