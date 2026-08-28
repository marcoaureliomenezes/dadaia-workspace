# Security review 2 — definition of release 0.5.0 (post-fold)

**Agent:** security-reviewer · **Stage:** definition re-review (NOT a push verdict — no `commit_sha`, no committed handoff)
**Date:** 2026-08-26 · **Subject:** `specs/releases/_ideas/0.5.0/{SPEC,PLAN,TASKS}.md` at `b1d424b8` (fold of five definition reviews)
**Prior pass:** `reviews/security-reviewer-definition-review.md` (REJECTED, S-1 … S-14 / A-1 … A-14)
**Read:** SPEC §9 first, then every FR/AS/acceptance/validation/task it cites — FR1 (both boundaries), FR2, FR3 6b/6c, FR4, FR6, FR9,
FR11, FR13, FR14, FR19, AS-13/14/15, A1.7–A1.9, A2.2/2.6/2.7/2.9, A3.9, A6.1–A6.6, A9.2/A9.6, A13.2/A13.5, A14.6, A19.3, V20–V24,
T-050-01/02/03A/06/06A/13A/14/36/37/41/42/43.
**Re-verified in the repo (read-only, no exploit run):** `git check-ignore -q` over the ten canon paths; `.github/scripts/pr-verdict-check.sh`;
`.github/workflows/ci.yml` (`security-verdict-gate`); `dadaia_workspace/core/specs_version.py` + its five consumers;
`dadaia_workspace/public/agents/security-reviewer.md`; a bash `case`-vs-glob probe.

## 1. Scan summary

**12 of 14 CLOSED · 2 PARTIAL · 0 regressions.** Residual severity after the fold: **MEDIUM 2 · LOW 3**. No CRITICAL, no HIGH survives.
No secret, token, credential, key or PII in the revised trio: a re-scan of all three files for home-absolute paths, e-mail literals,
IPv4 literals and external URLs returns **zero hits** (S-14 re-verified on the revised text, not carried over).

Both blocking classes are now **owned by a task with a write set and a validation gated before the step that would break**: T-050-06A
carries `.gitignore` + `pr-verdict-check.sh` + `ci.yml` + `core/specs_version.py` with V21 and V20, and its precondition is T-050-06 —
so both run at the head of `S1`, not at T-050-41. The fold refused the one amendment option that contradicted `DADAIA.md` §6 (archive
before ship) and took the structural option instead; that refusal is correct and I withdraw the alternative.

## 2. Disposition, S-1 … S-14

| id | Sev (orig) | CWE | Disposition | Evidence / what is missing |
|---|---|---|---|---|
| S-1 | CRITICAL | CWE-693 | **PARTIAL** (residual MEDIUM) | Owned: AS-15, FR1 boundary 2, A1.8, V20, T-050-06A write set, re-confirmed at T-050-41. Missing: (a) AS-15 admits `_ideas/` as an evidence **root**, but T-050-01 `git mv`s the trio out of `_ideas/` as the first task — no verdict ever lives there, so this widens a required gate's trust root for nothing, and V20 names an `_ideas/` fixture with **no stated expected outcome**; (b) no fail-closed posture for the derivation itself; (c) the derived id pattern's relation to `RELEASE_SEMVER_RE` is unstated — that object is identity-locked by `tests/contract/test_release_semver_canon.py` and consumed by `features/specs/{scaffolder,doctor_release}.py` + `features/spec_artifacts/new_artifacts.py`, none of which is in T-050-06A's write set. **Correction to my first pass:** in a bash `case`, `*` crosses `/`, so the offender allowlist at `:161` already matches `specs/releases/_archive/<id>/verdicts/*` — verified. Only the pathname glob breaks, which FR1 names exactly right. |
| S-2 | HIGH | CWE-778 | **CLOSED** | FR1 boundary 1 + A1.7 + V21 + T-050-06A. Probes re-run today confirm the stated facts (`FINDINGS.jsonl`, both `ADRs/` paths and `backlog/_archive/backlog_histo.jsonl` IGNORED; `AUDIT.md`, `BUGS.jsonl`, `releases/**` tracked). The inversion is stated as the deliberate privacy decision it is. Note only: T-050-06A deletes the root `specs/_archive/` stanza while that tree still exists until T-050-14 — harmless (tracked files stay tracked), but a new file written there in between would be silently untracked. |
| S-3 | HIGH | CWE-532 | **CLOSED** | FR2 redaction paragraph names `eb03d01b`/`0cb08157`; both write paths route through the schema-derived `redact`; A2.6 proves it by adding a property to the schema fixture with **no code list edited**. |
| S-4 | HIGH | CWE-212/532 | **CLOSED** | FR3 6b (migration writes through the seam, counts-only report) + 6c (rename voids the amnesty, procedure fixed in advance, never `--no-verify`) + A3.9 + V22 gated **before** the T-050-10 push. Nit (LOW): 6b enumerates five free-text fields and omits `title`/`solution` and the v5 `evidence*`/`reason` — the mechanism is schema-derived so it covers them; say "every free-text property in the schema" so the enumeration cannot be read as the set. |
| S-5 | HIGH | CWE-636 | **CLOSED** | FR9 bullet 2 gives `pre-push` its fail-closed runner in its own sentence with the subject named; A9.2 refuses **exactly three** things and its runner fixture asserts the push is *refused*, not skipped; T-050-18 carries it. |
| S-6 | MEDIUM | CWE-693 | **CLOSED** | A6.1 (remote `ls-remote` + throwaway-clone proof), A6.2 (historical `verdicts/**` relocated, gate proven), A6.4, A6.6 (scan-refusal path), executed as T-050-14 steps 1–4 in that order. |
| S-7 | MEDIUM | CWE-284 | **CLOSED** | A2.2 states seam-level enforcement and names its own limit in the test docstring; A2.7 adds the doctor WARN; FR14 pillar 1 makes an in-window core-field hunk a HIGH finding; FR11 rewrites the `DADAIA.md` §3 ADDITIVE row to "audited, not gated". |
| S-8 | MEDIUM | CWE-269 | **CLOSED** | FR13 decides explicitly: allowlist = `specs/audits/**` + `specs/bugs/BUGS.jsonl` (governance fields, through the FR2 seam); A13.2 retargeted at FROZEN, which is mechanically true; A14.6 pins one atomic rewrite per record. |
| S-9 | MEDIUM | CWE-532 | **PARTIAL** (residual LOW) | A13.5 + V24 applied for both the audit folder and the FR3 report. Missing: A13.5 makes a `.dadaia/tmp/**` path the citation, and the same fold records (CR-11) that `.dadaia/tmp/` is GC'd at 3 days — a finding read by its remediation release cites a path that no longer exists. |
| S-10 | MEDIUM | CWE-359 | **CLOSED** | `session_id` dropped outright; envelope is `{ts, event, agent, data}` with `additionalProperties` forbidden; the four examples carry shas, PR numbers, tags and audit slugs only. |
| S-11 | MEDIUM | CWE-693 | **CLOSED** | A6.3 enumerates the post-v6 FROZEN set exhaustively (one deletion, one addition), one fixture per path in T-050-14 step 4, and states `_ideas/` stays MUTATING deliberately. |
| S-12 | LOW | CWE-1053 | **CLOSED** (accepted, stated) | FR9 last bullet + A9.6 record the limit as a known gap with an intake candidate rather than a passed check. The `.gitignore` inversion now commits any file type under `audits/`/`ADRs/`, so V24 is the compensating control for the lane gitleaks does not cover — that dependency is worth one sentence in A9.6. |
| S-13 | LOW | — | **CLOSED** | T-050-02/36/37/42/43 each name the exact path and the 40-hex rule; T-050-42/43 correctly name the archived path after T-050-41. |
| S-14 | INFO | — | **CLOSED** | Re-scanned; zero hits. Sample records still use synthetic shas; QA-1 removed the fabricated bug id from every example, which also removes a fabricated-evidence surface. |

## 3. New, introduced by the fold

- **N-1 · MEDIUM · CWE-693** — AS-15 makes `specs/releases/_ideas/<id>/verdicts/` an evidence root of a **required** CI check while A6.3
  keeps `_ideas/` deliberately MUTATING and T-050-01 moves this release out of `_ideas/` before any PR exists. Unnecessary widening of a
  trust root, and V20's `_ideas/` arm asserts nothing. (Rolled into S-1.)
- **N-2 · MEDIUM · CWE-754** — the derivation has no stated failure posture. `security-verdict-gate` runs `bash` on a bare checkout with
  **no** `setup-python` and no install step, so the derivation must shell out to the interpreter. Feasibility is fine — I verified
  `dadaia_workspace/__init__.py` and `core/__init__.py` are empty and `core/specs_version.py` imports only `re` and `pathlib`, so a
  stdlib-only import succeeds on a bare checkout. The risk is the bash reflex `|| <default glob>`: a failed derivation must **exit 1**.
- **N-3 · LOW · CWE-1059** — T-050-03A widens four reviewer personas to `specs/releases/**/reviews/**` only. `security-reviewer`'s
  allowlist at HEAD is `.dadaia/reports/<ctx>/security-reviewer/**` + `.dadaia/handoff/<ctx>/**`, yet `DADAIA.md` §4 and the persona's own
  approval contract require it to commit `specs/releases/<id>/verdicts/<sha>.handoff.json`. That is the same "persona forbidden to write
  the artifact the law requires of it" shape FR13 just fixed for `project-auditor` — one line, in a task that already exists.

## 4. Bug-surface direction (standing order)

The fold **reduces** the surface it was rejected for. Three re-entries into punished shapes are gone: the gitignore catch-all is inverted
per area instead of gaining a tenth whitelist line; the verdict gate stops carrying a hard-coded glob and derives from the canon, with the
third firing named as such; the redaction seam installed one day earlier is now the single route for four new free-text fields and a second
write path. Two amendments were taken as *deletions* — `session_id` removed rather than constrained, `picked` removed from the status
vocabulary — and one claim was made honest rather than defended (A19.3's attribution limit, A2.2's seam-level scope). The residuals below
add no branch and no code path: four are one-clause statements and one is a fixture arm.

## 5. Verdict

**APPROVED — definition stage.** This is a definition-stage verdict, not a push verdict: no `metrics.commit_sha`, no committed handoff, and
it grants nothing to any PR. The trio may proceed once the five residuals below land; none requires re-opening a ratified ruling.

### Residuals — must land before the trio becomes `Em revisão`

1. **V20 states an expected outcome per fixture arm, and `_ideas/` is refused as an evidence root** (T-050-01 removes the only reason to
   admit it). If the widening is kept, AS-15 justifies it explicitly and A6.3's MUTATING statement cross-references it. *(N-1, S-1)*
2. **State the derivation's failure posture in FR1 boundary 2 and T-050-06A: interpreter failure, missing module or missing symbol ⇒ the
   gate exits non-zero.** No fallback glob, no `||` default. *(N-2)*
3. **V20 gains one arm proving a non-verdict path in the diff still disqualifies coverage**, so a derivation that touches the offender
   allowlist cannot silently un-gate it; and T-050-06A records that only the pathname glob is broken today, not the `case`. *(S-1)*
4. **Name where the bare-vs-`v` id pattern lands relative to `RELEASE_SEMVER_RE`** — identity-locked by `tests/contract/test_release_semver_canon.py`
   with three production consumers outside T-050-06A's write set — and keep it anchored, refusing `_`-prefixed and traversal shapes. *(S-1)*
5. **A13.5 and the FR3 report make `evidence` self-contained:** the reproducible command plus a redacted one-line result, with the
   `.dadaia/tmp/**` capture as a convenience, never the sole citation. Add `security-reviewer`'s `verdicts/**` path to T-050-03A. *(S-9, N-3)*

Re-review is not required for these five: each is a stated clause or a fixture arm, verifiable by the `S1` QA close (T-050-15) and by V20's
capture. A change to AS-15's trust root, or any new write set touching `.github/**`, does require one.
