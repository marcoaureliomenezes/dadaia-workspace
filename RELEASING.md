# Releasing `dadaia-workspace`

This guide describes the manual steps to cut and publish a release.
The CI/CD pipeline does the heavy lifting; this document captures the
human checklist.

## Prerequisites (one-time operator setup)

1. **PyPI account** with 2FA enabled. Owner: `marcoaurelioreislima@gmail.com`.
2. **PyPI pending publisher** configured for the `dadaia-workspace` project:
   - Owner: `marcoaureliomenezes`
   - Repository: `dadaia-workspace`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. **GitHub environment `pypi`** created in the repository settings with deployment branches restricted to `v*.*.*` tags.
4. **Branch protection on `main`**:
   - Require PR before merging.
   - Required status checks: `lint`, `typecheck`, `test`.
   - No force push.
   - Include administrators.
5. `poetry.lock` is committed.

## Per-release checklist

The version vX.Y.Z used below is illustrative — substitute your actual target.

1. **Update `pyproject.toml`** — bump `[tool.poetry] version` to `X.Y.Z`.
2. **Update `CHANGELOG.md`** — move every entry under `[Unreleased]` into a new `[X.Y.Z] — YYYY-MM-DD` section. Leave an empty `[Unreleased]` skeleton on top.
3. **Commit** the bump:
   ```bash
   git checkout -b release/vX.Y.Z
   git commit -am "chore(release): vX.Y.Z"
   git push -u origin release/vX.Y.Z
   ```
4. **Open the PR** against `main` and wait for CI to go green.
5. **Merge** the PR into `main`.
6. **Tag**:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
7. **Watch `release.yml`** in the GitHub Actions tab. It runs four jobs:
   `validate → build → publish → smoke-test`.
8. **Verify** on PyPI: `https://pypi.org/project/dadaia-workspace/X.Y.Z/`.
9. **Local smoke**:
   ```bash
   python -m venv /tmp/dw-smoke
   /tmp/dw-smoke/bin/pip install dadaia-workspace==X.Y.Z
   /tmp/dw-smoke/bin/dadaia --help
   /tmp/dw-smoke/bin/dadaia init --workspace /tmp/dw-smoke-ws
   ```
10. **Announce** internally (or in the README) the new version.

## Hotfix releases (X.Y.Z+1)

Same checklist, but branch off `main` directly (no Spec/PLAN gates needed for a one-line fix). The PR title should start with `fix:` so semantic-version automation can detect a patch release.

## Recovery

- **Wrong tag pushed:** delete the tag locally and remotely; PyPI does **not** allow republishing the same version. If the publish job already finished, bump the patch and re-release.
  ```bash
  git tag -d vX.Y.Z
  git push origin :refs/tags/vX.Y.Z
  ```
- **Publish failed mid-flight:** inspect the Actions log. The `validate → build → publish → smoke-test` chain is idempotent up to PyPI publish; failures before publish can be retried by re-running the workflow. After publish, the version is gone forever — bump and retry.
