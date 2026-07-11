---
name: context-name-allowlist-at-resolution-rungs
status: delivered
delivered_in: v0.1.80
opened: 2026-07-11
owner: project-manager (curates)
priority: P4
source: "v0.1.77 security review INFO recommendation (push-cycle review of aeb97983): the explicit/--context and DADAIA_CONTEXT rungs feed the repos/<name>/specs path join unvalidated; operator-controlled (no privilege elevation), but defense-in-depth wants the existing [A-Za-z0-9_-]+ allowlist applied at the seam"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/cli/_specs_resolution.py#resolve_context_for_cli" }
    change: "apply the existing context-name allowlist (the [A-Za-z0-9_-]+ pattern already used for bind-epoch marker filenames in core/specs_resolver.py) to the explicit and DADAIA_CONTEXT rungs of resolve_context_for_cli, rejecting traversal-shaped names with an actionable message before any path join. Defense-in-depth only: both rungs are operator-controlled and the operator can already touch any path directly (v0.1.77 security review, STRIDE: no elevation). Executed-path unit cases: traversal-shaped explicit/env names rejected; valid names unchanged."
---

# BACKLOG — Apply the context-name allowlist at the resolution rungs (P4)

**Priority: P4 (defense-in-depth, LOW).** See frontmatter source. One small guard +
tests at the seam; no behavior change for valid names.
