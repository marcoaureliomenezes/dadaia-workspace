---
slug: harness-pi
title: Harness — PI (pi-coding-agent)
category: product
tldr: 'Dual-layer harness: post-trust Ring-1 entry + DADAIA_ENTRY_HARNESS pi pin + PI_HEADLESS worker; auths on the operator''s Codex subscription.'
summary: Capability and scaffold truth for the PI harness at both agentic layers — the
  post-trust Ring-1 extension, the PI_HEADLESS worker transport and auth, the model
  set including the OpenRouter allowlist, telemetry posture, and what a PI-only
  workspace installation contains.
tags:
- harness
- pi
- layer-1
- layer-2
- projection
token_estimate: 720
last_updated: '2026-07-07'
release_origin: v0.1.64
---

## Purpose

PI (`@earendil-works/pi-coding-agent`) is a **dual-layer** harness. Layer 1: the
operator's `pi` terminal agent — it reads `AGENTS.md` natively up-tree and, once the
operator grants trust to `.pi/`, gains a genuine **pre-disk Ring-1 gate**: the
projected `.pi/extensions/dadaia-sdd-gate.ts` `tool_call` handler blocks write/edit
before disk by delegating to the same Python `pre_gate` the other harnesses use.
Layer 2: the `PI_HEADLESS` worker — `pi --mode json` driven one-shot per step, Ring-2
bounded. In a PI entry session, dadaia-workflows default the Layer-2 harness to `pi`
unless the operator overrides — mechanically, via the post-trust entry-signal pin below.

## Usage flow

1. Operator installs `pi` (external optional CLI — never a pinned dependency; build
   stays offline-first without it) and grants `.pi/` trust on first launch.
2. Layer-1 governance: `AGENTS.md` up-tree + post-trust extension gate + git
   chokepoints. **Trust boundary:** `.pi/**` is post-trust executable TypeScript — a
   deliberate privilege grant, lib-originated and manifest-tracked, never hand-edited.
3. **Entry-signal seam (post-trust):** at factory load the Ring-1 extension
   (`dadaia-sdd-gate.ts`) sets `process.env.DADAIA_ENTRY_HARNESS = "pi"` **only when
   unset**, so PI tool subprocesses (bash → `dadaia lifecycle …`) auto-default
   `--harness` to `pi`. **Security posture: the pin is session-wide and
   credit-affecting** — every child process of the PI session inherits it, and an
   auto-defaulted `pi` worker spends real credits. The guardrails are structural:
   **set-only-when-unset** (an operator pin always wins); the **loud
   `[harness] auto-default:` echo** guards every real-worker auto-default (never
   silent); and the signal is **never derived from telemetry** (no session-file/mtime
   heuristics — the pin is the extension's explicit, post-trust act). Pre-trust
   (extension not loaded) there is no signal and the default honestly stays `fake`.
4. As a Layer-2 worker: the engine invokes `pi --mode json --model <id>` with the
   fragment+persona step prompt; auth comes from `~/.pi/agent/auth.json` under the
   operator's **Codex subscription** (provider openai-codex) — PI itself requires no
   Anthropic key. Qualification: the PI worker env allowlist **deliberately passes
   `ANTHROPIC_API_KEY` through when present** (`infrastructure/pi_runtime.py`, via the
   shared `headless_adapter_base` env filter) so provider-flexible setups work; it is
   pass-through, not a requirement. Result extraction is the shared
   strict-schema-first path (tolerates bare unfenced JSON).
5. Telemetry: `features/telemetry/reader/pi.py` ingests session METADATA only from
   `~/.pi/agent/sessions/` (invariant T1 — no message bodies; cost unknown ⇒ never
   fabricated).

## Typical trigger

Layer 1: operator preference for PI. Layer 2: every dadaia-workflow step whose
governed harness resolves to `pi` — model set `(gpt-5.5, high)`, `(gpt-5.5, low)`,
`(gpt-5.3-codex, medium)`, plus the curated OpenRouter `kimi-2.7:high` (via the
Layer-2 allowlist + the `pi-openrouter-kimi-high` profile; never a `claude-*` id).

## Differentiator

The only harness with BOTH a real Layer-1 pre-disk gate (post-trust) and a Layer-2
worker role, and the widest Layer-2 model set (operator-extensible via the local
profile store, validated, no API keys stored). Live-verified build: pi 0.79.3.

## Runtime state touched

Scaffold projected by `dadaia public install --target pi`: `.pi/SYSTEM.md`,
`.pi/settings.json`, `.pi/prompts/`, `.pi/extensions/dadaia-sdd-gate.ts`.
Operator-local model profiles live in `.dadaia/states/workflow_model_profiles.local.json`
(validated, never projected to `public/`). A PI-only workspace = `--target pi`
(+ shared `--target agents`). This isolation is now **enforced mechanically at init** —
`dadaia init --harness pi` scaffolds only the `.pi/` post-trust projection and persists
the profile ([[workspace-init]]) — not merely documented.

## Dependencies

- [[tech-stack]] — roster, PI auth truth, model catalog single source.
- [[lifecycle-foundation]] — the engine driving the PI_HEADLESS worker.
- [[sdd-gate-v3]] — the pre_gate the Ring-1 extension delegates to.
- [[agent-monitoring]] — the metadata-only PI telemetry posture.
- [[public-asset-distribution]] — the `.pi/` projection pipeline.
