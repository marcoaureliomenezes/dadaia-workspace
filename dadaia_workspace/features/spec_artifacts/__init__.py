"""Feature: spec_artifacts — CLI helpers for creating conformant SDD artifacts.

Provides:
- memory_product_add: create a product feature HTML and regenerate index.html
- release_new: create a new release directory with SPEC.md stub
- backlog_new: create a new backlog entry

The legacy ``bug_new`` Markdown scaffolder was retired in v0.1.53 — bugs are
event-sourced JSONL via ``dadaia bugs append`` (the v0.1.46 canon).
"""
