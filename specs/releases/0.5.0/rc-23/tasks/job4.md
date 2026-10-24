# Job 4 — task variants: the render script (FR3)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN section 1 (R06, R07) and section 5 (H8). Wave 2, beside Jobs 3 and 5 (disjoint `W:`); it opens when Jobs 1 and 2 have merged.

**Contract.** `render.py OUT HARNESS LABEL` copies the tracked `evals/tasks/` (found relative to the script) into the new directory `OUT`, then changes exactly two tokens: in `t1-cold-onboarding/instruction.md` the words `Claude Code harness` become `LABEL harness`, and in `t2-block-list-bug/environment/project.sh` `--harness claude` becomes `--harness HARNESS`. Every `tests/` folder, every Dockerfile and every `task.toml` is a byte copy. The tracked tree is never written (AC3.1). `OUT` is chosen by the caller outside the checkout (`$RUNNER_TEMP`), so no rendered file can be committed. A Claude leg does not render: the tracked tasks are its variant. A token that is absent from its file is an error, not a silent copy, so a reworded instruction cannot drift unseen (the T3 bug pair in PLAN section 1 R06 was an instruction that drifted from its grader).

**Definition of done (each task).** `python scripts/ci.py job` passes (about 73 s); the reached test `python -m pytest -q tests/e2e/test_evals_render.py` passes (an estimate of a second or two: one directory copy per row); for the implementation task, reverting `render.py` makes the RED rows red again; the own-diff self-check of `dd-release-implementation` section 3. The test file carries its `Owner:` line and no task or AC id in a docstring. No tracked file under `evals/tasks/` appears in `git diff --name-only <base>...HEAD` (AC3.2).

| task | who | AC | `W:` | waits on | tests | outcome |
|---|---|---|---|---|---|---|
| J4.T1 | sr | AC3.1 | `tests/e2e/test_evals_render.py` | - | owner `tests/e2e/test_evals_render.py`. RED: render `codex` / `Codex` into `tmp_path`; the set of files that differ from the tracked tree is exactly the two named files and each differs in exactly its token; every file under a `tests/` folder is byte-equal; the tracked tree's bytes are unchanged after the run; a token missing from a copied tree exits non-zero | RED acceptance test for the render |
| J4.T2 | jr | AC3.1 | `evals/scripts/render.py` | J4.T1 | owner `tests/e2e/test_evals_render.py` | ADD `render.py` (no unit carries it); about 25 lines |
