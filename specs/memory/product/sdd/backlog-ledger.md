---
slug: backlog-ledger
title: backlog-ledger
tldr: "The operator's demand queue: BACKLOG.json active[] plus one histo record per exit; backlog.py writes it, dadaia doctor judges bound subjects."
summary: The backlog ledger — specs/backlog/BACKLOG.json holding every live entry in active[], and _archive/backlog_histo.jsonl holding one terminal record per exited slug; backlog.py is the one writer and validator, and the doctor's ledgers section resolves each entry's bound intents.
tags: [sdd, backlog, ledger, governance]
sources:
  - dadaia_workspace/public/skills/dd-backlog-definition/**
  - dadaia_workspace/public/schemas/backlog/**
  - dadaia_workspace/public/schemas/histo/**
  - dadaia_workspace/features/backlog/**
  - dadaia_workspace/core/models/backlog.py
---

## The document

- Only the operator creates demand; `dd-product-engineer` curates it, and an entry materializes only through the main thread's operator-facing intake report or an operator-ratified deferral inside a release ([[agent-orchestration]]).
- `specs/backlog/` holds `BACKLOG.json` (`backlog-v1`, `{schema, active: [...]}`), `AGENTS.md` and `_archive/backlog_histo.jsonl`; no per-entry file exists.
- An `active[]` entry carries `title`, `opened`, `status`, `description`, `provenance`, optional `intents` and `relates` — the live entries it was judged to update, obsolete or relate to at birth, empty for none, absent when the backlog was empty; its slug matches `^[a-z][a-z0-9-]+$`.
- `status` is a lowercase live token, never a backlog terminal word; an `idea` needs no intents, every later status binds `intents[]` whose subjects resolve to one of four anchor kinds, each derived from live truth: `code` (a repo-relative tracked path, any language, an optional `#word` that must occur in the file), `catalog` (a catalog slug), `doc` (a `SPEC-DOC` id or memory heading anchor) or `invariant` (an `INV-*` id).
- The document is written in a `backlog/<slug>` worktree, which lands `specs/` only, `BUGS.jsonl` included, so a bug registration and the `to-bug` exit it receives share one ([[worktrees]], [[bug-ledger]]).
- A release picks an entry by naming its slug in the `backlog:` clause of a candidate SPEC's first `**Origin:**` line, read by `release.py`'s one Origin parser; the entry stays in `active[]` and exits once, at the closure disposition sweep ([[release-lifecycle]]); a deferred entry stays in `active[]`.

## The writer — `backlog.py`

- `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py <verb> [--specs <path>]` is the one writer and validator; every write validates the bytes it is about to commit, so writer and validator cannot disagree, and refuses a new entry or histo record carrying a match the push refuses that the document's published text does not already carry ([[bug-ledger]]).
- `new <slug> [--title] [--description] [--provenance] [--intent KIND:REF=CHANGE] --relates <slugs>|none` (KIND one of `code|doc|invariant|catalog`) appends one entry born at `idea`; with a non-empty `active[]` it refuses a missing `--relates` or one naming a slug not live, listing the live slugs.
- `exit <slug> --disposition delivered|superseded|rejected|to-bug [--release <id>] [--reason <text>] [--summary <text>]` removes the one `active[]` object and appends one `histo-record-v1` `{id, ts, disposition, release, reason, summary, entry}`, `entry` being the removed object, redacted.
- `exit` refuses before writing anything, each refusal with one fix line: a slug not live in `active[]` (already exited or unknown); a disposition outside the four (`Operator action: a postponed item stays in active[] and needs no exit`); `delivered`/`superseded` without a `--release` whose candidate SPEC picked the slug, the fix naming the latest picking release, else an `Operator action:` to name the slug in a SPEC's Origin; `rejected` without `--reason`; `to-bug` whose `--reason` names no `BUGS.jsonl` record, read through `bugs.py`'s reader, the fix an `Operator action:` to register that bug first.
- `check [--json]` validates `BACKLOG.json` and `backlog_histo.jsonl`, one finding per invalid entry or line, its fix an `Operator action:` to discard or revert the change that wrote it and redo it through `backlog.py new` or `exit`.

## Validation

- `dadaia doctor`'s `ledgers` section runs `backlog.py check` (`LEDGER-BACKLOG-SCHEMA`), the one entry validator, and two anchor rules over the repo's git-tracked paths: `BL-SCHEMA` (a bound subject that resolves to no live anchor) and `BL-CONFLICT` (two entries binding one anchor with incompatible changes); each carries its `fix:` line ([[workspace-doctor]]).
- One histo vocabulary serves every ledger: `delivered resolved superseded deferred rejected to-bug`; a backlog entry exits `delivered`, `superseded`, `rejected` or `to-bug` (its `reason` the bug's id), and `deferred` is not terminal for it.
- `release.py check` lists each picked slug with whether its exit points back to the release, and a `to-bug` exit whose bug was later rejected ([[release-lifecycle]]).

## Runtime state

`specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`.

## Dependencies

[[release-lifecycle]], [[workspace-doctor]], [[agent-orchestration]], [[worktrees]], [[bug-ledger]].
