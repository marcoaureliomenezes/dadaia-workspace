# RUBRIC — dd-audit-project compliance scoring (1–10)

Disclosed reference reached from `SKILL.md`'s Compliance Scoring section and from
`public/agents/project-auditor.md` Step 5 — this is the **one** dimension list; neither
file restates it (A26.3). Score each dimension independently. Use the anchors at
1 / 4 / 7 / 10 as calibration points; interpolate for intermediate values.

## Dimension A — Architecture

| Score | Anchor |
|---|---|
| 10 | Every module in code maps exactly to a declared layer; no cross-layer violations; all ADRs reflected |
| 7 | Minor violations (1–2 files in wrong layer); ADRs mostly reflected; no undeclared external deps |
| 4 | Significant layer mixing; 1–2 ADRs ignored; architecture docs lagging by 1 release |
| 1 | Architecture memory does not reflect code; layers not enforced; no ADR log maintained |

## Dimension B — Product Features

| Score | Anchor |
|---|---|
| 10 | Every criterion in every feature slug file has a passing test and matching implementation |
| 7 | 90%+ criteria covered; 1–2 minor behaviors undocumented |
| 4 | 70–89% criteria covered; several edge cases missing from impl or from memory |
| 1 | < 50% criteria covered; feature memory significantly outdated |

## Dimension C — Tech Stack

| Score | Anchor |
|---|---|
| 10 | All deps declared in memory; versions match lockfile exactly |
| 7 | 1–2 minor version discrepancies; no undeclared prod deps |
| 4 | Several undeclared deps in lockfile; versions drifted |
| 1 | Tech-stack memory does not reflect actual tooling |

## Dimension D — Security

| Score | Anchor |
|---|---|
| 10 | OWASP checklist green; no secrets in repo; all auth patterns correct |
| 7 | No CRITICAL/HIGH findings; 1–2 MEDIUMs with mitigations planned |
| 4 | 1 HIGH finding open; or 3+ MEDIUMs unmitigated |
| 1 | CRITICAL open; secrets in repo; auth bypasses present |

## Dimension E — Test Detection Quality

Line coverage measures execution, not detection — it never anchors this score. See
`dadaia-test-stewardship`.

| Score | Anchor |
|---|---|
| 10 | Every test declares intent; every LARGE demoted or SENTINEL-justified at closure; flake within ceiling; quarantine within cap and not expired; every LARGE has a named owner |
| 7 | Intent mostly declared; 1–2 undemoted LARGE with a tracked plan; flake and quarantine within limits |
| 4 | Intent sparsely declared; LARGE tests accumulate without demotion; quarantine over cap or an expired entry |
| 1 | No intent taxonomy in use; tombstone tests present; flake above the ceiling with no quarantine |

The CI coverage floor (`DADAIA.md` §7 (Quality)) is checked separately as a pass/fail
gate, never scored here.

## Dimension F — Agent-surface

The AI-entity surface: personas, skills, rules, hooks (`public/agents/`, `public/skills/`,
law files, hook wiring). Evidence agent: `ai-engineer` (persona-shape / prompt-efficiency
drift when memory's agent topology diverges from on-disk personas/skills/rules).

| Score | Anchor |
|---|---|
| 10 | Every persona/skill/rule matches its declared scope and topic row in `rules-skills-map.json`; `dadaia public doctor` reports zero drift; no undeclared activation-glob overlap; no disclosed content orphaned from its `SKILL.md` pointer |
| 7 | 1–2 minor scope/pointer staleness issues; projections mostly hash-matched; no undeclared overlap |
| 4 | Several personas/skills diverge from actual agent behavior; disclosed depth duplicated across files instead of pointed-to; projection drift present but non-blocking |
| 1 | Personas/skills/rules materially out of sync with actual behavior; undeclared activation-glob overlaps; `dadaia public doctor` reports drift or missing projections |

---

## Aggregation formula (reference, lives in `SKILL.md`)

The weighting algorithm and the per-dimension weights (A×0.20 + B×0.25 + C×0.15 +
D×0.20 + E×0.15 + F×0.05) are declared in `SKILL.md`'s Aggregation Formula section —
this file supplies anchors only, not weights.
