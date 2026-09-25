# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-project-manager
**Opened:** 2026-09-21
**Origin:** backlog:standalone-skills-distribution,public-presence-and-launch
**Consumes:** standalone-skills-distribution, public-presence-and-launch

---

## 1. Problem and context

Candidate 9 — "skills as a standard package, and a public face" — is the fifth candidate cut by
the 2026-09-18..20 grill (Q13, Q14, Q30; ADR 0016/0017 in force). It takes the two launch
entries whose library half is implementable without an operator act, and lists the operator
acts (repository creation, marketplace submission, posts, video) as decisions with their exact
commands. `release-please-semantics` stays out: ADR 0021 is `proposed` and only the operator
accepts it (D2).

Measured on the candidate 8 closure (781a2d65):

- **The skills exist only inside a workspace.** Eight `dd-*` skills stand on their own —
  `dd-grill-me`, `dd-bug-resolution`, `dd-code-review`, `dd-test-stewardship`,
  `dd-codebase-design`, `dd-domain-modeling`, `dd-architecture-survey`, `dd-ai-eng-knowhow` —
  yet reach a user only through `pip install dadaia-workspace && dadaia init`. Their `SKILL.md`
  frontmatter already carries `name` (= directory) and `description`; the Agent Skills
  specification (agentskills.io) asks for exactly those, plus optional `license`,
  `compatibility`, `metadata`; `skills-ref validate <dir>` checks one skill directory.
- **One repository layout serves every harness.** `npx skills add <repo>` discovers
  `skills/<name>/SKILL.md` (and `.agents/skills`), installs by per-skill symlink into
  `.claude/skills` (Claude Code) or `.agents/skills` (Codex, Cursor, Cline, Kimi Code); a Claude
  Code marketplace is `.claude-plugin/marketplace.json` with a plugin whose `skills` list points
  at `./skills/`; Codex reads a cloned `.agents/skills` natively and installs curated skills
  through `$skill-installer` (a "codex marketplace add" verb is UNVERIFIED — the backlog text
  named it; the layout above needs none).
- **Discoverability is a README and a PyPI page.** `docs/` holds four derived pages; there is
  no quickstart under five minutes, no positioning page, no page on the bug loop, no index a
  static site could serve; the repository's homepage points at PyPI. The bug ledger holds
  the material for the article the entry asks for (`bugs.py stats`).
- **The backlog names a spelling the wheel cannot honour.** `uvx dadaia-workspace init …`
  fails because the only console script is `dadaia` (candidate 8 review F9, ratified for this
  candidate); `uvx --from dadaia-workspace dadaia init …` works once 0.4.7 is on PyPI.

## 2. Objective

One candidate, one CLOSURE: the eight standalone skills validate against the Agent Skills
specification and declare where the full lifecycle lives; one stdlib build script renders the
`dadaia-skills` repository (skills, README, LICENSE, Claude marketplace manifests) from
`public/skills` and CI publishes it on release; the docs gain a five-minute quickstart, a
positioning page, the bug-loop page and the ledger article, every one derived from a memory
atom under its hash and served as a static site from `docs/`; `uvx dadaia-workspace …`
resolves; every operator act is a decision with its command.

## 3. Scope (candidate 9)

### FR1 — Standalone skills conform to the Agent Skills specification

- The standalone set is data: `public/entities/behavior-map.json` gains one top-level key
  `standalone_skills` naming the eight skills that need no workspace (beside
  `declared_overlaps`); the rest are workspace-bound.
- Each standalone `SKILL.md` frontmatter validates against the spec: `name` 1–64 chars,
  lowercase/digits/hyphens, equals the directory; `description` 1–1024 chars; plus
  `license: MIT` and `compatibility:` one line naming dadaia-workspace as the home of the full
  lifecycle (`pip install dadaia-workspace`). Its body must not hard-require a workspace file:
  a step that opens a scoped `AGENTS.md` reads "inside a dadaia workspace, open …".
- **AC1.1** `tests/contract/test_standalone_skills.py` validates the eight against the spec
  rules (name, description, required fields, no consecutive hyphens, `SKILL.md` ≤ 500 lines)
  and runs `skills-ref validate` on each when the binary is present; V35 stays 18 dirs /
  2880 lines (lines added to a frontmatter are paid by deletions in the same skill).

### FR2 — The skills repository is built, not written

- `dadaia_workspace/public/scripts/build-skills-repo.py` (stdlib, ≤ 150 lines, the
  `lint-dadaia-cli-reachability.py` precedent) renders `<out>/` as: `skills/<name>/**` (the
  eight, every file), `README.md` (derived from [[public-asset-distribution]] and
  [[agentic-entities]] under their hashes; install lines for `npx skills add`, Claude
  marketplace, Codex clone), `LICENSE` (copied), `.claude-plugin/marketplace.json` (`name:
  dadaia-skills`, `owner`, one plugin `dadaia-skills` with `source: "./"` and `skills:
  ["./skills/"]`), `.claude-plugin/plugin.json` (`name`, `description`, `version` = pyproject
  version, `author`, `repository`, `license`). Idempotent; byte-identical on re-run.
- `.github/workflows/release.yml` gains one job after publish: build the repo and push it
  to `marcoaureliomenezes/dadaia-skills` (`main`) with the tag's version — fail-closed on the
  missing `SKILLS_REPO_TOKEN` secret with one `::error::` naming the secret (the
  `security-review` precedent).
- **AC2.1** `tests/contract/test_skills_repo_build.py`: the build output has exactly the
  manifest set above, every skill directory equals its `public/skills` source, both JSON
  manifests validate against the documented field set, and a second build changes nothing;
  `claude plugin validate <out>` runs when the binary is present.

### FR3 — Public presence, library side

- `docs/index.md` (landing, the tagline once, the three pages), `docs/quickstart.md` (five
  minutes: install, `init <dir> --harness <name> --repo <url>`, bind, doctor, first backlog entry,
  first candidate — derived from [[workspace-init]], [[context-management]],
  [[sdd-bug-backlog-governance]]), `docs/positioning.md` ("your product repos never carry agent
  config; one law governs ten projects" — derived from [[product-vision]],
  [[spec-context-project]]), `docs/bug-loop.md` (register → RED → fix → resolve, derived from
  [[sdd-bug-backlog-governance]]), `docs/bug-ledger-lessons.md` (the article: the ledger's
  counts from `bugs.py stats` — 514 records, 497 resolved, 38 CRITICAL / 231 HIGH at closure
  — and the fix-chain lesson, derived from [[QUALITY]] and [[sdd-bug-backlog-governance]]). Every page carries `<!-- derived-from: … -->` markers;
  `tests/contract/test_docs_derived_from_memory.py`'s coverage set includes them.
- `README.md` gains a Documentation section linking the site (`https://marcoaureliomenezes.github.io/dadaia-workspace/`) and the skills repository; `llms.txt` lists the new pages;
  `pyproject.toml` `[tool.poetry.urls]` gains `Documentation`; the docs site is GitHub Pages
  from `/docs` on `main` (D3, operator: enable Pages; no build tooling enters the repo).
- `pyproject.toml` `[tool.poetry.scripts]` gains `dadaia-workspace = "dadaia_workspace.cli.main:_safe_app"`
  so `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` resolves (review F9);
  `docs/quickstart.md` shows the uvx line first and the pip line second.
- **AC3.1** `dadaia doctor` on the live instance exit 0; the derived-docs test passes with the
  five new pages in its covered set; `tests/unit/cli/test_console_scripts.py` proves both
  entry points resolve to the same callable.

### FR4 — Closure

- Memory pass (`public-asset-distribution`: the second distribution; `harness-codex`,
  `harness-kimi-code`, `harness-claude-code`: the skills reachable without a workspace;
  `pypi-distribution`: the docs site and the alias; `brand-identity`: the site, the slug rule
  "always `dadaia-workspace`"), CHANGELOG "Candidate 9", `_RELEASE.json` log, live instance
  reflected, dd-code-review, PR #260 updated.
- **AC4.1** Every CI job green except the by-design red `security-review` (D1); review
  APPROVED; `dadaia doctor` exit 0.

## 4. Out of scope

- `release-please-semantics` — candidate 10, gated on ADR 0021 (D2).
- The operator acts of D3–D7 below; a Codex marketplace verb (unverified); a docs build
  toolchain (mkdocs, Docusaurus); the video and the posts themselves.
- `hooks-multi-harness-study` stays an idea (Q31).

## 5. Decisions and constraints

- D1 (operator): `CLAUDE_API_KEY` + required check — PR #260 stays red on it.
- D2 (operator): accept ADR 0021 to unlock candidate 10.
- D3 (operator): create `marcoaureliomenezes/dadaia-skills` (public, empty, `main`), add the
  `SKILLS_REPO_TOKEN` secret (fine-grained, contents:write on that repo), enable GitHub Pages
  on this repository from `main` `/docs`.
- D4 (operator): submit the marketplace — a PR adding `dadaia-skills` to
  `anthropics/claude-plugins-official` (or the community index), the `npx skills add
  marcoaureliomenezes/dadaia-skills` line in the README once the repo exists.
- D5 (operator): `gh repo edit --homepage https://marcoaureliomenezes.github.io/dadaia-workspace/ --add-topic agent-skills --add-topic cursor --add-topic github-copilot --add-topic devin`.
- D6 (operator): the video, the Show HN post, the awesome-list PRs — the handoff carries the
  drafts; always the full slug `dadaia-workspace`.
- D7 (operator): a bug proposal remains unregistered from candidate 7 — `SPEC-DOC-039` names a
  non-canon fix path (ask-first policy).
- ADR 0018: a new verb enters only when an old one leaves — this candidate adds no verb; the
  build is a script, the alias is a second name for the one entry point.

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-80 |
| FR2 | T-047-81, T-047-82 |
| FR3 | T-047-83, T-047-84, T-047-85 |
| FR4 | T-047-86 |
