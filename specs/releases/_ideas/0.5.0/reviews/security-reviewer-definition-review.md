# Security review — definition of release 0.5.0 (Draft)

**Agent:** security-reviewer · **Stage:** definition review (NOT a push verdict) · **Date:** 2026-08-26
**Subject:** `specs/releases/_ideas/0.5.0/{SPEC,PLAN,TASKS}.md` (2 817 lines, read in full)
**Authority:** grill handoff `2026-08-26T120000Z-…-governance-lineage-audits-adr-grill` (D1–D15)
**Also read:** `DADAIA.md` §4/§7/§9 · `infrastructure/{privacy_check,git_objects,install_helpers}.py` · `features/chokepoints/{denylist_scan,service}.py` ·
`core/models/bugs.py` · `features/bugs/service.py` · `features/spec_context/gate_policy.py` · `public/scripts/{pre-commit-presence-gate,pre-push-ci-gate}.sh` ·
`.github/workflows/{ci,secret-scan}.yml` · `.github/scripts/pr-verdict-check.sh` · `.gitignore`
**Method:** read-only, no exploit run. Probes: `git check-ignore -q` over the ten canon paths this release creates; `git tag -l 'archive/*' | wc -l` (= 50, matches AS-9).

## 1. Scan summary

**CRITICAL 1** (S-1) · **HIGH 4** (S-2 · S-3 · S-4 · S-5) · **MEDIUM 6** (S-6 … S-11) · **LOW 2** (S-12 · S-13) · **INFO 1** (S-14).
No secret, token, credential, key or PII appears in the definition (§9 clean). The findings are publication-boundary and
evidence-integrity defects, plus one required CI gate this release mechanically breaks.

## 2. Findings

### S-1 · CRITICAL · CWE-693 — archiving before shipping disables `security-verdict-gate` on both remaining PRs
**Where:** `TASKS.md` T-050-41 → T-050-42 → T-050-43 (archive precedes both PRs) × `SPEC.md` FR1 (release dirs become bare semver) ×
D-G / closure "Archive decision: MOVE — into `specs/releases/_archive/0.5.0/`" × `.github/scripts/pr-verdict-check.sh:79` (`_RELEASE_ID_RE`
requires a `v` prefix), `:96-100` (candidate globs), `:161` (`case` evidence allowlist).
**Evidence:** the gate resolves a verdict only from `specs/releases/*/verdicts/*.handoff.json` or `specs/_archive/releases/*/verdicts/*.handoff.json`.
After T-050-41 the verdicts sit at `specs/releases/_archive/0.5.0/verdicts/…` — one level deeper, matching neither glob (`*` does not cross `/`)
— and root `specs/_archive/` no longer exists (FR6). Line 161 then classifies those same moved files as *offenders*, disqualifying any other
otherwise-valid verdict in the range. The final-`rc` PR and the ship PR cannot pass their required check; the release cannot ship. No write set
names `.github/**`.
**Bug history:** third firing of the class the script documents at `:24-32` — `verdict-gate-cannot-resolve-evidence-after-release-archive`
(HIGH, T-044-50) after the `ACTIVE.md`-pointer variant. Both prior fixes patched the resolution shape, never derived it from the canon.
**Amendment A-1:** give the CI evidence contract an owning FR (extend FR1) with `.github/scripts/pr-verdict-check.sh`, `.github/workflows/ci.yml`
and `core/specs_version.py` (`RELEASE_SEMVER_RE`: bare vs `v`-prefixed) in its write set; canon v6 must **name** `verdicts/` and `reviews/` as
conformant release-directory members; add **V20** — run the gate script against a v6 fixture tree (live, `_ideas/`, `_archive/`) proving it
resolves and refuses correctly, before T-050-41. Whatever replaces `_RELEASE_ID_RE` stays fail-closed: still refuse `_archive`, `_ideas` and
any traversal shape before interpolation.

### S-2 · HIGH · CWE-778 — three new governance artifacts are gitignored; `.gitignore` is in no write set
**Where:** `.gitignore:106-141` (the `/specs/*` catch-all "privacy backstop" + per-artifact opt-in) × FR13 (`FINDINGS.jsonl`),
FR19 (`specs/ADRs/**`), FR5 (`backlog_histo.jsonl`).
**Evidence (`git check-ignore -q`, verified):** `specs/audits/<slug>/FINDINGS.jsonl`, `specs/ADRs/0001-x.md`, `specs/ADRs/AGENTS.md` and
`specs/backlog/_archive/backlog_histo.jsonl` are all **IGNORED** (`BUGS.jsonl`, `RELEASE.jsonl`, `releases_histo.jsonl`, `bugs_histo.jsonl`,
`AUDIT.md` are tracked). Security consequence beyond governance vacuity: an untracked `FINDINGS.jsonl` never reaches a PR, is never reviewed,
and is **never seen by the range-scoped denylist scan** — audit evidence escapes the boundary both ways. `grep -n gitignore` over the three
files returns only §1.1 prose.
**Bug history:** §1.1 names this class with eight bug ids and four recurrences; `.gitignore:152-160` records that the catch-all-plus-opt-in
shape *was itself the defect* and was already inverted once, for `specs/releases/**`. This release re-enters the defective shape.
**Amendment A-2:** own `.gitignore` in FR1; apply the proven inversion to each new area (`!/specs/audits/**`, `!/specs/ADRs/**`,
`!/specs/bugs/_archive/**`, `!/specs/backlog/_archive/**`, only the narrow scratch class denied); delete the stanzas FR1/FR6 orphan
(`specs/assets/`, `specs/backlog/remote-bugs/`, `specs/_archive/`); add **V21** — a contract test asserting `git check-ignore` reports
"not ignored" for every canon path. State the widening as the deliberate privacy decision it is.

### S-3 · HIGH · CWE-532 — FR2 replaces the model carrying the write-time redaction seam and never mentions it
**Where:** FR2 (`BugEvent` → `BugRecord`; "a governance update rewrites that record's line in place") × `core/models/bugs.py:204`
(`_OPTIONAL_STR_FIELDS`), `:232` (`redact_text`), `:302` (`redact`) × `features/bugs/service.py:93`
(`append_event(event.redact(self._denylist_terms))`).
**Evidence:** `grep -n 'redact\|denylist\|privacy'` over the three files returns zero hits inside FR2/FR3 — the seam is invisible to the
release replacing it. It is one day old (`eb03d01b`, T-045-19) and its docstring states why the field set must be schema-derived: a hand-kept
list "twice missed a newly added free-text field" (T-043-23 → T-044-62). FR2 adds four free-text fields at once (`cause`, `root_cause`,
`solution`, `migration_note`) **and** a second write path (in-place line rewrite) that no acceptance routes through redaction.
**Amendment A-3:** add **A2.6** — the redaction field set derives from `bug-record-v1.schema.json` (one source); the in-place
update seam redacts identically to the append seam; a contract test adds a new free-text property to the schema fixture and
proves it is scrubbed with **no** code list edited.

### S-4 · HIGH · CWE-212 / CWE-532 — FR3 copies historical prose into the live ledger unredacted, on a path that voids the scan amnesty
**Where:** FR3 step 6 ("`cause` is copied from the v5 `evidence_diff`/`notes`") × T-050-10 ×
`features/chokepoints/denylist_scan.py#_first_match` (amnesty) × `infrastructure/git_objects.py:501,719` (`prior_text` resolved
**per path**; `None` ⇒ never suppress).
**Evidence:** (a) the migration writes `BUGS.jsonl` directly, not through the service seam, so 490 records of copied prose get no redaction;
(b) operator-**denylist**-term scrubbing at write time began only yesterday (`eb03d01b`), so the whole 1 005-event history predates it and
denylisted terms may sit in `notes`/`evidence_diff` today; (c) `bugs.jsonl` → `BUGS.jsonl` is a **rename**, so the new path has no prior text
and the v0.11.0 amnesty suppresses nothing — every historical value is re-flagged as new, and the first push after T-050-10 is expected to be
refused wholesale, with no stated procedure and a standing "no `--no-verify`, ever" rule. A3.5 checks *fabrication* only, never redaction.
**Amendment A-4:** FR3 routes every migrated free-text value through the A-3 seam with operator terms loaded; the migration report records
counts only, never values; add **V22** — run `dadaia ci push-gate-check` over the migration range *before* the push, remediating any hit at
the source record, never by bypassing the hook.

### S-5 · HIGH · CWE-636 — "the fail-closed runner is deleted" is ambiguous across two scripts that share it
**Where:** FR9 / D9 × T-050-18 write set (both scripts) × `pre-commit-presence-gate.sh` and `pre-push-ci-gate.sh` (identical `resolve_runner`
+ `exit 1`: "None found → fail CLOSED … never silently skip the gate").
**Evidence:** D9 attaches the deletion to the pre-commit bullet, but T-050-18 edits both files and repeats the sentence without a subject.
A fail-open pre-push runner means a machine without the venv pushes with **no branch policy and no denylist scan**, silently — the exact
boundary D9 says it preserves.
**Amendment A-5:** FR9 states that `pre-push-ci-gate.sh` keeps its fail-closed runner resolution (exit 1, message, never skip);
A9.2 gains a third fixture — runner unresolvable ⇒ push **refused**. Only pre-commit may become unconditionally exit 0.

### S-6 · MEDIUM · CWE-693 — FR6: local-only reachability proof, deleted verdict evidence, no scan-refusal path
**Where:** FR6 A6.1-A6.5 / D-H × T-050-14 × `features/chokepoints/service.py:15,639,702` (tags **are** scanned; tags bypass
branch policy).
**Evidence:** (i) A6.4 proves reachability with a **local** `git show <tag>:…`, which passes on a tag that never reached the remote — the
recovery story for an irreversible deletion rests on an unproven premise; (ii) root `specs/_archive/releases/*/verdicts/**` holds every past
security approval and is deleted with no relocation (A6.2 gates only on the FR3/FR4 back-fills; see S-1); (iii) the SPEC is silent on the tag
push being **refused by the denylist scan**, which it can be.
**Amendment A-6:** A6.1 verifies remote reachability (`git ls-remote --tags`, then fetch into a throwaway clone and `git show`
from *that* clone); A6.2 adds "historical `verdicts/**` relocated and the CI gate proven against it (V20)"; new **A6.6** defines
the refusal path — stop, redact at the source object, re-tag; never `--no-verify`, never disable the scan.

### S-7 · MEDIUM · CWE-284 — mutable fields on an ADDITIVE class: the SPEC implies prevention where only detection exists
**Where:** FR2 A2.2 ("cannot be changed … through the service seam") × `gate_policy.py:49,231` (`specs/bugs/` is ADDITIVE —
always writable, any mode, any session) × `install_helpers.py:42` (a persona `write_allowlist` is parsed at **projection** time;
it is documentation, not a write-time control).
**Evidence:** any session can rewrite `id`, `ts`, `symptom` or `root_cause` with a file tool and no mechanism objects. The event
model made this structurally impossible; the record model trades that away and the SPEC does not say so.
**Amendment A-7:** rewrite A2.2 to state the loss honestly — core-field immutability holds at the service seam and is otherwise **detected**,
never prevented — and add **A2.7**: a `specs doctor` WARN comparing each record's immutable core against FR3's first-add derivation (which
already exists; no new engine), plus pillar 1 reporting any in-window core-field diff.

### S-8 · MEDIUM · CWE-269 — FR14 has `project-auditor` write the bug ledger, contradicting FR13's own allowlist
**Where:** FR14 pillar 1 ("On each record reviewed it sets `audited: <audit-slug>`") × FR13 A13.2 ("gains `specs/audits/**` and
**nothing else**") × T-050-26 write set (no `specs/bugs/BUGS.jsonl`).
**Evidence:** the auditor must mutate the bug ledger to do pillar 1, which the same release forbids it; the gate allows it
(ADDITIVE), so the contradiction resolves silently toward the wider access. A13.2's fixture ("a write elsewhere under `specs/` is
still refused") is unfulfillable as stated — nothing refuses a persona's write to an ADDITIVE path.
**Amendment A-8:** decide explicitly — the `audited` marker written by the implementer through the bugs service seam (preferred: keeps the
auditor read-only over `specs/bugs/` and the write redacted per A-3), or the allowlist widened to that one field with T-050-26's write set
saying so. Retarget A13.2 at what holds: `specs/audits/_archive/` is **FROZEN** (`gate_policy.py:64`, matched before ADDITIVE) and stays
FROZEN for the auditor — the archive move is a `git mv`, outside the file-tool envelope.

### S-9 · MEDIUM · CWE-532 — `FINDINGS.jsonl.evidence` quotes commands and output with redaction as discipline only
**Where:** FR13 (`evidence` = "the command + the observed output, redacted") × D15 (the auditor writes with file tools — no CLI
verb, so no seam can redact) × S-2 (gitignored, so the push scan never sees it either).
**Evidence:** pillar-3 `Measured by:` runs (`lint-imports`, `pytest`, ratchet checks) emit runner-absolute paths routinely;
pillar 1 quotes `git show` diffs. Nothing mechanical stands between that output and a permanently committed file.
**Amendment A-9:** add **A13.5** — before the `S3` QA close the audit folder is scanned by the same detector the push uses
(`ci push-gate-check` over the range, or a `specs doctor` WARN reusing `features/chokepoints/denylist_scan`); raw `Measured by:` output is
captured under `.dadaia/tmp/**` and cited by path in `evidence`, never pasted. Same rule for the FR3 migration report.

### S-10 · MEDIUM · CWE-359 — `RELEASE.jsonl` publishes `session_id` into a permanently committed file
**Where:** FR4 record shape `{ts, event, agent, session_id, data}` and its four examples.
**Evidence (answers Q3):** the `data` payloads are clean — `sha`, `pr`, `tag`, `rc`, `audit` only; no PR titles, no author names,
no e-mails; the back-fill takes `sha`/`pr` from `CLOSURE.md` tables and `null` otherwise (A4.3), the right posture. The
**envelope** is the problem: a harness session id today lives only in `.dadaia/sessions/` (PROTECTED, §3) and in allowlist-gated
telemetry; committing it links every governance milestone to a local session identifier forever.
**Amendment A-10:** drop `session_id` from the committed envelope, or constrain it in the schema to a truncated opaque token with
a stated non-linkability rationale, and add it to A-3's scrub scope. The examples (`s-9f1c`) suggest the truncated form was
intended — make it a constraint, not a sample.

### S-11 · MEDIUM · CWE-693 — FR6/A6.3 does not enumerate the new FROZEN set
**Where:** A6.3 ("FROZEN … repointed to the per-area `*/_archive/` paths") × `gate_policy.py:63-65` (today: `backlog/`, `audits/`, `bugs/`
`_archive/`) and `:73` (`_FROZEN_PREFIX = "specs/_archive/"`).
**Evidence:** the new archive home `specs/releases/_archive/` is in neither list. Deleting the root prefix without adding it leaves every
archived release **MUTATING** — freely rewritable in IMPLEMENTATION mode. A net integrity loss versus today.
**Amendment A-11:** enumerate the post-v6 FROZEN set in A6.3 — `specs/releases/_archive/`, `specs/bugs/_archive/`,
`specs/backlog/_archive/`, `specs/audits/_archive/` — one fixture per path, and state that `_ideas/` stays MUTATING deliberately.

### S-12 · LOW · CWE-1053 — the secret-scan lane never covers the edge where the migrated ledger lands
**Where:** `.github/workflows/secret-scan.yml` (`push: main`, `hotfix/v*`; `pull_request: [main]`). `hotfix/*` is retired (§4) and `main` is
never pushed directly, so gitleaks effectively runs once per release, on the ship PR. The 490 migrated records and the first audit folder
reach `develop` at `rc-1` with only the privacy denylist scan, which is not a secret scanner.
**Amendment A-12:** extend the trigger to PRs targeting `develop` (same FR as A-1), or state the limit in FR9's acceptance so
"publication boundary intact" is not read as "secrets scanned at `rc-1`".

### S-13 · LOW — verdict tasks never name the path and field the gate keys on
**Where:** T-050-02/36/37/42/43 ("the verdict handoffs") × `pr-verdict-check.sh:112,119-131`, which requires
`specs/releases/<release-id>/verdicts/<sha>.handoff.json` with `agent="security-reviewer"`, `verdict="APPROVED"` and a **40-hex**
`metrics.commit_sha` (a branch name or short sha is skipped).
**Amendment A-13:** name the exact path and the 40-hex rule in every verdict task's write set and done-criterion.

### S-14 · INFO — the definition text itself is clean
Scanned all three files for home-absolute paths, e-mail literals, IPv4 literals and external URLs: **zero hits**. Sample records use
synthetic shas and a synthetic session token; no secret or key; ADR references are bibliographic (Nygard 2011, MADR 4), no URL to rot.
The no-private-data standing rule sits in both SPEC §3 and TASKS §47 — keep it: these examples are copied verbatim into skills at FR7/FR12/FR14.

## 3. The commissioned questions, answered

| # | Question | Answer |
|---|---|---|
| 1 | Hooks de-slop (FR9) | The denylist scan and the `develop`/`main` refusal are **not** weakened (A9.2 pins both). Removing the pre-commit blockers opens **no** new publication path — commits are local, `push-gate-check` is range-scoped over the objects a push publishes. CI keeps `backlog-doctor` (`ci.yml:418`) and `security-verdict-gate` (`ci.yml:503`), which FR9 declares untouched. **Caveat: S-5.** |
| 2 | Ledger rewrite (FR3) | Copied prose is **not** re-redacted; the rename voids the amnesty; pre-`eb03d01b` denylisted terms can surface into the live ledger; the report is discipline-redacted only. **S-4, S-3, S-9.** |
| 3 | Milestone shas (FR4, D-G) | Clean — shas, PR numbers, tags, `rc`/audit ids only; no PR titles, no author e-mails; `null` never guessed. One exception: the committed `session_id`. **S-10.** |
| 4 | Destructive step (FR6) | Operator-present: yes. Tag before deletion: stated — but the reachability proof is local-only, the tag push's own scan-refusal path is undefined, and historical verdict evidence is deleted with no relocation. **S-6**, consequence in **S-1**. |
| 5 | Audits (FR13/14) | No write-time redaction rule for `evidence` (**S-9**); the allowlist contradicts FR14 (**S-8**); `specs/audits/_archive` **does** stay FROZEN (`gate_policy.py:64`) — state it in the SPEC. |
| 6 | ADRs (FR19/20) | A path exists: `specs/ADRs/**` is MUTATING, so any agent in IMPLEMENTATION mode can write `Status: accepted`. Discipline is acceptable per D15 — but A19.3 is **not honest about the detector**: pillar 3 cannot detect an *agent-written* `accepted`, because commit identity is shared (§7 carries "de-personalising the git commit identity" as open). It can only detect the *pairing* rule (a Part-1 hunk with no accepted ADR in the commit). **Amendment A-14:** restate A19.3 to claim the pairing detection only and record attribution as a named limitation. |
| 7 | Mutable fields on ADDITIVE (FR2) | Yes — any session can mutate immutable core fields undetected, and A2.2 reads as prevention. **S-7**, with the detector to add. |
| 8 | Anything else | **S-1, S-2, S-11, S-12, S-13**; examples and sample records clean (**S-14**). |

## 4. Verdict

**REJECTED** for the definition stage (definition-stage verdict; not a push verdict, no `commit_sha`).

Bug-surface direction, per the standing order: the release's *intent* reduces it — deleting the event fold (the U+2028 silent-loss
family), two hook blocks, BL-DUP and the prose regexes is real structural simplification with named bug-history evidence. As written it
**increases** the security surface in three ways the bug history already punished: it re-enters the gitignore shape that fired four times
(S-2), re-breaks the verdict gate that already broke twice on release-archive moves (S-1), and replaces a redaction seam installed one day ago
to close a defect that fired twice (S-3). One cause, three instances: a canon change landing without its dependent boundary.

### Required amendments, in order

1. **A-1** (S-1) — own the CI evidence contract; canon names `verdicts/`/`reviews/`; V20 before T-050-41.
2. **A-2** (S-2) — own `.gitignore`; invert the shape for the new areas; V21 `check-ignore` contract.
3. **A-3** (S-3) — schema-derived redaction for `BugRecord`, on both write paths, with its test.
4. **A-4** (S-4) — redact migrated prose through that seam; V22 scans the migration range pre-push.
5. **A-5** (S-5) — pre-push keeps its fail-closed runner; third fixture proving refusal.
6. **A-6** (S-6) — remote reachability proof, verdict relocation, scan-refusal path (A6.6).
7. **A-7** (S-7) — A2.2 states detection, not prevention; add the core-vs-first-add doctor WARN.
8. **A-8** (S-8) — resolve the `audited`-write contradiction; retarget A13.2 at FROZEN.
9. **A-9** (S-9) — scan the audit folder and the migration report with the push detector.
10. **A-10** (S-10) — drop or constrain `session_id` in the committed envelope.
11. **A-11** (S-11) — enumerate the post-v6 FROZEN set, one fixture per path.
12. **A-14** (Q6) — A19.3 claims the pairing detection only; record the attribution limit. · **A-12** (S-12) · **A-13** (S-13) — secret-scan coverage stated or extended; verdict path named.

Amendments 1-6 are blocking. Re-review the amended trio before approval; this verdict is superseded only by a fresh review of the revised text.
