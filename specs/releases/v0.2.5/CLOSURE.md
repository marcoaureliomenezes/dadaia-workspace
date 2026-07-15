# Closure: Release — v0.2.5

> **Status:** Aprovado
> **Release ID:** v0.2.5
> **Owner:** product-engineer
> **Closed:** 2026-07-15

## Summary

dadaia-workspace now exposes a machine-readable capability contract, exact-version
transactional reconciliation, caller-owned context binding, safe empty-repository
baselining, and disposable full-capability certification. Fresh scaffolds are doctor-clean;
all four lifecycle workflows complete through their Python gates; panel, reports, context
transitions, public projections, Codex, and PI have executable validation paths.

Hermes Crawler now consumes those contracts through canonical commands, full diagnostic
retention, exact-version update checks, and certification. Its consumer specs are pattern v4
and doctor-clean.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Enforce caller-owned context contracts | Pending operator commit |
| T2 | Publish machine-readable capabilities | Pending operator commit |
| T3 | Make upgrades transactional | Pending operator commit |
| T4 | Support explicit empty-repository baselines | Pending operator commit |
| T5 | Preflight lifecycle workers and retain diagnostics | Pending operator commit |
| T6 | Certify every public feature family | Pending operator commit |
| T7 | Project version-matched agent mastery | Pending operator commit |
| T8 | Prove Hermes compatibility and close | Pending operator commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Provider suite | `python -m pytest -p no:cacheprovider` | `2661 passed, 9 expected skips in 165.84s` |
| Hermes Crawler suite | `python -m pytest -p no:cacheprovider docker/hermes-crawler/tests` | `50 passed in 1.27s` |
| Static quality | `ruff check; ruff format --check; mypy dadaia_workspace; lint-imports --no-cache` | `814 files formatted; 323 source files typed; 10 contracts kept, 0 broken` |
| Live Codex contract | `DADAIA_CODEX_LIVE=1 pytest tests/integration/codex_live` | `2 passed in 202.40s` |
| Live PI contract | `DADAIA_E2E_REAL_WORKER=1 DADAIA_PI_LIVE=1 pytest tests/integration/pi_live` | `3 passed in 280.73s` |
| Built wheel install | `pip install dadaia_workspace-0.2.5-py3-none-any.whl` | `installed 0.2.5 with declared dependencies and no invalid-extra warning` |
| Built wheel certification | `dadaia certify --json` | `ok=true; provider=0.2.5; 16/16 checks PASS` |
| Consumer specs | `dadaia specs doctor --specs-dir repos/dadaia-agents/specs` | `0 errors, 0 warnings` |

Final wheel:

```text
/home/ubuntu/workspace/.dadaia/tmp/release-v025-certified-final/wheelhouse/dadaia_workspace-0.2.5-py3-none-any.whl
sha256 da094518e88c92ef47f5c58cccda64c2055bbdc17b488389967fca845db9edbd
```

## Drifts

### static-quality-debt

**Description:** The final ladder exposed mypy errors, stale import-linter entries, broken
architecture edges, and Ruff drift that ordinary runtime tests did not surface.

**Resolution:** Types were made explicit, a missing human `--show-policy` printer was
implemented, certification process control moved behind a core port, presence reads became
injected, ignored-import debt was ratcheted, and the repository was canonically formatted.

**Memory updates:** `specs/memory/tech-stack.md` and Codex harness memory now match the
verified runtime and quality contract.

### codex-runtime-facts-changed

**Description:** Codex CLI 0.144.4 now fires projected hooks in headless exec, contradicting
historical 0.139 behavior and old doctor/skill prose.

**Resolution:** Live probes now assert headless and TUI parity; doctor, mastery skills,
shared harness literacy, and product memory report the current fact and require re-probing
after future CLI upgrades.

**Memory updates:** `specs/memory/product/harness/harness-codex.md`,
`specs/memory/product/index.md`, and generated catalog.

## Memory updates

- `specs/memory/product/harness/harness-codex.md` — current hook parity and
  `workspace-write` lifecycle default.
- `specs/memory/product/index.md` and `catalog.json` — regenerated from atom frontmatter.
- `specs/memory/tech-stack.md` — live-certified Codex CLI and release toolchain facts.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/bugs.jsonl` | event-sourced bug ledger | all v0.2.5 findings resolved | `dadaia bugs status --specs-dir specs` reports `0 open bug(s)` |

## Backlog returns

None. Every defect discovered during implementation and certification was fixed in this
release rather than deferred.

## Archive decision

**KEEP** — retain the release in `specs/releases/` until the operator creates the final
commit; archive movement is intentionally not performed from an uncommitted working tree.
