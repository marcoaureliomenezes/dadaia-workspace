# PLAN: go-open-source

**Status:** Aprovado
**Release ID:** go-open-source
**Owner:** product-engineer
**Depends on:** SPEC.md Status: Aprovado

---

## Strategy

This release is a cleanup + governance release, not a feature release. It touches no
production logic — only repo hygiene, canonical asset content, CI/packaging files, and
documentation. The work is naturally parallelizable into five independent tracks:

| Track | Owner | What |
|---|---|---|
| A — Repository hygiene | software-engineer-python | `git rm --cached`, `.gitignore` updates, stale file removal |
| B — Public asset scrub | ai-engineer | Edit `public/skills/`, `public/scripts/`, `public/agents/` |
| C — CI/CD hardening | devops-engineer | Pin `release.yml`, add `secret-scan.yml`, add `repo-hygiene` CI job |
| D — Security gates | security-reviewer | Run gitleaks (full history) + pip-audit, sign off |
| E — Docs + license | product-engineer | `LICENSE`, `CONTRIBUTING.md`, README badge, active spec path fix |

Tracks A, B, C, D, E are fully independent (disjoint write sets). All five can start
immediately after SPEC approval and TASKS approval. The only ordering constraint is that
Track B must complete before Track D validates `public/` assets, and all tracks must
complete before the operator performs the visibility flip (GOV-7).

---

## Layers affected

| Layer | What changes |
|---|---|
| Repository root | `LICENSE`, `CONTRIBUTING.md`, `.gitignore` |
| `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` | Operator-specific content stripped |
| `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | Two hardcoded path triggers removed (lines 321–325) |
| `dadaia_workspace/public/agents/software-engineer-node.md` | Concrete runtime name `redacted-infra` genericized |
| `dadaia_workspace/public/agents/qa-engineer.md` | Concrete runtime name `redacted-infra` genericized |
| `.github/workflows/release.yml` | Floating tags → commit SHAs; top-level permissions narrowed |
| `.github/workflows/ci.yml` | New `repo-hygiene` job added |
| `.github/workflows/secret-scan.yml` | New file (gitleaks) |
| `.github/CODEOWNERS` | Add `/dadaia_workspace/public/` entry |
| `README.md` | License badge added |
| `specs/releases/sdd-release-lifecycle-v1/SPEC.md` | Remove `/home/marco` path at line 168 |
| `tests/conftest.py` (new) | Autouse sandbox fixture |
| `dadaia_workspace/features/public/public_assets.py` | `_is_self_repo` guard strengthened |
| Stale files deleted | `playwright-pr3-22.config.ts`, `tests/e2e/pr3-22-evidence/`, `docs/superpowers/` |
| Git index | `git rm -r --cached` for all 364 junk files |

---

## Execution order

### Wave 1 — Pre-cleanup (all parallel, no dependencies)

Run tracks A, B, C, E in parallel.

- **A:** `git rm -r --cached` for all 364 files + `.gitignore` additions + stale
  file deletions. Commit: `chore(repo): untrack runtime projections and junk files`.
- **B:** Edit `public/` assets per B3 spec. Run `dadaia public stage && dadaia public install --target all && dadaia public doctor` (exit 0 required). Commit: `chore(public): strip operator-specific content from canonical assets`.
- **C:** Pin action SHAs in `release.yml`, narrow top-level permissions, add
  `secret-scan.yml`, add `repo-hygiene` CI job, update CODEOWNERS. Commit(s) per task.
- **E:** Add `LICENSE`, add `CONTRIBUTING.md`, add README badge, fix active spec path.
  Commit: `docs: add LICENSE, CONTRIBUTING.md, and license badge`.

### Wave 2 — Python source edits (depends on Wave 1 completion)

- Strengthen `_is_self_repo` guard in `public_assets.py` (Track A / software-engineer-python).
- Add `tests/conftest.py` autouse sandbox fixture (Track A / software-engineer-python).
- Suite must pass: `poetry run pytest` (exit 0, coverage maintained).

### Wave 3 — Security gates (depends on Wave 1 + Wave 2)

- **D:** security-reviewer runs `gitleaks detect --log-opts=--all` and
  `poetry run pip-audit`. Both must exit 0. security-reviewer signs off.

### Wave 4 — Operator visibility flip + post-flip governance

Operator performs the visibility flip; devops-engineer applies branch protection,
enables secret scanning, verifies status checks, runs release dry-run.

---

## Technical risks

**TR-1 — gitleaks full scan finds a secret (R1 in SPEC)**
If gitleaks exits non-zero in Wave 3, work stops. The operator must decide on
`git filter-repo` / BFG Repo Cleaner remediation before proceeding. Timeline impact:
potentially several hours for history rewrite + force push to a still-private repo.

**TR-2 — `public/` propagation drift (R3 in SPEC)**
If Track B edits `public/` but does not run `dadaia public stage && install`, the staging
and projection files will be inconsistent. The `dadaia public doctor` exit-0 check in
AC-GOS-05 gates task completion. Enforced by task done criteria.

**TR-3 — conftest.py autouse fixture breaks existing tests**
A global `chdir` fixture could break tests that depend on the current working directory.
Mitigation: implement the fixture as opt-out (marker-based) rather than forcing chdir;
focus the backstop on asserting no repo-root writes rather than enforcing chdir globally.

**TR-4 — SHA verification for pinned actions**
The SHA table in the devops report must be verified against the official action repos
before applying. Stale or incorrect SHAs would silently break the release pipeline.
Mitigation: devops-engineer verifies each SHA via `gh api` before committing.

---

## Validation plan

| AC | Validation command | Gate |
|---|---|---|
| AC-GOS-01 | `cat LICENSE \| head -1` | Shows MIT License |
| AC-GOS-02 | `git ls-files \| grep -E '^\.(claude\|agents\|codex\|opencode)/' \| wc -l` | 0 |
| AC-GOS-02 | `git ls-files \| grep -E '^\.dadaia/(agentic\|scripts\|reports)/' \| wc -l` | 0 |
| AC-GOS-02 | `git ls-files \| grep '^tests/e2e/panel/screenshots/' \| wc -l` | 0 |
| AC-GOS-03 | `grep -c '\.claude/' .gitignore` | >= 1 |
| AC-GOS-04 | `grep -r 'vps-redacted-infra-1\|vps-redacted-infra-1\|redacted-infra-agent-wqps\|redacted-infra-x44i' dadaia_workspace/public/ \| wc -l` | 0 |
| AC-GOS-05 | `dadaia public doctor` exit code | 0 |
| AC-GOS-06 | `grep -E 'uses:.*@v[0-9]\|uses:.*@release/' .github/workflows/release.yml \| wc -l` | 0 |
| AC-GOS-07 | `grep 'contents: write' .github/workflows/release.yml \| grep -v 'job'` | empty |
| AC-GOS-08 | `gitleaks detect --log-opts=--all` exit code | 0 |
| AC-GOS-09 | `poetry run pip-audit` exit code | 0 |
| AC-GOS-10a | `dadaia public install` in dir with `name = "dadaia-workspace"` pyproject | Refused |
| AC-GOS-10b | `ls tests/conftest.py` | exists |
| AC-GOS-10c | `grep 'repo-hygiene' .github/workflows/ci.yml` | present |
| AC-GOS-11 | `cat CONTRIBUTING.md \| grep -c 'specs/'` | >= 1 |
| AC-GOS-13 | `git ls-files playwright-pr3-22.config.ts tests/e2e/pr3-22-evidence docs/superpowers \| wc -l` | 0 |
| AC-GOS-14 | `grep '/home/marco' specs/releases/sdd-release-lifecycle-v1/SPEC.md` | empty |

AC-GOS-12 is operator-verified post-flip via GitHub UI / `gh api`.
