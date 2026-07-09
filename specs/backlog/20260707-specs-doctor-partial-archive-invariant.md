---
name: specs-doctor-partial-archive-invariant
status: candidate
opened: 2026-07-07
owner: project-manager (curates)
source: v0.1.61 closure backlog return (audit G-23 doctor-coverage-gap INFO — deferred per ADR-5, small new invariant out of an already-wide release)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/doctor_release.py#ReleaseValidator" }
    change: "add a specs-doctor invariant (WARNING severity) flagging PARTIAL archived release dirs: a specs/_archive/releases/<id>/ directory that contains none of SPEC.md/PLAN.md/TASKS.md/CLOSURE.md is residue, not an archived release (the v0.1.41 case held only GRILL.md + OQ-DECISIONS.md and sat undetected until the 2026-07-06 audit). The check should honor the SPEC-DOC-027 legacy-name allowlist, suggest relocation to specs/_archive/wip-abandoned/<id>/ with a README breadcrumb (the v0.1.61 G-23 remediation precedent), and stay WARNING-severity so historical trees never hard-fail doctor."
---

# BACKLOG — Specs-doctor invariant for partial archived release dirs

**Priority:** LOW (doctor coverage gap, INFO in the 2026-07-06 audit). The audit's G-23
finding exposed that `specs/_archive/releases/v0.1.41/` contained **only** `GRILL.md` +
`OQ-DECISIONS.md` — a never-implemented release's working residue masquerading as an archived
release — and no doctor invariant flags this class. v0.1.61 fixed the instance (residue
relocated to `specs/_archive/wip-abandoned/v0.1.41/` + README breadcrumb) but deferred the
invariant (ADR-5: small new check, out of an already-wide audit-remediation release).

Add the invariant to the archive-aware release validator: an `_archive/releases/<id>/` dir
carrying none of the four SDD artifacts (SPEC/PLAN/TASKS/CLOSURE) is flagged (WARNING) with
the wip-abandoned relocation as the suggested fix. Must not fire on the SPEC-DOC-027
legacy-name allowlist entries and must tolerate segmented release layouts
(`<id>/<segment>/`).

**Anchor:** `features/specs/doctor_release.py#ReleaseValidator` (the validator that already
walks `specs/_archive/releases/`).
