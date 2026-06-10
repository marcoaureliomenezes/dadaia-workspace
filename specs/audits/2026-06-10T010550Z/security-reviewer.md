# Security Review — dadaia-workspace source library

- **Date:** 2026-06-10 (UTC)
- **Target:** `dadaia_workspace/` source library (audited inside the live instance)
- **Scope:** subprocess/hooks injection surface, projection/install path handling, state-file trust (locks/leases/sessions), panel auth, secrets/credentials, `context dead` auto-commit, public-privacy boundary, closed-bug verification, dependency audit
- **Auditor:** security-reviewer (AUDIT ONLY — no fixes written)
- **Tools run:** `grep`/`Read` source review, empirical `classify_path` probe, `pip-audit 2.10.0` over the venv third-party closure
- **Score:** 7/10

---

## Findings table

| # | Severity | CWE | OWASP | Location (`file:line`) | Title |
|---|----------|-----|-------|------------------------|-------|
| F-1 | **HIGH** | CWE-863 / CWE-667 | A01 Broken Access Control | `features/spec_context/gate_policy.py:84-98` | ADDITIVE/MEMORY/FROZEN classifier is workspace-root-only; in-repo `repos/<ctx>/specs/bugs|audits|memory/…` mis-classify as **MUTATING** → ADDITIVE write steals the implementation lease (confused-deputy lease-theft) |
| F-2 | MEDIUM | CWE-732 / CWE-754 | A02 / A05 | `infrastructure/privacy_check.py:95-97` | Public-privacy boundary **fails open**: when the operator-local denylist file is absent (fresh clone, CI, pip install) the gate returns `[ok]` with **zero terms checked** — no protection against leaking private identifiers into public assets |
| F-3 | MEDIUM | CWE-200 / CWE-668 | A04 / A07 | `features/panel/handler.py:328-334,374-400` | `loopback_bypass` disables **all** Bearer auth for 127.0.0.1 binds; any local process or a malicious local web page (DNS-rebinding / CSRF-style) reaches every sensitive panel API with no token |
| F-4 | MEDIUM | CWE-22 | A01 | `public/scripts/sdd-spec-gate.sh` (FPATH classifier) | Bash gate does not `realpath` FPATH before classification; a symlink from an UNGATED path into a gated subtree could mis-classify (already filed `gate-fpath-not-canonicalized-before-classifier`, Open). The **Python** gate (`hooks/sdd_gate.py:101`) DOES `.resolve()` first — defect is bash-path-only |
| F-5 | MEDIUM | CWE-200 / CWE-552 | A09 / A03 | `features/spec_context/service.py:292-302` + `infrastructure/git_subprocess.py:26-73` | `context dead()` auto-stages **all untracked non-gitignored files** and `git push`es them with **no review, no secret scan, no operator confirmation** — known historical leak vector, still present |
| F-6 | LOW | CWE-1395 | A06 Vulnerable Components | `poetry.lock` (dev/build group) | `dulwich 0.21.7` (CVE-2026-42305, CVE-2026-47734) and `poetry 1.8.3` (CVE-2026-34591, CVE-2026-41140) carry known CVEs. **Tooling/build deps only** — NOT in the published runtime closure (typer/rich/openpyxl/pyyaml/jinja2/jsonschema/mistune) |
| F-7 | LOW | CWE-732 | A02 | `features/panel/auth.py:34-35` | `ensure_token` re-reads a **pre-existing** token file without verifying its mode; a token created by an older (pre-fix) version at `0o644` stays world-readable — the atomic-create fix only protects newly minted tokens |
| F-8 | INFO | — | A05 | `hooks/*.py` (all) | Hook trust model is **fail-open by design** (parse error / unresolved workspace → ALLOW). No hook performs a destructive action (no rmtree/delete). Sole fail-CLOSED path is PROTECTED `.dadaia/sessions/`. This is the correct posture but means a crafted payload yields ALLOW, never a block — acceptable, noted for completeness |

### F-1 detail (HIGH — the load-bearing one)

`classify_path` (`gate_policy.py:84-98`) matches `_ADDITIVE_PREFIXES`, `_MEMORY_PREFIX`,
`_FROZEN_PREFIX` only against **workspace-root-relative** strings (`specs/bugs/`,
`specs/memory/`, …). The MUTATING branch matches `repos/` first for any in-repo path.
Empirically verified against the real classifier:

```
ADDITIVE   <- specs/bugs/x.md
MUTATING   <- repos/dadaia-workspace/specs/bugs/x.md     <-- should be ADDITIVE
MUTATING   <- repos/foo/specs/audits/y/r.md              <-- should be ADDITIVE
MUTATING   <- repos/foo/specs/memory/a.md                <-- should be MEMORY
PROTECTED  <- .dadaia/sessions/runtime/x.ptr             (correct)
```

Consequence: in any **consumer context repo** (and in the self-hosting workspace where the
bug-registration law mandates `repos/dadaia-workspace/specs/bugs/`), an ADDITIVE write the
product law declares "never gate-blocked, never locked" instead **acquires the
IMPLEMENTATION lease** via `lease.acquire` (`gate_policy.py:147`). A passive/read-bound
session that merely files a bug **takes over a live session's lease** (broken access
control / confused deputy). This is the same kernel as the registered CRITICAL bug
`lease-stolen-by-additive-write-from-live-session` (D1) — I confirm it reproduces from the
classifier alone. I rate the **security dimension** HIGH (mutual-exclusion bypass; the
project bug file's CRITICAL severity for the availability/correctness dimension stands).

---

## Closed-bug verification verdicts

| Bug | Status in file | Code verdict | Evidence |
|-----|----------------|--------------|----------|
| `panel-token-file-chmod-toctou` | Closed | **ROOT-CAUSE FIXED** | `auth.py:104` uses `os.open(O_CREAT\|O_WRONLY\|O_EXCL, 0o600)` — file is born at 0o600, no widen window; `O_EXCL` also closes the double-write race. Parent dir restricted to 0o700 / `FilePermissionSetter` before creation; Windows path fails loud (`PlatformSecurityError`). Residual: pre-existing wide-mode token not re-checked → F-7 (LOW) |
| `panel-handler-parallel-auth-registries` | Closed | **ROOT-CAUSE FIXED** | `handler.py:131-172` collapses the three parallel registries into ONE declarative `_ROUTE_TABLE` of `(pattern, name, AuthClass)`; no silent-public fallback; unclassified route ⇒ import-time `ValueError`. Dispatch reads `auth_class` directly (`handler.py:374-400`). DELETE has its own ordered `_DELETE_ROUTE_TABLE` with `/important$` before the catch-all. Standing E2E guard tests present |
| `gate-fpath-not-canonicalized-before-classifier` | Open (MEDIUM) | **SYMPTOM-LEVEL / PARTIAL** | The **Python** gate now `.resolve()`s before classification (`hooks/sdd_gate.py:101`), closing the symlink vector for the Python enforcement path. The **bash** gate (`sdd-spec-gate.sh`) still does not `realpath`. As both enforce, the bash path remains exploitable on symlink traversal → F-4. No live bypass demonstrated (PROTECTED glob + slug strip mitigate); hardening still owed |
| `lease-stolen-by-additive-write-from-live-session` | Open (CRITICAL) | **NOT FIXED (reproduced)** | Root cause D1 confirmed in `gate_policy.classify_path` (see F-1). In-repo additive paths classify MUTATING and acquire the lease. Security dimension surfaced as F-1 HIGH |
| `spec-context dead() auto-commit` (memory note, no open bug file) | n/a | **PRESENT** | `service.py:292-302` commits-all + push on `dead()`; `_stage_files_safe` respects `.gitignore` (`git ls-files --others --exclude-standard`) but stages all other untracked files with no review/secret-scan → F-5 |

**Positive controls observed (no finding):**
- `git_subprocess.clone` blocks `ext::` transport (RCE) and leading-`-` URLs (CWE-88 argument injection) — `git_subprocess.py:82-83`.
- No `shell=True` anywhere; every subprocess call uses an argv list (`subprocess_runner.py:33`, `git_subprocess.py:13`).
- `push` is plain (no `--force`); `commit_all` cannot force-overwrite remote history.
- Lease uses **O_EXCL CAS** + TTL-only liveness (no PID, no `os.kill` — avoids the Windows `os.kill` destructiveness and PID-reuse forgery). Lease/`.ptr`/record reads are defensive (`None` on malformed JSON; `lease.py:182-185`).
- Session-id and context-slug sanitized to `[A-Za-z0-9_-]` (CWE-22) in `_common.sanitize_session_id` and `sdd_gate._context_slug`.
- Panel `memory` view guards traversal with `resolve()` + `is_relative_to(memory_root)` (`views/memory.py:95-99`); `reports_doctor.py:126,137-139` rejects `..` parts and verifies `relative_to(reports_root)`.
- Bearer validation is constant-time (`auth.py:validate` → `hmac.compare_digest`).
- `.dadaia/sessions/` lease-identity `.ptr` is the sole fail-CLOSED PROTECTED class — agents cannot Write/forge it (SEC-01 / CWE-284), verified by classifier probe.

---

## Dependency-audit summary

`pip-audit 2.10.0` over the venv third-party closure (127 packages; local editable
self-package excluded):

| Package | Version | CVE | Fix | In runtime closure? |
|---------|---------|-----|-----|---------------------|
| dulwich | 0.21.7 | CVE-2026-42305 | 1.2.5 | No (poetry transitive — dev/build) |
| dulwich | 0.21.7 | CVE-2026-47734 | 1.2.5 | No (poetry transitive — dev/build) |
| poetry | 1.8.3 | CVE-2026-34591 | 2.3.3 | No (build/dev group) |
| poetry | 1.8.3 | CVE-2026-41140 | 2.3.4 | No (build/dev group) |

Runtime dependencies declared in `pyproject.toml` (`typer`, `rich`, `openpyxl`, `pyyaml`,
`jinja2`, `jsonschema`, `mistune`) carry **no known CVEs** in this scan. All 4 findings are
in **dev/build tooling** that does not ship in the published wheel's runtime closure →
production exposure is LOW (F-6). Recommend bumping the dev `poetry`/`dulwich` pins
opportunistically; none is a release blocker. No CVE with CVSS ≥ 9.0 in a production
dependency → no escalation triggered.

---

## Hook trust model assessment

All five PreToolUse hooks (`hooks/*.py`) parse harness JSON from stdin and act on the
write-target path. Trust posture:

- **Fail-open everywhere** except PROTECTED. A crafted/unparseable payload → `{}` → ALLOW
  (`_common.read_stdin_json:53-64`; `sdd_gate.main:87,93`). This means a malicious payload
  can at worst **evade a block**, never **cause a destructive action** — no hook deletes,
  rmtrees, or writes outside `.dadaia/sessions/runtime` / lease records.
- **Path-traversal contained:** session-id and slug are stripped to `[A-Za-z0-9_-]`; the
  Python gate `.resolve()`s before classifying. Residual symlink gap is bash-path-only (F-4).
- **No injection from tool JSON into a shell:** hooks never pass any field to a shell; they
  only classify and emit a JSON envelope. Codex `apply_patch` header parsing
  (`_common.target_path:88-94`) is pure string slicing.
- **Root-whitelist hook** gates only writes whose immediate parent resolves to the workspace
  root, fails open on resolve error, and reads its exception list defensively
  (`root_whitelist.py:84-95`). Minor: `basename` is taken from the raw (un-resolved) name,
  but the gating decision uses `parent.resolve()`, so the check is sound.

**Verdict:** the hook layer cannot be coerced by a crafted path/tool input into a
destructive action or a write outside its sandbox. Its only failure mode is permissive
(fail-open), which is the documented and intended posture. No finding beyond F-8 (INFO).

---

## Security score & top 5 risks

**Score: 7 / 10.** Strong fundamentals — no `shell=True`, argv-only subprocess, git URL
injection guards, constant-time auth, O_EXCL atomic token + lease CAS, traversal guards on
served paths, and a fail-open-but-non-destructive hook layer. The deductions are a
broken-access-control classifier defect (lease-theft), a fail-open privacy boundary, an
unauthenticated-loopback panel posture, and an unreviewed auto-push on `dead()`.

**Top 5 risks (priority order):**

1. **F-1 (HIGH) — in-repo ADDITIVE→MUTATING mis-classification → lease-theft.** The
   `classify_path` prefixes only match workspace-root paths; every consumer context repo
   loses ADDITIVE/MEMORY/FROZEN protection and an additive write steals the lease. Fix:
   strip a leading `repos/<slug>/` segment before prefix-matching (or match the prefixes
   anywhere after the context root). Kernel of the CRITICAL `lease-stolen` bug.
2. **F-5 (MEDIUM) — `context dead()` auto-commits + pushes untracked files with no
   review.** Gitignore is respected, but any private file the operator forgot to ignore is
   pushed silently. Fix: refuse to auto-commit untracked files (require a clean tree or an
   explicit `--commit` flag) and/or run a secret-scan before push.
3. **F-3 (MEDIUM) — loopback auth bypass.** All Bearer auth is disabled on 127.0.0.1 binds,
   exposing sensitive APIs to any local process / malicious local page. Fix: keep Bearer
   required even on loopback, or add an `Origin`/`Host` allowlist and a same-origin check.
4. **F-2 (MEDIUM) — public-privacy gate fails open when the denylist file is absent.** In
   CI or a fresh clone the gate reports `[ok]` having checked nothing. Fix: ship a baseline
   structural denylist (IP/hostname/path regexes) in-package so the check is never a no-op,
   keeping operator terms externalized as additive.
5. **F-4 (MEDIUM) — bash SDD gate does not canonicalize FPATH before classification.** A
   symlink into a gated subtree can mis-classify on the bash enforcement path (Python path
   is fixed). Fix: `realpath`/canonicalize FPATH consistently with `$WS` before the `case`,
   mirroring `hooks/sdd_gate.py:101`.

_No secrets, live credentials, or PII detected in source. No CVE ≥ 9.0 in a production
dependency. No escalation-threshold trigger fired during this audit._
