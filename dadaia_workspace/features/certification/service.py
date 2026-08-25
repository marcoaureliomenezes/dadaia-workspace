"""Built-artifact certification of assembled dadaia-workspace capabilities."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sys
import time
import urllib.request
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.protocols.certification_process import CertificationProcess
from dadaia_workspace.core.redaction import Redactor


@dataclass(frozen=True)
class CertificationCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class CertificationResult:
    schema_version: str
    ok: bool
    workspace: str
    checks: tuple[CertificationCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git(process: CertificationProcess, cwd: Path, *args: str) -> None:
    proc = process.run(
        ["git", "-c", "user.email=certify@dadaia.invalid", "-c", "user.name=dadaia-certify", *args],
        cwd=cwd,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"git {args} failed")


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _CertificationSkip(Exception):
    """An honest, non-failing degrade for one certification check (A22.4).

    Raised when the runtime dependency a check would exercise is genuinely
    unavailable in this environment — absent entirely (e.g. no Codex CLI on PATH), or
    installed but unusable (e.g. signed in without the plan/model entitlement the
    check needs) — never for a real failure. ``certify``'s ``check`` wrapper records
    this as ``SKIP``, never ``FAIL``; a caller that runs the same check outside
    ``certify`` (e.g. a live pytest sentinel) catches it and skips honestly too.
    """


# A22.4 — codex-live-probe: exercises the INSTALLED Codex CLI with a real `codex exec`
# call, bounded and read-only. Static Codex projection tests (TOML shape, frontmatter
# parsing) never attest this — they cannot prove a live session actually answers.
_CODEX_LIVE_PROBE_PROMPT = (
    "Reply with exactly the single line: DADAIA-LIVE-PROBE-OK. No tool calls, no other text."
)
_CODEX_LIVE_PROBE_MARKER = "DADAIA-LIVE-PROBE-OK"
_CODEX_VERSION_PROBE_TIMEOUT = 15.0
_CODEX_LIVE_PROBE_TIMEOUT = 60.0
# Upstream 4xx classes that mean "this account cannot use Codex", not "Codex is
# broken" — auth/entitlement rejections, never a genuine probe defect.
_CODEX_ENV_UNAVAILABLE_STATUS_CODES = frozenset({400, 401, 403})
_CODEX_ENV_UNAVAILABLE_PHRASES = ("not logged in", "not authenticated")


_CODEX_DETAIL_MAX_LEN = 200  # certify --json detail cap, applied after masking (CWE-532).


def _codex_capped_detail(text: str, cwd: Path) -> str:
    """Cap + redact via the existing masking primitive (never a new one) — CWE-532.
    *cwd* is the one candidate known sensitive here (the banner's ``workdir:``)."""
    redactor = Redactor([str(cwd)], placeholder_fmt="[REDACTED-CODEX-DETAIL-{n}]")
    masked = redactor.mask(text.strip())
    return masked if len(masked) <= _CODEX_DETAIL_MAX_LEN else f"{masked[:_CODEX_DETAIL_MAX_LEN]}…"


def _codex_probe_outcome(output: str, cwd: Path) -> tuple[bool, str]:
    """Classify + bound the detail for a nonzero ``codex exec`` exit, one pass.

    Returns ``(environment_unavailable, detail)`` — ``detail`` is never the raw blob
    (CWE-532): the parsed ``error.message``, the matching refusal line, or a
    byte-count marker, always through :func:`_codex_capped_detail`.
    """
    lowered = output.lower()
    for phrase in _CODEX_ENV_UNAVAILABLE_PHRASES:
        if phrase in lowered:
            line = next((ln for ln in output.splitlines() if phrase in ln.lower()), phrase)
            return True, _codex_capped_detail(line, cwd)
    for match in re.finditer(r"\{.*?\}\}", output):
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            continue
        status = payload.get("status") if isinstance(payload, dict) else None
        unavailable = (
            error.get("type") == "invalid_request_error"
            and status in _CODEX_ENV_UNAVAILABLE_STATUS_CODES
        )
        message = error.get("message")
        if unavailable or message:
            return unavailable, _codex_capped_detail(str(message or "invalid_request_error"), cwd)
    return False, _codex_capped_detail(
        f"non-JSON codex exec output ({len(output)} bytes captured)", cwd
    )


def _codex_live_probe_detail(process: CertificationProcess, cwd: Path) -> str:
    """A22.4: prove the installed Codex CLI actually answers, not just that its files exist.

    Runs ``codex --version`` then a bounded, read-only, non-interactive ``codex exec``
    that must echo back a fixed marker. Raises :class:`_CertificationSkip` (never
    fails) when the installed Codex is unavailable to this environment — no binary on
    ``PATH``, or a signed-in account the upstream API rejects with an
    ``invalid_request_error``-class 4xx (no plan/model entitlement; see
    :func:`_codex_probe_outcome`) — an absent or unusable OPTIONAL local dependency
    is an honest degrade, not a certification failure. Raises ``RuntimeError`` for
    any genuine probe failure (crash, timeout, missing marker); both exceptions'
    detail is bounded/redacted, never the raw blob (CWE-532).
    """
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise _CertificationSkip(
            "codex CLI not found on PATH — live probe skipped (A22.4 honest degrade; "
            "static Codex projection tests validate shape only, never runtime behavior)"
        )
    version_proc = process.run(
        [codex_bin, "--version"], cwd=cwd, timeout=_CODEX_VERSION_PROBE_TIMEOUT
    )
    if version_proc.returncode != 0:
        raise RuntimeError(
            f"codex --version exited {version_proc.returncode}: "
            f"{(version_proc.stderr or version_proc.stdout).strip()}"
        )
    version = version_proc.stdout.strip()
    exec_proc = process.run(
        [
            codex_bin,
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            _CODEX_LIVE_PROBE_PROMPT,
        ],
        cwd=cwd,
        timeout=_CODEX_LIVE_PROBE_TIMEOUT,
    )
    if exec_proc.returncode != 0:
        combined = (exec_proc.stderr or exec_proc.stdout).strip()
        unavailable, detail = _codex_probe_outcome(combined, cwd)
        if unavailable:
            raise _CertificationSkip(
                "codex CLI installed but unusable in this environment — "
                f"{detail} (A22.4 honest degrade; upstream auth/entitlement "
                "rejection, not a probe defect)"
            )
        raise RuntimeError(f"codex exec exited {exec_proc.returncode}: {detail}")
    if _CODEX_LIVE_PROBE_MARKER not in exec_proc.stdout:
        raise RuntimeError(
            "codex exec did not echo the expected marker on stdout; "
            f"stdout={exec_proc.stdout[:200]!r}"
        )
    return f"{version}: live exec probe observed {_CODEX_LIVE_PROBE_MARKER!r}"


def _all_checks_ok(checks: Iterable[CertificationCheck]) -> bool:
    """PASS and SKIP are both acceptable certification outcomes (A22.4).

    An honest degrade for an absent OPTIONAL runtime dependency (e.g. no installed
    Codex CLI on this host) must never turn a certification run RED — only a genuine
    FAIL does.
    """
    return all(item.status in ("PASS", "SKIP") for item in checks)


def certify(
    workspace_root: Path, process: CertificationProcess, *, keep: bool = False
) -> CertificationResult:
    """Run the deterministic public-feature journey in a disposable workspace."""
    run_root = workspace_root / ".dadaia" / "tmp" / "certification" / uuid.uuid4().hex
    target = run_root / "workspace"
    home = run_root / "home"
    target.mkdir(parents=True)
    home.mkdir(parents=True)

    package_parent = Path(__file__).resolve().parents[3]
    source_pythonpath = (
        [str(package_parent)] if (package_parent / "pyproject.toml").is_file() else []
    )
    inherited_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(
        [*source_pythonpath, *([inherited_pythonpath] if inherited_pythonpath else [])]
    )
    env = {
        **os.environ,
        "HOME": str(home),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    else:
        env.pop("PYTHONPATH", None)
    for key in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        env.pop(key, None)

    checks: list[CertificationCheck] = []

    def cli(*args: str, cwd: Path | None = None, extra_env: dict[str, str] | None = None) -> str:
        child_env = {**env, **(extra_env or {})}
        proc = process.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
            cwd=cwd or target,
            env=child_env,
            timeout=180,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"dadaia {' '.join(args)} exited {proc.returncode}: "
                f"{(proc.stderr or proc.stdout).strip()}"
            )
        return proc.stdout

    def check(name: str, action: Callable[[], str | None]) -> None:
        try:
            detail = action() or "passed"
            checks.append(CertificationCheck(name=name, status="PASS", detail=detail))
        except _CertificationSkip as exc:
            checks.append(CertificationCheck(name=name, status="SKIP", detail=str(exc)))
        except Exception as exc:  # noqa: BLE001 - complete ledger, not fail-fast prose.
            checks.append(CertificationCheck(name=name, status="FAIL", detail=str(exc)))

    def doctor_clean(*args: str, **kwargs: Any) -> str:
        payload = json.loads(cli(*args, **kwargs))
        summary = payload.get("summary", {})
        errors = int(summary.get("errors", 0))
        warnings = int(summary.get("warnings", 0))
        if errors or warnings or payload.get("issues"):
            raise RuntimeError(f"doctor not clean: {json.dumps(payload, sort_keys=True)}")
        return "0 errors, 0 warnings"

    check(
        "workspace-init-all-harnesses",
        lambda: (
            cli("init", "--workspace", str(target), "--harness", "all", cwd=run_root)
            and "workspace initialized with Claude, Codex, and Kimi projections"
        ),
    )

    capability_payload: dict[str, Any] = {}

    def capability_check() -> str:
        nonlocal capability_payload
        capability_payload = json.loads(cli("capabilities", "--json"))
        if capability_payload.get("schema_version") != "dadaia-capabilities-v2":
            raise RuntimeError("unexpected capability schema")
        return f"provider={capability_payload['provider']['distribution_version']}"

    check("capability-contract", capability_check)

    def reconcile_check() -> str:
        version = capability_payload["provider"]["distribution_version"]
        payload = json.loads(cli("reconcile", "--expect-version", version, "--json"))
        if not payload.get("ok"):
            raise RuntimeError(str(payload))
        return ",".join(payload["steps"])

    check("exact-version-reconciliation", reconcile_check)

    standalone_specs = run_root / "standalone" / "specs"
    check(
        "specs-scaffold-and-doctor",
        lambda: (
            cli("specs", "init", "--specs-dir", str(standalone_specs), "--name", "certified")
            and doctor_clean("specs", "doctor", "--specs-dir", str(standalone_specs), "--json")
        ),
    )

    bare = run_root / "consumer.git"

    def empty_remote() -> str:
        _git(process, run_root, "init", "--bare", str(bare))
        cli(
            "context",
            "create",
            "certified-consumer",
            "--repo",
            "certified-consumer",
            "--url",
            str(bare),
        )
        cli("context", "alive", "certified-consumer")
        repo = target / "repos" / "certified-consumer"
        _git(process, repo, "config", "user.email", "certify@dadaia.invalid")
        _git(process, repo, "config", "user.name", "dadaia-certify")
        cli("context", "baseline", "certified-consumer", "--yes", "--push")
        _git(process, repo, "rev-parse", "--verify", "HEAD")
        return "empty remote materialized, scaffolded, committed, and pushed"

    check("context-empty-remote-baseline", empty_remote)

    def context_json() -> str:
        rows = json.loads(cli("context", "list", "--json"))
        if len(rows) != 1 or rows[0]["state"] != "alive":
            raise RuntimeError(f"unexpected context list: {rows}")
        shown = json.loads(cli("context", "show", "certified-consumer", "--json"))
        if shown["name"] != "certified-consumer":
            raise RuntimeError(f"unexpected context show: {shown}")
        return "list/show JSON stable"

    check("context-list-show-json", context_json)

    harness_env = {"CODEX_THREAD_ID": "certification-session"}

    def bind_heartbeat() -> str:
        cli(
            "context",
            "bind",
            "certified-consumer",
            "--mode",
            "implementation",
            "--release",
            "v0.0.1",
            extra_env=harness_env,
        )
        output = cli("context", "heartbeat", extra_env=harness_env)
        if "certification-session" not in output:
            raise RuntimeError(output)
        return "caller-owned bind and heartbeat"

    check("context-bind-heartbeat", bind_heartbeat)
    check(
        "context-specs-doctor",
        lambda: doctor_clean("specs", "doctor", "--context", "certified-consumer", "--json"),
    )

    def handoff_validation() -> str:
        path = target / ".dadaia" / "handoff" / "certified-consumer" / "cert.handoff.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "handoff-v1.2",
                    "self_pull": {"refs": ["specs/memory/quality-assurance.md"]},
                    "agent": "qa-engineer",
                    "context": "certified-consumer",
                    "produced_at": "2026-07-15T00:00:00Z",
                    "artifact": {"type": "other"},
                    "scope": "full capability certification",
                    "metrics": {"checks": 1},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        cli("reports", "validate", str(path), "--strict", "--json")
        return "handoff-v1.2 strict validation"

    check("reports-handoff-validation", handoff_validation)

    port = _free_loopback_port()

    def panel_check() -> str:
        cli("server", "register", "--port", str(port), "--project", "certification-panel")
        panel = process.start(
            [
                sys.executable,
                "-m",
                "dadaia_workspace.cli.main",
                "panel",
                "--port",
                str(port),
                "--no-open",
            ],
            cwd=target,
            env=env,
        )
        try:
            deadline = time.monotonic() + 15
            last_error = "panel did not respond"
            while time.monotonic() < deadline:
                if panel.poll() is not None:
                    stderr = panel.read_stderr()
                    raise RuntimeError(f"panel exited early: {stderr}")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception as exc:  # noqa: BLE001 - bounded readiness polling.
                    last_error = str(exc)
                    time.sleep(0.1)
            else:
                raise RuntimeError(last_error)
        finally:
            panel.terminate()
            try:
                panel.wait(timeout=10)
            except TimeoutError:
                panel.kill()
                panel.wait(timeout=5)
            cli("server", "release", "--port", str(port))
        return f"HTTP 200 on loopback port {port}; registry released"

    check("panel-and-server-registry", panel_check)

    def context_round_trip() -> str:
        cli("context", "release", extra_env=harness_env)
        cli("context", "dead", "certified-consumer", "--commit")
        cli("context", "alive", "certified-consumer")
        cli("context", "dead", "certified-consumer")
        cli("context", "delete", "certified-consumer")
        rows = json.loads(cli("context", "list", "--json"))
        if rows:
            raise RuntimeError(f"context delete left entries: {rows}")
        return "release, dead, alive, dead, delete"

    check("context-dead-alive-delete-roundtrip", context_round_trip)

    # A22.4: exercise the INSTALLED Codex CLI live — never rely on static Codex
    # projection tests (TOML shape only) to attest runtime behavior. Honest SKIP
    # (never FAIL) when no `codex` binary is reachable on this host.
    check("codex-live-probe", lambda: _codex_live_probe_detail(process, target))

    ok = _all_checks_ok(checks)
    result = CertificationResult(
        schema_version="dadaia-certification-v1",
        ok=ok,
        workspace=str(target),
        checks=tuple(checks),
    )
    if not keep:
        shutil.rmtree(run_root, ignore_errors=True)
    return result
