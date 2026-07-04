---
name: hard-remove-model-flag-across-run-verbs
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.56 closure backlog return (the `--model` non-fatal deprecation-warning ruling)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/cli/commands/lifecycle.py#_warn_model_deprecated" }
    change: "hard-REMOVE the `--model <id>:<effort>` flag from every `dadaia lifecycle` run verb (release define, backlog define, implement, review qa|security|code, close, pipeline, audit, research, bug_report, implement-review) once all callers and tests migrate to `--step-model <profile-id>`; delete the `_warn_model_deprecated` soft-deprecation seam and the `--model` option itself so the retired raw id:effort surface leaves no legacy code path. v0.1.56 made `--model` a non-fatal stderr deprecation warning (naming `--step-model <profile-id>` + `workflow profiles list`) that proceeds under the resolved policy; this entry tracks retiring the flag entirely."
---

# BACKLOG — Hard-remove `--model` across run verbs

**Priority:** MEDIUM. Follow-through on the v0.1.56 `--model` deprecation ruling.
v0.1.56 kept `--model` as a **non-fatal deprecation warning** rather than a hard error
or a silent no-op: accept the flag, emit a one-line stderr warning naming
`--step-model <profile-id>` + `workflow profiles list`, then proceed under the
resolved policy. A silent no-op would be a hidden-side-effect (anti-slop) defect; a
hard error would break every script/test still passing `--model` mid-mandate. Once
every caller migrates to `--step-model`, **remove the flag and the
`_warn_model_deprecated` seam across all run verbs** so the retired raw
`<id>:<effort>` surface disappears (no-legacy-code path). Gated on caller migration;
no user-facing behavior change beyond the flag's removal.
