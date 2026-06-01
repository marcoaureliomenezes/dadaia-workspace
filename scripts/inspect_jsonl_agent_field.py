"""inspect_jsonl_agent_field.py — PR4-05 investigation script.

Walks all *.jsonl files under ~/.claude/projects/-home-marco-workspace-dadaia/
(and their subagent sub-directories) and finds events that record a dispatched
subagent.

Discovered JSON path for subagent_type (canonical schema as of 2026-05-19):

  event.message.content[i].input.subagent_type
    where event.type == "assistant"
      AND event.message.content[i].type == "tool_use"
      AND event.message.content[i].name == "Agent"

Additionally, sibling *.meta.json files inside parent-session/subagents/
carry the key "agentType" for the sidechain jsonl alongside them.

Usage:
  python3 scripts/inspect_jsonl_agent_field.py
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLAUDE_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()
TARGET_PROJECT = "-home-marco-workspace-dadaia"
MAX_DISPLAY = 40  # maximum lines to print before summarising

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_subagent_type(raw_event: dict) -> str | None:
    """Return the first subagent_type found in the assistant message content,
    or None if the event does not carry one.

    JSON path:
        event.message.content[*].input.subagent_type
    Preconditions:
        event.type == "assistant"
        event.message.content[*].type == "tool_use"
        event.message.content[*].name == "Agent"
    """
    if raw_event.get("type") != "assistant":
        return None
    message = raw_event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_use" and item.get("name") == "Agent":
            inp = item.get("input")
            if isinstance(inp, dict):
                val = inp.get("subagent_type")
                if val is not None:
                    return str(val)
    return None


def _scan_jsonl(file_path: pathlib.Path, source_label: str) -> list[dict]:
    """Scan a single jsonl file and return a list of match records."""
    matches = []
    try:
        with file_path.open("rb") as fh:
            for line_no, raw_line in enumerate(fh, 1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                subagent_type = _extract_subagent_type(event)
                if subagent_type is not None:
                    matches.append(
                        {
                            "source": source_label,
                            "file": str(file_path),
                            "line": line_no,
                            "session_id": event.get("sessionId", "<none>"),
                            "subagent_type": subagent_type,
                            "json_path": (
                                "event.message.content[i].input.subagent_type"
                                " (where type='tool_use', name='Agent')"
                            ),
                        }
                    )
    except OSError as exc:
        print(f"[WARN] Cannot read {file_path}: {exc}", file=sys.stderr)
    return matches


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    project_dir = CLAUDE_PROJECTS_DIR / TARGET_PROJECT
    if not project_dir.is_dir():
        print(f"[ERROR] Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    all_matches: list[dict] = []
    distinct_types: dict[str, int] = {}

    # --- Walk flat *.jsonl files in the project root ---
    for jsonl_path in sorted(project_dir.glob("*.jsonl")):
        matches = _scan_jsonl(jsonl_path, "parent-session")
        all_matches.extend(matches)

    # --- Walk subagent *.jsonl files in parent-session/subagents/ ---
    for session_dir in sorted(project_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        subagents_dir = session_dir / "subagents"
        if not subagents_dir.is_dir():
            continue
        # Read meta.json files to capture agentType even without full jsonl scan
        for meta_path in sorted(subagents_dir.glob("*.meta.json")):
            try:
                with meta_path.open() as f:
                    meta = json.load(f)
                agent_type = meta.get("agentType")
                if agent_type:
                    # Record the meta.json source — agentType is the canonical
                    # label for the sidechain session
                    all_matches.append(
                        {
                            "source": "sidechain-meta",
                            "file": str(meta_path),
                            "line": 1,
                            "session_id": session_dir.name,
                            "subagent_type": agent_type,
                            "json_path": "meta_json.agentType",
                        }
                    )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[WARN] Cannot read meta {meta_path}: {exc}", file=sys.stderr)

    # --- Tally distinct subagent types ---
    for m in all_matches:
        t = m["subagent_type"]
        distinct_types[t] = distinct_types.get(t, 0) + 1

    # --- Print results ---
    print("=" * 72)
    print("PR4-05 — jsonl subagent_type inspection")
    print("=" * 72)
    print(f"\nProject dir : {project_dir}")
    print(f"Total matches: {len(all_matches)}")
    print()

    # Print sample matches (up to MAX_DISPLAY)
    for displayed, m in enumerate(all_matches):
        if displayed >= MAX_DISPLAY:
            remaining = len(all_matches) - displayed
            print(f"  ... and {remaining} more matches (truncated)")
            break
        print(
            f"  [{m['source']}] {os.path.basename(m['file'])}:{m['line']}"
            f"  session={m['session_id'][:8]}..."
            f"  subagent_type={m['subagent_type']!r}"
        )

    print()
    print("Distinct subagent_type values (from parent-session jsonls):")
    for agent_type, count in sorted(distinct_types.items(), key=lambda kv: -kv[1]):
        print(f"  {agent_type!r:30s}  {count:4d} dispatch event(s)")

    print()
    print("Canonical JSON path (parent-session dispatch events):")
    print("  event.message.content[i].input.subagent_type")
    print("  where:")
    print("    event.type                     == 'assistant'")
    print("    event.message.content[i].type  == 'tool_use'")
    print("    event.message.content[i].name  == 'Agent'")
    print()
    print("Alternative path (sidechain meta files):")
    print("  <parent_session_id>/subagents/<agent_id>.meta.json -> agentType")
    print("=" * 72)

    # Exit non-zero if fewer than 3 distinct subagent_type values found
    parent_types = {m["subagent_type"] for m in all_matches if m["source"] == "parent-session"}
    if len(parent_types) < 3:
        print(
            f"\n[WARN] Only {len(parent_types)} distinct parent-session subagent_type"
            " values found (expected >= 3). Check the project directory.",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(
            f"\n[OK] {len(parent_types)} distinct parent-session subagent_type values"
            " found — acceptance criterion satisfied."
        )


if __name__ == "__main__":
    main()
