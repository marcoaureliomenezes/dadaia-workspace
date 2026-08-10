---
name: security-low-carryforwards-v030
status: OPEN
created: 2026-08-10
origin: security-reviewer push verdicts for v0.3.0/v0.4.0 (handoffs 2026-08-10, dadaia-workspace context) — 4 LOW findings, none push-blocking, routed per §6
owner: project-manager (curates)
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
