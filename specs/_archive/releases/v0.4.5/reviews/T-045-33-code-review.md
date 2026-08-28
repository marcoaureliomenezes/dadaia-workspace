# T-045-33 — release code review, v0.4.5

**Author:** code-reviewer, 2026-08-26
**Governs:** TASKS.md T-045-33 (six-axis review on the thawed tree)
**Target:** branch `feature/0.4.5`, HEAD `b207c20d`; base `68658783` (ship 0.4.4)
**Attribution range:** `135a768d..HEAD`, release task commits only
**Method:** every number below was re-measured by this reviewer (`git diff --numstat`,
`ast` walks, executed-path probes on the installed venv). Nothing is taken on report.

## Verdict

**REQUEST-CHANGES** — one HIGH finding (F1: FR7 silently destroys legitimate whitespace in
every bug-event free-text field, on the executed path, untested, 8.2% historical base
rate). Everything else is sound and, in most surfaces, materially better than what it
replaced. F1 is a contained rework inside S3's own seam — not a redesign.
## 1. CI status

`dadaia ci preflight` at `b207c20d` — **exit 0**: `ruff format --check`, `ruff check`,
`mypy --strict`, `lint-imports`, `pytest` all `[PASS]`. Run by me, unpiped.
`dadaia bugs stats`: total 493, `status:open 1` (`windows-xdist-workers-crash-on-unit-fast-tier`,
LOW, left open by the AS-5 verdict — never closed by a quarantine). A16.3/A16.4 and the
test delta re-measured independently, reproducing T-045-32 exactly: V10 `+464/−426 = +38`,
V11 `+213/−251 = −38`, tests `+2749/−980 = +1769`.
## 2. Question 1 — did FR1 leave the gate feature smaller?

**Yes, on every axis measured.** `features/spec_context/gate_policy.py`, AST-measured at
`68658783` vs HEAD:

| metric | before | after | delta |
|---|---:|---:|---:|
| total lines | 390 | 389 | −1 |
| non-comment code lines | 263 | 262 | −1 |
| branch nodes (`If`/`For`/`While`/`IfExp`/`BoolOp`/`Try`) | 43 | 42 | **−1** |
| `return` statements | 40 | 39 | −1 |
| functions | 12 | 12 | 0 |

`hooks/` over the same range: `_common.py` −11 (the FR2 writer deletion), no other hook
file touched. Combined `gate_policy.py` + `hooks/`: **8 insertions, 20 deletions**.

The shape matters more than the count. `_is_law_path` **loses a parameter** (`ctx_rel`)
and the branch that shadowed the floor (`if ctx_rel is not None: return ctx_rel in
_LAW_BASENAMES`); `classify_path` hoists the LAW test above the context computation. What
remains is a pure string predicate with **zero I/O** — no manifest read, no filesystem
stat — so A1.7 (CWE-284: a manifest edit can never demote a floored LAW path) holds by
construction rather than by a guard. One decision path replaced two. A1.4 is met.

Recorded divergence: SPEC FR1 describes an additive manifest arm; the landed fix has **no
manifest arm at all** — simpler and safer than specified, with A1.3's contract test still
enumerating the manifest. Not a finding; one CLOSURE line.
## 3. Question 2 — did the four demolitions land as expand → switch → contract?

**Three of four cleanly; FR2 with one deviation at the contract step (F4, LOW).**

**FR2 (atomic write)** — verified per-commit by numstat, in strict `git log` order:

| phase | commit(s) | production diff |
|---|---|---|
| expand | `740ceecb` | `core/atomic_write.py` +75/−0 — **nothing deleted, no call site moved** |
| switch | `c6294ede` hooks · `10b41e27` infra · `bdc29f93` migrate · `83621574` specs+spec_context · `59fa0516` import_ · `04f5d0a3` docstring | disjoint module families, one per commit; **no writer deleted in any of them** |
| contract | `091b2401` | 19 production files: all 13 writers + shims deleted, census landed, characterization test deleted (`test_migration_symlink_hardening.py` +17/−386) |

Each intermediate records its own scoped green run in its message; the QA closes re-ran the
cited suites independently and preflight is green at HEAD. The expand commit is
additive-only and the switch commits delete nothing, so every intermediate tree is
compilable and independently testable by inspection — the property D7 exists to buy.
**Not a big-bang.** Post-demolition dead-code sweep by me: zero occurrences of
`atomic_write_text` / `write_text_atomic` / `_atomic_write_json` / `_atomic_write_bytes`
outside `core/atomic_write.py`; zero inline `.tmp` writers outside it; `ruff check` clean.

**FR3/FR4/FR5 (test-only)** — `053f55e8`, `78daad25`, `c4ba5383`: each self-contained,
adding the derived source before or with the hand-kept thing it replaces, touching zero
production files. For a test-only consolidation expand and switch collapse legitimately.

**FR6 (`eb03d01b` → `0cb08157`) and FR12 (`5c4f30c9` → `d85dfc19`)** — implement-then-amend
after an architect firing, amendment applied **before** the `[x]` flip in both (commit
order confirms). FR6's amendment is itself a demolition: the CLI's duplicate redaction pass
deleted, an 11-field hand-kept kwarg list replaced by iteration over the schema tuple.
## 4. Question 3 — FR7's +41 production lines: logic or prose?

**39 prose, 2 logic.** `2b9b30c1` production diff is `+46/−5 = +41`:

| file | added | comment/docstring | logic |
|---|---:|---:|---:|
| `core/models/bugs.py` | 31 (−4) | 27 + 1 blank | **2** |
| `infrastructure/jsonl_bug_store.py` | 15 (−1) | 14 | 1 (replaces 1) |

The two added logic lines are `core/models/bugs.py:248` (the `_UNSAFE_FORMAT_CHARS_RE`
module constant) and `:272` (`out = _UNSAFE_FORMAT_CHARS_RE.sub("", text)` at the head of
`redact_text`). `infrastructure/jsonl_bug_store.py:89` is an in-place swap
(`text.splitlines()` → `text.split("\n")`), net zero. **No new function, no new call site,
no new branch, no new field list** — the "net-neutral" claim about the *logic direction* is
substantively accurate. The *label* is not (F2), and the prose weight is extreme: a 17-line
`#:` block for a one-line regex (F10). And the logic that was added is wrong in one
respect — F1.
## 5. Findings

### F1 · **HIGH** · security/correctness · `dadaia_workspace/core/models/bugs.py:248,272`

The strip class (`\x00`–`\x1f` plus `\x85`, U+2028, U+2029) includes **TAB (0x09), LF
(0x0A) and CR (0x0D)**, and it **deletes** rather than separates. Every free-text field of
every future bug event is therefore word-joined. Probed on the executed path against the
installed venv: `redact_text("step one\nstep two\ttabbed")` returns
`'step onestep twotabbed'`. `BugService.append_event` (`features/bugs/service.py:93`)
routes every field through `BugEvent.redact` → `redact_text`, so this is the live write
path, not a corner.

- **Base rate:** 83 of 1012 events already in `specs/bugs/bugs.jsonl` (**8.2%**) carry an
  embedded LF or TAB in a free-text field (`expected`, `notes`, `repro`, …). The regression
  fires on the next such append, silently, with the CLI still printing `[ok] appended`.
- **Fields affected include `evidence_red_loop` / `evidence_regression_seam` / `repro`** —
  the exact evidence the FR23 gate consumes. A multi-line reproduction command becomes a
  concatenated string that still *looks* like a command.
- **Not required by the fix's own goal.** `json.dumps` already escapes the whole C0 range,
  so a C0 byte can never fragment a JSONL line; only `\x85`/U+2028/U+2029 pass through raw
  — precisely the fragmentation hazard. The render hazard (CWE-117) is the ESC family, not
  TAB/LF. Deleting the whitespace controls buys nothing and costs fidelity; pre-FR7 they
  round-tripped intact.
- **Zero test coverage.** `tests/unit/features/bugs/test_control_format_char_sanitation.py`
  (176 lines) has no newline or tab case at all — invisible to the suite, which is why S3's
  close, correctly against A7.1–A7.6 as written, reports GREEN.

**Fix direction (no code here).** Keep the one pass at the one seam; do not add a second
guard. Map the whitespace controls (`\t`, `\n`, `\r`) to a single space and delete the rest,
or narrow the delete class to the fragment+render hazard set. Either way the re-join
property A7.6 depends on is preserved for the ESC/U+2028 case, which is what the docstring's
deletion rationale actually argues for. Land the RED test first: a multi-line `--repro` must
keep its word boundaries through `append_event`. **Register the bug** before the fix
(proposed slug `bug-event-sanitation-deletes-legitimate-whitespace`, MEDIUM-to-HIGH, surface
`core/models/bugs.py`) — I did not append the event myself because this task's write set is
one file; the implementing agent owns the registration.

### F2 · **MEDIUM** · process/evidence · `specs/bugs/bugs.jsonl` (resolved event, `2b9b30c1`)

The `resolved` event for `bug-event-field-with-unicode-line-separator-silently-drops-the-event`
records `evidence_diff: "net-neutral: …"` for a commit measuring `+46/−5 = +41` production
LOC. Firings 1–3 routed `+17`, `+52` and `+59` diffs to `software-architect` before commit;
this one was not routed, and the label is what suppressed it. The claim's *substance*
survives scrutiny (§4) and T-045-32 flagged the discrepancy honestly — but `evidence_diff`
is the field the FR23 gate reads, and an architect firing here is the most likely place F1
would have been caught. Fix direction: restate as `net-positive: +41 (39 doc, 2 logic)`
with the direction argument intact, and route the F1 rework through FR23.

### F3 · **MEDIUM** · bug-surface · stale-citation class, no structural close

Third instance in two releases: `t044-04-renumber-stale-DADAIAmd-section-citations`,
`dadaia-task-manager-stale-workspace-protocol-citation` (S1, `db9d0c20`), and now
`ai-engineer.md` §5→§8 (FR14, `af7bd369`). Each fixed by hand, each detected after the fact
by the same enforcer (`tests/contract/test_rules_skills_map.py`). A third instance on one
class is the structural signal, not a third incident. FR14's scope was correctly the
instance, not the class — so this surface's honest verdict is **unchanged**, and the class
belongs in the PM's intake. Fix direction: named anchors or citation derivation, later.

### F4 · **LOW** · patterns · `091b2401`

The contract commit also *switches* 12 call sites no switch commit had touched
(`install_helpers`, five `json_*_store` modules, `public_assets`, `workspace_guardrail`,
`agent_tier_frontmatter`, `bugs_single_file`, `retired_frontmatter_keys`, `state_v3`) —
including the two writers the scan discovered beyond the TASKS enumeration. They went from
old-name to deleted-name in one step, with no independently-green switch-only intermediate.
Each is a mechanical call swap and that commit's full-suite run is green, so no harm is
evidenced; recorded because D7's guarantee is per-site.

### F5 · **LOW** · tests (P1 class) · `tests/unit/features/spec_context/test_dadaia_references_lifecycle_sanction.py:35`

Imports the private module `dadaia_workspace.cli._specs_resolution`. Justified in the
docstring (it is the real function behind `context bind`/`show` no-arg resolution), but it
couples a contract test to a leading-underscore module. Fix: promote the seam, or assert
through the public CLI entry.

### F6 · **LOW** · tests/perf · `tests/integration/infrastructure/test_live_bugs_ledger_still_parses.py:26`

Binds a permanent test to live mutable repo state (the whole 1012-row
`specs/bugs/bugs.jsonl`), re-parsed every run and growing with every append — the same class
as `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` (registered at the
S4 close, fixed in `aea57a34`): an oracle made of live state concurrent ADDITIVE writes are
entitled to change. A7.4 needed one live proof. It reads only and carries a vacuity check, so
nothing is broken today. Fix: record the demotion decision at CLOSURE.

### F7 · **INFO** · `tests/helpers/scan_population.py:29`

Docstring prose says "20 files / 21 call sites"; the module's own enumeration below lists
19 files / 20 call sites. Recorded by the S2 close (§6 item 2), still unfixed at HEAD.

### F8 · **INFO** · `specs/releases/v0.4.5/SPEC.md` (FR13)

SPEC names **four** over-ceiling personas; at HEAD there are **five** (`product-engineer`
277, `qa-engineer` 267, `ai-engineer` 250, `software-architect` 248, `software-engineer` 243
— the last omitted from SPEC and TASKS). Fleet 2170 → 2077 source lines (−93), so A13.1
holds; V9 is 5 → 5. Admissible under AS-1/A13.4, but each residual needs naming in CLOSURE
and SPEC's "four" needs operator/PM reconciliation. Same posture for the three missed S4
targets (V6 20502 vs ≤3.5k; V7 257 vs ≤60; V8 877.8 vs ≤700) — honest, measured misses with
recorded reasons, none redefined, all needing an operator ruling at closure.

### F9 · **INFO** · `dadaia_workspace/features/certification/service.py:181`

FR23 Firing 1's own LOW residual is still live: the marker-mismatch branch embeds
`exec_proc.stdout[:200]!r` instead of routing through `_codex_capped_detail`
(`service.py:87`) — capped but unredacted, the same CWE-532 class the S1 fix closed on the
other two branches. One line, when the file is next touched.

### F10 · **INFO** · `dadaia_workspace/core/models/bugs.py:230–247`

17 comment lines plus 10 docstring lines for 2 lines of logic. The prose is high quality and
load-bearing, but a 20:1 ratio is where a gap like F1 hides in plain sight: the block argues
at length for *deleting rather than escaping* and never asks which characters deletion is
safe for.
## 6. Bug-surface delta (FR24) — per touched feature

| Surface | Verdict | Ledger evidence |
|---|---|---|
| gate / `spec_context.gate_policy` | **reduced** | 2 open MEDIUMs (`sdd-gate-blocks-fresh-repo-root-agents-md`, `repo-agents-md-law-gate-contradicts-template`) → 0, one shared cause; third bug on this classifier historically (`gate-fpath-not-canonicalized-before-classifier`). −1 branch, zero I/O, manifest-enumerating contract test added |
| atomic write / `core` | **reduced** | 13 divergent writers → 1; 2 of 13 leaked temp on injected `os.replace` failure (`two-atomic-writers-leak-temp-file…`, superseded). AST-shape census makes a 14th fail loud; the leak class is structurally impossible |
| bugs ledger — core (`redact_text`) | **increased** | Two chains closed by construction: privacy-leak ×3 (write-time seam now sees the push denylist) and hand-kept-field-list (T-043-23 → T-044-62 → schema-derived scrub set, no list left to forget). But **F1 opens a new silent-data-loss lane on the same function** — net for this surface is an increase until F1 lands |
| bugs ledger — infra (`jsonl_bug_store`) | **reduced** | `splitlines()` → `split("\n")` is the reader's actual root cause and holds regardless of what any writer emits; 1012-row live-ledger parse proof, no historical event rewritten |
| bugs ledger — CLI | **reduced** | AM-1 deleted the duplicate `.redact()` pass; one masking pass, one file-reading loader (verified by grep on `load_privacy_terms`) |
| certification | **reduced** | Fix-then-bug chain (`codex-live-probe-gate-checks-presence-not-usability` → `certify-skip-detail-leaks-full-codex-output`, ~37 min apart) closed by deleting the half-seam, not stacking on it; one LOW residual (F9) |
| `.dadaia` layout / migrate | **reduced** | `doctor-whitelist-legitimizes-slop-dirs` → FR10 → `dadaia-reconcile-quarantines-sanctioned-references-clone` (reported within the hour of FR10 landing, because a second hand-kept list existed) → both lists collapsed into `core/workspace_layout.DADAIA_ALLOWED_SUBDIRS`, `+54/−54`, identity-asserted |
| specs doctor / catalog | **reduced** | FR9/INV-6 closes lane 3 of the F-1/F-12 slug-ownership class report-only, no branch on any destructive verb, `dead()` untouched; FR12's twin catalog writer now shares one curation function, F-84 pinning both written outputs |
| `specs init` / CWE-59 | **reduced** | One call-site swap onto the existing hardened resolver (`cli/commands/specs.py:328`); no second symlink check, no new refusal vocabulary |
| chokepoints / privacy | **unchanged (by design)** | A6.3 pins push-scan behaviour; the write-time seam complements, never replaces |
| public assets / agents / skills / `DADAIA.md` | **reduced** | V11 −38; the 5×-repeated NO-LOCKS restatement collapsed to one pointer, 12 duplicate blocks to pointers, all 34 coverage rows verified at their surviving home. **Except** the stale-citation class (F3): unchanged |
| tests | **reduced** | 3 hand-kept skill inventories → 1 derived oracle (killed the cause of `test-public-pipeline-stale-skill-roster` + `skill-orphan-checker-misses-disable-model-invocation`); 10-case hand-kept writer table → AST census; goldens 214→36 and 404→164 lines, policy-only; 20 vacuity guards. 1 new LOW registered and fixed in-release (`aea57a34`) |

**Release-wide.** Open bugs 8 → 1 (the AS-5 item, correctly never closed by a quarantine).
Three recurrence chains — hand-kept-field-list, `.dadaia` duplicate allowlists, atomic-writer
divergence — are now structurally unrepresentable rather than patched, which is the shape the
standing order asks for. F1 is the one place this release *added* surface.
## 7. Tests axis — +1,769 lines, more valuable per line

**Added (derived oracles, high value):** `tests/unit/core/test_atomic_write.py` (+284; the
21-case injected-failure matrix — 2 preserve-mode × 3 content-kind × 3 failure-point — landed
*before* any writer was deleted); `test_atomic_write_census.py` (+163) identifying writers
**by AST shape**, never by name, with a docstring explaining why the three legitimate
`os.replace` users are not name-excluded but simply never match the predicate;
`tests/helpers/public_asset_roster.py` (+136) delegating to the product's own
`FileSystemPublicAssetManager` enumeration; `skill_inventory_oracle.py` (+52) delegating to
that roster; `scan_population.py` (+107 doc, **2 executable lines**) as a convention, not a
harness, per the standing ruling. Plus RED proofs: gate policy (+168), write-time denylist
(+201), sanitation (+176), symlink refusal (+100), references lifecycle (+154).

**Deleted (hand-kept, low value):** the 10-case hand-authored writer table inside
`test_migration_symlink_hardening.py` (−349, 9 unrelated symlink-security tests retained);
both file-inventory byte goldens regenerated policy-only (214→36, 404→164 — a regen is no
longer where an unintended change hides); the leak characterization test, deleted in the
same commit that made leaking impossible; `test_io_encoding.py` −71; `EXPECTED_SKILLS`.

**Structure-sensitive additions (P1 class):** one private-module import (F5); one
live-state-bound permanent test (F6). No exact-string assertion on a message body, no
hand-kept inventory inside a test. Every new file declares `Intent:` and size; the one new
skip is a real `_can_symlink()` capability probe, not a `sys.platform` guess.

**Judgement: more valuable per line.** The growth is oracles derived from the product's own
enumeration plus a 21-case failure matrix; what left is exactly the hand-kept-table class
that produced four registered bugs. The one gap: the new sanitation suite tests the
characters the SPEC named and none of the characters the regex actually eats (F1).
## 8. Other axes

**Architecture.** `lint-imports` 9/9 kept, no new accepted edge, ignore cap unchanged.
`core/atomic_write.py` satisfies all six AR-1 conditions as verified on the code: no
`dadaia_workspace.*` import, no module-level mutable state, ratchet stem declared with an
AR-1-citing rationale, no surviving alias. `features → core` and `hooks → core` are legal
downward edges; the hooks-never-import-container latency law holds by construction.

**Security.** The FR6/FR7 write-seam order is correct — `redact_text` strips first
(`bugs.py:272`), then IPv4, home paths, denylist terms, so a term split by an injected ESC
re-joins before masking (A7.6 holds). FR8 reuses the existing resolver seam, adding no
second symlink check (CWE-59 closed by reuse). FR1's LAW predicate performs zero I/O, so
CWE-284 demotion-by-manifest-edit is impossible rather than guarded. The delta scans clean
for home-absolute paths, operator email and IP literals. No new third-party dependency.

**Performance.** One added regex substitution per free-text field on append — negligible.
FR1 removed a call-time computation from the LAW path. F6 is the only growth-coupled cost.

**Dead code.** None from the demolitions: zero writer shims, zero orphan inline `.tmp`
writers, zero unreferenced imports (`ruff check` clean), no commented-out block over 10
lines in the delta.
## 9. Summary

CRITICAL 0 · **HIGH 1** (F1) · MEDIUM 2 (F2, F3) · LOW 3 (F4, F5, F6) ·
INFO 4 (F7, F8, F9, F10).

## 10. Recommendation

**REQUEST-CHANGES** at commit `b207c20d`.

Blocking: **F1** only. Land the RED test and the narrowed strip class, register the bug, and
correct F2's `evidence_diff` in the same rework; then re-review. F3 is a bug-surface verdict
for the PM's intake. F4–F10 are recorded, none blocking; F8 and F9 already have homes in
CLOSURE and intake. Everything else is approved on the evidence above: FR1 left the gate
feature smaller on every axis, the demolitions landed as `expand → switch → contract` with
one recorded per-site deviation, and eleven of twelve touched surfaces reduced their bug
surface with named ledger evidence rather than "tests green".

## Re-verdict @27c3374a

**APPROVE.** F1 is closed. Re-verified by me at HEAD `27c3374a`, on the executed path.

**Arm B order correct.** `2dbc2b41` registers `bug-event-sanitation-strips-tab-lf-cr-from-free-text`
(HIGH) as an isolated one-line ledger commit; `27c3374a` carries the fix. No history rewritten.

**The fix is a narrowing in place, not an addition.** `core/models/bugs.py:255` — the class
becomes `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f` + U+2028/U+2029`]`: same one assignment,
same one `sub()` call, no new branch, function or call site. Production diff `+25/−18`, of
which 24 of 25 added lines are the rewritten `#:` block. Per-character probe against the
installed venv:

| input | result |
|---|---|
| `"a\tb\nc\rd"`, `"a b  c"` | **preserved byte-identically** |
| ESC `\x1b`, DEL `\x7f`, NUL `\x00`, C1 `\x9d`, NEL `\x85`, U+2028, U+2029 | **stripped** |

So the fragment hazard (A7.1 — the bytes `json.dumps` leaves raw) and the render hazard
(A7.2/CWE-117 — the ESC/C1 family) both stay closed, while the whitespace that carries word
boundaries round-trips. A7.6's re-join property is unaffected: the masking passes still run
after the strip.

**Tests.** `tests/unit/features/bugs/test_control_format_char_sanitation.py` +
`test_live_bugs_ledger_still_parses.py` → **13 passed** (`-p no:cacheprovider`), re-run by
me. Three new cases: TAB/LF/CR preservation, ESC/C1/NEL/LS still stripped, and a
`BugService.append_event` multi-line `repro` round-trip that also asserts the record stays
one physical JSONL line. **No new structure-sensitive test** — no private-symbol import, no
hand-kept inventory, no exact-string assert on a message body; the oracles are round-trip
identity on data each test constructs itself. `dadaia ci preflight` exit 0 at HEAD;
`dadaia bugs stats` open 1 (the AS-5 item only).

**F2 addressed.** The new `resolved` event carries `evidence_diff: net-negative: …` with the
measured figures, a RED-loop command, three named regression seams, and it explicitly names
T-045-20's prior mislabel — the append-only ledger is corrected forward rather than rewritten.

### Updated bug-surface row (FR24)

| Surface | Verdict | Ledger evidence |
|---|---|---|
| bugs ledger — core (`redact_text`) | **reduced** (was *increased*) | Privacy-leak ×3 and hand-kept-field-list (T-043-23 → T-044-62 → schema-derived scrub set) both closed by construction; the F1 lane opened by `2b9b30c1` is now closed by `27c3374a` with a RED proof, and the strip class is narrowed to exactly the two hazards it exists to close — smaller than it was at my first pass |

**Standing:** F3 (stale-citation class, no structural close) remains a PM intake item;
F4–F10 remain LOW/INFO and non-blocking. Nothing else in the release changed.

## Re-verdict @395bfb35

**APPROVE.** Six-axis quick pass on `git diff 27c3374a..395bfb35 -- dadaia_workspace/ tests/`
(prod `+30/−7` across 2 files, tests `+80`). The reviewed code is byte-identical at the
current branch tip, so this verdict binds `395bfb352a4cdefa7cbbbf06d0c1908a1af38728`.

**One seam, no allowlist, no branch.** The whole change is one regex literal inside the
existing list comprehension at `features/chokepoints/denylist_scan.py:138` —
`\b<slug>\b` → `(?<![\w-])(?<!\w\.)<slug>(?![\w-])(?!\.\w)`, `re.IGNORECASE` kept. Same
one function, same one return, no exception list, no flag, no second predicate. A4.1 (no
allowlist) stays green unmodified. `service.py` is docstring-only (`hyphen-aware` →
`whole-token`), and because `_PathMasker._segment_is_offending` and `_slug_suppressed`
still consume this *same* compiled matcher, detector-hit ⇒ masker-hit parity survives by
construction rather than by convention.

**Behaviour, probed on the executed path** (synthetic slug):

| still BLOCKS | now MISSES (the ruled trade) |
|---|---|
| bare in prose · `repos/<slug>/…` · `<slug>.` at sentence end · quoted/bracketed/comma'd · `<slug>/README` · `<slug>:8080` · `https://host/org/<slug>` · upper-case | `<slug>-x` · `x-<slug>` · `<slug>.md` · `pkg.<slug>` |

`<slug>_x`, `x<slug>` and `<slug>s` were already misses under `\b` — not new.

**The false-negative trade is acceptable at this boundary.** The ruling
(`reviews/T-045-35-foreign-slug-ruling.md` §3 option 1) states the risk explicitly and
names the compensating control: the operator-denylist layer is a case-insensitive
**substring** match and is untouched, so a genuinely private term still fires wherever it
appears, glued or not. The layer being narrowed is the auto-derived registry-slug layer —
defense in depth, not the sole control — and the pre-fix shape was blocking the release on
the library's own tracked asset basenames and its own ledger bug ids, i.e. false positives
on non-private material. Narrowing one predicate beats options 2/3, both of which the
ruling correctly rejects as reopening a smuggling path or adding a carve-out predicate.

**F11 · INFO · residual worth naming for intake.** The dotted-suffix miss class includes
**clone URLs** — `https://host/org/<slug>.git` and `git@host:org/<slug>.git` both go from
BLOCK to MISS, while the same URL without `.git` still blocks. That is the highest-value
instance of the `<slug>.ext` trade the ruling names in the abstract (`<slug>.md`,
`acme-prod.tf`) without calling out this shape. Within the ruled trade, not a new decision;
routed to the PM's intake, not reworked here.

**Tests.** `tests/unit/features/chokepoints/` → **108 passed** (`-p no:cacheprovider`),
re-run by me; `dadaia ci preflight` exit 0; `dadaia bugs stats` open 1 (the AS-5 item only).
The +5 cases use the synthetic `zz-fake-context-name` throughout — **no real slug enters the
tree**. Two negatives (hyphen-glued basename + bug id; `pkg.<slug>`) and three positive
controls (bare prose, sentence-end dot, `repos/<slug>/`). **No structure-sensitive test
added**: public API (`scan_objects`, `compile_slug_patterns`), no private-symbol import, no
hand-kept inventory, oracles are hit-count and the pre-existing `source_layer` discriminator
on data each test constructs itself. Every case declares `Intent: CONTRACT`.

### Updated bug-surface row (FR24)

| Surface | Verdict | Ledger evidence |
|---|---|---|
| chokepoints / privacy push gate | **reduced** (was *unchanged by design*) | `push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings` (HIGH, `e34f1209` → `395bfb35`) closed by narrowing the one predicate — the first fix on this surface to touch the matcher rather than edit the offending text (the ruling's forensic: 10 of the P3 class fixed by RELOCATE, none structural except `new-branch-push-loses-prior-published-denylist-amnesty`, which also deleted rather than added). The slug-in-identifier sub-class is closed permanently with zero new code paths; A6.3's push-scan-unchanged pin still holds for the operator-term layer, which this fix does not touch |

**Standing:** F3 remains a PM intake item; F4–F10 remain LOW/INFO; F11 joins intake. The
release verdict is **APPROVE at `395bfb35`**.
