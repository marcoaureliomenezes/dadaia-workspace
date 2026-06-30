release: none
phase: none
---

# Active release: none

**v0.1.43** — *lifecycle fragment context-engineering optimization + release-aware lease* —
is **CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.43/` (CLOSURE.md). It closed the
two model-driven review-gate coverage holes (authored `implementation.security_review` +
`implementation.code_review`, wired both pipeline review steps off the generic-prompt
fallback), broadly wired `shared.anti_slop` / `output_handoff` / `memory_selection`, made
`backlog_definition.conflict_scan` a downgrade-only model consult and clamped the classifier
fail-open to `{OVERLAP, SUPERSEDES, DEPENDS_ON}`, fixed the HIGH bug
`lease-pid-veto-ignores-archived-release` (release-aware lease reclaim), added the
no-generic-prompt / no-orphan guardrail, and trimmed token redundancy. Shipped rebased-clean
onto `main` (squash, PR #76) — independent of the unmerged v0.1.33–v0.1.42 line. All gates
green: contract coverage 82.35%, pytest 4160 passed, mypy/ruff clean, public + specs doctor
clean; architect + qa + security APPROVED.

No release is currently active. Open the next release with `dadaia release new` when work is
picked.

**Residual (not in scope):** the unmerged `feature/v0.1.36-pi-layer2-validation` /
`wip/abandoned-v0.1.40-42` line (releases v0.1.33–v0.1.42, incl. the constitution-realignment
work) remains unmerged and carries an accumulated unit+contract coverage-gate debt
(~45% vs the 80% gate) that must be remediated before that line can ship.
