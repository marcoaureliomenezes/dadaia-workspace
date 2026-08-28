# T-045-35 — Arm B ruling: foreign-slug layer flags library asset + bug-id substrings

**Reviewer:** software-architect · **Bug:** `push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-substrings` (HIGH)
**Verdict:** fix BEFORE push, option (1), one-line seam, no `--no-verify`.

## 1. Problem (architect-core-workflow step 1)

- **Core problem.** `denylist_scan.compile_slug_patterns` (line 126) anchors every registry-derived
  slug with `\b`. Python's `\b` is a `\w`/non-`\w` transition; `-` and `.` are non-`\w`, so a slug
  that is itself hyphenated (every `repos/` dir name is) matches inside `<slug>-anything` and
  `<slug>.ext`. Rc-1 hits: the tracked basename `public/data/dadaia-AGENTS.md` cited in review prose
  and the ledger id `dadaia-agents-md-canonical-table-omits-sanctioned-references`. Neither is a
  private name; both are immutable identifiers (a tracked asset, an append-only ledger key).
- **Structural cause.** The layer's own VALUES contain the character its boundary treats as a
  delimiter. `service.py:383` calls this "hyphen-aware word boundaries" and justifies it with GRILL P8
  (`Acme-Corp` vs term `acme`) — an argument for the operator-TERM layer (substring), transplanted onto
  an IDENTIFIER layer where it is self-contradictory. `re.IGNORECASE` (code-reviewer LOW, v0.9.0)
  widened it further; together they produced this hit.
- **Constraints.** Pure module, no I/O, no allowlist (A4.1 source-scan test pins it), masker parity
  by construction (`_PathMasker` consumes the same compiled patterns), standing order: no puxadinho.
- **Success.** Basename + bug id pass; bare slug in prose still BLOCKS; `repos/<slug>/…` still BLOCKS;
  diff does not grow the feature.

## 2. Prior art (step 2) — the ledger, not the web

Bug history on this surface (ids + fix shape): `push-gate-refuses-its-own-privacy-baseline-fixtures`
(RELOCATE: fixtures retired, literals runtime-composed); `privacy-baseline-noreply-local-part-not-
carved-out` (REGEX carve-out, baseline v6); `repo-self-scan-hits-alpha2-qa-historical-literal`,
`t043-33-absolute-path-leaked-into-tasks-md`, `self-scan-baseline-drift-t04343-evidence-prose`,
`…-pre-pr-review-secrets-prose`, `s2-qa-close-review-leaks-home-abs-path`,
`…-s4-qa-close-review-prose` (all RELOCATE: redact/paraphrase prose);
`…-t04427-test-fixture-email` (fixture value swap). Ledger line for the S4 bug: "Third recurrence …
flagged to the code-review lane for a structural verdict" — no structural verdict followed.
`new-branch-push-loses-prior-published-denylist-amnesty` is the one structural fix (deleted a branch).
Every P3 fix so far edited the TEXT; none touched the matcher. This is the first P3 instance where the
text cannot be edited: a ledger key is immutable and the asset basename is the product's own.

## 3. Options

| # | Option | Closes | False-negative risk | LOC | Prior bugs prevented |
|---|---|---|---|---|---|
| 1 | Whole-token slug match (token = run of `[\w-]` plus dotted continuation) | Instance + the whole "slug embedded in identifier/basename" sub-class | A private slug `acme` inside `acme-prod.tf` no longer fires on the slug layer; the operator denylist (substring) remains the net for genuinely private terms | prod +2/−1 | 0 of the P3 ten (those are baseline-pattern-on-prose); would have prevented THIS and every future slug-in-identifier hit |
| 2 | Amnesty by any already-published path on base | Instance only | HIGH: an identity published once anywhere becomes free everywhere — reopens the A1.2 smuggling path v0.11.0 rejected; a bare slug in prose passes → fails the RED contract | adapter +30 (tree listing I/O) | 0 |
| 3 | Drop identities colliding with own tracked path segments | Instance only | HIGH: removes the slug from the layer → bare slug passes; silent hole for any private slug that collides with a public segment; new collision predicate = puxadinho | CLI +20 | 0 |
| 4 | Smaller: case-sensitive only | Nothing | Bug id still fires (lowercase); pure regression of the A3.3 case test | 0 | 0 |

Honest scope statement: no option closes P3 as a class. P3 is "baseline patterns police review prose";
its structural fix is a policy decision (where review prose lives / what the scanner reads), not
Arm B material. Route it to the 0.5.0 backlog as already named by the forensic. This ruling closes the
slug-layer sub-class permanently, which is the one P3 shape that RELOCATE cannot fix.

## 4. Ruling — option (1)

**Seam:** `dadaia_workspace/features/chokepoints/denylist_scan.py::compile_slug_patterns`, line 126.
Replace `r"\b" + re.escape(slug) + r"\b"` with
`r"(?<![\w-])(?<!\w\.)" + re.escape(slug) + r"(?![\w-])(?!\.\w)"`, keep `re.IGNORECASE`.
Semantics: a slug is a hit only as a whole token — bounded by start/end, whitespace, `/`, quotes,
brackets, punctuation not glued to a word. `<slug>-x`, `x-<slug>`, `<slug>.md`, `pkg.<slug>` are other
identifiers. `<slug>.` at sentence end still fires (dot not followed by a word char). Update the
docstring at lines 115-118 and `service.py:382-388` ("hyphen-aware" → "whole-token"). `_slug_suppressed`
and `_PathMasker._segment_is_offending` inherit the change unmodified — one predicate, parity kept.
**Estimated diff:** production +2/−1 code, ~6 docstring lines; tests +~30. No branch, no list, no flag.

**RED test** (`tests/unit/features/chokepoints/test_denylist_scan.py`, A3.3 section, synthetic names only):
- `_obj("specs/releases/x/reviews/r.md", "cites public/data/ZZ-FAKE-context-name-AGENTS.md and bug id zz-fake-context-name-md-canonical-table-omits-sanctioned-references\n")`, `slugs=("zz-fake-context-name",)` → `hits == ()` (fails today: 1 hit, line 1).
- Controls that must keep firing: `"see zz-fake-context-name in prose\n"` → 1 hit; `"see zz-fake-context-name.\n"` → 1 hit; existing `repos/{slug}/README.md` and upper-case tests unchanged; `prefix{slug}suffix` still no hit.
- Real-chokepoint proof for the `resolved` event: reinstall the library into the workspace venv (it is not an editable install), replay the rc-1 stdin refspec through `dadaia ci push-gate-check` → exit 0 with the 11 objects clean, then insert a bare foreign slug into a scratch blob → BLOCKED.

**Bug-surface direction: REDUCED.** The layer stops matching one class of non-private material with
zero new code paths; A4.1 (no allowlist) stays green unmodified. Evidence: 10 P3 bugs / 100 fixed by
editing text (forensic §4); the only structural fix on this surface (`new-branch-push-…`) deleted a
branch and had no recurrence. This fix is the same shape — narrowing, not carving out.

## 5. `--no-verify` for this push

**Not acceptable.** (a) This gate IS the publication boundary; bypassing it publishes 11 objects the
gate never evaluated, and the defect stays live for rc-2, `develop`→`main`, and every consumer push.
(b) DADAIA.md §7 reserves the bypass for emergencies; a 3-line fix on the live feature branch is not
one. (c) Arm B law: bugs are fixed on the spot on the feature branch, and the fixed gate then proves
itself on the very range that exposed it — the strongest evidence the `resolved` event can carry.
(d) The attempted-and-reverted history rewrite shows what the bypass pressure already cost; a bypass
would be the eleventh RELOCATE-shaped non-fix of P3. Order: fix → reinstall venv → RED/GREEN →
`resolved` event → commit → push through the gate.
