# FR23 firings — v0.4.5 net-positive-diff rulings

**Ledger owner:** software-architect. One section per FR23 firing (net-positive diff on a
bug fix routed to architecture review before commit), mirroring the v0.4.4 S5-FR23
pattern. Verdicts: **SOUND** (commit proceeds with `--evidence-diff`) / **UNSOUND**
(structural alternative named, engineer re-implements).

---

## Firing 1 — T-045-07 — SOUND

**Bug:** `certify-skip-detail-leaks-full-codex-output` (LOW, CWE-532, privacy)
**Surface:** `dadaia_workspace/features/certification/service.py` — codex-live-probe
SKIP/FAIL detail rendered by `certify --json`
**Measured diff:** service.py +38/−21 = **net +17**, after three minimization passes
(+58 → +40 → +25 → +17). New test suite:
`tests/unit/features/certification/test_service_codex_detail_redaction.py` (4 tests,
RED before / GREEN after). Suite 2788 passed, preflight green, self-scan 5/5
(dispatcher-attested; this reviewer is shell-less and verified the tree state by
direct read).

### The case

Both failure branches of `_codex_live_probe_detail` embedded the raw captured
`codex exec` blob — upstream banner including `workdir:` and `session id:` lines —
into the `detail` field `certify --json` renders. Root cause was structural, not a
missing cap: the SKIP classifier's phrase branch returned `output.strip()` (the whole
blob) and the FAIL branch embedded raw `combined` with **zero parsing** — there was no
seam at all that produced a bounded, content-safe detail. The fix replaces the old
half-seam `_codex_environment_unavailable_reason` (classification only, no detail
discipline) with `_codex_probe_outcome(output, cwd) -> (environment_unavailable,
detail)` — one pass that classifies SKIP-vs-FAIL **and** produces the bounded detail
for both branches — plus `_codex_capped_detail(text, cwd)` routing every detail
through the existing `core.redaction.Redactor` primitive, capped at
`_CODEX_DETAIL_MAX_LEN = 200`.

Problem/prior-art trail (architect-core-workflow): the core problem is preventing any
captured upstream byte from reaching a rendered diagnostic field; the surveyed prior
art is internal — the workspace already owns exactly one masking primitive
(`core/redaction.py`, consumed by the CLI's ContextRedactor and the chokepoints
denylist gate). Reusing it was the correct simplest candidate; inventing a second
redaction algorithm would itself have been a finding.

### Bug-history audit (standing order: permanent architecture review)

Three prior resolved bugs touch `features/certification`:

1. `certify-workflow-checks-predate-v023-gate-contract` (2026-07-16, HIGH) — checks
   rewritten to the honest-block contract; different sub-surface, no recurrence.
2. `codex-live-probe-gate-checks-presence-not-usability` (2026-08-23, MEDIUM,
   v0.4.4) — introduced `_codex_environment_unavailable_reason`. Its classification
   was correct, but its phrase branch returned `output.strip()` — the exact defect the
   present bug reports. **The current bug appeared in the same surface within hours of
   that fix.** Per the standing order this repetition marks the v0.4.4 seam as
   under-structured on its detail axis: classification was seamed, detail rendering
   was not.
3. The present fix does not stack a third layer on that chain — it **deletes and
   replaces** the under-structured seam. Grep confirms zero production references to
   `_codex_environment_unavailable_reason` remain (only historical mentions in
   `specs/bugs/bugs.jsonl` and the new test's docstring describing the pre-fix state).

### The four questions

**1. Is the +17 net structural, or a puxadinho?** Structural. The added lines are
logic that genuinely did not exist: (a) FAIL-branch parsing — before, raw `combined`
was embedded with no parsing whatsoever; (b) routing through the existing redaction
primitive; (c) the non-content byte-count fallback for unparseable output. No flag, no
new exception type, no new branch in `certify()`'s `check()` wrapper — both consumers
(SKIP and FAIL) consume the single return unchanged. The engineer's stated floor is
credible and test-proven: `test_fail_detail_never_leaks_raw_output_when_no_json_error_is_parseable`
demonstrates that a naive cap-without-parse still leaks (the banner places the session
id well inside the first 200 characters), so going lower than +17 means either leaving
the FAIL leak live or duplicating parsing elsewhere. The diff removes an asymmetry
(one branch classified, the other did nothing) rather than adding one.

**2. Does the one-seam claim hold?** Yes, for the declared surface. `_codex_probe_outcome`
is now the sole classification+detail seam for a nonzero `codex exec` exit; the old
seam is deleted, not wrapped — no build-on-stale-layer. One residual, outside this
bug's declared surface: the marker-mismatch branch (service.py, `RuntimeError` at the
`_CODEX_LIVE_PROBE_MARKER` check, exit-0 path) embeds `stdout[:200]!r` — capped but
not routed through `_codex_capped_detail`. Pre-existing, distinct condition (probe
answered but wrong content), bounded. **LOW residual:** route that one string through
`_codex_capped_detail` when next touching the file; one line, backlog-intake note, not
a blocker and not grounds to grow this diff now.

**3. Does the Redactor routing respect boundaries?** Yes. `features/certification` →
`core.redaction` is the correct dependency direction (Features → Core); the feature
becomes the third consumer of the one existing stdlib-pure masking primitive alongside
`cli/redact.py` and `features/chokepoints/service.py` — no cross-feature reach-in, no
`cli` import from a feature, no new redaction algorithm. Defense is correctly layered:
the primary control is structural (parse the message, never render the blob), the
Redactor masks the one known-sensitive candidate (the probe cwd), and the length cap
bounds everything else. A fresh single-pass `Redactor` instance per detail is
consistent with the primitive's per-rendering-pass contract.

**4. Bug-surface delta of the certification feature?** **Reduced**, with ledger
evidence. The v0.4.4 fix (`codex-live-probe-gate-checks-presence-not-usability`,
resolved 2026-08-23T19:23Z) was followed by this bug (reported 2026-08-23T20:00Z) in
the same surface — a one-hop fix-then-bug chain on the detail path. This fix closes
the entire raw-blob class on both branches (three sentinel-fixture RED tests prove no
workdir, session-id, or raw-content byte reaches `detail`; a fourth proves the cap),
and deletes the half-seam that bred the chain. Failure-path renderings collapse from
two ad-hoc constructions to one seam. Net LOC is +17, but branch count on the failure
path is down and the leak class — not one leak instance — is eliminated.

### Persona gates

- **Root-cause gate: PASS.** The fix addresses the actual root cause (absence of a
  parse-and-bound seam), not a symptom cap; the RED suite fails against the unfixed
  tree for that exact cause.
- **Architecture-fidelity gate: PASS.** Feature-consumes-core-primitive is the
  documented redaction architecture (core extracted precisely so features and CLI
  share one masker); no layer or boundary is misrepresented.

### Verdict

**SOUND.** Commit may proceed with
`--evidence-diff "net-positive: +17 is the missing parse-and-bound seam itself (FAIL-branch parsing + redaction routing that did not exist); old half-seam deleted, not wrapped; leak class eliminated on both branches, bug surface reduced per the 944→946 fix-then-bug chain"`.

**Precedent (one line):** a net-positive diff on a bug fix is SOUND when the added
lines *are* the missing structure the bug-history chain proves absent, the superseded
seam is deleted rather than wrapped, and the floor below the measured net is
test-proven to leave the defect live.

---

## Firing 2 — T-045-19 — SOUND-WITH-AMENDMENT

**Subject:** commit `eb03d01b` "fix(T-045-19): one denylist loading seam, consumed by
write-time redaction and the push scan" (SPEC FR6, A6.1–A6.5).
**Measured diff:** `core/models/bugs.py` +37/−?, `features/bugs/service.py` +23,
`cli/commands/bugs.py` +12, `infrastructure/privacy_check.py` +12 (docstring only) =
**net +52**. By direct read, roughly 8 of those lines are logic (one `for` loop in
`redact_text`, one kwarg on `redact`, one kwarg + attribute on `BugService`, one
argument at the CLI call site); the remaining ~44 are provenance prose. Shell-less
reviewer; tree state verified by read of all four files, both new tests, `container.py`,
`setup.cfg` contracts, `core/redaction.py`, `denylist_scan.py`, and the ledger.

### Problem and prior art (architect-core-workflow)

Core problem: the operator denylist was consulted only at the publication boundary
(push scan), never when a bug event is written, so a leak was committed first and
refused later. Constraint: three import-linter contracts (`core-no-upper-layers`,
`features-no-infrastructure`, `cli-no-infrastructure`) make `infrastructure.
privacy_check.load_privacy_terms` reachable from the ledger only through the
composition root. Prior art surveyed, all internal: `core/redaction.Redactor`
(word-boundary, case-sensitive), `redact_text` (IP/home regexes, already the ledger's
one masking call), `container.load_denylist_terms` (already the push gate's seam).

### The four questions

**1. Structurally sound, or a puxadinho?** Sound in shape. One loader (A6.2:
`container.load_denylist_terms` → `load_privacy_terms`, the same seam
`cli/commands/ci.py:316` uses; `grep` finds no second reader). DI through the existing
`BugService(store, …)` constructor pattern. The terms ride the same `redact_text` call
every field already goes through — no second algorithm, no flag, no new branch in the
append path. Enforcement sits in `BugService.append_event`, the seam that already
enforces coherence — the right home, per the ledger's own history (the coherence bugs
were exactly "the CLI wrote what the doctor flagged"). Push scan untouched (A6.3).
Two residuals keep this from plain SOUND, both fixable by deletion:
- **`cli/commands/bugs.py:248` still calls `.redact()`** before validation. The append
  path now redacts twice: CLI (IP/home) then service (IP/home + terms). That is the
  superseded half-seam Firing 1's precedent says to delete, not leave beside the new one.
- **A6.5 is not met.** `BugEvent.redact()` keeps its hand-kept 11-field list
  (`title … evidence_diff`) while `_OPTIONAL_STR_FIELDS` (16, schema mirror) sits 60
  lines above it. The SE reads A6.5 as "add no *new* hand list"; the SPEC says fields are
  "enumerated by the schema, not by a hand-kept field list". The list is the thing.

**2. Write-set overrun — necessary or avoidable?** Necessary; the TASKS write set was
wrong. `core` cannot import the loader, so *some* caller must hand terms in; the only
callers are the service and the CLI. The one-file alternative — passing terms straight
into the CLI's `.redact()` at line 248 — would put enforcement in the CLI and leave
`BugService` able to write raw terms, re-creating the coherence-bug pattern
(`bugs-append-accepts-second-terminal-event`). Correction owed by `product-engineer`:
amend T-045-19's write set to add `features/bugs/service.py` and
`cli/commands/bugs.py`; no SE fault.

**3. Class closed or instance patched?** Ledger evidence, `specs/bugs/bugs.jsonl`:
- `public-privacy-consumer-leak-in-public-repo` (l.820/822, resolved 0.4.2, HEAD-only
  scrub of 315 occurrences) — the denylist existed; nothing consulted it at write time.
- T-043-23 (docstring in `BugEvent.redact`, v0.4.3) widened the hand list by
  `release`/`reason`; T-044-62 (v0.4.4) widened it again by three `evidence_*` fields.
  Same method, same defect shape, twice: a hand-kept list misses a field.
- `reconciliation-merge-body-scan-unamendable-main-squash` (l.917/918, v0.4.3) —
  push-time-only catch of an already-published body; fixed by a baseline carve-out.
- SPEC FR6: two more committed leaks inside v0.4.4, one forcing an `rc-1` rewrite.
This change **closes the class "denylist never consulted at write time"** (RED unit +
integration tests fail for exactly that cause on the unfixed tree). It **leaves open
the class "field missed by the hand list"** — the one the T-043-23 → T-044-62 chain
proves — which A6.5 was written to close. Hence the amendment.

**4. Smaller shape?** Not by relocation — `core.redaction.Redactor` is the wrong
primitive here: word-boundary + case-sensitive versus the push scan's case-insensitive
substring (`denylist_scan.py:250`), so `ACME-Corp` or `acme-corpx` would pass write-time
and still be refused at push, breaking A6.3 parity. The kwarg thread is the minimum DI
the three contracts allow. The smaller shape is by **deletion**, inside the same seam:
- **AM-1** delete `.redact()` at `cli/commands/bugs.py:248` — one masking pass, in the
  service. (−1 LOC; schema validation is shape-only, unaffected.)
- **AM-2** in `BugEvent.redact`, replace the 11 explicit `field=_scrub(self.field)`
  kwargs with `replace(self, **{n: _scrub(getattr(self, n)) for n in _OPTIONAL_STR_FIELDS})`
  and cut the 30-line provenance docstring to the schema-mirror sentence. (≈ −11/+3 logic,
  −25 prose.) Behavior change: `severity`/`component`/`context`/`surface`/`superseded_by`
  now pass through `redact_text` — a no-op unless they carry a denylisted term, in which
  case masking is the correct outcome (the push gate would refuse that record anyway).
  Add one test: every schema string property is scrubbed, derived from the schema file.
- **AM-3 (LOW, optional)** trim the duplicated provenance comments in `service.py`
  and `cli/commands/bugs.py` to one line each.
Expected landing: net ≈ +10 logic, prose −40; two paths → one; A6.5 literally met.

### Persona gates

- **Root-cause gate: PASS.** Structural cause (no write-time consumer of the loader)
  fixed at the owning seam; RED proves the cause on both layers.
- **Architecture-fidelity gate: PASS on layers** (core ← features ← cli → container →
  infrastructure, all three contracts honored, `lint-imports` green). **A6.5 acceptance:
  UNMET as committed** — resolved by AM-2.

### Bug-surface verdict

**Decreased** for the bugs-ledger feature on the write-time class (four-event chain
above, third recurrence per SPEC FR6, now closed by tests at the service and CLI
seams). **Unchanged** on the hand-list class until AM-2 lands; with AM-1 + AM-2 the
append path drops from two redaction passes to one and the field set can no longer
drift from the schema — decreased on both classes.

### Verdict

**SOUND-WITH-AMENDMENT.** The SE applies AM-1 and AM-2 (AM-3 at discretion) before the
marker flips; `product-engineer` amends the T-045-19 write set. Then commit with
`--evidence-diff "net-positive: one loader consumed at the write seam via container DI; superseded CLI redact pass deleted; field set derived from the schema mirror, closing the T-043-23/T-044-62 hand-list chain"`.

**Precedent (one line):** when a fix closes the class the bug names but leaves beside
it the older half-seam (a duplicate pass, a hand-kept list) whose own bug chain the
SPEC already cites, the ruling is amendment-by-deletion, never acceptance as-is.

---

## Firing 3 — T-045-26 — SOUND-WITH-AMENDMENT

**Subject:** commit `5c4f30c9` "feat(T-045-26): catalog digest curation policy" (SPEC FR12,
A12.1–A12.4). **Measured diff:** `features/specs/catalog.py` +59 (by read: 27 lines of
comment block l.259–285, 7 lines of `write_catalog` docstring, **~16 lines of logic** —
`_TLDR_INJECTED_CATEGORIES`, `_curate_features_for_persistence`, two lines in
`write_catalog`), test +27, `catalog.json` −27 (26 tldr lines + timestamp), `index.md`
untouched, `hooks/ctx_inject.py` untouched. Evidence file read; V8 1505.6 → 877.8 tokens.

### Problem and prior art (architect-core-workflow)

Core problem: the bound-session prefix is dominated by 26 tldr strings and A12.2 pins the
consumer (`_digest_catalog`) byte-unchanged, so the only lever is the persisted file. Prior
art is internal: `_digest_catalog` already tolerates an absent key (`if k in feat`), and
`category` is an existing required frontmatter field — no new key, no schema change.
Candidate rejected correctly: `rank` (F-77, alphabetical, not priority).

### The three questions

**1. Is +59 the minimum?** No — the logic is (≈16 lines); the prose is not. The l.259–285
block restates FR12, A12.2, A12.3, F-77, the schema note and the PE-ratification plan —
all of which live in the SPEC, the evidence file and the docstrings. **Delete l.259–285 to
≤5 lines** (what the policy is, that only the persisted file is curated, that `category`
is the tier key) and cut the `write_catalog` docstring to its one-sentence A12.3 note.
Expected: +59 → ≈ +30. The mechanism itself is minimal: one frozenset, one pure function,
no flag, no second branch in the CLI, no mutation of the caller's dict.

**2. Two divergent renderings — the `memory-catalog-cli-skips-index-md` class again?**
Not that class: that bug was two *generation runs* (CLI wrote `catalog.json`, never
`index.md`) drifting in time. Here `cli/commands/memory.py:111–117` feeds ONE
`generate_catalog` dict to both writers in one run; `index.md` full and `catalog.json`
curated are two projections of one source, and `index.md` is exactly A12.3's documented
one-step lookup. Sound. **But a second generation path is live:**
`public/scripts/generate-memory-catalog.py:419` writes the full catalog with no curation,
and the F-84 contract (`test_memory_catalog_render_contract.py:166`) pins only the
in-memory `features` list and `index.md`, never the written `catalog.json`. The ledger
names the shape: `memory-catalog-cli-skips-index-md` — "divergent surfaces, so the
canonical path drifts". The AI-engineer's own evidence file flags it and defers it; a
consumer workspace whose catalog is regenerated by the script silently loses the diet.
The TASKS write set ("`catalog.json` + the generator that produces it") already covers the
twin. Hence:
- **AM-1** apply the same tier filter in the script's writer (importless twin: copy the
  3-line filter + the frozenset, pinned like `estimate_tokens` is) and extend the F-84
  test to compare the two **written** `catalog.json` texts modulo `generated_at`. One
  contract, both writers — the on-disk output can no longer diverge unnoticed.
- **AM-2** the prose deletion from Q1.
Residual noted, not amended: the persisted file drops the short `tldr` and keeps the long
`summary` (which `_digest_catalog` never injects). Correct for FR12's lever; the
`dadaia-step0-memory-bootstrap` wording "tldr/summary" should read "summary" at CLOSURE.

**3. The honest miss (877.8 vs ≤700).** FR12's acceptance is A12.1–A12.4, none of which
is a number; the ≤0.7k figure is the bound-session target FR11's AS-3 governs ("if the
measurement lands short, CLOSURE records the number, the operator rules, the residual goes
to the PM's intake report"). The tech-stack digest floor (~564 tokens,
`_digest_tech_stack`, A30.3-pinned) is outside FR12's lever. Routing to CLOSURE under AS-3
is correct and **does not redefine the target**; the catalog's own floor (~314 tokens with
`slug`/`title`/`path` on 26 entries) is the honest number to record, the tech-stack
residual goes to intake, and the default `frozenset({"core"})` is PE's to ratify.

### Persona gates

- **Root-cause gate: PASS.** The dominant contributor (tldr × 26) is removed at the
  generator, not by a hand edit; A12.4 met literally.
- **Architecture-fidelity gate: PASS with AM-1.** Layers untouched (features → hooks read
  only a file). The "one source, two projections" claim is true for the CLI path and false
  across the two writers until AM-1 lands.

### Bug-surface verdict

Memory-catalog feature ledger: `memory-catalog-cli-skips-index-md` (06-25, resolved),
`memory-index-table-broken-gfm` (v0.1.48, present in BOTH renderers — the twin already
bred one dual-surface bug), `closure-catalog-references-missing-memory-atom` (0.4.2),
`memory-catalog-regenerator-orphaned-factory` (v0.4.3, pure deletion). **Unchanged** as
committed: no new branch on the CLI path, the fixed class stays closed by
`test_cli_generate_emits_both_catalog_and_index`, but the writer-parity gap the gfm bug
already proved is widened by one field. **Decreased** with AM-1: the written output of
both generators becomes contract-pinned for the first time.

### Verdict

**SOUND-WITH-AMENDMENT.** AM-1 (script parity + written-output contract) and AM-2 (prose
to ≤5 lines) before the marker flips; then commit with
`--evidence-diff "net-positive: policy lives in the generator (A12.4), one dict feeds both projections, ctx_inject untouched (A12.2); twin script curates identically and the F-84 contract now pins written catalog.json"`.

**Precedent (one line):** a curation policy applied to a persisted artifact must be
applied by every writer of that artifact and pinned by the contract that already binds
them — otherwise the "one source of truth" claim holds only on the path that was tested.
