"""ctx_inject driven as a real harness does: a subprocess, the session id on stdin.

bind-driven injection (FR-W2-01/02, T-50-03), compaction re-entry
(claude-compact-reinjection-missing, kimi-postcompact-omits-bound-context-bootstrap),
the catalog digest (AC-W4-03), A19.1 (associated repos inject nothing), A30.1,
bind-lost-silently-after-five-idle-minutes (a lost bind is told once); AC1.2 Cursor/Copilot
envelopes and new-session injection.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core import session_store
from tests.fixtures.harness_env import claude_hook_env, kimi_hook_env, run_hook_subprocess


def _ws(root: Path, *contexts: dict[str, Any]) -> Path:
    """Register *contexts* (``name`` plus optional ``slug``/``state``/``stack``/``catalog``/
    ``index``/``assoc``) and write each main repo's memory."""
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    entries = []
    for c in contexts:
        slug = c.get("slug", c["name"])
        entry = {"name": c["name"], "repo_slug": slug, "state": c.get("state", "alive"),
                 "repo_url": "", "created_at": "2026-09-30T00:00:00+00:00"}  # fmt: skip
        product = root / "repos" / slug / "specs" / "memory" / "product"
        product.mkdir(parents=True)
        (product.parent / "ARCHITECTURE.md").write_text(
            f"# Architecture\n\n## Tech Stack\n\n{c.get('stack', 'Python 3.12')}\n",
            encoding="utf-8",
        )
        if "index" in c:
            (product / "index.md").write_text(c["index"], encoding="utf-8")
        else:
            (product / "catalog.json").write_text(
                c.get("catalog", '{"features": []}'), encoding="utf-8"
            )
        if "assoc" in c:  # an associated repo carrying its OWN memory tree
            entry["associated_repos"] = [{"slug": "assoc", "url": "https://example.invalid/a.git"}]
            assoc = root / "repos" / "assoc" / "specs" / "memory"
            assoc.mkdir(parents=True)
            (assoc / "ARCHITECTURE.md").write_text(
                f"# A\n\n## Tech Stack\n\n{c['assoc']}\n", encoding="utf-8"
            )
        entries.append(entry)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": entries}), "utf-8"
    )
    return root


def _bind(root: Path, sid: str, context: str) -> None:
    """What ``dadaia context bind`` persists: the self-keyed record with a fresh ``bound_at``."""
    now = datetime.now(tz=UTC).isoformat()
    session_store.write_session(
        root, sid, {"session_id": sid, "context": context, "bound_at": now, "last_seen_at": now}
    )


def _run(
    root: Path,
    sid: str,
    *,
    event: str | None = None,
    source: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    env = claude_hook_env(  # the env id is the one id channel: bind sees no stdin (review F1)
        root,
        session_id=sid,
        extra={**(extra or {}), **({"DADAIA_HOOK_EVENT": event} if event else {})},
    )
    env.pop("DADAIA_CONTEXT", None)
    payload: dict[str, object] = {"session_id": sid}
    if source:  # Claude Code's SessionStart re-entry
        payload.update(hook_event_name="SessionStart", source=source)
    result = run_hook_subprocess("ctx_inject", payload, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


_UNBOUND = "[no bound context]"
_A = "[alpha]"


@pytest.mark.parametrize(
    "steps",
    [
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
                ("bind", "beta"),
                ("prompt", "[beta]"),
                ("prompt", ""),
            ],
            id="bind-injects-once-and-a-rebind-to-another-context-reinjects",
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
            ],
            id="same-context-rebind-reinjects-T-50-03",
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
                ("PostCompact", _A),
                ("prompt", _A),
                ("prompt", ""),
            ],
            id="kimi-postcompact-reemits-and-the-next-prompt-reinjects-once",
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("prompt", ""),
                ("PostCompact", _UNBOUND),
                ("prompt", _UNBOUND),
                ("prompt", ""),
            ],
            id="unbound-postcompact-reemits-the-generic-preflight",
        ),
        pytest.param(
            [("PostCompact", _UNBOUND), ("prompt", _UNBOUND)],
            id="postcompact-without-record-or-env-binds-nothing",
        ),
        pytest.param(
            [("bind", "alpha"), ("PostCompact", _A), ("prompt", _A)],
            id="kimi-postcompact-omits-bound-context-bootstrap-bind-before-any-prompt",
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
                ("compact", _A),
                ("prompt", ""),
            ],
            id="claude-compact-reinjection-missing-sessionstart-compact-restamps",
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("prompt", ""),
                ("clear", _A),
                ("prompt", ""),
            ],
            id="sessionstart-clear-reinjects-the-bound-context",
        ),
        pytest.param([("clear", _UNBOUND), ("prompt", "")], id="sessionstart-clear-unbound"),
        pytest.param(
            [("bind", "alpha"), ("prompt", _A), ("lose", ""), ("prompt", "")], id="lost-bind"
        ),
        pytest.param(
            [
                ("prompt", _UNBOUND),
                ("bind", "alpha"),
                ("prompt", _A),
                ("resume", ""),
                ("startup", _A),
            ],
            id="sessionstart-resume-continues-a-new-session-injects",
        ),
        pytest.param(
            [("bind", "alpha"), ("SessionStart", _A), ("SessionStart", _A)],
            id="AC1.2-every-new-session-of-a-sessionstart-only-harness-injects",
        ),
    ],
)
def test_injection_sequence(tmp_path: Path, steps: list[tuple[str, str]]) -> None:
    """Each prompt/event emits the header it names, or nothing (``""``): injection fires once
    per bind; PostCompact stamps the marker and leaves the sentinel for the next prompt;
    SessionStart(compact|clear) re-injects and restamps at once."""
    _ws(tmp_path, {"name": "alpha"}, {"name": "beta", "stack": "Node 20"})
    marker = tmp_path / ".dadaia" / "tmp" / "hooks" / "ctx-compact-s"
    for kind, want in steps:
        if kind == "bind":
            _bind(tmp_path, "s", want)
            continue
        if kind == "lose":
            session_store.session_record_path(tmp_path, "s").unlink()
            assert "context bind alpha" in _run(tmp_path, "s")  # told once
            continue
        if kind == "prompt":
            out = _run(tmp_path, "s")
        elif kind in ("PostCompact", "SessionStart"):  # the lane's own env names the event
            out = _run(tmp_path, "s", event=kind)
            assert marker.is_file() is (kind == "PostCompact")
        else:
            out = _run(tmp_path, "s", source=kind)
            assert not marker.exists()
        assert out.startswith(want) if want else out == "", (kind, out)


_NO_MEMORY = ("end memory bootstrap", "Python 3.12")


@pytest.mark.parametrize(
    ("contexts", "bound", "present", "absent"),
    [
        pytest.param([{"name": "alpha"}], None, [_UNBOUND], _NO_MEMORY, id="unbound-no-memory"),
        pytest.param(
            [{"name": "alpha"}, {"name": "beta"}],
            None,
            [_UNBOUND, "=== ALIVE contexts", "- alpha\n- beta\n"],
            (),
            id="unbound-lists-the-alive-contexts-A30.1",
        ),
        pytest.param(
            [{"name": "x", "state": "dead"}],
            None,
            [
                _UNBOUND,
                "\nNext (command step context): no ALIVE Spec Context",
                "context create with a context name and --main-repo set to the main repo's",
            ],
            _NO_MEMORY,
            id="no-alive-context-prints-the-doctor-step-AC6.2",
        ),
        pytest.param(
            [{"name": "alpha"}],
            ("other-sess", "alpha"),
            [_UNBOUND],
            _NO_MEMORY,
            id="a-foreign-session-bind-never-leaks-FR-W2-02",
        ),
        pytest.param(
            [{"name": "beta"}, {"name": "alpha", "stack": "Node 20"}],
            ("s", "alpha"),
            [_A, "Node 20", "end memory bootstrap"],
            ("[beta]", "ALIVE contexts"),
            id="own-record-beats-first-alive-ctx-inject-ignores-session-bind-first-alive-proxy",
        ),
        pytest.param(
            [{"name": "alpha", "assoc": "ASSOC-ONLY-MARKER"}],
            ("s", "alpha"),
            [_A, "Python 3.12"],
            ("ASSOC-ONLY-MARKER",),
            id="associated-repo-memory-never-injected-A19.1",
        ),
        pytest.param(
            [{"name": "pretty", "slug": "actual-dir"}],
            ("s", "pretty"),
            ["[pretty]", "Python 3.12"],
            (),
            id="registry-name-maps-to-its-repo-slug-F003",
        ),
        pytest.param(
            [{"name": "alpha", "index": "# product index\n- feature A\n"}],
            ("s", "alpha"),
            ["# product index\n- feature A"],
            (),
            id="index-md-fallback-without-a-catalog",
        ),
    ],
)
def test_first_emission(
    tmp_path: Path,
    contexts: list[dict[str, Any]],
    bound: tuple[str, str] | None,
    present: list[str],
    absent: tuple[str, ...],
) -> None:
    """A first emission carries only the memory of the context THIS session bound; unbound, none."""
    _ws(tmp_path, *contexts)
    if bound:
        _bind(tmp_path, *bound)
    out = _run(tmp_path, "s")
    assert all(p in out for p in present), out
    assert not any(a in out for a in absent), out


def test_env_override_injects_context_memory(tmp_path: Path) -> None:
    """sa-bind-has-two-stores#S2: a session with no id (a Kimi shell, no payload id) is
    bound by DADAIA_CONTEXT."""
    _ws(tmp_path, {"name": "ctx"})
    env = kimi_hook_env(tmp_path, extra={"DADAIA_CONTEXT": "ctx"})
    result = run_hook_subprocess("ctx_inject", {}, env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("[ctx]")
    assert "Python 3.12" in result.stdout


@pytest.mark.parametrize(
    ("extra", "event", "key"),
    [
        ({"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "SessionStart"}, "SessionStart", ""),
        ({"DADAIA_HOOK_OUTPUT": "cursor-json"}, None, "additional_context"),
        ({"DADAIA_HOOK_OUTPUT": "copilot-json"}, None, "additionalContext"),
    ],
    ids=["codex-json-envelope", "AC1.2-cursor-top-level", "AC1.2-copilot-top-level"],
)  # fmt: skip
def test_output_contract_envelopes(
    tmp_path: Path, extra: dict[str, str], event: str | None, key: str
) -> None:
    """Each output mode is its vendor's documented envelope: the native ``hookSpecificOutput``,
    or (Cursor, Copilot sessionStart) one top-level context key."""
    _ws(tmp_path, {"name": "ctx"})
    out = json.loads(_run(tmp_path, "s", extra=extra))
    envelope = out["hookSpecificOutput"] if event else out
    assert list(out) == [key or "hookSpecificOutput"]
    assert envelope.get("hookEventName") == event
    assert envelope[key or "additionalContext"].startswith(_UNBOUND)


def test_emissions_attach_the_derived_help_digest(tmp_path: Path) -> None:
    """T-053-24: the digest rides every emission, read from .dadaia/agentic/help-digest.md."""
    _ws(tmp_path)
    (tmp_path / ".dadaia" / "agentic").mkdir()
    (tmp_path / ".dadaia" / "agentic" / "help-digest.md").write_text(
        "# dadaia CLI digest (vX)\n", encoding="utf-8"
    )
    assert "# dadaia CLI digest (vX)" in _run(tmp_path, "s")


def test_injected_catalog_is_tldr_digest_and_measurably_smaller(tmp_path: Path) -> None:
    """AC-W4-03 / F-77: the injected catalog keeps slug/title/tldr/path only (never the heavy
    ``summary`` nor ``rank``), is under half the raw bytes, and the file on disk is untouched."""
    feature = {
        "rank": 1,
        "slug": "agent-comms",
        "title": "agent-comms",
        "tldr": "handoffs",
        "summary": "heavy self-pull text " * 60,
        "tags": ["handoff"],
        "path": "specs/memory/product/agents/agent-comms.md",
    }
    raw = json.dumps({"context": "ctx", "features": [feature, {**feature, "slug": "b"}]})
    _ws(tmp_path, {"name": "ctx", "catalog": raw})
    _bind(tmp_path, "s", "ctx")
    out = _run(tmp_path, "s")
    block = out[out.index("{") : out.rindex("}") + 1]
    assert json.loads(block)["features"][0] == {
        "slug": "agent-comms",
        "title": "agent-comms",
        "tldr": "handoffs",
        "path": "specs/memory/product/agents/agent-comms.md",
    }
    assert len(block) < len(raw) * 0.5
    assert (tmp_path / "repos/ctx/specs/memory/product/catalog.json").read_text("utf-8") == raw
