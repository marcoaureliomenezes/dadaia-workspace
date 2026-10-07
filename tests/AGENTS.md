# Test Rules — dadaia-workspace

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them.

- Test basics: the root `AGENTS.md` map §1; slop: `dd-code-review` SLOP.md and `specs/memory/QUALITY.md` fixed section.

## Architecture

- `tests/<p>/test_<m>.py` mirrors `dadaia_workspace/<p>/<m>.py`: one owner per module, the
  folder never says the size. A second file for the same module is `test_<m>__<topic>.py`.
- `tests/fixtures/**`: the suite's own support and the tests of it.
- `tests/e2e/**`: named end-to-end journeys only. Every file names an owner.
- `tests/tmp/**`: temporary debugging reproductions only; excluded from default
  collection and deleted or promoted before closure.

## Sizes and cost

| Size (marker) | What puts a test there | Timeout default |
|---|---|---|
| `small` | no process, no real git: pure or tmp-filesystem only | 10 s |
| `medium` | its module reaches a subprocess, real git or `pytester` | 60 s |
| `e2e` (LARGE) | lives in `tests/e2e/**`; every file names an owner | 120 s |

The size comes from what the test reaches (`tests/conftest.py`), never from its folder; an
explicit `@pytest.mark.small` / `@pytest.mark.medium` wins. A test that needs more time than
its size's default is **mis-sized** — fix the size, never raise the default.

`flaky` and `quarantine` markers are registered in `pyproject.toml`; a
`quarantine` marker without `bug="<bug-slug>"` refuses collection, and every
gating selector (CI jobs, release jobs) excludes the
quarantine lane. Diagnosis runs use `-m quarantine` explicitly.

## Markers and cost

- Size markers are applied at collection by `tests/conftest.py`.
- Add `@pytest.mark.slow(reason="...")` to any test over 1 second or any test
  that starts a subprocess/server.
- The local loop is:

```bash
pytest -q -m "small and not slow" tests
```

Coverage is not the default loop. Use explicit coverage only for curated
small runs:

```bash
python -m pytest -q -p scripts.covdata -m "small" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
```
