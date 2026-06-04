# SPEC: v0.1.4.3 - handoff-directory-contract

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Objective

Move machine-readable agent handoff files out of `.dadaia/reports/` into a new
canonical runtime directory:

```text
.dadaia/handoff/<spec-context-project>/<handoff-file>
```

HTML reports remain under `.dadaia/reports/<context>/<agent>/`. Handoff JSON
must no longer be written as a sibling inside the reports tree.

## 2. Requirements

### PR-1: Canonical handoff root

`dadaia-workspace` must install and document `.dadaia/handoff/` as the canonical
location for inter-agent handoffs.

The directory must include a small scoped rule file:

```text
.dadaia/handoff/AGENTS.md
```

### PR-2: Context-scoped handoff files

Agents must write handoff JSON under:

```text
.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json
```

The file may reference an HTML report artifact in `.dadaia/reports/...` through
`artifact.path`, but the handoff file itself must not live in `.dadaia/reports`.

### PR-3: Agent instructions

Public agent, skill, workflow, and scoped-rule instructions must teach:

- reports are human-readable artifacts;
- handoffs are machine-readable coordination artifacts;
- downstream agents read the latest relevant handoff from `.dadaia/handoff/<context>/`;
- agents should keep handoffs concise, structured, and actionable.

### PR-4: CLI validation default

`dadaia reports validate --all` must discover handoff JSON from
`.dadaia/handoff/` by default. Explicit path validation must continue to work.

### PR-5: Hash validation across directories

Handoff hash validation must support the new layout where the handoff JSON and
the referenced HTML report are in different directories.

### PR-6: Public asset projection

`dadaia public {stage|install|doctor}` must manage `.dadaia/handoff/AGENTS.md`
as a lib-originated scoped rule, the same way it manages other runtime
control-plane scoped AGENTS files.

## 3. Non-Goals

- Do not rename `dadaia reports validate` in this release.
- Do not remove `.dadaia/reports/` or change the HTML report location.
- Do not add a new dependency.
- Do not create or use release `v0.1.5`.

## 4. Acceptance Criteria

### AC-1: Scoped rule exists

The public asset source contains a concise handoff scoped AGENTS file and the
installer projects it to `.dadaia/handoff/AGENTS.md`.

### AC-2: Report sidecar language removed

Default public instructions no longer require handoff JSON to be adjacent to
HTML reports in `.dadaia/reports/`.

### AC-3: CLI default updated

`dadaia reports validate --all` validates files under `.dadaia/handoff/` by
default.

### AC-4: Cross-directory artifact hashes work

A handoff in `.dadaia/handoff/<context>/` can reference an HTML report under
`.dadaia/reports/<context>/<agent>/` and pass content-hash validation.

### AC-5: Tests cover the new contract

Unit and contract tests cover public projection, CLI discovery, and validation
for the new handoff root.

### AC-6: Verification

Run focused tests for public assets, handoff models/schema, reports validation,
and CLI reports validation.
