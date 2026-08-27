# PILLAR-SPECS — spec compliance

Disclosed sibling of `SKILL.md`, pillar 2. Input: `git log` over every commit in the
audit window (`SKILL.md`'s window section) and `dadaia specs doctor` against every
release the window touches.

## Commit-shape conformance (FR8)

Walk every commit in the window with `git log --format='%H%x09%s' --stat`. Classify each
by its subject-line pattern and its staged-path set, and check it against the five
canonical shapes — **defined once, at `dd-gitflow-default` §3a; this pillar reads that
table, it does not restate it.** A commit matching none of the five shapes, or matching a
shape's message pattern while staging paths outside that shape's declared set, is a
finding (severity by shape: registration/backlog/ADR isolation violations are MEDIUM; a
bug fix that is not self-contained — code + regression test + the `BUGS.jsonl` line,
alone — is HIGH, since it is exactly the "no second commit" rule FR8 exists to prove).

Report conformance **per shape**, not as one aggregate pass/fail — a release can be
100 % conformant on shape 5 (release definition) and non-conformant on shape 3 (bug fix)
at the same time, and the finding must say which.

## Canon-v6 pattern compliance

```bash
dadaia specs doctor --context <ctx> --json
dadaia specs doctor --context <ctx> --recipe
```

`--json` gives the structured issue list (path, code, severity); `--recipe` gives the
ordered, copy-pasteable remediation steps for each. Every non-zero-severity issue inside
the window becomes a `FINDINGS-FORMAT.md` record with `pillar: "specs"`; a WARN that
`--recipe` can fix mechanically is still a finding — this pillar measures, it never
fixes.

## `RELEASE.jsonl` milestone completeness

For every release whose `RELEASE.jsonl` the window's commits touch: confirm the three
canonical milestones — `defined` (SPEC `Aprovado`), `implemented`/`shipped`'s
predecessor (final-rc QA close), `shipped` (merge to `main`) — each carry a `sha` (and,
where applicable, a `pr`). A release with a `shipped` milestone but no `defined` or no
implemented-and-tested milestone is a finding — the chain has a gap.

## SPEC provenance and purge-on-pick

For each release's SPEC in the window: confirm `**Consumes:**` names the backlog
entry/entries it picked, and confirm the release-definition commit (shape 5, above)
actually removed those entries from `BACKLOG.md`'s `## ACTIVE` in the **same** commit —
a SPEC that consumes an entry still present in `## ACTIVE` after the definition commit
is a finding (the purge-on-pick rule, unmet).

## Findings

Every check above emits `pillar: "specs"` records via `FINDINGS-FORMAT.md`'s shape —
never a bespoke report format.
