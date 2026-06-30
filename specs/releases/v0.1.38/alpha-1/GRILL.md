# GRILL: v0.1.38 alpha-1 - pi-agent-fourth-harness WS-PI-5

> **Status:** Aprovado
> **Release ID:** v0.1.38
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Created:** 2026-06-29

## Intake

Operator objective: define and implement `pi-agent-fourth-harness`.

Current backlog truth:

- `pi-agent-fourth-harness` is already delivered for WS-PI-1, WS-PI-2, WS-PI-3, WS-PI-4,
  and WS-PI-6.
- The only surviving residual is WS-PI-5: add/keep a deprecation pointer in the standalone
  `dadaia-pi-workspace` repo and mark the `dadaia-pi-workspace` context DEAD.
- The backlog item explicitly forbids deleting the repo history.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-1 | Consume `pi-agent-fourth-harness` only if WS-PI-5 is completed end-to-end. | It is the last residual; partial handling would keep the item live. |
| D-2 | Use `dadaia context dead dadaia-pi-workspace --commit` rather than manual registry edits or deletion. | Workspace management state is CLI-owned and context dead performs the ALIVE to DEAD transition. |
| D-3 | The standalone repo may be removed from disk by the context lifecycle command, but its git history must remain in its remote. | Backlog says never delete the repo; DEAD state means not cloned/active in this workspace. |
| D-4 | Treat the existing untracked `repos/dadaia-pi-workspace/README.md` as the deprecation pointer, after validating content and committing it through the context lifecycle. | It already points to the folded-in dadaia-workspace PI harness and the live epic. |

## Acceptance

- `dadaia-pi-workspace` context is `dead`.
- `repos/dadaia-pi-workspace/` is absent after the DEAD transition.
- The standalone repo remote contains the deprecation `README.md` pointer before it is removed
  locally.
- `pi-agent-fourth-harness` is terminally dispositioned as consumed/delivered by v0.1.38.
- Specs doctor and public doctor pass with no new errors.
