# CONTEXT-ENGINEERING.md — Authoring and Auditing the AI-Entity Surface

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth).
Persona files, skills, and rules are themselves prompts — every shipped line is paid for in tokens by every downstream invocation.
The craft: maximize behavior-change-per-token under a hard context budget, keeping every persona structurally identical.

- Five disciplines, ordered by how often you reach for them: token economy, instruction hierarchy.
- Disciplines (continued): consistency invariants, tier selection, scope-drift detection.
- Apply them in that order when authoring; apply them in reverse when reviewing someone else's change (safety first).

---

## 1. Token Economy

```
cost(file) = tokens(file) x invocations(file) x unit_price(tier)
```

- A persona body is re-read on every invocation; a skill body only when loaded; an `always_on` rule on every turn of every in-scope agent.
- The first question for any line: does it change behavior often enough to justify its lifetime token cost in this layer?

| Layer | Read frequency | Rule of thumb |
|---|---|---|
| `always_on` rule | Every turn, every in-scope agent | Reserve for invariants that must never be forgotten; keep terse |
| Agent persona body | Every invocation of that one agent | Lean on frontmatter for hard rules |
| Skill body | Only when the skill is loaded | Right home for deep protocols and tables |
| Frontmatter (any) | Parsed by tooling, not re-reasoned | Put machine-enforced hard rules here |

- Corollary: depth belongs in skills, not personas — an inlined 40-line protocol pays every dispatch, a referenced skill only when needed.
- A table compresses roughly 3-5x versus prose carrying the same machine-readable signal.

| Content shape | Use | Reason |
|---|---|---|
| Enumerable rules with fixed columns | Table | Positional encoding; no connective tokens |
| One-off rationale / a "why" | Prose (1-3 sentences) | Tables can't carry causal nuance economically |
| Branching decision logic | Decision table or tree | Each row is a complete rule |
| A single hard constraint | Frontmatter field | Machine-enforced; zero body cost |

- "First... then... however... unless..." prose is almost always a table in disguise — convert it.
- Inline content only if: short (<=~3 lines), needed on essentially every invocation, and changes behavior at the point of reading.
- Otherwise link to the canonical source and carry only a one-line orientation pointer.
- Shared protocol (workspace-protocol, tmp-file guardrail, SDD gate flow, task-manager flow) is authored once, referenced everywhere.
- Restating shared protocol in N personas multiplies lifetime cost by N and drifts N ways.
- Smell: the same paragraph appears verbatim in two or more files — a missing link or a missing skill (see §5).
- Token estimation for audits: `tokens ~= words x 1.33` (English), `tokens ~= words x 1.20` (Portuguese).
- Compute via `wc -w` on the file body, multiply by rate, multiply by invocation frequency for lifetime-cost.

---

## 2. Instruction Hierarchy and Attention Ordering

- A persona is read top-to-bottom; identity and early constraints anchor everything that follows.
- Refusal templates must be encountered before the agent reasons itself into accepting an out-of-scope task.
- Reordering sections moves the agent's attention and changes which constraints dominate on conflict.

| # | Section | Answers the question | Form |
|---|---|---|---|
| 1 | Identity | What IS this agent? | One paragraph |
| 2 | Scope | What does it write / NOT write? | Table preferred |
| 3 | Forbidden actions + `[SCOPE ERROR]` | How does it refuse? | Verbatim refusal block |
| 4 | Stack expertise | What technical depth does it have? | Sub-headed by stack |
| 5 | Workflow protocol | TDD / task-manager / release resolution | Steps |
| 6 | Security rules | What must it never do? | OWASP-style table where applicable |
| 7 | Collaboration patterns | Who does it hand off to? | Named-agent table |
| 8 | Write permissions | Where may it write? | Table mirroring `paths.write_allowlist` |
| 9 | Report contract | What does it emit at the end? | Steps / template ref |
| 10 | CLI reference | What tools does it drive? | Command list |

- Ordering logic: who -> what -> how-it-refuses -> what-it-knows -> how-it-works -> what-it-must-not.
- Ordering logic (continued): who-it-talks-to -> where-it-writes -> what-it-emits -> how-it-operates.
- Refusal (3) precedes capability (4) deliberately — an agent that knows its limits before its powers is harder to talk out of scope.
- Do not reorder without a documented reason; reordering changes behavior.

Audit protocol — detecting order drift:

1. Extract the section spine: `grep -n '^## ' <persona>.md`.
2. Map each heading to a canonical slot (1..10); omission is allowed, reordering is not.
3. Verify mapped slot numbers are strictly non-decreasing top-to-bottom.
4. Any inversion (a later slot above an earlier one) is an ORDER-DRIFT finding.
5. Classify: inversion of 1/2/3 = HIGH; inversion among 4..10 = MEDIUM; extra non-canonical section = LOW.
6. Fix by moving sections to restore canonical order — never rewrite content while reordering.

---

## 3. Persona-Consistency Invariants

Five invariants MUST hold across all personas. Inconsistencies are bugs — file them in a refactor report.

| # | Invariant | What must match |
|---|---|---|
| I1 | Frontmatter schema | Same keys, same order (see below); no `tier`/`model` frontmatter key |
| I2 | Body section order | The canonical 10-section spine of §2 |
| I3 | `[SCOPE ERROR]` block format | Opener, one-line identity, explicit redirect per foreign domain |
| I4 | TDD / task-manager reservation flow | Identical `[ ]`->`[-]`->`[x]` flow, referenced (not restated) |
| I5 | Handoff JSON contract | All agents emit via `dd-handoff-emitter` against the same schema version |

- I1 reference key list (on-disk today): `name`, `description`, `dispatch_band`, `activity_class`, `concurrency_relationship`.
- I1 reference key list (continued): `gate_role`, `tools`, `skills`, `maxTurns`, `input_contract`, `paths.write_allowlist`.
- Model resolution is a separate policy-overlay mechanism, never asserted in persona frontmatter.

Detection method:

1. I1: `grep -n '^[a-z_]*:' <persona>.md`, diff the key list against the on-disk reference (re-derive if the schema changes).
2. I2: run the §2 audit protocol.
3. I3: `grep -A12 '\[SCOPE ERROR\]' <persona>.md`; verify opener, one-line identity, and a correct redirect per domain.
4. I4: confirm the persona references the task-manager flow rather than restating it.
5. I5: confirm `dd-handoff-emitter` is in the skills list and the report section cites the current schema.

Fix protocol:

1. Never spot-fix one persona in isolation for a fleet-spanning invariant — check whether the reference changed.
2. Schema/format changes propagate via release, never a quiet edit to a single file.
3. Keep the fix diff minimal and mechanical — reviewers must confirm "this only restored the invariant."
4. Re-run detection across the whole fleet after the fix.

---

## 4. Model-Tier Selection Decision Protocol

- Tier is a cost-and-quality decision from workload character and measured evidence — never "make it smarter."

| Axis | Low -> High |
|---|---|
| Reasoning depth | Mechanical transform -> multi-step synthesis / recursive analysis |
| Context breadth | Single file -> whole-fleet / cross-layer reasoning |
| Error cost | Easily reverted -> ships to all consumers / hard to undo |
| Output novelty | Reformat existing -> author new structure from a brief |
| Volume | Occasional -> high-frequency / bulk |

- The dominant task drives the tier — not the easiest or the rarest.
- Tier names are derived from `core/model_registry.py` — never hand-maintain a copy that can drift.

| Registry tier | Workload character |
|---|---|
| `deep` | Heavy synthesis, recursive analysis, persona/skill authoring, fleet audit, security reasoning |
| `dispatch` | Orchestration, dispatch authority, review verdicts, broad-context implementation |
| `standard` | Mid-cost general implementation |
| `fast` | High-volume mechanical reformatting, bulk renames, deterministic transforms |

- Current per-runtime model ids and Codex reasoning-effort come from `core/model_registry.py`, never hand-copied.
- On Codex the tiering axis is (model id x model_reasoning_effort); on Claude it is the model id.
- Quote the registry entry (id + latest pricing row) when recommending a move, so the cost delta comes from live data.
- Move up a tier only when depth/breadth/error-cost are all high; move down only when the task is mechanical and high-volume.

Justify a tier BUMP (down -> up):

1. Capture concrete invocation traces where the current tier produced incorrect, shallow, or rework-triggering output.
2. Show the failure correlates with the workload axes, not a fixable prompt defect.
3. State the cost delta (bump price x invocation frequency); bump only if rework cost exceeds the price delta.
4. Record the justification one-liner in the release task.
5. Require an operator-approved release task — never a silent edit, especially a self-edit bumping your own tier.

Justify a tier DOWNGRADE (up -> down):

1. Sample recent outputs at the current tier; confirm none required the depth the tier provides.
2. Confirm error-cost is low or the work is reviewed downstream anyway.
3. Estimate the saving: price delta x invocation frequency.
4. Downgrade, then watch the next few dispatches for quality regression; revert if rework appears.
5. Route through the release flow so the change stays observable, even though it is the cheaper experiment.

---

## 5. Recursive Scope-Drift Detection

- The AI-entity surface is recursive: an agent can edit another agent's file, and `ai-engineer` can edit `ai-engineer`.
- Failure signature: agent A "fixes" agent B's persona -> B's behavior shifts -> agent C (dispatches B) breaks, far from the edit.
- Defense: three detection rules applied before the edit lands, plus a topology guard for the self-edit case.

Detection rule 1 — write_allowlist agreement (frontmatter vs body):

1. Extract the frontmatter `paths.write_allowlist` globs and the body Write-permissions table rows.
2. Diff them; a body-granted/frontmatter-omitted path is a FALSE-PROMISE drift.
3. A frontmatter-granted/body-omitted path is a SILENT-PRIVILEGE drift.
4. The frontmatter is authoritative by convention — fix both so they match the SPEC's authorized scope, never wider.
5. Widening an allowlist requires an operator-approved release task (privilege-escalation control).

Detection rule 2 — forbidden-actions table propagates via release, not spot-edit:

1. Compare each persona's `[SCOPE ERROR]` redirect set against the reference.
2. A single persona whose redirect set differs from all others is spot-edit drift.
3. If the reference changed: open a fleet-wide release task and update all personas together.
4. If one persona drifted: restore it to the reference — never "improve" one persona's refusal block in isolation.

Detection rule 3 — self-edit risk + topology-guard protocol:

1. `ai-engineer` editing `ai-engineer.md` (or any dispatch-graph/allowlist/tool-grant change) is the highest-risk operation.
2. Confirm an operator-approved release task authorizes the specific change — no self-granted privileges.
3. Make the edit minimal and single-purpose.
4. Re-verify topology by hand: persona count matches the roster, required frontmatter keys are present and non-empty.
5. Confirm `project-manager` and `project-auditor` each still name every leaf agent.
6. Pair with `security-reviewer` for any change adding a powerful tool or widening an allowlist.
7. Re-validate frontmatter via the workspace reader test so the parse still succeeds.

Re-verify topology invariants whenever: `write_allowlist` changes, `tools` changes (esp. adding `Agent`), or a persona is added/removed.
Re-verify topology invariants also when: `ai-engineer` self-edits, or a `[SCOPE ERROR]` redirect set changes.

- Skill-extraction trigger: when two or more personas restate the same protocol, extract it into `public/skills/<name>/SKILL.md`.
- Replace every inline copy with a one-line reference — a skill loads once and is referenced; inline content loads N times and drifts N ways.
- This is the highest-leverage move when an efficiency audit finds repeated context across personas.

---

## Applying this file

- Authoring a new persona/skill/rule: walk §1 (cheapest layer) -> §2 (spine) -> §3 (invariants) -> §4 (tier) -> §5 (drift).
- Reviewing someone else's AI-entity change: walk in reverse — §5 first, then §3, §2, §1, §4.
- Auditing the fleet (efficiency report): §1 ranks files by lifetime cost, §2/§3 find structural drift.
- Auditing (continued): §4 recommends tier moves, §5 recommends deduplication.
