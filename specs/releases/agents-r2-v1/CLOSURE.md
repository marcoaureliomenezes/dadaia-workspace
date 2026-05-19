# Closure: Release — agents-r2-v1

> **Status:** In progress
> **Release ID:** agents-r2-v1
> **Owner:** product-engineer
> **Phase:** TASKS (finalised in P14)
> **SPEC:** specs/releases/agents-r2-v1/SPEC.md (Aprovado)
> **PLAN:** specs/releases/agents-r2-v1/PLAN.md (Aprovado)
> **TASKS:** specs/releases/agents-r2-v1/TASKS.md (Aprovado)

## Operator manual migration (FR10)

This release ships the lib-side rewrite of `data/AGENTS.md` (FR7) and the
dual-projection installer (FR7 / Option C). FR10 declares the **operator-owned**
side of the migration: moving Hostinger / Hermes / OpenClaw / Traefik domain
content out of the workspace-root `CLAUDE.md` (where it lives today, mixed with
lib content) into a new operator-authored, non-lib-managed pair
`services/CLAUDE.md` + `services/AGENTS.md`.

The 5 numbered command groups below are **literal** — copy-paste ready. The
operator runs them in order, in the workspace root
(`$WORKSPACE_ROOT=/home/marco/workspace/dadaia`). The PR description for this
release (AGT-r2-44) links the anchor `#operator-manual-migration` back to this
section so the migration cannot be missed.

The operator MUST complete groups 1–3 **before** running group 4 (`dadaia public
install`). If the install runs before `services/CLAUDE.md` exists, the install
will overwrite the workspace-root `CLAUDE.md` from the new (clean) lib source
and the operator's deployment content will be lost — group 1 captures the SHA
beforehand precisely to support recovery via `git checkout` if this race occurs.

### Group 1 — Capture pre-r2 workspace-root `CLAUDE.md` SHA

Record the SHA-256 of the current workspace-root `CLAUDE.md` (the file that
mixes lib + deployment content today). This SHA is the recovery anchor: if
anything goes wrong in groups 2–5, the operator can `git checkout` the file at
that SHA and start over.

```bash
sha256sum "$WORKSPACE_ROOT/CLAUDE.md" > /tmp/pre-r2-claude-sha.txt
cat /tmp/pre-r2-claude-sha.txt
```

### Group 2 — Author `services/CLAUDE.md`

Create the new operator-authored file `services/CLAUDE.md` with the deployment
content extracted from the pre-r2 workspace-root `CLAUDE.md`. The sections that
MUST appear in `services/CLAUDE.md` (per FR10.5 forbidden-strings inverse
assertion): Hermes Agent (image, gateway invocation, `HERMES_WRITE_SAFE_ROOT`),
OpenClaw (image, config path, `dmPolicy`, `allowFrom`, `groupAllowFrom`),
Traefik (proxy + bridge IP for `trustedProxies`), Hostinger VPS network
(public IP, admin SSH IP, hostname `srv1608865.hstgr.cloud`).

```bash
# operator: write the file with deployment-specific content; example below is a placeholder
$EDITOR "$WORKSPACE_ROOT/services/CLAUDE.md"
```

### Group 3 — Mirror to `services/AGENTS.md` and verify byte-identical

The operator-authored pair must also be byte-identical (mirroring the
workspace-root pair invariant established by FR7). Use `cp` then verify with
`sha256sum` — both lines must print the same hex digest.

```bash
cp "$WORKSPACE_ROOT/services/CLAUDE.md" "$WORKSPACE_ROOT/services/AGENTS.md"
sha256sum "$WORKSPACE_ROOT/services/CLAUDE.md" "$WORKSPACE_ROOT/services/AGENTS.md"
```

### Group 4 — Stage + install + doctor

With groups 1–3 complete, run the full lib propagation cycle. The installer
will rewrite workspace-root `CLAUDE.md` + `AGENTS.md` from the new (clean,
domain-free) `data/AGENTS.md` source, and `services/CLAUDE.md` /
`services/AGENTS.md` MUST be untouched (FR7 nested-pair non-interference
invariant; covered by `tests/integration/test_public_install_e2e.py`).

```bash
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public stage
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public install --target all
/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public doctor
```

### Group 5 — Post-verify

Three checks confirm the migration succeeded.

**(a)** Workspace-root `AGENTS.md` and `CLAUDE.md` are byte-identical (one
SHA-256 across both):

```bash
sha256sum "$WORKSPACE_ROOT/AGENTS.md" "$WORKSPACE_ROOT/CLAUDE.md"
```

**(b)** Forbidden-strings grep on the workspace-root `CLAUDE.md` MUST exit 1
(grep found nothing). If exit is 0, deployment content leaked into the lib
source — STOP and audit `dadaia_workspace/public/data/AGENTS.md`.

```bash
grep -iE 'Hostinger|Hermes|OpenClaw|Traefik|srv1608865|hermes-jobs|openclaw-shopping|mistralai|187\.77\.42\.229|45\.180\.188\.119' "$WORKSPACE_ROOT/CLAUDE.md"
echo "exit=$?"   # must print exit=1
```

**(c)** Same grep on `services/CLAUDE.md` is EXPECTED to find matches (the
keywords ARE the migrated content). Exit 0 = OK; exit 1 also acceptable if the
operator chose different terminology. Either outcome confirms the pair is the
intended home for deployment data.

```bash
grep -iE 'Hostinger|Hermes|OpenClaw|Traefik' "$WORKSPACE_ROOT/services/CLAUDE.md"
echo "exit=$?"   # may print exit=0 if operator put those keywords; exit=1 also OK
```

After all three checks pass, the operator pastes the `sha256sum` output and the
`grep` exit codes into `## Validations` below (finalised in P14 / AGT-r2-48).

---

## Summary

_To be finalised in P14 (AGT-r2-48)._

## Tasks completed

_To be finalised in P14 (AGT-r2-48)._

## Validations

_To be finalised in P14 (AGT-r2-48)._

## Drifts

_To be finalised in P14 (AGT-r2-48)._

## Memory updates

_To be finalised in P14 (AGT-r2-48)._

## Backlog returns

_To be finalised in P14 (AGT-r2-48) + AGT-r2-51._

## Archive decision

_To be finalised in P14 (AGT-r2-53)._
