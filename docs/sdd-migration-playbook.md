# SDD Migration Playbook — Legacy to Release-Based

> Operator-facing. Terse. Run these commands; you already know what SDD is.
> Canonical worked example: `sdd-release-lifecycle-v1/SPEC.md` Phase 6 — the
> dadaia-workspace self-migration executed on 2026-05-16.

---

## Preconditions

- `dadaia` CLI installed (`dadaia doctor` → healthy)
- Target repo has a writable git working tree (clean or stashed)
- `SDD_LEGACY_FEATURES=1` set for the session (allows gate to pass while specs tree is partial)
- You know the repo slug (example: `redacted-slug-barbe`, `redacted-slug-explorer`)

```bash
export SDD_LEGACY_FEATURES=1
```

---

## Step 1 — Scaffold

Run `dadaia specs init` to create the canonical tree under the target repo. The command
is idempotent — existing files are skipped.

```bash
dadaia specs init \
  --specs-dir repos/<slug>/specs \
  --name <slug>
```

Expected output: ≥11 `[created]` lines covering memory HTML stubs, ACTIVE.md
(`release: none / phase: none`), backlog stubs, and `.gitkeep` sentinels.

After this step the repo has a valid SDD skeleton and `dadaia specs doctor` exits 0.

---

## Step 2 — Triage existing `specs/features/`

List every directory under `specs/features/`. Classify each into one of three buckets:

**(a) Implemented** — feature shipped and in production.

```bash
# For each implemented feature <id>:
mkdir -p specs/_archive/releases/<id>
# Create specs/_archive/releases/<id>/CLOSURE.md with retroactive evidence
# (git log SHA, test output, or deploy timestamp as evidence triple)
```

Seven features were migrated this way in the dadaia-workspace migration; see
`specs/_archive/releases/` for concrete CLOSURE.md examples.

**(b) Draft / never built** — SPEC written, nothing shipped.

```bash
# Add one bullet to specs/backlog/candidates.md:
# - <name> — <one-liner> (owner: <agent>, contexto: specs/_archive/legacy-features/<name>/SPEC.md)
mkdir -p specs/_archive/legacy-features/<name>
git mv specs/features/<name>/SPEC.md specs/_archive/legacy-features/<name>/SPEC.md
git rm -r specs/features/<name>  # remove emptied dir
```

Fifteen features were moved to `specs/_archive/legacy-features/` in the worked example.

**(c) In-flight** — active work underway.

```bash
mkdir -p specs/releases/<release-id>
git mv specs/features/<name>/SPEC.md specs/releases/<release-id>/SPEC.md
# Carry over PLAN.md and TASKS.md if they exist
```

After triage `specs/features/` should be empty or removed.

---

## Step 3 — Migrate memory markdown

Move legacy `.md` memory files to a timestamped archive, then render fresh HTML from
templates using the current code state as input.

```bash
TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%SZ)   # e.g. 2026-05-16T180000Z
mkdir -p specs/_archive/legacy-memory/$TIMESTAMP
git mv specs/memory/*.md specs/_archive/legacy-memory/$TIMESTAMP/
```

Then activate CLOSURE phase temporarily to unlock memory writes:

```bash
# Edit specs/releases/ACTIVE.md: set phase: CLOSURE
# Render memory HTML (product-engineer fills templates with real content):
#   specs/memory/architecture.html
#   specs/memory/tech-stack.html
#   specs/memory/product/index.html
#   specs/memory/product/<slug>.html  (one per feature area)
# Revert ACTIVE.md to phase: IMPLEMENTATION after writing
```

This exact sequence was executed with timestamp `2026-05-16T180000Z` in the canonical
worked example. The legacy-root content (`specs/PLAN.md`, `specs/TASKS.md`,
`security/`, `foundation/`) was also archived:

```bash
mkdir -p specs/_archive/legacy-root
git mv specs/PLAN.md specs/TASKS.md specs/_archive/legacy-root/   # if they exist
```

---

## Step 4 — Activate first release

If in-flight work exists, set ACTIVE.md to that release. If no active work, leave as-is
(`release: none / phase: none`).

```bash
# Edit specs/releases/ACTIVE.md:
release: <release-id>     # or: none
phase: TASKS              # or: none
```

Create the three required artifacts for any new release:

```bash
# Delegate to product-engineer:
specs/releases/<release-id>/SPEC.md    # Status: Aprovado
specs/releases/<release-id>/PLAN.md    # Status: Aprovado
specs/releases/<release-id>/TASKS.md   # Status: Aprovado
```

After this step the gate enforces production-path discipline: memory writes require
`phase: CLOSURE`; `specs/_archive/` is always blocked.

---

## Step 5 — Verify

```bash
dadaia specs doctor --specs-dir repos/<slug>/specs
# Expected: 0 errors. Warnings on legacy content are acceptable during transition.
```

Spot-check memory HTML in the browser (Mermaid diagrams must render; no broken `<img>`
links). Use the browser's network tab to confirm CDN assets load.

---

## Step 6 — Activate context

```bash
dadaia context activate <slug>
```

After activation the gate reads `primary_context.json` and enforces the release-based
write policy for this repo. Agents resolve specs via `specs/releases/ACTIVE.md` instead
of legacy `specs/features/`. Unset `SDD_LEGACY_FEATURES` once all target repos are
migrated.
