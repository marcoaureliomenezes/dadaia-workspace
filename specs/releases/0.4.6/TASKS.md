# TASKS — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 1 — release-candidates system

- [x] T-046-01 — core/release_state: `_RELEASE.json` decider + legacy constant;
  readers (doctor_release, specs_tree, reports/next, invocation) import it.
  Write set: dadaia_workspace/core/release_state.py, dadaia_workspace/features/specs/**,
  dadaia_workspace/features/reports/next.py, dadaia_workspace/core/invocation.py, tests/**.
- [-] T-046-02 — canon: `_RELEASE.json` entry, `rc-N/` trio entries, legacy
  rename-lane entry; segment entries retired. Write set:
  dadaia_workspace/features/specs/canon.py, tests/**.
- [ ] T-046-03 — doctor: fixable rename rule, one-live-release rule, segment
  rules retired, phase cycle per candidate. Write set:
  dadaia_workspace/features/specs/*.py, tests/**.
- [ ] T-046-04 — scaffolder + CLI: segment lane deleted; `release new` new shape
  + single-live refusal; `release rc-archive` verb. Write set:
  dadaia_workspace/features/specs/scaffolder.py, dadaia_workspace/cli/**, tests/**.
- [ ] T-046-05 — migration: `_archive/*/RELEASE.json` → `_RELEASE.json`; this
  release flips to `_RELEASE.json`; pyproject 0.4.6; CHANGELOG `[0.4.6]`.
  Write set: specs/releases/**, pyproject.toml, CHANGELOG.md.
- [ ] T-046-06 — law + skills: DADAIA.md §4.2/§6.7/glossary; dd-gitflow-default;
  dd-release-definition; behavior-map hashes; CONTEXT.md glossary. Write set:
  dadaia_workspace/public/**, CONTEXT.md, tests/**.
- [ ] T-046-07 — closure: memory atoms, reprojection (stage/install/doctor),
  full preflight, candidate CLOSURE. Write set: specs/memory/**, CHANGELOG.md,
  specs/releases/0.4.6/**.
