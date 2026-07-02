---
title: Hoist shared headless-adapter logic into one base (de-duplicate pi/codex/claude_sdk)
status: delivered
opened: 2026-06-25
surface: dadaia_workspace/infrastructure/{pi_runtime,codex_runtime,claude_sdk_runtime}.py
owner: project-manager
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/headless_adapter_base.py#_SECRET_NAME_PARTS" }
    change: "single home for the secret-scrubbing invariant (_redact/_SECRET_NAME_PARTS); the three real adapters import it (v0.1.30 Wave A)"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/headless_adapter_base.py#ChangedPathsMixin" }
    change: "single home for the _GitDiffPort + _with_changed_paths Ring-2 git-diff override; pi/codex import it, claude_sdk reuses the seam (v0.1.30 Wave A)"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/headless_adapter_base.py#SubprocessAdapterMixin" }
    change: "single home for the _env/allowlist filter, Runner seam, and prompt envelope; pi/codex import it (v0.1.30 Wave A)"
---

## Finding

The Layer-2 runtime adapters physically copy-paste several **security-relevant** invariants
across the real headless adapters. Current adapter set:
`pi_runtime`, `codex_runtime`, `claude_sdk_runtime` (3 real) + `fake_runtime`.

> **Premise correction (2026-06-26):** the `opencode_runtime` this finding originally named
> was **deleted entirely in v0.1.24** — it is no longer one of the duplicating adapters. The
> dedup target is the three real adapters above.

Duplicated invariants:

- `_redact` + `_SECRET_NAME_PARTS` (secret scrubbing of surfaced output) — in
  `codex_runtime.py`, `pi_runtime.py`, and `claude_sdk_runtime.py` (added there for CWE-209
  parity).
- `_GitDiffPort` + `_with_changed_paths` (the Ring-2 git-diff override that stops a lying
  worker hiding an out-of-scope write) — in `pi_runtime.py` and `codex_runtime.py`.
- `_env` / `_DEFAULT_ENV_ALLOWLIST` (env allowlist filtering), the `Runner` seam, and the
  prompt envelope — duplicated across the CLI-headless adapters.

The logic is consistent and fully tested today, but it is duplicated; because these are
security invariants (redaction, env allowlist, the changed_paths override), a divergence
between copies is a latent security bug, not just style debt — and a future adapter copies
it again.

## Proposed direction

Hoist a shared `HeadlessAdapterBase` (or a small shared-helpers module) carrying
`_redact`/`_SECRET_NAME_PARTS`, `_GitDiffPort`/`_with_changed_paths`, `_env`/allowlist, and
the `Runner` seam. Leave per-adapter only the genuinely CLI-specific `_command` builder and
result/stream extraction. The Claude SDK adapter (not CLI-headless) shares redaction + the
git seam but not the subprocess bits, so factor the base so the SDK adapter reuses the
common parts without inheriting subprocess machinery.

## Acceptance (draft)

- One shared home for `_redact`/`_SECRET_NAME_PARTS`, `_GitDiffPort`/`_with_changed_paths`,
  `_env`/allowlist; zero verbatim copies across the three real adapters.
- Per-adapter modules keep only `_command` + result/stream extraction.
- A test that fails if redaction or the changed_paths override diverges between adapters.

## Provenance

Surfaced by the v0.1.23 review ladder (software-architect MEDIUM, code-reviewer LOW DRY, qa
LOW uncovered branches); deliberately deferred out of v0.1.23 as a completion release. PM
to curate.
