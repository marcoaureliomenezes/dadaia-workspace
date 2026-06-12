---
name: codex-rules-dadaia-prefix-never-matches-venv-invocation
status: Closed
severity: MEDIUM
reported: 2026-06-11
resolved_in: v0.1.13
surface: codex_assets (generated .codex/rules/dadaia-command-policy.rules)
session_id: null
---

**Symptom:** The generated Starlark command policy gates `["dadaia", "public",
"install"]` and `["dadaia", "context", "dead"]` by bare-name argv0 prefix — but the
workspace convention (root AGENTS.md "Operating Defaults", shell-hygiene discipline)
mandates invoking `.dadaia/.venv/bin/dadaia`, and bare `dadaia` is intentionally
off-PATH. A prefix rule on argv0 `dadaia` never matches an absolute-path argv0, so the
two highest-value prompt rules can never fire in a compliant session.

**Repro:** Read `.codex/rules/dadaia-command-policy.rules`; compare the `prefix_rule`
patterns against the mandated invocation form `<ws>/.dadaia/.venv/bin/dadaia public
install`. The pattern cannot match. Doctor D-CX-8 validates rule *shape* only, so it
stays `[ok]`.

**Expected:** Command-policy rules match the invocation form the workspace itself
mandates (venv-absolute path), proven by `match=` examples using the real form.

**Notes:** Found by the Codex runtime fidelity audit (F-5),
`specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`. Secondary nit:
`git commit` appears in a `not_match` example but no rule governs it.

**Resolution (v0.1.13, T-013-10):** generated patterns now use the mandated venv
invocation form (`.dadaia/.venv/bin/dadaia public install`,
`.dadaia/.venv/bin/dadaia context dead`), proven by real-form `match=` examples in the
projected `.codex/rules/dadaia-command-policy.rules`; tests assert the real form
matches and bare-name-only patterns are gone. Evidence in
`specs/_archive/releases/v0.1.13/CLOSURE.md` (Dispositions).
