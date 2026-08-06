---
name: panel-unused-logo-assets
status: idea
opened: 2026-08-06
owner: project-manager (curates)
priority: P4
source: 'found by the served-vs-requested asset ratchet added in 0.4.2: two logo assets are served and referenced by nothing.'
---
# BACKLOG — two panel logo assets are served but referenced by nothing

**Observation.** `static.py` serves `logo-rhino-16.svg`, `logo-rhino-24.svg` and
`logo-rhino-36.svg`, and exports a `LOGO_RHINO_*` constant for each. Only `LOGO_RHINO_36`
is used — inlined into the topbar markup. The 16 and 24 variants have no reference of
either kind: no `/static/` URL in any view or script, and no use of their constant.

**Why it was not removed in 0.4.2.** That release demolished the workflow engine, and the
ratchet that surfaced this was written to catch *demolition* leftovers. These two predate
it and are unrelated; deleting them there would have widened a release's diff with a
change nobody asked for. They are exempted by name in
`tests/unit/features/panel/test_no_dead_assets.py`, with the exemption pointing here.

**To decide.** Whether a favicon-sized and a 24px variant are wanted for a surface that
does not yet exist (browser tab icon, a compact header, an embed), or whether both should
go along with their constants and the test exemption. Check whether anything outside this
repository fetches them before deleting — they are reachable URLs today.
