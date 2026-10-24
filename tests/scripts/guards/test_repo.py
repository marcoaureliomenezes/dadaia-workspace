"""The tests-mirror guard's refusals: each fix names the real path and owner, no placeholder."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest


class _Tree:
    def tracked(self, *_spec: str) -> list[str]:
        return ["tests/e2e/test_journey.py", "tests/test_loose.py"]

    def read(self, _rel: str) -> str:
        return '"""A journey."""\n'


@pytest.mark.medium
def test_each_mirror_refusal_names_its_file_and_a_real_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts" / "guards"))
    repo = importlib.import_module("repo")
    assert repo.tests_mirror_the_package(_Tree()) == [  # type: ignore[arg-type]
        "no-owner: tests/e2e/test_journey.py names no `Owner:`. "
        "Agent action: add an `Owner: dd-sw-engineer-sr` docstring line to tests/e2e/test_journey.py",
        "loose-test: tests/test_loose.py mirrors no module. "
        "Agent action: git mv tests/test_loose.py under the tests/ folder that mirrors the module "
        "it tests, or under tests/fixtures/ when it tests the suite itself",
    ]


def _guards(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts" / "guards"))
    return importlib.import_module("run"), importlib.import_module("repo")


_PKG, _SNAKE = "dadaia" + "-workspace", "dadaia" + "_workspace"


@pytest.mark.medium
@pytest.mark.parametrize(
    "line",
    [
        f'CMD = "uv pip install -U {_PKG}"\n',
        f'CMD = "pip install {_SNAKE}==0.4.7"\n',
        f"CMD = 'pip install \"{_PKG}>0.4\"'\n",
    ],
    ids=["flag-between-verb-and-name", "underscore-spelling", "bare-greater-than"],
)
def test_the_published_install_rule_catches_every_spelling_of_the_name(
    monkeypatch: pytest.MonkeyPatch, line: str
) -> None:
    run, repo = _guards(monkeypatch)
    found = run._judge(
        [], repo.CHECKS["workflow-never-rules"][0], repo._file("tests/helpers/pin.py", line)
    )
    assert [v for v in found if v.startswith("published-dadaia-workspace-install:")]


@pytest.mark.medium
def test_the_published_install_rule_leaves_the_import_name_and_a_local_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, repo = _guards(monkeypatch)
    text = (
        f"import {_SNAKE}\nCMD = 'python -m {_SNAKE}.cli'\nW = 'uvx --from ./dist/x.whl dadaia'\n"
    )
    found = run._judge(
        [], repo.CHECKS["workflow-never-rules"][0], repo._file("tests/helpers/pin.py", text)
    )
    assert [v for v in found if v.startswith("published-dadaia-workspace-install:")] == []


@pytest.mark.medium
def test_the_memory_shape_rule_flags_the_headings_the_doctor_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, repo = _guards(monkeypatch)
    plant = repo._edit(repo._A, "\n## Tech Stack", "\n### Version notes\n\n## Tech Stack")
    found = run._judge([], repo.memory_canonical_shape, plant)
    assert [v for v in found if v.startswith("history-heading:")]


_PIN = "2.1.284"
_TASKS = ("t1-cold-onboarding", "t2-block-list-bug", "t3-discovery")
_ROWS = "".join(
    f"          - harness: {h}\n            task: {t}\n            model: {m}\n"
    f"            version: {v}\n            secret_name: {s}\n"
    for h, m, v, s in (
        ("claude-code", "anthropic/claude-sonnet-5", _PIN, "CLAUDE_CODE_OAUTH_TOKEN"),
        ("codex", "openai/gpt-6.1-sol", "0.163.0", "CODEX_AUTH_JSON"),
    )
    for t in _TASKS
)
_SCAN_RUN = "python3 evals/scripts/scan.py evals/jobs evals/summary.md"
_EVAL_YML = f"""name: eval
on:
  workflow_dispatch:
permissions:
  contents: read
env:
  CLAUDE_CODE_VERSION: {_PIN}
jobs:
  prepare:
    runs-on: ubuntu-24.04
    permissions:
      checks: read
    outputs:
      wheel_sha256: ${{{{ steps.build.outputs.sha }}}}
    steps:
      - uses: actions/checkout@aaa
      - name: Build the wheel
        id: build
        run: poetry build -f wheel
      - name: Upload the wheel
        uses: actions/upload-artifact@bbb
        with:
          name: wheel
          path: dist/*.whl
  eval:
    needs: prepare
    runs-on: ubuntu-24.04
    environment: evals
    timeout-minutes: 45
    strategy:
      fail-fast: false
      matrix:
        include:
{_ROWS}    env:
      SCAN_SECRET: ${{{{ secrets[matrix.secret_name] }}}}
    steps:
      - uses: actions/checkout@aaa
      - uses: actions/download-artifact@ccc
        with:
          name: wheel
      - name: Run the leg
        run: harbor run -i ${{{{ matrix.task }}}} -o evals/jobs/${{{{ matrix.harness }}}}/${{{{ matrix.task }}}}
      - name: Compare
        id: compare
        run: python3 evals/scripts/compare.py evals/jobs/h/t t
        continue-on-error: true
      - run: {_SCAN_RUN}
      - run: cat evals/summary.md >> "$GITHUB_STEP_SUMMARY"
      - uses: actions/upload-artifact@bbb
        with:
          name: jobs-h-t
          path: |
            evals/jobs/
            evals/summary.md
      - if: steps.compare.outcome == 'failure'
        run: exit 1
  aggregate:
    needs: eval
    if: ${{{{ !cancelled() }}}}
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@aaa
      - uses: actions/download-artifact@ccc
        with:
          pattern: jobs-*
          path: evals
          merge-multiple: true
      - name: Table
        id: compare
        run: python3 evals/scripts/compare.py --table evals/jobs > evals/summary.md
        continue-on-error: true
      - run: {_SCAN_RUN}
      - run: cat evals/summary.md >> "$GITHUB_STEP_SUMMARY"
      - if: steps.compare.outcome == 'failure'
        run: exit 1
  result:
    needs: [prepare, eval, aggregate]
    if: ${{{{ always() }}}}
    runs-on: ubuntu-24.04
    env:
      PREPARE: ${{{{ needs.prepare.result }}}}
      EVAL: ${{{{ needs.eval.result }}}}
      AGGREGATE: ${{{{ needs.aggregate.result }}}}
    steps:
      - run: test "$PREPARE $EVAL $AGGREGATE" = "success success success"
"""


def _eval_rules(monkeypatch: pytest.MonkeyPatch, text: str) -> set[str]:
    run, repo = _guards(monkeypatch)
    found = run._judge([], repo.no_model_calls_in_ci, repo._file(repo._EVAL, text))
    return {v.split(":")[0] for v in found}


@pytest.mark.medium
def test_the_multi_job_eval_workflow_yields_no_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _eval_rules(monkeypatch, _EVAL_YML) == set()


_LEG_PUBLISH = f"""      - run: {_SCAN_RUN}
      - run: cat evals/summary.md >> "$GITHUB_STEP_SUMMARY"
      - uses: actions/upload-artifact@bbb
        with:
          name: jobs-h-t
          path: |
            evals/jobs/
            evals/summary.md
"""
_LEG_UPLOAD = (
    "      - uses: actions/upload-artifact@bbb\n        with:\n          name: jobs-h-t\n"
    "          path: {}\n"
)


@pytest.mark.medium
@pytest.mark.parametrize(
    ("rule", "old", "new"),
    [
        (
            "action-not-allowlisted",
            "      - uses: actions/download-artifact@ccc\n        with:\n          name: wheel\n",
            "      - uses: someone/else@v1\n",
        ),
        (
            "upload-other-path",
            "            evals/summary.md\n      - if",
            "            evals/other.md\n      - if",
        ),
        ("summary-unscanned", f"      - run: {_SCAN_RUN}\n", "      - run: echo skipped\n"),
        (
            "summary-unscanned",
            f"> evals/summary.md\n        continue-on-error: true\n      - run: {_SCAN_RUN}\n",
            "> evals/summary.md\n        continue-on-error: true\n",
        ),
        (
            "step-env-secret",
            "      - name: Run the leg\n",
            "      - name: Run the leg\n        env: {K: '${{ secrets.OTHER }}'}\n",
        ),
        ("eval-cli-pin", f"            version: {_PIN}\n", ""),
        ("summary-unscanned", _LEG_PUBLISH, _LEG_UPLOAD.format("evals/jobs")),
        ("summary-unscanned", _LEG_PUBLISH, _LEG_UPLOAD.format("evals/")),
        (
            "upload-before-scan",
            "      - name: Run the leg\n",
            "      - uses: actions/upload-artifact@bbb\n        with:\n          name: wheel2\n"
            "          path: dist/*.whl\n      - name: Run the leg\n",
        ),
    ],
    ids=[
        "action",
        "upload-path",
        "no-scan",
        "summary-no-scan",
        "step-secret",
        "row-without-version",
        "leg-uploads-jobs-without-slash",
        "leg-uploads-evals-dir",
        "wheel-upload-in-the-secret-leg",
    ],
)
def test_each_mutation_of_the_multi_job_eval_workflow_trips_its_own_rule(
    monkeypatch: pytest.MonkeyPatch, rule: str, old: str, new: str
) -> None:
    assert old in _EVAL_YML
    assert _eval_rules(monkeypatch, _EVAL_YML.replace(old, new, 1)) == {rule}
