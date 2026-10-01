#!/usr/bin/env python3
"""The two backlog schemas, this ledger's vocabulary, and the JSON-Schema subset the
documents are read with — `backlog.py`'s one validation primitive.

The schemas are ``schemas/backlog-v1.schema.json`` and
``schemas/histo-record-v1.schema.json`` beside this file, copies `public stage` makes.
"""

from __future__ import annotations

CODE = "LEDGER-BACKLOG-SCHEMA"
LEDGER = "backlog/BACKLOG.json"
HISTO = "backlog/_archive/backlog_histo.jsonl"
#: A backlog item is delivered, superseded, rejected or handed to a bug — `resolved` is a bug's word.
DISPOSITIONS = ("delivered", "superseded", "rejected", "to-bug")
#: The terminal words no LIVE active[] entry carries; a postponed item keeps any other status.
TERMINAL = (*DISPOSITIONS, "resolved")
#: The one status exempt from the typed-intents requirement (dd-backlog-definition §2).
IDEA = "idea"
