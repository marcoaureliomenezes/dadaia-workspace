---
name: codex-posttooluse-heartbeat-matcher-write-only
status: Resolved
severity: HIGH
session_id: null
reported: 2026-06-10
resolved: 2026-06-10
resolved_in: v0.1.10 (rc-2)
surface: infrastructure/runtime_config.py codex_hooks() PostToolUse matcher (+ ai-harness-codex skill claim)
---

**Resolution (v0.1.10 rc-2, re-audit N-2):** `codex_hooks()` PostToolUse block now
omits the `matcher` key entirely — Codex's canonical match-all form (the same shape
already used by the `UserPromptSubmit` block). The heartbeat therefore fires after
*every* Codex tool, including Bash and read-only calls, matching the Claude `*` form and
closing the renewal-starvation half of the lease-theft incident on the Codex harness.
The PreToolUse write gates stay scoped to `^(apply_patch|Edit|Write)$`. Projected
`.codex/hooks.json` re-verified (PostToolUse carries no matcher; doctor exit 0,
`[ok] public-privacy`). Regression test:
`tests/unit/infrastructure/test_public_assets.py::TestConfigGenerators::test_codex_posttooluse_heartbeat_fires_on_all_tools`
(pins omitted PostToolUse matcher + write-only PreToolUse matchers);
`test_codex_hooks_structure` updated to assert the omitted matcher.

Note (ai-engineer follow-up, out of software-engineer scope): the `ai-harness-codex`
SKILL.md:321 illustrative wording uses the literal `PostToolUse *` glyph. Behaviorally
the claim ("must fire on every tool, so its matcher stays broad") is now TRUE; the
glyph-vs-omitted-matcher nuance is a public-skill doc detail for ai-engineer to refine.

**Symptom:** The generated Codex `hooks.json` wires the lease heartbeat
(`hooks.sdd_post_gate`) on PostToolUse with the WRITE matcher
`^(apply_patch|Edit|Write)$` (runtime_config.py:152,181-194; confirmed in the live
`.codex/hooks.json`). On Codex the heartbeat therefore fires only after write tools — a
holder doing >120 s of reads/Bash never renews and its lease goes TTL-stale, re-opening
the renewal-starvation half of the lease-theft bug on one of the two active harnesses.
The Claude generator was fixed (T-010-18: PostToolUse `*`, runtime_config.py:55-59,99)
but the Codex generator was not. Compounded by
`lease-pid-veto-records-ephemeral-hook-pid` (no working pid backstop).

Additionally, the `ai-harness-codex` skill states the live shape falsely
(SKILL.md:321): "`PostToolUse * → …hooks.sdd_post_gate` (lease heartbeat — must fire on
every tool, so its matcher stays broad)" — a text-vs-code contradiction in the
ai-engineer-restricted compiled protocol.

**Repro:** `python -c "from dadaia_workspace.infrastructure.runtime_config import codex_hooks; from pathlib import Path; import json; print(json.dumps(codex_hooks(Path('.'))['hooks']['PostToolUse'], indent=2))"`
→ matcher `^(apply_patch|Edit|Write)$`.

**Expected:** Heartbeat must fire after every tool (T-010-04 breadth requirement, same
rationale as the Claude `*` matcher), or — if Codex cannot match-all on PostToolUse —
the limitation must be documented and the skill claim corrected.

**Notes:** Fix: broaden the Codex PostToolUse matcher to the Codex match-all form +
unit test mirroring AC-R6-05 for the Codex generator; correct ai-harness-codex
SKILL.md:321. Found by the 2026-06-10T052944Z ai-engineer re-audit.
