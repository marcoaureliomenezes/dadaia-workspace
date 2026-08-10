---
name: ai-context-engineering
description: >
  Harness-agnostic context-engineering craft for ai-engineer. Compiled decision
  protocols for token economy, instruction hierarchy and attention ordering,
  persona-consistency invariants, model-tier selection, and recursive
  scope-drift detection. Use when authoring or auditing any AI-entity surface
  file (agent persona, skill, rule, workflow, command, hook).
applyTo: "dadaia_workspace/public/**"
---

# ai-context-engineering — Authoring and Auditing the AI-Entity Surface

Persona files, skills, and rules are themselves prompts. Every line you ship is paid
for in tokens by every downstream invocation that loads the file. The craft is not
"write good instructions" — it is **maximize behavior-change-per-token under a hard
context budget, while keeping every persona structurally identical so the fleet stays
auditable.** This skill is the protocol layer: rubrics, decision tables, and audit
procedures, not platitudes.

The five disciplines below are ordered by how often you reach for them: token economy
governs every line; instruction hierarchy governs every file's shape; consistency
invariants govern the fleet; tier selection governs cost; scope-drift detection governs
safety of edits. Apply them in that order when authoring; apply them in reverse when
reviewing someone else's change (safety first).

---

## 1. Token Economy

### The core identity

```
cost(file) = tokens(file) × invocations(file) × unit_price(tier)
```

A persona body is re-read by the model on **every invocation**. A skill body is read
**only when the skill is loaded**. A rule with `always_on` is read on **every** turn of
**every** agent it applies to. These three multipliers differ by orders of magnitude, so
the same paragraph has a wildly different lifetime cost depending on which layer it lives
in. The first question for any line is never "is this true?" but "does this line change
behavior often enough to justify its lifetime token cost in this layer?"

### Layer cost ranking (most expensive first)

| Layer | Read frequency | Rule of thumb |
|---|---|---|
| `always_on` rule | Every turn, every in-scope agent | Reserve for invariants that must never be forgotten. Keep it terse. |
| Agent persona body | Every invocation of that one agent | The agent's behavioral contract. Lean on frontmatter for hard rules. |
| Skill body | Only when the skill is loaded | The right home for deep protocols, tables, and procedures consulted occasionally. |
| Frontmatter (any) | Parsed by tooling, not re-reasoned each turn | Put machine-enforced hard rules here (allowlists, tools, tier). |

**Corollary:** depth belongs in skills, not personas. A persona that inlines a 40-line
protocol pays for those 40 lines on every dispatch; the same protocol as a referenced
skill is paid for only when actually needed. This is exactly why the context-engineering
content was lifted out of the ai-engineer persona into this skill.

### Tables-vs-prose compression

For any **enumerable** content (paths, OWASP items, collaboration handshakes,
decision branches), a table compresses roughly **3–5×** versus prose carrying the same
machine-readable signal, because prose repeats connective tokens ("when X then Y, but if
Z then...") that a table encodes positionally.

| Content shape | Use | Reason |
|---|---|---|
| Enumerable rules with fixed columns | Table | Positional encoding; no connective tokens; scannable |
| One-off rationale / a "why" | Prose (1–3 sentences) | Tables can't carry causal nuance economically |
| Branching decision logic | Decision table or tree | Each row is a complete rule; no narrative threading |
| A single hard constraint | Frontmatter field | Machine-enforced; zero body cost |

If you find yourself writing "first... then... however... unless..." you are almost
always describing a table in disguise. Convert it.

### Link-vs-inline decision rule

```
Inline the content IFF:
  (a) it is short (≤ ~3 lines), AND
  (b) the reader needs it on essentially every invocation, AND
  (c) it changes behavior at the point of reading.

Otherwise: link to the canonical source and carry only a one-line orientation pointer.
```

The dominant case is the **workspace-constitution link pattern**: shared protocol
(workspace-protocol.md, tmp-file-guardrail, the SDD gate flow, the task-manager
reservation flow) is authored **once** and **referenced** from every persona via a
single pointer line, never restated. Restating shared protocol inside N personas
multiplies its lifetime cost by N and — worse — creates N copies that drift out of sync
the moment the canonical version changes. A link costs one line and stays correct by
construction.

**Smell:** the same paragraph appears verbatim (or near-verbatim) in two or more files.
That is a missing link or a missing skill. See §5 skill-extraction trigger.

### Token estimation for audits

When you must quantify (efficiency audit), approximate:

```
tokens ≈ words × 1.33   (English)
tokens ≈ words × 1.20   (Portuguese)
```

`wc -w` on the file body, multiply, then multiply again by the invocation frequency from
the layer table above to get a lifetime-cost estimate per file. This is the input to the
tier-move and skill-extraction recommendations.

---

## 2. Instruction Hierarchy and Attention Ordering

### Why order is load-bearing

A persona is read top-to-bottom and the model's attention is not uniform across the
window: identity and early constraints anchor everything that follows; refusal templates
must be encountered **before** the agent has reasoned itself into accepting an
out-of-scope task. Reordering sections does not merely reorganize — it **moves the
agent's attention** and changes which constraints dominate when instructions conflict.
Treat section order as part of the contract, not as cosmetics.

### The canonical 10-section body order

Every agent persona body MUST present these sections in this exact order:

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

Rationale for the ordering: **who → what → how-it-refuses → what-it-knows →
how-it-works → what-it-must-not → who-it-talks-to → where-it-writes → what-it-emits →
how-it-operates.** Refusal (3) precedes capability (4) deliberately: an agent that knows
its limits before its powers is harder to talk out of scope. Do not reorder without a
documented reason; if you reorder, you are changing behavior.

### Audit protocol — detecting order drift in a persona

Run this when reviewing any persona change, or as a fleet sweep.

```
STEP 1 — Extract the section spine.
  grep -n '^## ' <persona>.md          # list H2 headings with line numbers

STEP 2 — Map each heading to a canonical slot (1..10).
  Some agents legitimately omit a slot (e.g. a non-implementer has no TDD
  workflow). Omission is allowed; REORDERING is not.

STEP 3 — Verify monotonic ordering.
  The mapped slot numbers must be strictly non-decreasing top-to-bottom.
  Any inversion (a later canonical slot appearing above an earlier one) is
  an ORDER-DRIFT finding.

STEP 4 — Classify each finding.
  - Inversion of 1/2/3 (identity/scope/refusal misplaced): severity HIGH —
    attention anchors compromised.
  - Inversion among 4..10: severity MEDIUM.
  - Extra non-canonical section: severity LOW — record and ask whether it
    belongs in a skill instead (token economy §1).

STEP 5 — Fix.
  Move sections to restore the canonical order. Do NOT rewrite content while
  reordering — keep the diff to pure moves so the review is auditable.
```

A persona that diverges from this spine is a maintenance hazard: reviewers can no longer
scan two personas side by side, and the consistency invariants (§3) become unverifiable.

---

## 3. Persona-Consistency Invariants

The fleet is auditable only because every persona is structurally identical. Five
invariants MUST hold across **all** personas. Each has a detection method and a fix
protocol. Inconsistencies are bugs — file them in a refactor report.

| # | Invariant | What must match |
|---|---|---|
| I1 | Frontmatter schema | Same keys, same order: `name`, `description`, `tier`, `model`, `activity_class`, `concurrency_relationship`, `gate_role`, `tools`, `skills`, `maxTurns`, `input_contract` (`requires_inputs` + `produces_outputs`), `paths.write_allowlist` |
| I2 | Body section order | The canonical 10-section spine of §2 |
| I3 | `[SCOPE ERROR]` block format | Same shape: `[SCOPE ERROR]` opener, one-line identity, explicit redirect per foreign domain to the owning agent |
| I4 | TDD / task-manager reservation flow | Implementer agents follow the identical `[ ]`→`[-]`→`[x]` reservation + commit flow, referenced (not restated) |
| I5 | Handoff JSON contract | All agents emit via the same `dadaia-handoff-emitter` skill against the same schema version |

### Detection method

```
I1 — Frontmatter schema
  For each persona, extract the frontmatter key list in order and diff against
  the reference key list. A missing/extra/reordered key is a finding.
    grep -n '^[a-z_]*:' <persona>.md   # top-level frontmatter keys (pre-body)

I2 — Body order
  Run the §2 audit protocol.

I3 — [SCOPE ERROR] format
  grep -A12 '\[SCOPE ERROR\]' <persona>.md
  Verify: opens with the marker; states identity in one line; redirects EACH
  foreign domain to the correct owning agent by name. A redirect to the wrong
  agent, or a missing redirect for a domain the agent could plausibly be
  handed, is a finding.

I4 — Reservation flow
  Confirm the persona REFERENCES the task-manager flow rather than restating it
  (restating is both an I4 risk and a token-economy violation). For implementer
  agents, confirm the [-] reservation + commit-before-edit step is present.

I5 — Handoff contract
  Confirm dadaia-handoff-emitter is in the skills list and the report section
  references emitting handoff JSON under .dadaia/handoff/<ctx>/ with the current
  schema_version.
```

### Fix protocol

1. **Never spot-fix one persona in isolation** for an invariant that spans the fleet. If
   the `[SCOPE ERROR]` format is wrong in one persona, check whether the *reference*
   format changed (then all personas need the update) or just that one drifted (then fix
   the one to match the reference).
2. **Schema/format changes propagate via release, not via ad-hoc edits.** A change to the
   canonical frontmatter schema or the refusal-block shape is a fleet-wide refactor task
   under an approved release — never a quiet edit to a single file.
3. **Keep the fix diff minimal and mechanical.** Structural fixes should not smuggle
   content changes; reviewers must be able to confirm "this only restored the invariant."
4. **Re-run detection across the whole fleet** after the fix to confirm no persona was
   left behind.

---

## 4. Model-Tier Selection Decision Protocol

A persona pinned to a tier heavier than its workload requires is a recurring tax on
every dispatch; a persona pinned too light produces work that must be redone. Tier is a
cost-and-quality decision, made from workload character and measured evidence — never
from "make it smarter."

### Step 1 — Characterize the workload

Score the agent's dominant task on these axes:

| Axis | Low → High |
|---|---|
| Reasoning depth | Mechanical transform → multi-step synthesis / recursive analysis |
| Context breadth | Single file → whole-fleet / cross-layer reasoning |
| Error cost | Easily reverted → ships to all consumers / hard to undo |
| Output novelty | Reformat existing → author new structure from a brief |
| Volume | Occasional → high-frequency / bulk |

The **dominant** task drives the tier — not the easiest or the rarest.

### Step 2 — Apply the decision table

Tier names are **derived from `core/model_registry.py`** (the single
source of truth for model identity, pricing, and tier — never hand-maintain a copy
that can drift):

| Registry tier | Workload character |
|---|---|
| `deep` | Heavy synthesis, recursive analysis, persona/skill authoring, fleet audit, security reasoning |
| `dispatch` | Orchestration, dispatch authority, review verdicts, standard implementation with broad context |
| `plugin` | Plugin-domain implementation (frontend/design/devops surfaces) |
| `fast` | High-volume mechanical reformatting, bulk renames, deterministic transforms |

Current per-runtime model ids and (for Codex) reasoning-effort come from
`core/model_registry.py` via the per-runtime tier view — never hand-copied. On Codex
the tiering axis is (model id × model_reasoning_effort); on Claude it is the model id.

When recommending a tier move, quote the registry entry (id + latest pricing row) so
the cost delta comes from live data, not a stale table. Move **up** a tier only when
depth/breadth/error-cost are all high. Move **down** only when the task is genuinely
mechanical and high-volume.

### Step 3 — Justify a tier BUMP (down → up)

A bump must be backed by **measured-cost evidence**, not intuition:

```
1. Capture concrete invocation traces where the current tier produced
   incorrect, shallow, or rework-triggering output.
2. Show the failure correlates with the workload axes (depth/breadth/error-cost),
   not with a fixable prompt defect — a bad prompt is cheaper to fix than a tier.
3. State the cost delta: bump price × invocation frequency. Bump only if the
   rework/quality cost of the lower tier exceeds the per-dispatch price delta.
4. Record the justification one-liner in the release task (e.g. "ai-engineer →
   deep tier: heavy synthesis + fleet-wide authoring; per-dispatch not per-session").
```

Tier bumps in personas require an **operator-approved release task** — never a silent
edit. (See §5: a self-edit that bumps your own tier is the highest-risk drift.)

### Step 4 — Justify a tier DOWNGRADE (up → down)

```
1. Sample recent outputs at the current tier; confirm none required the depth
   the tier provides (no recursive analysis, no novel structure authored).
2. Confirm error-cost is low or the work is reviewed downstream anyway.
3. Estimate the saving: price delta × invocation frequency.
4. Downgrade, then watch the next few dispatches for quality regression; revert
   if rework appears (rework cost can erase the saving).
```

Downgrades are the cheaper experiment (worst case: revert), but still go through the
release flow for personas so the change is observable.

---

## 5. Recursive Scope-Drift Detection

### The failure mode

The AI-entity surface is recursive: an agent can edit another agent's file, and
`ai-engineer` can edit `ai-engineer`. The signature failure is **recursive scope
drift**: agent A edits agent B's persona to "fix" a perceived bug → B's behavior shifts
→ agent C, which dispatches to B, breaks → the break surfaces far from the edit. Because
the edit and the failure are decoupled in time and location, drift is expensive to
diagnose after the fact. The defense is three detection rules applied **before** the edit
lands, plus a topology guard for the self-edit case.

### Detection rule 1 — write_allowlist agreement (frontmatter vs body)

Every persona declares its writable paths in **two** places: the frontmatter
`paths.write_allowlist` (an agent-instruction convention — NOT gate-enforced as of 0.1.7 rc-3) and the body "Write
permissions" table (human-readable). They must agree.

```
DETECT:
  - Extract the frontmatter allowlist globs.
  - Extract the body Write-permissions table rows.
  - Diff. Any path the body grants but the frontmatter omits is a FALSE-PROMISE
    drift (the agent believes it can write outside its declared scope). Any
    path the frontmatter grants but the body omits is a SILENT-PRIVILEGE drift
    (a capability with no documented rationale).
RESOLVE:
  - The frontmatter is authoritative by convention (the gate does NOT enforce write_allowlist). Fix BOTH so they
    match, and confirm the intersection is exactly what the SPEC authorizes —
    never wider. Widening an allowlist requires an operator-approved release
    task that justifies the widening (privilege-escalation control).
```

### Detection rule 2 — forbidden-actions table propagates via release, not spot-edit

Every persona names its forbidden-actions / `[SCOPE ERROR]` redirects verbatim against a
shared reference. Operator-driven changes to that reference are fleet-wide and **must
propagate through a release**, touching every persona in one reviewed change set.

```
DETECT:
  - Compare each persona's [SCOPE ERROR] redirect set against the reference.
  - A single persona whose redirect set differs from all others is spot-edit
    drift — someone changed one file instead of the fleet.
RESOLVE:
  - If the reference changed: open a fleet-wide release task and update all
    personas together. If one persona drifted: restore it to the reference.
  - Never "improve" one persona's refusal block in isolation; that guarantees
    divergence and breaks side-by-side auditability.
```

### Detection rule 3 — self-edit risk + topology-guard protocol

`ai-engineer`'s own persona lives in the same `public/agents/` tree it edits, so
`ai-engineer` can recursively edit itself. This is **allowed but the highest-risk
operation on the surface** — a self-edit can widen its own allowlist, bump its own tier,
or weaken its own refusals, and the agent that would normally review the change is the
same agent that made it.

```
SELF-EDIT PROTOCOL (whenever ai-engineer edits ai-engineer.md, or any change
that alters the dispatch graph / allowlists / tool grants across personas):

  1. Confirm an operator-approved release task authorizes the specific change
     (tier bump, allowlist edit, tool grant). No self-granted privileges.
  2. Make the edit minimal and single-purpose.
  3. Re-verify the topology invariants by hand: persona count matches the
     canonical roster; every persona has the required frontmatter keys
     (name/description/tier/model/tools/paths.write_allowlist, non-empty); and
     project-manager + project-auditor each still name every leaf agent. This
     catches a self-edit that broke another agent's expectations.
  4. Pair with security-reviewer for any change that adds a powerful tool
     (Agent/dispatch, broad WebSearch, network) or widens an allowlist; hooks
     (executable surface) always require security-reviewer.
  5. Re-validate frontmatter via the workspace reader test so the parse still
     succeeds.

RE-VERIFY THE TOPOLOGY INVARIANTS WHENEVER:
  - any persona's paths.write_allowlist changes,
  - any persona's tools list changes (especially adding Agent/dispatch),
  - any persona is added or removed,
  - ai-engineer self-edits,
  - a forbidden-actions / [SCOPE ERROR] redirect set changes.
```

### Skill-extraction trigger (the anti-drift refactor)

The structural cure for repeated drift is to stop duplicating. When **two or more
personas restate the same protocol** (the TDD reservation flow, a shared review gate, a
common refusal preamble), extract it into a skill under
`public/skills/<name>/SKILL.md` and replace every inline copy with a one-line reference.
A skill is loaded once and referenced; inline content is loaded N times and drifts N
ways. Extraction simultaneously cuts lifetime token cost (§1) and removes the surface
where rules 1 and 2 drift — it is the highest-leverage move when an efficiency audit
finds repeated context across personas.

---

## Applying this skill

- **Authoring** a new persona/skill/rule: walk §1 (place each line in the cheapest
  correct layer) → §2 (lay out the canonical spine) → §3 (match the fleet invariants) →
  §4 (pick the tier from workload + evidence) → §5 (confirm no allowlist/refusal drift).
- **Reviewing** someone else's AI-entity change: walk in reverse — §5 first (did this
  edit drift scope, allowlists, or refusals?), then §3 (do invariants still hold?), §2
  (is the spine intact?), §1 (did it add expensive duplication?), §4 (is the tier still
  justified?).
- **Auditing** the fleet (efficiency report): use §1 estimation to rank files by lifetime
  cost, §2/§3 detection protocols to find structural drift, §4 to recommend tier moves,
  and the §5 skill-extraction trigger to recommend deduplication.

---

## Authoring guardrails (apply every time)

- This skill is restricted to `ai-engineer` (`DADAIA.md` §2 (skill scope)). General
  agents use `harness-primitives`. Phase mapping: ai-engineer / harness literacy.
- All authoring targets are `dadaia_workspace/public/...` source. Never hand-edit
  `.claude/`, `.codex/`, `.agents/` projections; propagate via
  `dadaia public stage && dadaia public install`.
- No consumer-specific names, hostnames, IPs, private repo slugs, secrets, or
  operator-private data in any authored asset.
