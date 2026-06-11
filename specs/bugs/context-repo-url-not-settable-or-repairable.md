---
name: context-repo-url-not-settable-or-repairable
status: Open
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: dadaia context create/alive/dead (repo_url lifecycle)
---

**Symptom:** A spec context can exist with `repo_url: ""` and there is no CLI path to set or repair it. `dadaia context create <name> --repo <slug>` exposes no `--url` option (the service-layer `create(name, repo_slug, repo_url)` accepts it, the CLI never passes it), and neither `context alive` nor `context dead` back-fills `repo_url` from the on-disk repo's actual `origin` remote. Consequence: `context alive <name>` on another machine (e.g. after `dadaia export`/`import` to a VPS) attempts `git clone "" repos/<slug>` and fails — the context is permanently un-portable.

**Repro:**
1. `dadaia context create foo --repo foo` (no URL option exists) → record has `repo_url: ""`.
2. Clone/populate `repos/foo/` by any means; work normally (alive state, remote exists on disk).
3. `dadaia export` → import on a second machine → `dadaia context alive foo` → clone of empty URL fails.

**Expected:** Either (a) `context create` accepts `--url`, and/or (b) `context alive`/`dead` sync `repo_url` from `git remote get-url origin` when the record's URL is empty (the repo on disk knows its own remote), and/or (c) a `context update --url` repair verb exists. Doctor should flag an ALIVE context whose record has an empty `repo_url` (it is silent today).

**Notes:** Hit during a real VPS migration: a long-lived context had an empty URL while its on-disk repo had a valid origin remote the whole time. Workaround used: updated the record through `JsonContextStore.update()` (the library's own store API, preserving locking/shape) — not a raw file edit, but it required importing library internals, which an operator cannot be expected to do. Related older gap: "context create has no --url" was observed as early as v0.1.5-era operations and still holds in the v0.1.10 line.
