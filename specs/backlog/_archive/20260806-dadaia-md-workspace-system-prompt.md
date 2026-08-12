---
name: dadaia-md-workspace-system-prompt
status: CONSUMED — v0.5.0
created: 2026-08-06
origin: operator demand 2026-08-06 (rules-efficiency analysis session; declared ARCHITECTURAL)
owner: project-manager (curates)
disposition:
  terminal_status: CONSUMED
  closed_by: v0.5.0
  closed_at: '2026-08-12'
  evidence: specs/releases/v0.5.0/CLOSURE.md#dispositions
  verified:
    - One DADAIA.md ships; public/rules/*.md no longer projects always-on files.
    - The projected law is byte-identical across the four projections and mode 0444.
    - Projected law files are a PROTECTED gate class; an agent write is blocked with
      the edit-the-lib-and-reproject remedy.
    - Library development under dadaia_workspace/public/ is unaffected; v0.5.0 T-50-07
      amended §3 at source and re-projected via stage → install → public doctor.
    - dadaia public doctor reports [ok] public-privacy with zero drift.
  accepted_deviation:
    criterion: Measured always-on token count ≤ 3k.
    measured: ~3.5k
    decision: accepted, operator-approved at v0.3.0 — recorded, not silently missed.
intents:
  - subject: { kind: doc, ref: "memory/architecture.md#Agent Surface" }
    change: "NEW single always-on law file — the workspace system prompt. Consolidates every always-on rule the library ships (today: 9 public/rules/*.md + the law body of the root AGENTS.md) into one optimized, auditable, affirmative document."
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager" }
    change: "project DADAIA.md to every Layer-1 harness (.claude/rules/DADAIA.md, .codex/ and .kimi-code/ equivalents); retire the per-rule projection of public/rules/*.md"
  - subject: { kind: code, ref: "dadaia_workspace/hooks/pre_gate.py#evaluate_payload" }
    change: "new deterministic policy: projected law files (DADAIA.md + library-originated AGENTS.md) are HUMAN-ONLY in an instantiated workspace — agent file-writes are blocked with the edit-the-lib-and-reproject remedy"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager" }
    change: "write projected law files read-only (0444) so the restriction also holds outside the harness hook envelope"
---

# Backlog — `DADAIA.md`: the workspace system prompt

## Demand (operator, declared ARCHITECTURAL)

> "DADAIA-WORKSPACE PROVÊ 1 SYSTEM-PROMPT DO WORKSPACE, O JÁ MENCIONADO `DADAIA.md`.
> E `AGENTS.md` distribuídos por diretórios core do workspace. Essas são as únicas
> regras que vêm de fábrica do workspace. E os usuários, eles que criem suas regras."

The rule architecture the library ships is **exactly two things**:

1. **`DADAIA.md`** — one file, all always-on law of dadaia-workspace itself. It is the
   workspace's system prompt: the analogy is literal and is the reason for the name.
   Projected to every Layer-1 harness (`.claude/rules/`, `.codex/`, `.kimi-code/`).
2. **`AGENTS.md`** — scoped files in the workspace's core directories (`.dadaia/` and
   its subtrees: `reports/`, `handoff/`, `tmp/`, `states/`; the SDD `specs/` tree
   created inside the workspace; and the other core dirs). Each governs its subtree.

Nothing else ships as always-on law. Consumers who want additional always-on rules
create them wherever they like — the library does not occupy that space.

## Law — factory law files are human-only in an instantiated workspace

In an **instantiated** workspace, `DADAIA.md` and the library-originated `AGENTS.md`
files may be changed **only by a human operator, by hand**. An agent that wants to
change the law edits the **source in the library package** and re-scaffolds. A direct
agent write to `.claude/rules/DADAIA.md` (or any harness equivalent) is forbidden.

This is the general lib-originated non-edit rule raised to law for the law files
themselves, and the operator asked for it to be **deterministic where possible** —
not discipline. Two independent layers, because each covers the other's hole:

- **Gate policy** (covers file tools in every harness): the projected law paths get a
  dedicated path class that blocks agent writes with an actionable remedy — edit
  `dadaia_workspace/public/…`, then `dadaia public stage && dadaia public install`.
- **Filesystem mode** (covers the `Bash` write path, which the gate does not parse):
  projection writes the law files `0444`. A human operator can still `chmod` and edit;
  an agent's blind `>` redirect fails.

Note for definition: this workspace (the self-hosting source repo) is where the law is
authored and tested, so the restriction must not block library development — it binds
the **projected instance**, never `dadaia_workspace/public/`.

## Why (evidence from the 2026-08-06 analysis)

The always-on surface measured **1,000 lines / 7,500 words / ~13.5k tokens** across 10
files, entering every agent's context in every session.

| Pathology | Evidence |
|---|---|
| Duplication | `ADDITIVE` in 5 files; `NO-LOCKS`, `pre-push`, `presence`, `product-engineer` in 4 each. The root whitelist and the forbidden-repo-dirs table each exist twice, in two formats. The SDD gate is described twice (~40 lines each) in different words — and the two copies already disagree on whether memory is gated by phase or by persona. |
| Contradiction | `release-governance` heads a section `## Bug & backlog → release` and then decrees bugs are never release material — it even states the bug-picking language "survives solely for" a residual case. `backlog-ownership` needs an attached `Decision (OQ-3)` block to explain what it meant; needing that block is proof it was not clear. `AGENTS.md` asserts `public doctor` "must include `[ok] public-privacy`" while the command exits 0 on `[error]`. |
| Archaeology | 19 in-body version references (`v0.1.76`, `0.1.7 rc-3`, `ADR-1..4`, `OQ-3`). `backlog-ownership` spends a paragraph on why a lock was *removed*; `plugin-scope` closes on a *retired* deviation class. The corpus states that changelog belongs in `CLOSURE.md`, then carries changelog. Teaching an agent that rules get reverted invites treating rules as reversible. |
| Negative voice | 74 prohibition tokens (`never` ×56, `forbidden` ×5, `must not` ×5, `do not` ×8). The dominant voice is prohibition where it should be instruction. |
| Missing law | Zero lines describe the mandatory operating flow — the single most important contract in the workspace is the one thing not written down. |

## Authoring philosophy (binding on DADAIA.md)

Affirmative, direct statements. Teach the correct behavior; reserve prohibition for the
genuinely irreversible (credentials, `specs/_archive/`, `.dadaia/sessions/`). One fact,
one place — cross-reference by section name, never by copy. No version archaeology in
the body of the law. Optimized context: the target is **~2.5k tokens**, an ~81%
reduction, while *adding* the missing flow law.

## Content (sections, ordered by frequency of use, not by concept)

1. **The flow** — the mandatory default. Arm A (feature): demand → backlog-definition →
   release-definition → implementation + reviews/gates → audit. Arm B (bug): register →
   RED → root-cause fix → GREEN → `resolved` → commit. Deviation requires an explicit,
   confirmed operator request; the agent declares which arm it is operating in before
   acting.
2. **Who does what** — demand → agent dispatch table.
3. **What is deterministic** — the merged pre-gate (3 policies, first-block-wins), the
   5 path classes, NO-LOCKS presence, the git chokepoints.
4. **Where to write** — root whitelist, `.dadaia/tmp/` landing zone, repo cleanliness.
5. **Specs and memory** — task lifecycle, marker discipline, memory ownership.
6. **Quality** — TDD, pre-push security verdict + CI preflight.
7. **The library surface** — lib-originated assets, projection loop, and this law.
8. **Credentials** — the one wholly prohibitive section.
9. **Index** — scoped `AGENTS.md` files, skills, core CLI.

## Acceptance

- One `DADAIA.md` ships; `public/rules/*.md` no longer projects always-on files.
- The projected law is byte-identical across `.claude/`, `.codex/`, `.kimi-code/`.
- Every law present in the 10 retired files is either carried into `DADAIA.md` or
  explicitly recorded as dropped with a reason — no silent loss.
- Measured always-on token count ≤ 3k.
- An agent write to a projected law file is blocked deterministically, with the
  edit-the-lib remedy in the message; the projected files are mode `0444`.
- Library development in `dadaia_workspace/public/` is unaffected.
- `dadaia public doctor` exits 0; full suite green.

## Dependencies / interactions

- Interacts with the open bug `public-doctor-exits-zero-despite-error` — the doctor
  must fail loudly for the new law-file drift check to be worth anything.
- The `harness-skill-scope`, `plugin-scope` and `dev-guardrail` rules are absorbed;
  their scoped enforcement points (skills, plugin packs, manifest) are unchanged.
