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
