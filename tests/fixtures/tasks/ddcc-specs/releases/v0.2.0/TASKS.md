# TASKS: Release v0.2.0 — Hermes Dev-Factory Core

**Status:** Aprovado
**Release ID:** v0.2.0
**Owner:** product-engineer

> Traceability: every task lists its epic ID (HOP-1.x), SPEC FR IDs, and Done-line (DL-*) /
> acceptance (AC-*) references. Coverage: SPEC.md §Scope + §Done-line.
> HOP-0.1 was executed at v0.1.1 closure (SPEC DEC-1) and is NOT a task here.
> Parallelism: tasks in the same phase with disjoint write sets may run in parallel; at most
> one `[-]` per owner otherwise. Reserve `[ ]` → `[-]` before writing, `[-]` → `[x]` after
> review approval (`dadaia-task-manager` discipline).
> Workflow law: implementation and review work MUST be driven through `dadaia lifecycle`
> workflows, with explicit `--context dd-chain-capture --release-id v0.2.0` on every
> workflow command. Manual implementation/reviewer prompts are not an acceptable substitute
> for the workflow engine. Any failure, wrong result, blocked workflow step, invalid
> workflow handoff, context/bind inconsistency, or other `dadaia` tooling issue encountered
> while running the workflow MUST be registered immediately with `dadaia bugs append`
> before continuing or working around it.
> [PLUGIN] markers: NONE in this release — CI/GHCR is descoped (SPEC DEC-3). The freshness
> gate and image-path gate are plain scripts run locally / in the build lane, not GHA YAML.

---

## Phase 1 — Substrate upgrade + freshness gate (WS-1 / HOP-1.1)

**T-1.1 — Re-pin dadaia-workspace + Codex CLI substrate** (HOP-1.1; FR-1.1)
- Owner: software-engineer (+ ai-engineer for the breaking-change delta review)
- Write set: `docker/hermes-capture/Dockerfile` (`DADAIA_WORKSPACE_VERSION`, `CODEX_VERSION`
  ARGs only)
- Precondition: none
- Done: `DADAIA_WORKSPACE_VERSION` bumped from `0.1.6` to the value bound in PLAN's
  "Pinned substrate versions (bound at approval)" table (`0.2.1`); `CODEX_VERSION` per the
  same table (`0.139.0` retained; bump only via a recorded decision); `docker build` exits 0; any breaking
  CLI/hook-surface change across the jump is recorded (in the task handoff and, if it changes
  the plan, surfaced to product-engineer) BEFORE dependent code edits.

```
[x] T-1.1
```

**T-1.2 — Install `pi` CLI in the image** (HOP-1.1; FR-1.2)
- Owner: software-engineer
- Write set: `docker/hermes-capture/Dockerfile` (pi install layer, pinned)
- Precondition: T-1.1
- Done: the `pi` CLI (`pi-coding-agent`) is installed pinned and on `PATH`;
  `docker run --rm <img> pi --version` resolves; install uses `--no-cache-dir` (pip) or the
  equivalent to keep the layer slim.

```
[x] T-1.2
```

**T-1.3 — Project `.pi/` into the in-container workspace** (HOP-1.1; FR-1.3)
- Owner: ai-engineer (+ software-engineer for entrypoint wiring)
- Write set: `docker/hermes-capture/entrypoint.sh` (projection step),
  `docker/hermes-capture/workspace/` (seed if the projection is baked)
- Precondition: T-1.2
- Done: `dadaia public install` runs with the **pi target** so `.pi/**` is projected into the
  in-container workspace at `/opt/data/capture-workspace/.pi/` (a workspace SUBDIR, never a
  repo root — RL-5); idempotent (copy-if-absent, like the existing workspace seed);
  `.pi/` is present and non-empty after boot; no `.dadaia/` is created inside any repo.

```
[x] T-1.3
```

**T-1.4 — Extend image-path gate for the new substrate** (HOP-1.1; FR-1.4)
- Owner: software-engineer (path extraction) + ai-engineer (hook-import review)
- Write set: `scripts/check-image-paths.sh`
- Precondition: T-1.1, T-1.2, T-1.3
- Done: the existing build-time gate additionally asserts, in the built image:
  `pip show dadaia-workspace` = the pinned 0.2.1+; `codex` present at the re-pinned version;
  `pi --version` resolves on PATH; `.pi/` projected in the workspace (not at a repo root); the
  dadaia hook modules referenced by `workspace/.codex/hooks.json`
  (`dadaia_workspace.hooks.pre_gate`, `ctx_inject`, `sdd_post_gate`) import cleanly
  (`docker run --rm <img> ...`); exit-code-gated; verified by one deliberate failing pin.

```
[x] T-1.4
```

**T-1.5 — Substrate-freshness gate** (HOP-1.1; FR-1.5; DL-2 / AC-2)
- Owner: software-engineer (+ ai-engineer for the policy definition)
- Write set: `scripts/check-substrate-freshness.sh` (new),
  `docker/hermes-capture/substrate-policy.env` (new — approved-version policy)
- Precondition: T-1.4
- Done: a script reports the pinned Hermes-fleet / Codex / dadaia-workspace / `pi` versions
  **from the built image** and **warns or fails** when any is behind the approved policy in
  `substrate-policy.env`; a deliberate behind-policy pin makes it warn/fail (verified once);
  the gate is a plain script (run locally / in the build lane) — NO GitHub Actions YAML is
  added (SPEC DEC-3).

```
[x] T-1.5
```

---

## Phase 2 — MinIO dev S3 for the Hermes lane (WS-2 / HOP-1.2)

**T-2.1 — Bind the Hermes lane to MinIO in dev** (HOP-1.2; FR-2.1)
- Owner: software-engineer
- Write set: `services/dev/dd-capture-peripherals.yml` (MinIO **standing dev profile** +
  attach MinIO to the `hermes-internal` network per SPEC DEC-7; standing dev-only creds),
  `services/dev/dd-capture-apps.yml` (Hermes service env `AWS_ENDPOINT_URL` + network
  attach — the Hermes service lives here), `.env.example` + dev env template
- Precondition: Phase 1 complete (image boots)
- Done: the Hermes lane env carries **`AWS_ENDPOINT_URL`** (the single canonical endpoint
  env var) pointing at the dev MinIO endpoint; MinIO (standing dev profile, attached to
  `hermes-internal` per SPEC DEC-7) is reachable from the Hermes container on the dev
  network; **no real S3 credentials** are present in the Hermes environment (FR-2.3) —
  standing dev-only MinIO creds via the secret-resolver pattern; `docker compose config`
  resolves with no missing-var warnings.

```
[x] T-2.1
```

**T-2.2 — Point `s3_uploader.py` at MinIO when the endpoint is set** (HOP-1.2; FR-2.1)
- Owner: software-engineer
- Write set: `docker/hermes-capture/workspace/scripts/s3_uploader.py`
- Precondition: T-2.1
- Done: `s3_uploader.py` honors **`AWS_ENDPOINT_URL`** (MinIO) when set — accepting the
  legacy `S3_ENDPOINT_URL` only as a deprecated fallback, or removing it (the uploader
  reads `S3_ENDPOINT_URL` today; converge on `AWS_ENDPOINT_URL`, which boto3 honors
  natively); keeping the real-S3 code path intact but unused in dev; a test NDJSON object ships to MinIO
  under `raw/<source>/dt=<YYYY-MM-DD>/`; endpoint-selection unit-tested with a fake S3 client
  (network-free); idempotent + decoy-aware behavior preserved from v0.1.1.

```
[x] T-2.2
```

**T-2.3 — Dev bucket/prefix bootstrap mirrors prod** (HOP-1.2; FR-2.2)
- Owner: software-engineer
- Write set: `services/dev/dd-capture-peripherals.yml` (minio-init bucket/prefix), dev env
  (new `dd-chain-capture-dev` bucket name — NOT `E2E_BUCKET`)
- Precondition: T-2.1
- Done: the **new `dd-chain-capture-dev`** dev MinIO bucket (SPEC DEC-7 — the `E2E_BUCKET`
  `dd-chain-capture-e2e` is NOT overloaded) holds a `raw/<source>/dt=<YYYY-MM-DD>/` prefix
  tree that mirrors prod byte-layout; the bucket is created idempotently at bring-up (extend
  the existing minio-init pattern); the standing dev loop uses standing dev-only MinIO creds
  via the secret-resolver pattern (SPEC DEC-7), never real AWS creds.

```
[x] T-2.3
```

**T-2.4 — services/ audit: peripherals + Hermes only** (HOP-1.2; FR-2.4 / AC-4)
- Owner: software-engineer (review: security-reviewer)
- Write set: none (audit); record findings in the task handoff
- Precondition: T-2.1..T-2.3
- Done: `services/dev/` contains ONLY peripheral containers (MinIO + inherited peripherals) +
  Hermes — no production capture app lives in `services/`; the MinIO binding is the only
  service-level addition; audit result captured as CLOSURE evidence.

```
[x] T-2.4
```

---

## Phase 3 — Telegram command control plane (WS-3 / HOP-1.3) — parallel with Phase 2

**T-3.1 — Inbound `getUpdates` listener (no inbound port, no replay)** (HOP-1.3; FR-3.1, FR-3.6)
- Owner: software-engineer
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py` (new),
  `docker/hermes-capture/supervisord.conf` (listener program),
  `docker/hermes-capture/workspace/scripts/secret_resolver.py` (reuse — no change expected)
- Precondition: Phase 1 complete
- Done: an authenticated inbound listener uses outbound long-poll `getUpdates` ONLY — **no
  inbound port** is opened on the Hermes container (RL-7 / AC-9); the last-acknowledged
  `update_id` offset is persisted in `/opt/data` (durable volume, no secrets) and advanced
  only after handling, so a listener restart **does not replay** an acknowledged update;
  supervisord runs it as a program that stays RUNNING; network-free unit tests inject a fake
  `getUpdates` source + fake sender (mirror `crash_alert.py`'s injectable `Sender`).

```
[-] T-3.1
```

**T-3.2 — Deterministic command handlers** (HOP-1.3; FR-3.2)
- Owner: software-engineer
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py` (+ a handler
  module under `workspace/scripts/` if the handler set warrants separation)
- Precondition: T-3.1
- Done: deterministic handlers for `/new_app`, `/update_app`, `/status`, `/queue`,
  `/approve`, `/reject`, `/kill`, `/help`; each returns a correct, deterministic response;
  `/help` lists the command surface; `/status` and `/queue` report Hermes/lifecycle state;
  `/kill` stops the targeted work; unit-tested per handler (network-free).

```
[ ] T-3.2
```

**T-3.3 — Operator-only mutation gate** (HOP-1.3; FR-3.3)
- Owner: software-engineer (review: security-reviewer)
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py`
- Precondition: T-3.1
- Done: only the configured `TELEGRAM_OPERATOR_CHAT_ID` may issue **mutating** commands
  (`/new_app`, `/update_app`, `/approve`, `/reject`, `/kill`); a non-operator chat's mutating
  command is rejected with a deterministic refusal and never mutates state; read-only
  commands follow policy; the gate is unit-tested with operator + non-operator chat ids.

```
[ ] T-3.3
```

**T-3.4 — Demand→SDD refinement loop** (HOP-1.3; FR-3.4)
- Owner: ai-engineer (loop design) + software-engineer (wiring)
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py`,
  `docker/hermes-capture/defaults/playbook.md` (demand-intake flow),
  `docker/hermes-capture/workspace/AGENTS.md` (refinement-before-implementation law)
- Precondition: T-3.2
- Done: `/new_app` / `/update_app` drive a conversational refinement loop — the operator can
  define/review/improve a demand into **backlog → SPEC → PLAN → TASKS** before any
  implementation starts; implementation never begins on an unrefined demand (the playbook and
  workspace AGENTS.md state this law); the loop is documented and testable at the handler
  boundary (network-free).

```
[ ] T-3.4
```

**T-3.5 — NDJSON logging (no secrets) + alert-path coexistence** (HOP-1.3; FR-3.5, FR-3.7 / AC-6)
- Owner: software-engineer
- Write set: `docker/hermes-capture/workspace/scripts/telegram_listener.py`,
  `docker/hermes-capture/supervisord.conf`
- Precondition: T-3.1
- Done: commands and state transitions are logged as NDJSON (one JSON object per line, same
  discipline as `gateway_loop.py`) with NO secrets (bot token, operator chat id, OpenRouter
  key never logged); the inbound listener coexists with `crash_alert.py` — both resolve the
  bot token via `secret_resolver` and the FATAL-event alert path still fires ≤ 60s (verified
  by a simulated FATAL event); a redaction test asserts a secret-shaped string is not logged.

```
[ ] T-3.5
```

---

## Phase 4 — Layer-1→Layer-2 execution path (WS-4 / HOP-1.4)

**T-4.1 — OpenRouter creds via pi trusted config (bug mitigation)** (HOP-1.4; FR-4.2; SPEC DEC-5)
- Owner: ai-engineer (+ security-reviewer for the secret-handling review)
- Write set: `docker/hermes-capture/entrypoint.sh` (write creds into pi trusted config from
  the resolver), pi trusted-config template under
  `docker/hermes-capture/workspace/.pi/` (seeded), `docker/hermes-capture/defaults/config.env`
  (OpenRouter param name only — no value)
- Precondition: T-1.3 (`.pi/` projected)
- Done: the OpenRouter API key is resolved via `secret_resolver.get_secret` (SSM `*_PARAM` /
  `*_FILE` / env fallback) and written into pi's **in-container trusted config** at boot —
  mitigating HIGH bug `pi-openrouter-env-allowlist-strips-creds` (env allowlist strips
  `OPENROUTER_API_KEY`/`OPENAI_BASE_URL`, so env passthrough cannot deliver creds); the key
  is NEVER baked into the image, NEVER written to `/opt/data/.env`, NEVER logged; the upstream
  bug is referenced in the task; if fixed upstream, env passthrough may replace this later
  (not this release).

```
[ ] T-4.1
```

**T-4.2 — Egress allowlist gains `openrouter.ai`** (HOP-1.4; FR-4.4 / AC-8)
- Owner: software-engineer (review: security-reviewer)
- Write set: `docker/hermes-capture/proxy/tinyproxy.filter` (+ `tinyproxy.conf` if needed),
  `deploy/vps-hardening.md` (egress table),
  `docker/hermes-capture/workspace/rules/scrape-target-catalog.md` (egress note — keep-in-sync)
- Precondition: none (inherited egress proxy from v0.1.1)
- Done: the egress allowlist adds `openrouter.ai` and `api.openrouter.ai` so the in-container
  pi worker reaches the OpenRouter API through the proxy; `FilterDefaultDeny` / default-deny
  is preserved; acceptance: `curl` to a non-listed domain from inside Hermes still fails, and
  `curl` to `openrouter.ai` succeeds; the KEEP-IN-SYNC targets (hardening doc, catalog note)
  are updated consistently; additionally, `tinyproxy.filter`'s `KEEP IN SYNC` header is
  corrected to cite `deploy/vps-hardening.md` (it currently cites a nonexistent
  `services/security/vps-hardening.md`).

```
[ ] T-4.2
```

**T-4.3 — Drive `dadaia lifecycle` with `--harness pi` + explicit pi/OpenRouter model** (HOP-1.4; FR-4.1, FR-4.3 / RL-1)
- Owner: ai-engineer (lifecycle wiring) + software-engineer
- Write set: Hermes driver (the `/new_app` handler path in `telegram_listener.py` and/or a
  dedicated `workspace/scripts/lifecycle_driver.py`),
  `docker/hermes-capture/defaults/playbook.md` (Layer-2 invocation law)
- Precondition: T-1.2, T-1.3, T-4.1, T-4.2
- Done: Hermes invokes `dadaia lifecycle <verb> --harness pi --step-model
  <label>=pi-openrouter-<...>` (e.g. `pi-openrouter-kimi-high`) — the `--harness pi` flag and
  an explicit `--step-model` are ALWAYS passed; the `fake` default is NEVER used for a Layer-2
  step; the playbook documents that **no Layer-2 work runs on Codex or Claude** (RL-1);
  invocation-construction is unit-tested (assert `--harness pi` + explicit step-model always
  present, never `fake`).

```
[ ] T-4.3
```

**T-4.4 — End-to-end pi/OpenRouter Layer-2 proof** (HOP-1.4; FR-4.3 / DL-4 / AC-7)
- Owner: software-engineer (orchestration) + qa-engineer (acceptance)
- Write set: `scripts/pi-layer2-proof.sh` (new); evidence captured for CLOSURE
- Precondition: T-4.1, T-4.2, T-4.3
- Done: **one** `dadaia lifecycle` step runs a **real pi worker against an OpenRouter model
  end-to-end inside the container** (`--harness pi --step-model <label>=pi-openrouter-<...>`,
  creds via pi trusted config) — the worker produces real Layer-2 output, NOT a `fake` stub
  (asserted); egress to `openrouter.ai` succeeds, a non-listed domain fails; no Layer-2
  process is ever invoked with `--harness codex|fake` for a real step; qa-engineer emits an
  APPROVED handoff with the run evidence.

```
[ ] T-4.4
```

---

## Phase 5 — Integration proof (Done-line stitch)

**T-5.1 — Full-loop acceptance + red-line audit** (DL-1..DL-7 / AC-1..AC-10)
- Owner: qa-engineer (acceptance) + software-engineer (orchestration) + security-reviewer
  (red-line audit)
- Write set: `scripts/hermes-devfactory-loop.sh` (new — the stitched proof); evidence
  captured for CLOSURE
- Precondition: all of Phase 1–4 `[x]`
- Done: the stitched full loop passes in one run against MinIO + peripherals (no real S3):
  (1) the rebuilt image boots and `check-image-paths.sh` + freshness gate are green (DL-1,
  DL-2); (2) the operator sends a Telegram command from the operator chat and gets a correct
  handled response, a non-operator mutation is rejected, restart does not replay (DL-3);
  (3) one `dadaia lifecycle` step runs a real pi/OpenRouter Layer-2 worker end-to-end (DL-4);
  (4) a test NDJSON object lands in MinIO under `raw/<source>/dt=<YYYY-MM-DD>/` (DL-5);
  (5) **zero** real-S3 writes — no AWS creds present, endpoint is MinIO (DL-6);
  (6) security-reviewer audits and confirms every epic §12 red line (RL-1..RL-7) is honored,
  in particular no Layer-2 work ran on Codex or Claude (DL-7); qa-engineer emits an APPROVED
  acceptance handoff.

```
[ ] T-5.1
```

---

## Task summary

| Phase | Tasks | Count |
|-------|-------|-------|
| 1 Substrate upgrade + freshness gate | T-1.1..T-1.5 | 5 |
| 2 MinIO dev S3 | T-2.1..T-2.4 | 4 |
| 3 Telegram command plane | T-3.1..T-3.5 | 5 |
| 4 Layer-1→Layer-2 execution path | T-4.1..T-4.4 | 4 |
| 5 Integration proof | T-5.1 | 1 |
| **Total** | | **19** |

**No [PLUGIN REQUIRED] tasks** — CI/GHCR is descoped (SPEC DEC-3). The freshness gate and
image-path gate are plain scripts run locally / in the build lane.

**Operator-provisioned at runtime (not tasks, but preconditions for the live proof):**
`TELEGRAM_CAPTURE_BOT_TOKEN`, `TELEGRAM_OPERATOR_CHAT_ID`, the OpenRouter API key (via the
secret resolver), and `codex login` for the Layer-1 coordinator. None is baked into the image.
