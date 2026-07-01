# Security Re-Audit — dadaia-workspace (v0.1.10)

- **Date:** 2026-06-10 (UTC)
- **Target:** `dadaia_workspace/` source library, branch `feature/v0.1.10` @ HEAD `f77e96c`
- **Baseline:** `specs/audits/2026-06-10T010550Z/security-reviewer.md` (7/10)
- **Diff reviewed:** `git diff 8ccfa7a..HEAD` (164 files, +15634/-4438)
- **Auditor:** security-reviewer (SCORED audit pass — AUDIT ONLY, no fixes written)
- **Tools run:** `grep`/`Read` source review, `git diff` secret scan, `pip-audit 2.10.0` over the venv closure
- **Disclosure:** this is the scored adversarial pass, distinct from the rc-reviewer APPROVE on the same diff. Fresh eyes; verdicts re-derived from code.
- **Score:** **9 / 10**

---

## F-1..F-8 closure verdicts (in code, `file:line`)

| # | Sev (baseline) | Verdict | Evidence (`file:line`) |
|---|----------------|---------|------------------------|
| F-1 | HIGH | **FIXED** | `gate_policy.py:150-193` — new `_context_relative()` strips a leading `repos/<slug>/` and re-roots the `specs/` taxonomy at the context (`_classify_specs_relative`). In-repo `specs/bugs|audits` ⇒ ADDITIVE, `specs/memory` ⇒ MEMORY, unmatched in-repo ⇒ MUTATING (never UNGATED, `:179-180`). The confused-deputy lease-theft kernel (ADDITIVE-in-repo → MUTATING → `lease.acquire`) is closed: an in-repo additive write no longer reaches the lease path. Matrix tests `test_classifier_reroot_matrix.py` (227 lines) + hook-level `test_classifier_incident_hooklevel.py`. |
| F-2 | MEDIUM | **FIXED** | `privacy_check.py:80-119,162-232` — a packaged, versioned baseline (`infrastructure/data/privacy_baseline.json`, `version:1`, `released_in:v0.1.10`) of structural IP/IPv6/path/email/hostname/secret regexes is loaded from the wheel. `check_public_privacy:200-232` runs the baseline whenever the operator denylist is absent (`baseline_only` path) and merges operator terms additively on top. The fail-open `[ok]`-with-zero-terms hole is closed; baseline mode emits a distinct marker. |
| F-3 | MEDIUM | **FIXED** | `handler.py:304-313,371-392` — `loopback_bypass` removed entirely. All BEARER / BEARER_SECOND_LOOP / BEARER_TELEMETRY routes enforce `_validate_bearer` unconditionally (no 127.0.0.1 exemption); tokenless ⇒ 401. **Residual (token lifecycle):** token still travels `?token=` launch URL → `core.js` bootstrap → `authedFetch`. URL-borne token is observable in shell history / referrer / local proxy logs. Scored LOW residual (R-1) — replaceState/localStorage handling not re-verified line-by-line here; one-time launch URL is acceptable, but it is the remaining soft edge. |
| F-4 | MEDIUM | **FIXED (root)** | Bash gate quartet **retired in v0.1.10** (`gate_policy.py:1-10` module docstring; sole remaining shell asset is `public/scripts/pre-push-ci-gate.sh`, a real git hook). The Python gate `.resolve()`s before classification (`hooks/sdd_gate.py`); the symlink-traversal vector that lived only on the bash path is gone with the bash path. Test `test_classifier_symlink_canonicalization.py`. |
| F-5 | MEDIUM | **FIXED** | `service.py:359-413` (`_enforce_dead_review_gate`) + `:416-453` (`dead`). Untracked non-gitignored files + no `--commit` ⇒ `DeadReviewRequiredError`, **nothing pushed, repo left on disk** (`:381-394`). `--commit` ⇒ structural secret scan (`_scan_file_for_secrets:119`, rules at `:95-115`: github/slack token, generic secret assignment, private IPv4 RFC1918, internal hostname) over the files about to be committed; any hit ⇒ `DeadSecretFoundError`, push blocked (`:405-413`). Gate runs BEFORE any lock/commit/push/rmtree (`:450-453`). Failure to enumerate untracked ⇒ fail-closed refuse (`:371-379`). |
| F-6 | LOW | **UNCHANGED (accepted)** | `pip-audit` still flags `dulwich 0.21.7`, `poetry 1.8.3`, and now `pip 24.0` (5 new pip CVEs) — **all venv/build tooling, none in the runtime closure**. Runtime deps (`typer/rich/openpyxl/pyyaml/jinja2/jsonschema/mistune`) remain CVE-clean. No CVE ≥ 9.0 in a production dependency. tech-stack.md documents the `poetry≥2.3.4 / dulwich≥1.2.5` operator pins. No release blocker. |
| F-7 | LOW | **FIXED** | `auth.py:42-68` (`_recheck_pre_existing_token_mode`) + `ensure_token:71-128`. A pre-existing token file now has `S_IMODE(stat)` re-checked on every read and is tightened to `0o600` when group/other-readable (`:34-35,66-68`), via injected `permission_setter` (icacls) or `os.chmod` on POSIX. Windows-with-no-setter fails loud rather than silently leaving it wide (`:61-65`). The old 0o644-token-stays-wide residual is closed. |
| F-8 | INFO | **UNCHANGED (correct posture)** | Hook trust model remains fail-open-but-non-destructive; `.dadaia/sessions/` PROTECTED is the sole fail-CLOSED class, evaluated FIRST (`gate_policy.py:233-237`). No hook deletes/rmtrees outside its sandbox. `_common.read_stdin_json:52-64` → `{}` → ALLOW on malformed payload. Posture is intended; no finding. |

---

## New-surface adversarial pass (v0.1.10 net-new code)

| ID | Sev | CWE | Location | Finding (redacted) |
|----|-----|-----|----------|--------------------|
| N-1 | INFO | CWE-22/CWE-59 | `session_identity.py:63,71-73` | sid/ctx names validated by `_NAME_RE = [A-Za-z0-9_-]+` **fullmatch** before any path construction — `/`, `..`, NUL, absolute paths all rejected at `ptr_path`/`session_ptr_path`/`session_record_path`. Traversal closed. Reads fail-soft (`None`) on malformed input. No finding. |
| N-2 | INFO | CWE-667 | `sdd_post_gate.py:89-107` + `lease.py:411-458` | **Foreign-lease renewal is impossible from the post-gate.** `_renew_held_leases` iterates ALL lock-dir contexts, but `lease.renew_heartbeat` is holder-guarded (`lease.py:451`: `rec.get("session_id") != session_id ⇒ return False`) and runs inside the same O_EXCL sentinel CAS as `acquire`. Crucially the post-gate path does **not** consult `.ptr` for renewal — only exact `session_id` equality — so the stdin-supplied sid cannot renew a lease it does not literally hold. The first-ALIVE cross-context contamination path is deliberately removed (`:33-36`). D2/D3 root cause closed. |
| N-3 | LOW | CWE-552 | `service.py:70-90,119-126` | dead() secret scan covers a **suffix allowlist** (`_SECRET_SCAN_TEXT_SUFFIXES`, includes `""` so extensionless files like `Dockerfile` ARE scanned). Residual: a planted credential in a non-listed/binary suffix (e.g. `.pem`, `.p12`, `.key`, `.pdf`) is skipped → would still be committed under `--commit`. Defense-in-depth gap only; `--commit` is explicit operator consent and `.gitignore` is still honored. Add `.pem/.key/.crt/.p12` to the allowlist or scan-by-content-sniff. |
| N-4 | INFO | — | `lease.py:285-408` | PID record + injected `pid_probe` veto (`:388`, `core.lock_liveness.is_stale`) means a TTL-expired-but-running foreign holder is BLOCKed, not stolen. Probe is hook-injected (no `os.kill` in this module; Windows-safe). O_EXCL CAS preserved; no read-then-write acquire path. `_before_write` test seam is import-time asserted `None` in prod unless `DADAIA_TESTING=1` (`:104-107`). No finding. |
| N-5 | INFO | — | `model_registry.py:1-60` | Pure data, zero I/O, no OS-primitive imports (core layer). Append-only dated pricing. No injection/secret surface. No finding. |
| N-6 | INFO | — | `tests/e2e/test_two_actor_lease.py`, `tests/fixtures/harness_env.py`, `tests/e2e/lease_rendezvous.py` | Two-actor test helpers are test-tree only; file-based rendezvous under `tmp_path`, no repo-root writes, no prod import. `_before_write` seam gated by `DADAIA_TESTING`. No prod impact. No finding. |
| N-7 | INFO | — | `sdd_post_gate.py:169-189` | stdin payload only feeds `resolve_session_id` (sanitized `[A-Za-z0-9_-]`, `_common.py:97-116`) and lock-dir filename iteration. No field reaches a shell; `apply_patch` header parse is pure slicing. Fail-open exit 0 on any exception. No injection. |

**Re `bind --print-env`:** no `--print-env` / env-export surface exists in the spec_context CLI or service — bind persists mode to the session record/`.ptr`; nothing leaks env to a subprocess. `DADAIA_SESSION_ID` is honored only as an operator override in `resolve_session_id` (first in order), not exported by the tool. No finding.

---

## Secret scan over the release diff (`8ccfa7a..HEAD`)

Scanned `+`-lines for RFC1918 IPs, operator home paths (`/home/<u>/`, `/Users/<u>/`),
`password/api_key/secret` assignments, PEM headers, `ghp_`/`xox`/`AKIA` tokens. **All hits
are legitimate:** regex rule definitions (the new secret-scan engine + `privacy_baseline.json`),
docstrings, prior-audit text quoting F-5, and test fixtures with intentionally *harmless*
planted strings. **No planted operator-local path, IP, hostname, or live secret** in any
committed bug file, audit, spec, or memory atom. `/home/marco` does not appear in the diff.

---

## Dependency-audit summary

`pip-audit 2.10.0` over the venv closure: `dulwich 0.21.7` (CVE-2026-42305/47734), `poetry
1.8.3` (CVE-2026-34591/41140), `pip 24.0` (5 CVEs incl. PYSEC-2026-196). **Every finding is
venv/build tooling — none ships in the published wheel's runtime closure.** Runtime deps carry
no known CVEs. No CVE ≥ 9.0 in a production dependency → no escalation. Self-package
`dm-capture-utils` skipped (editable, not on PyPI). Posture: production-clean; tooling
documented in tech-stack.md. Recommend the opportunistic `pip`/`poetry`/`dulwich` venv bumps;
none is a release blocker.

---

## Residual risks (priority order)

1. **R-1 (LOW) — panel token in launch URL.** F-3's auth bypass is fully closed, but the
   bearer token still arrives via `?token=` and is browser-observable (history/referrer).
   One-time launch URL is acceptable; tightening (POST handshake or short-TTL launch token)
   would remove the last soft edge. Not a blocker.
2. **R-2 (LOW, N-3) — dead() secret scan suffix gap.** Credential in a non-listed binary
   suffix (`.pem/.key/.p12`) under `--commit` is skipped. `--commit` is explicit consent and
   `.gitignore` is honored, so exposure requires operator opt-in + an unignored cert file.
   Add cert suffixes to the allowlist.
3. **R-3 (INFO) — hook fail-open.** Unchanged intended posture: a crafted payload can at
   worst evade a block, never cause a destructive action. Documented, accepted.
4. **R-4 (INFO) — stale yield-message in historical SPEC text.** A v0.1.6-era SPEC line still
   quotes `'dadaia lock steal'`; the **live code** message (`lease.py:_yield_message:265-282`)
   correctly omits any steal/relaunch instruction. Doc-history only, not a code defect.

---

## Score & rationale

**Score: 9 / 10** (was 7/10).

v0.1.10 closed **all four MEDIUM/HIGH residuals** that drove the original deduction:
the lease-theft classifier (F-1 HIGH), the fail-open privacy boundary (F-2), the
unauthenticated loopback panel (F-3), and the unreviewed auto-push on `dead()` (F-5) — each
verified in code with standing tests, not asserted. F-4 was eliminated at the root by retiring
the bash gate entirely. F-7 (token mode re-check) is closed. The new WS-R2/R3/R4 surfaces
(PID-veto lease, session_identity consolidation, read-mode non-acquisition, holder-guarded
post-gate heartbeat) were adversarially probed and hold — foreign-lease renewal is structurally
impossible, traversal is fenced, no new injection or secret surface.

**What blocks a 10:** two LOW residuals remain (R-1 launch-URL token observability, R-2 dead()
secret-scan binary-suffix gap), and the dependency posture still carries documented (out-of-runtime)
tooling CVEs. None is a release blocker; all are defense-in-depth. Fundamentals were already
strong at 7; v0.1.10 converted the four exploitable gaps into closed, tested controls, which is
the honest delta.

_No secrets, live credentials, or PII detected in source or the release diff. No CVE ≥ 9.0 in a
production dependency. No escalation-threshold trigger fired._
