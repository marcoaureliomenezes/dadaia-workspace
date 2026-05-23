"""Runtime-specific prompt and model transforms for agent orchestration parity.

This package provides deterministic transformations that adapt canonical agent
personas (authored for Claude Code) to alternative runtimes (e.g. Codex) without
modifying the source files.

Modules:
    model_mapping — Claude-to-Codex model identifier mapping table.
    codex         — Prompt body transformer for the Codex runtime.
"""
