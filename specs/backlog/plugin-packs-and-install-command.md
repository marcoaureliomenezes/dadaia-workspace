---
name: plugin-packs-and-install-command
status: candidate
intents:
  - subject: { kind: cli, ref: "public install" }
    change: "add a real `dadaia plugin install|list|remove` command group alongside the existing public install/stage flow (stage + project pack assets, flip stub -> full persona, idempotent)"
  - subject: { kind: cli, ref: "public doctor" }
    change: "make `dadaia public doctor` aware of installed plugin packs (frontend-design, devops)"
---

# PLUGIN-PACKS-INSTALL — Plugin packs distribution + a real `dadaia plugin install` (MEDIUM)

**Status:** OPEN — candidate. Nothing here authorizes work; needs operator pick +
mandatory `dadaia-grill-me` before product-engineer authors a release SPEC.
**Reported:** 2026-06-11, as a v0.1.11 CLOSURE backlog return (ADR-4 honest-relabel;
PM-curation pre-approved by the release coordinator).
**Source bug:** `specs/bugs/plugin-install-command-missing.md` (Closed — v0.1.11
honest-relabel; this item is the REAL feature that bug exposed).

## Problem

The product advertises three plugin agents (`frontend-engineer`, `design-specialist`,
`devops-engineer`) that ship as thin stubs (`plugin: true` frontmatter, no behavior).
Until v0.1.11 the `plugin-scope` rule and the stubs instructed
`dadaia plugin install <name>` — a command that does not exist, dead-ending every
plugin-domain task (e.g. CI/CD work routed to devops-engineer). v0.1.11 resolved the
**dishonesty** (ADR-4 relabel: rule + stubs now state packs are not yet distributed and
route to the operator). v0.1.34 removed the old residue-grep pin as test slop; the
**capability gap** remains: plugin-domain tasks are unroutable without operator
hand-authoring.

## Scope sketch (needs grill)

1. **Pack format + distribution** — define what a plugin pack IS (persona bodies, skills,
   rules per pack: `frontend-design`, `devops`), where it lives (wheel extras? separate
   artifact? `public/plugins/` packs dir + manifest), and its privacy posture (generic
   only).
2. **`dadaia plugin` command group** — `install <name>` (stage + project pack assets,
   flip stub → full persona), `list` (installed vs available), `remove`. Idempotent;
   `public doctor` aware of installed packs.
3. **Re-point the relabel** — once the command exists, restore install instructions in
   `plugin-scope` + stubs and cover the real install/list/remove behavior.
4. **Related follow-up (rides along):** panel `core.js` still carries the dead legacy
   `?token=`/localStorage bootstrap (v0.1.11 T-011-13 moved the Bearer to an HttpOnly
   session cookie; server contract green without JS changes). Browser JS is
   frontend-engineer scope — the first consumer of the `frontend-design` pack should
   migrate `core.js` to the cookie mechanism and drop the dead bootstrap.

## Acceptance seed

- A consumer workspace can run `dadaia plugin install devops` and immediately dispatch
  `devops-engineer` with real behavior; `dadaia public doctor` exit 0 before and after.
- Zero references to a nonexistent command anywhere under `dadaia_workspace/public/`
  at every intermediate state.
