---
name: bug-guardrail-template-omits-required-session-id
status: Open
severity: LOW
reported: 2026-06-12
session_id: null
surface: bug-registration-guardrail rule (public/rules) vs specs doctor TREE-7 invariant
---

**Symptom:** The `bug-registration-guardrail` rule's "Minimum bug record" template
shows frontmatter `name/status/severity/reported/surface` — but the specs doctor
TREE-7 invariant (enforced by `test_repo_specs_have_no_tree_errors`, which runs in the
pre-push CI gate) REQUIRES a `session_id:` field. Agents that follow the rule verbatim
produce bug files that fail TREE-7 and block the next push. Reproduced three times in
one day (2026-06-11/12): `agents-md-instructs-html-report-validation-unsupported`,
`context-dead-nonwritable-guard-rejects-standard-git-objects`,
`context-release-leaves-lease-heartbeat-renewing` — each filed by a different agent,
each missing `session_id`, each blocking a push until hand-fixed.

**Repro:** Author a bug file copying the rule's template exactly; run
`dadaia specs doctor` (or the pre-push gate) → TREE-7 ERROR.

**Expected:** Rule template and doctor invariant agree: add `session_id: null` to the
template in `dadaia_workspace/public/rules/` source (and any scaffold/example bug
files), so the documented minimum record passes the tree invariants.

**Notes:** Doc-vs-validator contract drift; one-line source fix + reprojection.
