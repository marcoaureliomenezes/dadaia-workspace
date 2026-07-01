release: none
phase: none
---

# Active release: none

**v0.1.44** — *Layer-2 persona subsystem + fragment/persona optimization + pi model
openness* — is **CLOSED and ARCHIVED** at `specs/_archive/releases/v0.1.44/` (CLOSURE.md).
It introduced the **persona** entity (the Layer-2 codex/pi equivalent of a Claude
sub-agent) injected into every dadaia-workflow step prompt alongside the fragment as an
operative directive; a harness-universal persona library (`public/personas/<role>.md`, the
8 non-PM core roles) + `PersonaLoader`; reassigned the 7 `role: project-manager` fragments
to real personas (PM stays the Layer-1 orchestrator); a resolved-role anti-regression
guardrail (`persona_doctor`) wired into the doctor; and opened pi's Layer-2 model set from
GPT-only to registry-validated (`LAYER2_EXTRA_MODEL_IDS` incl. OpenRouter `kimi-2.7`;
no-`claude-*` retained; operator-overlay registration). Shipped to `main` via PR #78
(`7264f6c4`), all CI green (35 pass); qa alpha-1 + security APPROVED; constitution §8
amended (supersedes archived ADR-B).

No release is currently active.

**Fast-follow — v0.1.45 (panel redesign):** big expandable per-workflow **diagram** cards,
the Agentic tab reworked to surface Claude sub-agents **and** the new Layer-2 personas via
the role column, a per-workflow model picker (incl. the newly-allowed OpenRouter ids), and
an overall restyle. Depends on the persona entity shipped in v0.1.44.
