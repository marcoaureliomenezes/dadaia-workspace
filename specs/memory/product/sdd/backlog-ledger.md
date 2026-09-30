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
- An `active[]` entry carries `title`, `opened`, `status`, `description`, `provenance` and optional `intents`; its slug matches `^[a-z][a-z0-9-]+$`.
- `status` is a lowercase live token, never a backlog terminal word; an `idea` needs no intents, every later status binds `intents[]` whose subjects resolve to a code, doc or CLI anchor.
- A release picks an entry by naming its slug on its SPEC's `**Origin:** backlog:` line; the entry stays in `active[]` and exits once, at the closure disposition sweep ([[release-lifecycle]]); a deferred entry stays in `active[]`.

## The writer — `backlog.py`

- `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py <verb> [--specs <path>]` is the one writer and validator; every write validates the bytes it is about to commit, so writer and validator cannot disagree.
- `new <slug> [--title] [--description] [--provenance] [--intent KIND:REF=CHANGE]` appends one entry born at `idea`.
- `exit <slug> --disposition delivered|superseded|rejected [--release <id>] [--reason <text>] [--summary <text>]` removes the one `active[]` object and appends one `histo-record-v1` `{id, ts, disposition, release, reason, summary, entry}`, `entry` being the removed object, redacted.
- `exit` refuses before writing anything: a slug not live in `active[]` (already exited or unknown), a disposition outside the three, `delivered`/`superseded` without `--release` naming a live or archived release, `delivered`/`superseded` of an entry whose slug that release's `**Origin:** backlog:` line does not name, and `rejected` without `--reason` — each with one `fix:` line.
- `subjects [--kind <kind>]` lists the anchors of the operator alias map (`.dadaia/states/backlog_subject_aliases.txt`).
- `check [--json]` validates `BACKLOG.json` and `backlog_histo.jsonl`.

## Validation

- `dadaia doctor`'s `ledgers` section runs `backlog.py check` (`LEDGER-BACKLOG-SCHEMA`), the one entry validator, and two anchor rules over the source tree: `BL-SCHEMA` (a bound subject that resolves to no live anchor) and `BL-CONFLICT` (two entries binding one anchor with incompatible changes); each carries its `fix:` line ([[workspace-doctor]]).
- One histo vocabulary serves every ledger: `delivered resolved superseded deferred rejected`; a backlog entry exits `delivered`, `superseded` or `rejected`, and `deferred` is not terminal for it.

## Runtime state

`specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `.dadaia/states/backlog_subject_aliases.txt`.

## Dependencies

[[release-lifecycle]], [[workspace-doctor]], [[agent-orchestration]].
