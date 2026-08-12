---
name: security-low-carryforwards-v030
status: CONSUMED — v0.5.0
created: 2026-08-10
origin: security-reviewer push verdicts for v0.3.0/v0.4.0 (handoffs 2026-08-10, dadaia-workspace context) — 4 LOW findings, none push-blocking, routed per §6
owner: project-manager (curates)
disposition:
  terminal_status: CONSUMED
  closed_by: v0.5.0
  closed_at: '2026-08-12'
  evidence: specs/releases/v0.5.0/CLOSURE.md#dispositions
  findings:
    - finding: install-ledger relpath (CWE-22 class)
      status: FIXED
      by: v0.5.0 FR3.1 — validated in LedgerEntry.__post_init__, the one construction
        authority; zero validation added at either call site
    - finding: entities-derivation shape tolerance
      status: FIXED
      by: v0.5.0 FR3.3 — typed ENT-DERIVE-1 DoctorLine at the one parse seam
    - finding: kimi telemetry reader path containment
      status: FIXED
      by: v0.5.0 FR3.4 — lexical containment before stat, plus the reader's first test file
    - finding: certify surface re-scope post-engine-demolition
      status: RE-SCOPED (verified, no code)
      by: v0.5.0 FR3.5 — all 11 checks live, zero dead references; missing automated
        test routed to the backlog as a return
    - finding: CWE-117 doctor-line injection (new LOW, 2026-08-11 verdict)
      status: FIXED
      by: v0.5.0 FR3.2 — control-character escaping in DoctorLine.render()
    - finding: hook write-path latency on the resolution seam (new LOW, 2026-08-11 verdict)
      status: FIXED
      by: v0.5.0 six-axis review F-01 — container import removed from the hook path
        (2.25s → 0.46s measured), pinned by an attesting import-surface guard test
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/codex_doctor.py#check_entities_derivation" }
    change: "malformed-but-valid JSON (non-dict personas entries, non-dict implementations) raises AttributeError instead of an [error] line; fails closed today, but the verifier should degrade to a typed error line like the loader does"
  - subject: { kind: code, ref: "dadaia_workspace/features/telemetry/reader/kimi.py#read_kimi_sessions" }
    change: "session_dir/workDir strings from the untrusted index JSONL are used to build Paths without lexical validation (stat follows symlinks); metadata-only oracle, local-only — add a lexical containment check"
  - subject: { kind: code, ref: "dadaia_workspace/core/models/install_ledger.py#LedgerEntry" }
    change: "ledger relpath is not validated on the prune path (CWE-22 class); prune only deletes sha-matched files today — add relpath normalization + workspace containment before unlink"
  - subject: { kind: code, ref: "dadaia_workspace/features/certification/service.py#CertificationResult" }
    change: "certify surface carried forward from the v0.2.x reviews — re-scope what remains of the certify checks post-engine-demolition"
---

# Backlog — LOW security carry-forwards (v0.3.0/v0.4.0 verdicts)

Four LOW findings repeatedly re-verified across the 2026-08-10 push verdicts
(shas 8e4ce5e2 → f07bca39 → 153a0722 → 29ab43b8). Every one fails closed today;
none blocks a push. They are hardening items, not vulnerabilities in reach:
the panel is loopback-only, the readers are metadata-only, and the prune path
deletes only installer-recorded sha-matched files.

Disposition rule when picked: prefer the subtractive fix (validate at ONE
chokepoint each — the loader seam, the reader seam, the ledger model) over
scattering defensive checks at call sites.
