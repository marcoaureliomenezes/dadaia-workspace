# CLOSURE — Release v0.1.73 — Governance hygiene

**Release ID:** v0.1.73
**Status:** Aprovado

## Summary

Operator-mandated governance cleanup + all 4 open ledger bugs, self-applied to this repo.

| Item | Fix | Disposition |
|---|---|---|
| `bugs-store-fragments-into-hourly-files` (HIGH) | FR1 — single canonical append-only `bugs.jsonl` (hour-rotation removed); `specs upgrade` v3→4 `bugs-single-file` consolidates hourly files chronologically + collapses `_archive/*.md` into one `archive.jsonl` (verbatim, lossless). Self-applied: this repo went 52 files + 99 `.md` → 2 JSONL files, doctor clean, readers identical | resolved |
| backlog age-visibility (operator contract) | FR2 — `YYYYMMDD-` first-commit-date prefixes on all 8 entries; REJECTED entry archived; `candidates.md` rebuilt; backlog doctor clean | done |
| resolution law (blocking form) | FR3 — `bugs append --event resolved` refused without `--resolution-evidence` (≥20 chars); evidence lands in the event; schema history-tolerant (gate at the sole write path) | done |
| `migrate-agent-tier-frontmatter-redos-on-unterminated-block` (MEDIUM) | FR4 — linear splitlines frontmatter scan; adversarial 50k-newline input 33s → <1s | resolved |
| `specs-upgrade-backup-trips-preflight-dirty-gate` (MEDIUM) | FR5 — backups land at `<ws>/.dadaia/tmp/specs-upgrade-backups/<slug>/` (outside the worktree); sibling fallback without a workspace; proven live during the self-upgrade | resolved |
| `stray-dadaia-tmp-inside-repo` (MEDIUM) | FR6 — doctor invariant REPO-DADAIA-1 (flag in-repo `.dadaia/`; `--fix` removes only stateless strays, never `states/`) | resolved |

F2 (`central-bind-resolution-seam`) honestly descoped → timestamped HIGH backlog entry
(class-level fix mandated by the resolution law; too large to bundle).

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5073 passed / 19 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Self-application | PASS — real `specs upgrade` 2→4 on this repo: 151 moves, doctor clean, `bugs status` identical pre/post (4 open) | upgrade transcript |
| Deliberate contract updates | 4 store tests (hourly rotation) + 1 backup-location test + 4 bugs-CLI tests updated to the new operator contracts | diff |
| ruff / mypy --strict / import-linter | PASS (9/9 contracts) | pre-push + CI |
| Security | APPROVED keyed to pushed sha | handoff |
| CI (full matrix) | GREEN — PR #141 merged `9b4eb78d` | GitHub Actions |

## Drifts

- Doctor SPEC-DOC-033 extended: canonical `bugs.jsonl` gets schema + coherence checks,
  no rotation ceiling; legacy hourly files unchanged. Doctor golden regenerated for the
  canonical-version bump (3→4).
- `evidence` added to `bug-event-v1` as OPTIONAL (history-tolerant); the blocking
  requirement lives at the CLI append path.

## Memory updates

None required — the resolution law and gate-coherence laws landed in
`specs/memory/quality-assurance.md` at v0.1.72 closure; this release implements their
blocking/tooling half. Product catalog untouched.

## Next

Open ledger after dispositions: 0. Backlog: 8 timestamped entries, `candidates.md` as
index; top pick for next release: `20260709-central-bind-resolution-seam` (HIGH).
