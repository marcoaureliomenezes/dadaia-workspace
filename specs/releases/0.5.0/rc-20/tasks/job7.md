# Job 7 — eval T3, discovery (FR6; backlog `eval-t3-discovery`, ADR 0269(b))

**Status:** Draft

Wave 2, waits on Job 3 (the SPEC orders FR4 and FR5 first; no file is shared). Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §2 (seam AC6.2, T3 grader). A new capability: no unit carries a vague-goal eval, so the diff is an addition (PLAN §4).

- **Shape.** `evals/tasks/t3-discovery/` takes T1's layout (`evals/tasks/t1-cold-onboarding/`): `task.toml` (`schema_version "1.4"`, verifier 300 s, agent 900 s, `network_mode = "public"`), `instruction.md`, `environment/Dockerfile`, `tests/test.sh` (T1's two lines writing the reward) and `tests/test_grade.py`. `eval.yml` runs it unchanged through `harbor run -p evals/tasks`: it needs no new secret, no edit of `eval.yml`, `compare.py` (`FLOOR` already holds `t3-discovery: 2`) or `scan.py`.
- **Dockerfile.** T1's base and demo project (`file:///srv/demo.git`), `ARG CLAUDE_CODE_VERSION=2.1.284` (the guard `eval-cli-pin` compares it with `eval.yml`), no `ln -s` of `dadaia` into `PATH`, `COPY lib/ /lib/` last, then the wheelhouse step and the four `ENV` lines of PLAN §2 (seam AC6.2).
- **Instruction.** A vague goal: it names `dadaia-workspace` and the project at `file:///srv/demo.git`, asks the agent to try the tool on that project and to keep using it. It names no command, no install path, no doc URL, no verb.
- **Grader (AC6.3).** `test_grade.py` in T1's style (`dadaia` run through `/workspace/.dadaia/.venv/bin/dadaia … --json`): exactly one ALIVE context on the URL, `specs/constitution.md` present, `doctor` with no error, and at least one entry under `active[]` in a `BACKLOG.json` of that repo or of one of its lane trees (PLAN §2). It passes a hand-done workspace and fails an empty one.
- **Stop condition.** If the image cannot make `pip` and `uv` resolve from the wheelhouse only, T2 stops after its first build and returns the question to the main thread; T3 does not start (SPEC §5).
- **Out of this job.** The Hermes readout (the operator sets the keys; rc-21), the runs for the record (rc-21), the atom `agent-evals.md` (closure memory pass).
- **Contract tests that stay green:** `tests/e2e/test_evals_t1.py`, `test_evals_t2.py`, `test_evals_scripts.py`, the guard `eval-cli-pin` (`scripts/guards/repo.py:280`). They are not edited.

**Gate law.** `verify:` is `python scripts/ci.py job`, no change. Definition of done: that run, then `tests/e2e/test_evals_t3.py` (Docker required; T1's four-image suite took 95 s on `ubuntu-24.04`, `tests/e2e/test_evals_t1.py:6-7`, so the T3 file is about half that: a source-quoted estimate, not a measurement) and `tests/e2e/test_evals_t1.py` untouched and green, the own-diff self-check, the sweep greps.

**Sweep greps.** `git grep -nE "dadaia|uvx|pip install|http" -- evals/tasks/t3-discovery/instruction.md` prints one line, the `file://` project and the tool name, and no command; `git grep -n "ln -s" -- evals/tasks/t3-discovery` prints nothing; `git grep -n "CLAUDE_CODE_VERSION=" -- evals/tasks .github/workflows/eval.yml` prints the same value on every line.

Tasks: 3 (3 sr). T2 after T1; T3 after T2.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J7.T1 | sr | AC6.2, AC6.3 | `tests/e2e/test_evals_t3.py`, `tests/helpers/evals.py` | RED, E2E (Docker; a missing tool fails the row). `T3 = "t3-discovery"` and its hand path per version in the helper. For each of `VERSIONS`: the image builds; `command -v dadaia` in it exits 1; a plain `python3 -m venv /tmp/v && /tmp/v/bin/pip install dadaia-workspace && /tmp/v/bin/dadaia --version` prints the lib build's version (the candidate wheel's, or `0.4.7`), never PyPI's newer one; the grader passes the version's hand-done workspace (init, specs init, one backlog entry in a lane) and fails an empty one (fails today: no task folder) |
| J7.T2 | sr | AC6.1, AC6.2 | `evals/tasks/t3-discovery/environment/Dockerfile`, `evals/tasks/t3-discovery/task.toml` | the Dockerfile and `task.toml` (Dockerfile and Stop condition bullets); owner `test_evals_t3.py` rows 1 and 2 |
| J7.T3 | sr | AC6.1, AC6.3 | `evals/tasks/t3-discovery/instruction.md`, `evals/tasks/t3-discovery/tests/test.sh`, `evals/tasks/t3-discovery/tests/test_grade.py` | the instruction and the grader (Instruction and Grader bullets); owner `test_evals_t3.py` rows 3 and 4 |
