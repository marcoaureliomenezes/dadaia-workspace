"""Golden bytes of the registry renderers: ``was_shipped`` digests their output, so any drift
in a rendered table or CLI spelling silently re-labels every shipped template."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.core.workspace_layout import render_registry_tables, render_workspace_cli

ZONES = (
    "| Zone | Purpose | Class | TTL | Creator |\n"
    "|---|---|---|---|---|\n"
    "| `agentic/` | staged public assets + manifest.json | projection | never | install |\n"
    "| `hooks/` | projected hook entrypoints | projection | never | install |\n"
    "| `states/` | workspace database | state | never | init |\n"
    "| `sessions/` | session records; reaper = core.session_store | protected | never | runtime |\n"
    "| `handoff/` | agent handoffs, ack-on-consume | output | 86400 | runtime |\n"
    "| `reports/` | HTML reports; never reaped or committed | output | never | runtime |\n"
    "| `tmp/` | scratch + evidence | ephemeral | 86400 | runtime |\n"
    "| `reaped/` | slop held by the reaper; deleted only by TTL expiry | ephemeral | 604800 | runtime |\n"
    "| `dist/` | export artifacts: the soft JSON, the hard archive, and per-repo pause bundles"
    " in <repo>/ | state | never | runtime |\n"
    "| `mcps/` | anything an MCP server needs; never scanned | operator | never | operator |\n"
    "| `references/` | operator reference clones; never scanned | operator | never | operator |\n"
    "| `.venv/` | workspace venv; never scanned | managed | never | init |"
)
CANON = (
    "| Entry |\n|---|\n"
    "| `AGENTS.md` |\n"
    "| `agent_model_policy.json` |\n"
    "| `agent_model_policy.json.last-good.json` |\n"
    "| `harness_profile.json` |\n"
    "| `install_ledger.json` |\n"
    "| `privacy_denylist.json` |\n"
    "| `server_registry.json` |\n"
    "| `spec_contexts.json` |\n"
    "| `verdicts` |"
)
# One projection directory per harness row (claude, codex, cursor, devin) beside .agents.
ROOT = (
    ".agents/ .claude/ .codex/ .cursor/ .dadaia/ .devin/ .github/ repos/ worktrees/"
    " .dadaiaignore AGENTS.md prompt.md"
)
SPECS_CANON = (
    "| Area | Members |\n|---|---|\n"
    "| root | `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/` |\n"
    "| `memory/` | `AGENTS.md ARCHITECTURE.md QUALITY.md product/` |\n"
    "| `memory/product/` | `index.md catalog.json <area>/<slug>.md` |\n"
    "| `releases/` | `AGENTS.md _archive/ <M.m.p>/` |\n"
    "| `releases/_archive/` | `releases_histo.jsonl <M.m.p>/**` |\n"
    "| `releases/<M.m.p>/` | `_RELEASE.json RELEASE.json rc-<N>/` |\n"
    "| `releases/<M.m.p>/rc-<N>/` | `SPEC.md PLAN.md TASKS.md tasks/<slug>.md` |\n"
    "| `backlog/` | `AGENTS.md BACKLOG.json _archive/backlog_histo.jsonl` |\n"
    "| `bugs/` | `AGENTS.md BUGS.jsonl _archive/bugs_histo.jsonl` |\n"
    "| `audits/` | `AGENTS.md _archive/audits_histo.jsonl <YYYYMMDD-slug>/` |\n"
    "| `audits/<YYYYMMDD-slug>/` | `AUDIT.md FINDINGS.jsonl` |\n"
    "| `ADRs/` | `AGENTS.md decisions.jsonl` |"
)


@pytest.mark.parametrize(
    ("placeholder", "expected"),
    [
        ("<!-- zones -->", ZONES),
        ("<!-- canon -->", CANON),
        ("<!-- root -->", ROOT),
        ("<!-- specs-canon -->", SPECS_CANON),
    ],
)
def test_each_placeholder_renders_its_golden_bytes(placeholder: str, expected: str) -> None:
    assert render_registry_tables(f"a\n{placeholder}\nb") == f"a\n{expected}\nb"


def test_text_without_placeholders_is_unchanged() -> None:
    assert render_registry_tables("plain <!-- other --> text\n") == "plain <!-- other --> text\n"


def test_all_placeholders_in_one_template_render_together() -> None:
    template = "<!-- zones -->|<!-- canon -->|<!-- root -->|<!-- specs-canon -->"
    assert render_registry_tables(template) == "|".join([ZONES, CANON, ROOT, SPECS_CANON])


def test_workspace_cli_is_the_source_spelling_on_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("linux"))
    text = "run .dadaia/.venv/bin/dadaia doctor"
    assert render_workspace_cli(text) == text
    assert render_registry_tables(text) == text


def test_workspace_cli_is_the_windows_spelling_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    text = "run .dadaia/.venv/bin/dadaia doctor\n<!-- root -->"
    assert (
        render_workspace_cli(text) == "run .dadaia/.venv/Scripts/dadaia.exe doctor\n<!-- root -->"
    )
    assert render_registry_tables(text) == f"run .dadaia/.venv/Scripts/dadaia.exe doctor\n{ROOT}"
