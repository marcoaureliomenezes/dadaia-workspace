---
title: "Codex runtime fidelity: compact personas, loaded law and live certification"
status: candidate
opened: 2026-08-14
scope: codex-only
harness: codex
description: >-
  Repair the Codex harness as one fidelity boundary: shrink the nine 8-22 KB projected
  persona TOMLs to role identity and role-specific decisions; load canonical DADAIA.md
  once and prove parent plus delegated-agent visibility; replace the false claim that
  headless codex exec has no hooks with version-aware live evidence; make certification
  exercise the installed Codex rather than infer runtime behavior from static files;
  strengthen entities derivation from structural bijection to behavioral fidelity for
  personas, rules and universal projections; and correct stale Codex documentation,
  including the false 12-persona count. Also make native sandbox, output, memory
  injection and delegated-subagent contracts internally executable rather than
  contradictory. Scope is 100% Codex and must not change any other harness's generated
  bytes or behavior.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py#_render_codex_agent_toml
    change: >-
      Render compact Codex-only custom-agent instructions: keep only role identity,
      role-specific decisions, authority and write/refusal boundaries; remove shared
      DADAIA.md law and cross-role protocol repetitions; connect every Codex persona to
      one effective common-law loading path; and make each persona's native sandbox,
      dispatch authority and HTML/handoff output contract mutually executable.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/codex_doctor.py#check_codex_rule_corpus_reachable
    change: >-
      Stop treating a literal AGENTS.md @DADAIA.md line plus target-file existence as
      proof that the model received the law. Distinguish static reference integrity from
      effective prompt visibility and require executed-path evidence before reporting a
      loaded/reachable Codex law.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/codex_doctor.py#codex_trust_boundary_info
    change: >-
      Replace the stale interactive-only/headless-no-hooks claim with version-qualified
      observations from the installed Codex; live 0.147.0 evidence already proves both
      UserPrompt injection and blocking PreToolUse under codex exec.
  - subject:
      kind: code
      ref: dadaia_workspace/features/certification/service.py#certify
    change: >-
      Add version-aware live Codex certification probes for common-law visibility,
      UserPrompt injection, blocking PreToolUse, evidence-role outputs, QA write scope
      and authorized/unauthorized nested delegation. Static projection/wrapper tests may
      validate shape but must never attest runtime behavior.
  - subject:
      kind: code
      ref: dadaia_workspace/hooks/ctx_inject.py#_resolve_context
    change: >-
      Remove any first-alive Codex memory fallback and enforce the workspace law's exact
      context order: environment, own session, cwd repository, otherwise generic
      preflight. Distinguish deterministic hook injection from discoverable/on-demand
      memory-ctx skill invocation.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/codex_doctor.py#check_entities_derivation
    change: >-
      Extend ENT-DERIVE-1 beyond persona-name bijection and behavior-key presence to
      behavioral fidelity of Codex personas, deterministic rules and universal
      projections, including exact registry-to-generated hook/wrapper path mappings,
      with mutation fixtures that prove each drift class blocks.
  - subject:
      kind: catalog
      ref: harness-codex
    change: >-
      Make the common workspace law load exactly once in the effective Codex context for
      both the parent session and delegated custom agents; reconcile the Codex skill,
      memory and academy with live hook behavior, actual nine-persona registry, native
      sandbox/output constraints and proven PM/auditor delegation topology; leave all
      non-Codex harness behavior and projected bytes unchanged.
---

# Codex runtime fidelity: compact personas, loaded law and live certification

## Description

**Scope/harness:** `codex` only.

The target is the complete Codex truth boundary: generated `.codex/agents/*.toml`, actual
workspace-law visibility, hook/runtime claims, Codex live certification, entities-derived
projection checks, and Codex-specific memory/academy/skill text. This item does not
redesign or shorten Claude Code/Kimi Code personas, does not change their loading model,
and does not create a second source of workspace law. Canonical law remains `DADAIA.md`.

## Motivation

The 2026-08-14 baseline has nine generated Codex agent TOMLs totaling 124,557 bytes:
the smallest is 8,208 bytes and the largest is 22,836 bytes. Shared lifecycle, gate,
handoff and workspace-law prose is repeated across roles, so every delegation pays for
redundant context and each repeated statement can contradict or drift from `DADAIA.md`.
Codex needs compact role overlays plus one demonstrably loaded common-law layer.

The same gap appears in runtime truth. The projected root `AGENTS.md` contains the literal
text `@DADAIA.md`; Codex does not implement that as a native include, while
`check_codex_rule_corpus_reachable()` currently proves only that the named target file
exists and then overclaims model reachability. Separately, live Codex 0.147.0 evidence
proved UserPrompt injection and blocking PreToolUse under headless `codex exec`, but
`codex_trust_boundary_info()`, Codex memory and academy still say headless runs have no
hooks. The `ai-harness-codex` skill is internally contradictory: its earlier hook section
allows headless firing while its later enforcement section says interactive-only and
retains 0.139.0 conclusions. Static projection tests cannot settle these runtime facts.

Finally, `entities-derivation` currently checks the persona-name bijection and presence of
behavior implementation keys, not behavioral equivalence; its implementation explicitly
omits real validation of `rules` and `universal`. Codex memory also reports 12 TOML
personas although the abstract registry and current projection contain nine. These are
one defect family: static presence is being reported as runtime/behavioral fidelity.

There is already concrete behavioral drift that the green check misses: the Codex
implementations for the root/venv gate in `public/entities/registry.json` name the stale
wrapper `.dadaia/hooks/pre_gate.sh`, while the generated Codex projection actually uses
`.dadaia/hooks/codex-pre-gate`. `entities-derivation` passes despite that mismatch.
Likewise, the SDD lifecycle and sole-dispatch authority are model/document protocols;
they are not native or mechanically enforced Codex primitives. Codex doctor, memory,
academy and skills must preserve that classification rather than promote protocol prose
into a runtime-enforcement claim.

Five evidence roles (`code-reviewer`, `project-auditor`, `qa-engineer`,
`security-reviewer`, `software-architect`) currently project with native
`sandbox_mode = "read-only"` while their persona prose requires report/handoff writes;
QA additionally owns test/E2E writes. A role cannot satisfy an output contract its
sandbox forbids. The Codex contract must either grant the exact required write scope or
make the role return a structured payload for an authorized parent relay, and prove the
chosen path live. The same persona surface still contains QA and architect examples that
write Markdown `.md` reports despite the workspace's handoff-first/HTML-only report law.

The Codex `memory-ctx` fallback also overclaims universal execution: discovering an
on-demand skill is not invoking it. Deterministic memory injection belongs to the hook
path and must be proven there. Any fallback that selects the "first alive" context is
unsafe and contradicts the canonical `env -> own session -> cwd repo` resolution order;
an unbound session must receive generic preflight, never another project's memory.

Finally, Codex dispatch prose is behind demonstrated native behavior.
`project-orchestration` and the projected project-manager persona claim only the
top-level dispatcher may spawn and that every leaf must use manual handoffs, while the
authorized `project-auditor` has successfully spawned `ai-engineer`. The Codex projection
needs one accurate, role-specific delegation topology: authorized Tier-1 coordinators can
use native subagents within their declared fan-out; evidence leaves cannot silently gain
that authority.

## Acceptance criteria

- For the same nine core agents, `wc -c .codex/agents/*.toml` totals at most 49,823
  bytes (at least 60% below the 124,557-byte baseline), and no individual TOML exceeds
  8,192 bytes.
- Every generated Codex persona retains its `name`, `description`, resolved `model`,
  `model_reasoning_effort`, role identity, decision/authority boundaries, allowed writes
  and explicit refusals; contract tests cover all nine core roles.
- Across generated `developer_instructions`, there are zero paragraphs of 160 or more
  normalized characters duplicated between two personas and zero such paragraphs copied
  from `DADAIA.md`; the only common-law material allowed in a persona is one short load or
  reference instruction.
- The effective Codex prompt contains exactly one common-law layer sourced from canonical
  `DADAIA.md`, not one copy per persona and not a Codex-specific fork of the law.
- An executed-path Codex probe uses a unique sentinel present only in the canonical common
  law and proves that both (a) a parent Codex session and (b) a delegated custom agent can
  report that sentinel. The probe also records that the law was supplied once in each
  effective context.
- The literal `@DADAIA.md` text is not accepted as include evidence. A static doctor check
  may report only reference/path integrity; an `[ok]` claim that the law is loaded or
  reachable is emitted only when fresh executed-path evidence for the installed Codex
  version proves model visibility.
- Certification records the installed `codex --version` and runs in a disposable trusted
  workspace. It separately proves: UserPrompt injection reaches `codex exec`; a blocking
  PreToolUse hook prevents a marker write/tool action; parent and delegated custom-agent
  prompts each see the single common-law sentinel. Each check records observed version,
  command result and evidence artifact.
- Live certification dispatches `code-reviewer`, `project-auditor`, `qa-engineer`,
  `security-reviewer` and `software-architect` and proves each can complete its declared
  output contract under its generated native `sandbox_mode`. For read-only roles, direct
  report/handoff writes are absent and an authorized parent relay persists and validates
  the structured result; for directly-writing roles, the sandbox permits only the exact
  declared output paths. QA's test/E2E authoring path is separately proven writable when
  its task contract requires it. Permission denial cannot be reported as success.
- Runtime evidence is reusable only when its observed Codex version exactly matches the
  installed version. A missing binary, missing live evidence, changed version, skipped
  probe or static-only result cannot produce a green runtime-fidelity attestation; the
  result is explicit `unsupported`/`not verified` or blocking, according to certification
  mode, never a false `[ok]`.
- `codex_trust_boundary_info()`, `specs/memory/**`, the Codex academy and
  `ai-harness-codex` contain one non-contradictory, version-qualified hook contract. For
  the certified 0.147.0 path they state that headless `codex exec` executes UserPrompt
  and blocking PreToolUse hooks. Historical 0.139.0 observations are either removed or
  clearly labeled historical and non-authoritative; a repository scan finds zero
  unqualified claims that Codex headless never fires hooks.
- ENT-DERIVE-1 validates behavioral derivation for the complete Codex projection, not
  only structure: all nine persona identities and boundaries, deterministic rule
  semantics, and universal-law projection/loading declarations match their abstract
  registry/source. Mutation tests independently alter (a) a persona refusal/authority
  boundary, (b) a Codex rule behavior, and (c) a universal law projection; each mutation
  must produce a blocking derivation finding.
- Every Codex hook/gate implementation path declared by `public/entities/registry.json`
  exactly matches the generated projection plan and installed wrapper path. At this
  baseline the root/venv gate must resolve to `.dadaia/hooks/codex-pre-gate`, with zero
  live registry references to stale `.dadaia/hooks/pre_gate.sh`. A mutation that restores
  the stale path must make ENT-DERIVE-1 block; file/key presence alone cannot pass.
- Codex doctor, memory, academy and skills classify capabilities truthfully: SDD stage
  ordering, task-marker discipline and project-manager sole-dispatch authority are
  model/document protocols upheld by agents, not native/mechanical Codex enforcement.
  Native hooks, Starlark command rules and git chokepoints are identified separately as
  the mechanisms that can enforce their actual scopes. Contract scans find zero claims
  that Codex itself mechanically enforces lifecycle sequencing or sole-dispatch purity.
- Codex project-manager, project-auditor and `project-orchestration` projections agree on
  one explicit native delegation matrix. The project-manager may perform its declared
  core orchestration fan-out; the project-auditor may natively spawn its declared
  evidence agents, including `ai-engineer`; other evidence leaves cannot spawn unless
  explicitly authorized. A live nested-delegation probe proves auditor -> ai-engineer,
  and a negative probe proves an unauthorized leaf cannot fan out. No Codex instruction
  says authorized auditor delegation is impossible or requires a fictional manual relay.
- Codex persona output examples obey the workspace artifact law: JSON handoff is the
  default; an optional human-facing report is `.html`; no generated Codex persona
  prescribes or examples a Markdown `.md` report. Static scans cover all nine TOMLs, and
  live evidence-role outputs pass handoff/report validation.
- Codex memory documentation distinguishes skill discovery from invocation. It never
  claims `memory-ctx` runs universally merely because the skill is discoverable;
  deterministic injection is attributed only to the registered and live-proven hook,
  while `memory-ctx` remains on-demand unless explicitly invoked.
- Codex context-memory resolution is exactly `DADAIA_CONTEXT` environment -> the
  current session's own binding -> repository containing cwd -> no context/generic
  preflight. There is no "first alive" fallback. A two-context isolation test and a live
  unbound Codex probe prove that neither hook nor skill injects memory from an unrelated
  alive context.
- The number of Codex personas is derived from the canonical registry/projection and is
  nine at this baseline; no Codex memory, academy, skill or doctor message hard-codes or
  reports 12 TOML personas. A count-consistency test fails on registry/projection/docs
  disagreement.
- For identical staged inputs, before/after SHA-256 manifests for `.claude/agents/**`,
  `.kimi-code/**` and their harness configuration outputs are byte-identical; Codex is the
  only changed projection/runtime behavior.
- `dadaia public doctor` is green, including Codex projection checks and
  `[ok] public-privacy`, and the full test suite is green.

## Baseline note (2026-08-15 — v0.10.0 pick)

v0.10.0 (`dd-lifecycle-skills-family`, approved 2026-08-15) was explicitly ruled
**not** to absorb this entry (its SPEC §4.2 + §6-D: different surface, different
owner) — it stays `candidate`. However that release edits three personas that render
into the Codex TOMLs, so this entry's **124,557-byte / nine-TOML byte baseline is
invalidated at the v0.10.0 ship**. Per the release's SPEC §7 disposition, the PM
re-measures and rewrites the baseline figures here after v0.10.0 ships; until then
the byte numbers in this entry are historical (2026-08-14 adoption measurement), not
current.
