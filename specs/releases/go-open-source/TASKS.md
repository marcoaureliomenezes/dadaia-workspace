# TASKS: go-open-source

**Status:** Aprovado
**Release ID:** go-open-source
**Owner:** product-engineer

> Markers: `[ ]` OPEN — `[-]` IN PROGRESS — `[x]` DONE
> All tracks (A–E) are independent; disjoint write sets declared. Multiple `[-]` are
> safe across tracks. Within a track: at most one `[-]` at a time.

---

## Track A — Repository hygiene (software-engineer-python)

### T-GOS-A1
- **Owner:** software-engineer-python
- **Status:** `[x]`
- **Description:** Untrack all 364 junk files from git index and add missing `.gitignore` entries.
- **Target files/subsystem:** `.gitignore`, git index (via `git rm -r --cached`)
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Run: `git rm -r --cached .claude/ .agents/ .codex/ .opencode/ .dadaia/agentic/ .dadaia/scripts/ .dadaia/reports/ tests/e2e/panel/screenshots/`
     **IMPORTANT:** Do NOT pass `opencode.json` to `git rm --cached` — it is
     intentionally tracked as a starter template (OQ-01 RESOLVED).
  2. Add to `.gitignore` the block from SPEC.md § B2 (`.claude/`, `.agents/`, `.codex/`, `.opencode/`, `.dadaia/agentic/`, `.dadaia/scripts/`, `.dadaia/states/`, `.dadaia/tmp/`, `tests/e2e/panel/screenshots/`, `img/`)
     **IMPORTANT:** Do NOT add `opencode.json` to `.gitignore`.
  3. Commit: `chore(repo): untrack runtime projections and junk files; add gitignore guards`
- **Done criterion:**
  - `git ls-files | grep -E '^\.(claude|agents|codex|opencode)/' | wc -l` → 0
  - `git ls-files | grep -E '^\.dadaia/(agentic|scripts|reports)/' | wc -l` → 0
  - `git ls-files | grep '^tests/e2e/panel/screenshots/' | wc -l` → 0
  - `.gitignore` contains all new patterns (AC-GOS-02, AC-GOS-03)

---

### T-GOS-A2
- **Owner:** software-engineer-python
- **Status:** `[x]`
- **Description:** Delete stale artefacts from the git-tracked file set.
- **Target files/subsystem:** `playwright-pr3-22.config.ts`, `tests/e2e/pr3-22-evidence/`, `docs/superpowers/`
- **Preconditions:** T-GOS-A1 DONE
- **Work:**
  1. `git rm -r playwright-pr3-22.config.ts tests/e2e/pr3-22-evidence/ docs/superpowers/`
  2. Commit: `chore(repo): remove stale per-PR evidence artefacts and docs/superpowers`
- **Done criterion:**
  - `git ls-files playwright-pr3-22.config.ts tests/e2e/pr3-22-evidence docs/superpowers | wc -l` → 0 (AC-GOS-13)

---

### T-GOS-A3
- **Owner:** software-engineer-python
- **Status:** `[x]`
- **Description:** Strengthen `_is_self_repo` guard in `public_assets.py` to refuse scaffolding regardless of manifest presence.
- **Target files/subsystem:** `dadaia_workspace/features/public/public_assets.py` (lines ~1646–1664)
- **Preconditions:** T-GOS-A1 DONE (clean working tree before modifying Python source)
- **Work:**
  1. Read the existing `_is_self_repo` method. Locate the manifest-dependency path.
  2. Add a secondary check: if the target directory contains a `pyproject.toml` with `name = "dadaia-workspace"` (regardless of manifest state), return True (self repo — skip install).
  3. Add a unit test covering the new guard path: install refused when target dir has `pyproject.toml` with `name = "dadaia-workspace"` but no manifest.
  4. Run `poetry run pytest` — exit 0.
  5. Commit: `feat(public): strengthen _is_self_repo guard against manifest-absent scaffolding`
- **Done criterion:**
  - Unit test exists and passes covering manifest-absent self-repo detection (AC-GOS-10a)
  - `poetry run pytest` exit 0, no regression

---

### T-GOS-A4
- **Owner:** software-engineer-python
- **Status:** `[x]`
- **Description:** Add root `tests/conftest.py` with autouse sandbox fixture.
- **Target files/subsystem:** `tests/conftest.py` (new file)
- **Preconditions:** T-GOS-A1 DONE
- **Work:**
  1. Create `tests/conftest.py` with a module-scoped or session-scoped autouse fixture that:
     - Captures the repo-root file list before the test.
     - Asserts no new untracked files appear at `.claude/`, `.agents/`, `.codex/`,
       `.opencode/`, `.dadaia/agentic/`, `.dadaia/scripts/` after the test completes.
     - Note: do NOT force-chdir every test globally — implement as a root-guard only,
       not a chdir fixture (to avoid breaking tests with CWD assumptions). See TR-3 in PLAN.
  2. Run `poetry run pytest` — exit 0, no regression from the new conftest.
  3. Commit: `test: add root conftest.py with repo-root write backstop fixture`
- **Done criterion:**
  - `ls tests/conftest.py` exists (AC-GOS-10b)
  - `poetry run pytest` exit 0

---

## Track B — Public asset scrub (ai-engineer)

### T-GOS-B1
- **Owner:** ai-engineer
- **Status:** `[x]`
- **Description:** Strip operator-specific content from `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`.
- **Target files/subsystem:** `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Read the file to locate the operator-specific sections (lines 59–68, 171, 224–237 per security-reviewer report).
  2. Phase 0 inspection block (lines 59–68): replace concrete container names, absolute VPS-host paths, and env-var grep targets with generic placeholders (`<COMPOSE_FILE>`, `<CONTAINER_NAME>`, `<ENV_VAR_TARGET>`). The block must describe the inspection *protocol* using generic variable syntax.
  3. Line 171 (`docker inspect vps-traefik-1`): replace with a generic `docker inspect <CONTAINER_NAME>` example.
  4. "Problemas Conhecidos" section (lines 224–237): remove entirely. It is instance-specific backlog state, not a library-level skill definition.
  5. Verify that the skill still describes the core protocol (Fase 0 inspection, Fase 1 interview, Fase 2 synthesis, Fase 3 report) without any operator-specific deployment topology.
  6. Do NOT run `dadaia public stage` yet — that happens in T-GOS-B3 after both B1 and B2 are complete.
- **Done criterion:**
  - `grep -E 'vps-redacted-infra-1|vps-redacted-infra-1|vps-traefik-1|redacted-infra-agent-wqps|redacted-infra-x44i|/docker/redacted-infra|/docker/redacted-infra|REDACTED_CONFIG|TELEGRAM_ALLOWED_USERS|REDACTED_CONFIG' dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md | wc -l` → 0
  - "Problemas Conhecidos" section absent from the file (AC-GOS-04 scope)

---

### T-GOS-B2
- **Owner:** ai-engineer
- **Status:** `[x]`
- **Description:** Strip operator-specific content from `sdd-spec-gate.sh` and genericize `software-engineer-node.md` + `qa-engineer.md`.
- **Target files/subsystem:**
  - `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (lines 321–325)
  - `dadaia_workspace/public/agents/software-engineer-node.md` (lines 60, 258)
  - `dadaia_workspace/public/agents/qa-engineer.md` (line 217)
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. `sdd-spec-gate.sh:321–325`: remove the two hardcoded production-path triggers
     (`/docker/redacted-infra-agent-wqps/data/` and `/docker/redacted-infra-x44i/data/`). If these
     paths served as examples, replace with a comment indicating that consumer production
     paths should be derived from workspace config, not hardcoded in the gate script.
  2. `software-engineer-node.md:60,258`: find references to `redacted-infra` and `workflow-tools`
     as concrete runtime names. Replace with generic language (e.g., `<your-runtime-name>`,
     `<workflow-tool>`, or simply remove the instance-specific example while keeping the
     role description generic).
  3. `qa-engineer.md:217`: same treatment for `redacted-infra` reference.
- **Done criterion:**
  - `grep -n 'redacted-infra-agent-wqps\|redacted-infra-x44i' dadaia_workspace/public/scripts/sdd-spec-gate.sh | wc -l` → 0
  - `grep -n 'redacted-infra' dadaia_workspace/public/agents/software-engineer-node.md dadaia_workspace/public/agents/qa-engineer.md | wc -l` → 0

---

### T-GOS-B3
- **Owner:** ai-engineer
- **Status:** `[x]`
- **Description:** Re-stage and re-propagate edited `public/` assets; verify `dadaia public doctor` exits 0.
- **Target files/subsystem:** `.dadaia/agentic/` (staging), `.claude/`, `.agents/`, `.codex/`, `.opencode/` (projections)
- **Preconditions:** T-GOS-B1 DONE, T-GOS-B2 DONE, T-GOS-B4 DONE
- **Work:**
  1. Run: `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  2. Confirm doctor exits 0 with 0 drift / 0 missing.
  3. Commit all modified staged + projected files:
     `chore(public): strip operator-specific content from canonical assets; re-stage and re-project`
- **Done criterion:**
  - `dadaia public doctor` exit 0, 0 drift, 0 missing (AC-GOS-05)
  - Commit present with all edited staging + projection copies of SKILL.md, sdd-spec-gate.sh, agent files, and `AGENTS.md` (from T-GOS-B4)

---

### T-GOS-B4
- **Owner:** ai-engineer
- **Status:** `[x]`
- **Description:** Add header note to `dadaia_workspace/public/data/AGENTS.md` (the
  lib-originated source for root `AGENTS.md`) clarifying its purpose to contributors.
- **Target files/subsystem:** `dadaia_workspace/public/data/AGENTS.md`
- **Preconditions:** TASKS Aprovado
- **Critical ownership constraint:** The root `AGENTS.md` is lib-originated and fanned
  out by `dadaia public install`. It must NEVER be edited in place. This task edits the
  SOURCE at `dadaia_workspace/public/data/AGENTS.md` only. Re-propagation is handled
  by T-GOS-B3.
- **Work:**
  1. Open `dadaia_workspace/public/data/AGENTS.md`.
  2. At the very top of the file (before any existing content), add a header note block
     such as:
     ```
     > **FOR CONTRIBUTORS — READ THIS FIRST**
     > This file (`AGENTS.md`) is the workspace **agent-rules document** used by AI
     > coding agents (Claude Code, OpenCode, etc.). It is NOT a human contribution guide.
     > For human contribution guidelines, see `CONTRIBUTING.md`.
     >
     > If you need to add a workspace rule, you must scope it to a **repo-local rule
     > file** (e.g., `repos/<your-repo>/.claude/rules/<your-rule>.md`). Do NOT edit
     > this file directly — it is generated by `dadaia public install` from the library
     > source at `dadaia_workspace/public/data/AGENTS.md`. Any in-place edit will be
     > overwritten on the next `dadaia public install` run.
     ```
  3. Do NOT run `dadaia public stage` — that is T-GOS-B3's responsibility.
- **Done criterion:**
  - `dadaia_workspace/public/data/AGENTS.md` contains the header note covering both
    (a) "this is agent-rules, not human contribution guide" and (b) "add rules repo-locally,
    never edit canonical directly" (AC-GOS-15)
  - The note is at the top of the file, visually prominent

---

## Track C — CI/CD hardening (devops-engineer)

### T-GOS-C1
- **Owner:** devops-engineer
- **Status:** `[x]`
- **Description:** Pin all floating action tags in `release.yml` to commit SHAs and narrow top-level permissions.
- **Target files/subsystem:** `.github/workflows/release.yml`
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Verify each SHA from the devops report § 4.3 against the official action repos using `gh api` or the upstream repo commit history. Do not pin without verification.
  2. Replace all five floating references with verified commit SHAs (SHA table in SPEC.md § B4).
  3. Change top-level `permissions: contents: write` → `contents: read`.
  4. Run `.github/workflows/release.yml` syntax check (e.g., `yamllint` or GitHub Actions linter if available).
  5. Commit: `ci(release): pin action SHAs and narrow top-level permissions`
- **Done criterion:**
  - `grep -E 'uses:.*@v[0-9]|uses:.*@release/' .github/workflows/release.yml | wc -l` → 0 (AC-GOS-06)
  - Top-level permissions block shows `contents: read` (AC-GOS-07)

---

### T-GOS-C2
- **Owner:** devops-engineer
- **Status:** `[x]`
- **Description:** Create `/.github/workflows/secret-scan.yml` (gitleaks workflow).
- **Target files/subsystem:** `.github/workflows/secret-scan.yml` (new file)
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Create the file using the YAML from devops report § 3.2. The workflow triggers on `pull_request` (not `pull_request_target`) and `push: branches: [main, 'hotfix/v*']`. Uses `gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7` (commit-pinned).
  2. Confirm `permissions: contents: read` at top level.
  3. Commit: `ci: add gitleaks secret-scan workflow`
- **Done criterion:**
  - `.github/workflows/secret-scan.yml` exists and is valid YAML
  - Triggers on `pull_request` (not `pull_request_target`)
  - Uses a commit-SHA-pinned `gitleaks-action` reference

---

### T-GOS-C3
- **Owner:** devops-engineer
- **Status:** `[x]`
- **Description:** Add `repo-hygiene` CI job to `.github/workflows/ci.yml`.
- **Target files/subsystem:** `.github/workflows/ci.yml`
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Add a new job `repo-hygiene` that runs `git ls-files` and fails if any tracked file
     matches `^\.(claude|agents|codex|opencode)/` or `^\.dadaia/(agentic|scripts|states|reports)/`.
     Simple shell: `git ls-files | grep -E '^\.(claude|agents|codex|opencode)/|^\.dadaia/(agentic|scripts|states|reports)/' && exit 1 || exit 0`
  2. Commit: `ci: add repo-hygiene check to prevent re-tracking of projection files`
- **Done criterion:**
  - `grep 'repo-hygiene' .github/workflows/ci.yml` present (AC-GOS-10c)
  - Job fails on tracked projection paths

---

### T-GOS-C4
- **Owner:** devops-engineer
- **Status:** `[x]`
- **Description:** Update `/.github/CODEOWNERS` to add explicit entry for `dadaia_workspace/public/`.
- **Target files/subsystem:** `.github/CODEOWNERS`
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Read the current CODEOWNERS content.
  2. Add the entry: `/dadaia_workspace/public/      @marcoaureliomenezes` with a comment indicating it is the agent asset source of truth.
  3. Commit: `chore(governance): add dadaia_workspace/public/ to CODEOWNERS`
- **Done criterion:**
  - `grep 'dadaia_workspace/public/' .github/CODEOWNERS` present

---

## Track D — Security gates (security-reviewer)

### T-GOS-D1
- **Owner:** security-reviewer
- **Status:** `[x]`
- **Description:** Run `gitleaks detect --log-opts=--all` over the full 813-commit git history.
- **Target files/subsystem:** git repository history (read-only audit)
- **Preconditions:** T-GOS-A1 DONE (junk files removed from index, so gitleaks scans a clean working tree)
- **Work:**
  1. Install gitleaks if not present: `pip install gitleaks` or `docker run zricethezav/gitleaks`.
  2. Run: `gitleaks detect --source . --log-opts="--all"` from `repos/dadaia-workspace/`.
  3. If exit 0 and zero findings: record the stdout summary as evidence in CLOSURE.md.
  4. If exit non-zero: surface findings to operator immediately. Do NOT proceed to the visibility flip.
- **Done criterion:**
  - `gitleaks detect --log-opts=--all` exits 0, zero findings reported (AC-GOS-08)
  - security-reviewer sign-off recorded (commit or CLOSURE evidence entry)

---

### T-GOS-D2
- **Owner:** security-reviewer
- **Status:** `[x]`
- **Description:** Run `poetry run pip-audit` inside the Poetry venv.
- **Target files/subsystem:** `poetry.lock` + `pyproject.toml` (read-only audit)
- **Preconditions:** TASKS Aprovado (independent of other tracks)
- **Work:**
  1. `cd repos/dadaia-workspace`
  2. If `pip-audit` not in venv: `poetry add --group dev pip-audit`
  3. Run: `poetry run pip-audit`
  4. If exit 0 and zero medium+ CVEs: record the stdout summary as evidence.
  5. If any medium+ CVE found: surface to operator with the affected package + upgrade path.
- **Done criterion:**
  - `poetry run pip-audit` exits 0, zero medium+ CVEs (AC-GOS-09)
  - Evidence captured for CLOSURE.md

---

## Track E — Docs + license (product-engineer)

### T-GOS-E1
- **Owner:** product-engineer
- **Status:** `[x]`
- **Description:** Add MIT `LICENSE` file to repository root.
- **Target files/subsystem:** `LICENSE` (new file at repo root)
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Create `LICENSE` at the repo root with the standard MIT License text:
     - Copyright year: 2024 (year of first commit) through 2026
     - Copyright holder: `Marco Aurelio Reis Lima`
  2. Commit: `docs: add MIT LICENSE file`
- **Done criterion:**
  - `cat LICENSE | head -1` outputs `MIT License` (AC-GOS-01)
  - File is at repo root (not in a subdirectory)

---

### T-GOS-E2
- **Owner:** product-engineer
- **Status:** `[x]`
- **Description:** Create `CONTRIBUTING.md` at repo root.
- **Target files/subsystem:** `CONTRIBUTING.md` (new file at repo root)
- **Preconditions:** TASKS Aprovado
- **Work:**
  1. Create `CONTRIBUTING.md` covering at minimum:
     - What `specs/` is and why it exists (SDD lifecycle, release model, memory atoms)
     - That `.claude/`, `.agents/`, `.codex/`, `.opencode/` are generated by `dadaia public install` and MUST NOT be committed
     - That Node.js is only needed for Playwright E2E tests
     - The fork-only contribution model (fork the repo, open a PR from the fork)
     - A note explaining `AGENTS.md` at the root (lib-originated, for Claude Code/OpenCode context)
  2. Commit: `docs: add CONTRIBUTING.md`
- **Done criterion:**
  - `CONTRIBUTING.md` exists at repo root
  - Contains `specs/`, fork-only model, and projection-not-committed notes (AC-GOS-11)

---

### T-GOS-E3
- **Owner:** product-engineer
- **Status:** `[x]`
- **Description:** Add license badge to `README.md` and fix active spec local path.
- **Target files/subsystem:** `README.md`, `specs/releases/sdd-release-lifecycle-v1/SPEC.md`
- **Preconditions:** T-GOS-E1 DONE (LICENSE must exist before badge is accurate)
- **Work:**
  1. Add a license badge to `README.md` near the top:
     `[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)`
  2. Open `specs/releases/sdd-release-lifecycle-v1/SPEC.md`, go to line 168.
     Replace `/home/marco/.claude/plans/devemos-melhorar-o-streamed-snail.md` with
     a note such as: `(local plan file — not tracked in this repo)`.
  3. Commit: `docs: add license badge and remove local path from active spec`
- **Done criterion:**
  - `grep 'License: MIT' README.md` present
  - `grep '/home/marco' specs/releases/sdd-release-lifecycle-v1/SPEC.md` → empty (AC-GOS-14)

---

## Post-implementation operator gate (not an agent task)

### T-GOS-OPS1 — Visibility flip + post-flip governance (operator + devops-engineer)
- **Owner:** operator (with devops-engineer support)
- **Status:** `[ ]`
- **Description:** Execute the pre-public ordered checklist (devops report § 6) culminating in the visibility flip and immediate post-flip governance actions.
- **Preconditions:** ALL tasks T-GOS-A1 through T-GOS-D2 marked `[x]` DONE. All ACs validated.
- **Work (ordered steps):**
  1. Verify all ACs locally (validation table in PLAN.md)
  2. Flip repository visibility to Public (GitHub Settings > Danger Zone)
  3. Within minutes: apply branch protection ruleset on `main` (gh CLI command in devops report § 2.2) with `enforce_admins: true` — owner is also bound by protection rules (OQ-03 RESOLVED)
  4. Within minutes: enable GitHub native secret scanning + push protection (gh CLI in devops report § 3.1)
  5. Verify all required status checks are recognized (create test branch + PR)
  6. Confirm `/.github/CODEOWNERS` is active (create a test PR modifying `dadaia_workspace/public/` and verify review is requested)
  7. Optional: release dry-run (bump patch version, merge to main, approve gate)
- **Done criterion:**
  - Repository is Public on GitHub
  - Branch protection active on `main` with `enforce_admins: true` (verified via
    `gh api repos/.../branches/main/protection` — check `enforce_admins.enabled = true`) (AC-GOS-12)
  - Secret scanning + push protection enabled (verified via `gh api repos/... --jq '.security_and_analysis'`)
  - All required status checks (lint, typecheck, test, specs-doctor, gitleaks, repo-hygiene) pass on a test PR (AC-GOS-12)
