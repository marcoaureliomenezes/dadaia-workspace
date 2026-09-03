# PILLAR-SPECS — spec compliance

Disclosed sibling of `SKILL.md`, pillar 2. Input: `git log` over every commit in the audit window.
Also input: `dadaia specs doctor` against every release the window touches.

## Commit-shape conformance

1. Walk every commit in the window with `git log --format='%H%x09%s' --stat`.
2. Classify each by its subject-line pattern and staged-path set against the five canonical shapes.
3. The five shapes are defined once, at `dd-gitflow-default` §3a — this pillar reads that table, never restates it.
4. Flag a commit matching none of the five shapes, or matching a message pattern while staging paths outside its set.
5. Severity: registration/backlog/ADR isolation violations are MEDIUM.
6. Severity: a bug fix that is not self-contained (code + regression test + `BUGS.jsonl` line alone) is HIGH.
7. Report conformance per shape, never as one aggregate pass/fail — a finding must say which shape failed.

## Canon-v6 pattern compliance

```bash
dadaia specs doctor --context <ctx> --json
dadaia specs doctor --context <ctx> --recipe
```

1. `--json` gives the structured issue list (path, code, severity).
2. `--recipe` gives the ordered, copy-pasteable remediation steps for each.
3. Every non-zero-severity issue inside the window becomes a `FINDINGS-FORMAT.md` record with `pillar: "specs"`.
4. Record a WARN that `--recipe` can fix mechanically as a finding too — this pillar measures, it never fixes.
5. Treat an absent `specs/releases/**/verdicts/**` file on a merged PR as expected — the gate deletes a verdict once consumed.
6. Treat an archived release carrying no directory (only its `releases_histo.jsonl` summary) as the canon shape, not drift.

## `_RELEASE.json` milestone completeness

1. For every release whose `_RELEASE.json` the window's commits touch, confirm the three canonical milestones.
2. Milestones: `defined` (SPEC `Aprovado`), `implemented` (final-rc QA close), `shipped` (merge to `main`).
3. Confirm each carries a `sha` (and, where applicable, a `pr`).
4. Flag a release with a `shipped` milestone but no `defined`/`implemented` milestone — the chain has a gap.
5. For an archived release, check the same via its `releases_histo.jsonl` summary.

## SPEC provenance and purge-on-pick

1. For each release's SPEC in the window, confirm `**Consumes:**` names the backlog entry/entries it picked.
2. Confirm the release-definition commit (shape 5) actually removed those entries from `BACKLOG.json`'s `active` array.
3. Confirm the removal happened in the same commit as the SPEC.
4. Flag a SPEC that consumes an entry still present in `active` after the definition commit — purge-on-pick unmet.

## Slop readout

Input: the ratchet modules and the window `from-sha..HEAD`. Output: the "Slop readout" table in `AUDIT.md`
(ratchet, baseline, HEAD, trend, verdict). Definition and signals: `DADAIA.md` §7.6, `dd-code-review`'s `SLOP.md`.

1. Run `pytest tests/contract/test_slop_ratchets.py tests/contract/test_test_suite_ratchets.py`; record each count beside its pinned ceiling.
2. Trend each ratchet over the window: the count at the from-sha against HEAD, via a temporary worktree under `.dadaia/tmp/` — never a stash.
3. Read the density of every SPEC in the window: bytes, words, codes per 1,000 words, numbered families outside FR/AC/T-.
4. Read the GC: handoffs older than 30 days, `.dadaia/tmp/` files older than the window, `archive/` tags whose branch survives.
5. Sample the ten commits with the most additions; apply `SLOP.md` S1-S5 to each diff — the audit proves the review worked, it never redoes it.
6. One `FINDINGS-FORMAT.md` record per ratchet that rose or signal hit; ratchet rose HIGH, density over the ceiling MEDIUM, S4/S5 in a sample HIGH.

## Findings

- Every check above emits `pillar: "specs"` records via `FINDINGS-FORMAT.md`'s shape — never a bespoke report format.
