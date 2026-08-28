---
name: dadaia-workspace-spec-navigator
description: >
  Use when: loading dadaia-workspace specs in canonical order for implementation,
  review, planning, or release closure. Resolves the active release via its
  RELEASE.json phase field (no fold) and reads memory Markdown + the active release's
  SPEC/PLAN/TASKS. Supports both the dadaia-workspace repository itself and any
  active runtime context discovered via spec_contexts.json (v2 registry) or
  `dadaia context show --json`.
tldr: "Resolve context, read constitution+memory, resolve release via RELEASE.json phase, read SPEC/PLAN/TASKS, verify Aprovado."
---

# dadaia-workspace-spec-navigator

## 1. When

- Starting implementation, review, planning, or release closure work.
- Any task that needs the active release's SPEC/PLAN/TASKS or product memory.

## 2. Steps

1. Resolve the spec context: `DADAIA_CONTEXT` env var, else your own session binding (`dadaia context show --json`).
2. Fall back to the repo containing your cwd if neither of the above resolves it.
3. Never halt to ask for a bind — binding is optional; only zero ALIVE contexts stops navigation.
4. Read `<specs-dir>/constitution.md` first, always.
5. Read `<specs-dir>/memory/ARCHITECTURE.md` and `<specs-dir>/memory/TECHSTACK.md`.
6. Read `<specs-dir>/memory/product/catalog.json`; select the 1-3 relevant feature atoms.
7. Load only the selected atoms, not every atom in the catalog.
8. Resolve the active release: read `<specs-dir>/releases/<release-id>/RELEASE.json`'s `phase` field directly.
9. Read the release's `segment` field, when present, for the active `alpha-N`/`rc-N` segment.
10. If no RELEASE.json-carrying release directory exists: stop before implementation, inform the operator.
11. Set `<rel-path>` = `<release-id>/<segment>` when segmented, else `<release-id>`.
12. Read `releases/<rel-path>/SPEC.md` first.
13. Read `PLAN.md` next when planning or implementation is in scope.
14. Read `TASKS.md` next when implementation is in scope.
15. Read `RELEASE.json`'s `log` entries only when `phase` is `CLOSURE` or `ARCHIVED`.
16. Verify every loaded SPEC/PLAN/TASKS carries `**Status:** Aprovado` before any implementation.
17. Stop and name the unapproved artifact if step 16 fails.
18. Treat `specs/features/<name>/{SPEC,PLAN,TASKS}.md`, if present, as legacy — authorizes nothing on its own.
19. Report legacy-feature presence as a migration warning.

## 3. Done when

- Context, active release, and segment are resolved and named.
- Constitution, ARCHITECTURE.md, TECHSTACK.md, and 1-3 relevant product atoms are read.
- SPEC/PLAN/TASKS in scope all carry `**Status:** Aprovado`, or the gap is reported first.

## 4. References

- `DADAIA.md` §3 — context resolution order.
- `DADAIA.md` §6 — status-token lifecycle (`Draft` → `Em revisão` → `Aprovado`).
- `dd-release-implement` (`RELEASE-EVENTS.md`) — `RELEASE.json` shape.
- `_archive/` and `backlog/` are read-only history/informal sources — never a source of approval.
- Never reference `standby`, `context_dir`, `select`, `is_selected` — retired in v3.0.
- Memory Markdown is write-locked except `product-engineer` in DEFINITION/CLOSURE phase.
