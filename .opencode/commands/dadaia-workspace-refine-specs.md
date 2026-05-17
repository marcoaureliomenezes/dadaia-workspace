---
description: "Use when: refining dadaia-workspace specs before implementation. Runs the canonical review order, edits owner docs first, aligns derived docs second, and records unresolved gaps in specs/backlog/candidates.md."
sync_version: "1.2.0"
---

# dadaia-workspace-refine-specs

Refine the product specs before any implementation.

## Required workflow

1. Load documents in canonical order:
	- `specs/constitution.md`
	- `specs/memory/architecture.md`
	- `specs/memory/product.md`
	- `specs/memory/tech-stack.md`
	- `specs/foundation/SPEC.md`
	- `specs/SPEC.md`
	- the affected feature specs
	- `specs/PLAN.md` and `specs/TASKS.md` if planning scope is involved
	- `specs/backlog/candidates.md`
2. Decide which document owns each requested change before editing anything.
3. Edit owner documents first.
4. Align affected feature specs second.
5. Regenerate or realign `PLAN.md` and `TASKS.md` last if the contract changed.
6. If governance assets changed, update `dadaia_workspace/public/` directly and keep `dadaia-workspace/.claude/` absent.
7. If no unresolved issues remain, update every affected canonical artifact header to the explicit marker `**Status:** Aprovado`.
8. If unresolved issues remain, keep affected artifacts as `Em revisão` and record the remaining gaps in `specs/backlog/candidates.md` under `## Hotfixes pendentes`.
9. Treat `report-specs-review.md` as historical context only, never as the canonical source of current truth.
10. Do not implement product code in the same pass unless the user explicitly asks and the refined specs are approved.