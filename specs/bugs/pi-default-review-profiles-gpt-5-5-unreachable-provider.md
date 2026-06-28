---
name: pi-default-review-profiles-gpt-5-5-unreachable-provider
status: Closed
severity: HIGH
reported: 2026-06-28
surface: workflow model profiles and PiHeadlessAdapter provider-qualified model routing
session_id: sess_8cdf6cce
---

# Default PI review profiles use gpt-5.5, which routes to an unauthenticated provider (`azure-openai-responses`) → every PI review step is unrunnable

**Symptom:** Any lifecycle workflow step that runs on a **gpt-5.5** PI profile fails
immediately with a PI provider auth error:

```
No API key found for azure-openai-responses.

Use /login to log into a provider via OAuth or API key.
```

The library's default PI model profiles
(`dadaia lifecycle workflow profiles list`) include:

```
pi-reasoning-high: harness=pi model=gpt-5.5:high   — review/gate steps
pi-reasoning-low:  harness=pi model=gpt-5.5:low
pi-implementation-standard: harness=pi model=gpt-5.3-codex:medium  — create/worker steps
```

The `release_definition` PI auto-profile maps **every review step**
(`spec_arch_review`, `spec_qa_review`, `plan_review`, `tasks_implementability_review`) to
`pi-reasoning-high` = **gpt-5.5:high**. On this host, gpt-5.5 routes to provider
`azure-openai-responses`, for which there is **no key**, so all PI review steps are
unrunnable.

**Repro:**

```bash
# Any PI step forced onto gpt-5.5:
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace --release-id v0.1.36 --run-id v0136-spec55 \
  --backlog centralize-release-semver-canon --intent "..." \
  --harness pi --step-model spec_create=gpt-5.5:high --json
# -> BLOCKED ... "reason":"No API key found for azure-openai-responses."
```

**Provider evidence:** `pi --list-models` shows `openai-codex/gpt-5.3-codex-spark`,
`openai-codex/gpt-5.4`, `openai-codex/gpt-5.4-mini`, and `openai-codex/gpt-5.5`.
The stale catalog id `gpt-5.3-codex` is not available. The adapter was also passing bare
ids to `pi --model`, allowing PI provider resolution to choose an unreachable provider.

**Expected:** The library's default PI profiles should use model ids PI exposes and the
adapter should qualify them to the reachable `openai-codex` provider instead of relying on
bare-id provider resolution.

**Context / possible regression:** memory records that the v0.1.31/v0.1.32 live proofs ran
a real `pi` worker on **gpt-5.5** successfully on 2026-06-27 (one day before this report),
so either pi's model→provider routing for gpt-5.5 changed (now `azure-openai-responses`)
or the auth set changed. Either way the library's default PI review profile is currently
unreachable for this operator and the workflow surfaces it only mid-run.

**Severity rationale:** HIGH — blocks all PI review/gate steps, i.e. the review half of
every dadaia-workflow on the PI harness.

**Notes:** Registered via direct-Markdown fallback (the `bug report` workflow's default
`--harness fake` writes a stub — see `bug-report-fake-bug-write-emits-stub-and-discards-fields`).
Operator-local paths redacted to `~`. No secrets included (provider key contents not read;
only the provider *names* present in auth.json were enumerated).

## Resolution — v0.1.36 alpha-1

The PI catalog and `pi-implementation-standard` profile now use the live PI Codex model id
`gpt-5.3-codex-spark`. `PiHeadlessAdapter` qualifies every bare GPT id as
`openai-codex/<id>` before passing `--model` and forwards the selected effort through
`--thinking`.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py::test_pi_command_qualifies_model_and_threads_thinking \
  repos/dadaia-workspace/tests/unit/core/test_harness_models.py
```

Residual risk: live PI auth/provider behavior remains operator-local. If a provider-qualified
`openai-codex/...` model fails in a live run, file a new provider/auth bug with the exact
PI stderr and model pattern.
