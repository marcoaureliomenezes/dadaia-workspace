"""Built-artifact certification of assembled dadaia-workspace capabilities."""

from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import time
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.protocols.certification_process import CertificationProcess
from dadaia_workspace.core.spec_status import is_approved


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

    def cli_expect_complete(*args: str, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
        """Run a lifecycle verb on the driving fake and assert the run COMPLETES.

        Bug certification-passes-without-complete-workflow-chain: a green certification
        must prove one coherent canonical workflow chain (backlog materialization →
        approved definition → implementation → reviews → closure), not merely that each
        verb can reach some deterministic block. The ``--harness fake`` driving worker
        materializes gate-VALID deliverables, so every Python gate executes for real on
        real disk state and the run must end COMPLETED (exit 0).
        """
        child_env = {**env, **(extra_env or {})}
        proc = process.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
            cwd=target,
            env=child_env,
            timeout=180,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"expected COMPLETED exit 0, got {proc.returncode}: "
                f"{(proc.stderr or proc.stdout).strip()[:400]}"
            )
        payload: dict[str, Any] = json.loads(proc.stdout)
        if payload.get("completed") is not True:
            raise RuntimeError(
                f"expected completed=true, got status={payload.get('status')} "
                f"blocked={payload.get('blocked')}"
            )
        return payload

    def cli_expect_clean_failure(*args: str, extra_env: dict[str, str] | None = None) -> str:
        """Run a verb that MUST fail — non-zero exit, one clean line, NEVER a traceback.

        The F-22 class: a raw Python traceback from any dadaia CLI verb is a defect.
        This proves the honest-failure half of the contract the completion checks no
        longer exercise (a wrong invocation is refused loudly and cleanly).
        """
        child_env = {**env, **(extra_env or {})}
        proc = process.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
            cwd=target,
            env=child_env,
            timeout=180,
        )
        combined = f"{proc.stdout}\n{proc.stderr}"
        if proc.returncode == 0:
            raise RuntimeError(f"expected a non-zero refusal, got exit 0: {combined.strip()[:400]}")
        if "Traceback (most recent call last)" in combined:
            raise RuntimeError(f"raw traceback leaked (F-22 class): {combined.strip()[:400]}")
        return f"refused cleanly (exit {proc.returncode}, no traceback)"

    def check(name: str, action: Callable[[], str | None]) -> None:
        try:
            detail = action() or "passed"
            checks.append(CertificationCheck(name=name, status="PASS", detail=detail))
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
            and "workspace initialized with Claude, Codex, and PI projections"
        ),
    )

    capability_payload: dict[str, Any] = {}

    def capability_check() -> str:
        nonlocal capability_payload
        capability_payload = json.loads(cli("capabilities", "--json"))
        if capability_payload.get("schema_version") != "dadaia-capabilities-v1":
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
    consumer_specs = target / "repos" / "certified-consumer" / "specs"

    def backlog_chain() -> str:
        cli_expect_complete(
            "lifecycle",
            "backlog-definition",
            "--context",
            "certified-consumer",
            "--release-id",
            "v0.0.1",
            "--run-id",
            "cert-backlog",
            "--demand",
            "certify deterministic workflow",
            "--harness",
            "fake",
            "--json",
            extra_env=harness_env,
        )
        items = sorted(
            p.name
            for p in (consumer_specs / "backlog").glob("*.md")
            if p.stem not in {"README", "ideas", "candidates"}
        )
        if not items:
            raise RuntimeError("backlog-definition completed but wrote no backlog item")
        return f"completed; materialized backlog item(s): {', '.join(items)}"

    check("workflow-backlog-definition", backlog_chain)

    def release_chain() -> str:
        cli_expect_complete(
            "lifecycle",
            "release-definition",
            "--context",
            "certified-consumer",
            "--release-id",
            "v0.0.1",
            "--run-id",
            "cert-release",
            "--harness",
            "fake",
            "--json",
        )
        release_dir = consumer_specs / "releases" / "v0.0.1"
        for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
            path = release_dir / name
            if not path.is_file():
                raise RuntimeError(f"release-definition completed but {name} is missing")
            if name != "TASKS.md" and not is_approved(path.read_text(encoding="utf-8")):
                raise RuntimeError(f"{name} was not flipped to Aprovado by its review gate")
        active = (consumer_specs / "releases" / "ACTIVE.md").read_text(encoding="utf-8")
        if "v0.0.1" not in active or "IMPLEMENTATION" not in active:
            raise RuntimeError(f"ACTIVE.md was not repointed to the defined release: {active!r}")
        return "completed; SPEC/PLAN approved, TASKS authored, ACTIVE.md repointed"

    check("workflow-release-definition", release_chain)

    def audit_chain() -> str:
        cli_expect_complete(
            "lifecycle",
            "audit",
            "--context",
            "certified-consumer",
            "--release-id",
            "v0.0.1",
            "--run-id",
            "cert-audit",
            "--harness",
            "fake",
            "--json",
        )
        return "completed; audit report validated and dispositions gate passed"

    check("workflow-audit", audit_chain)

    # Honest-failure canaries (F-22 class): wrong invocations refuse cleanly — non-zero
    # exit, no raw traceback, no side effects.
    def audit_missing_release_refused() -> str:
        detail = cli_expect_clean_failure(
            "lifecycle",
            "audit",
            "--context",
            "certified-consumer",
            "--release-id",
            "v9.9.9",
            "--run-id",
            "cert-audit-missing",
            "--harness",
            "fake",
            "--json",
        )
        if (consumer_specs / "releases" / "v9.9.9").exists():
            raise RuntimeError("audit against an undefined release created a release tree")
        return detail + "; no phantom release tree created"

    check("workflow-audit-undefined-release-refused", audit_missing_release_refused)
    check(
        "workflow-completed-run-rerun-refused",
        lambda: cli_expect_clean_failure(
            "lifecycle",
            "backlog-definition",
            "--context",
            "certified-consumer",
            "--release-id",
            "v0.0.1",
            "--run-id",
            "cert-backlog",
            "--demand",
            "certify deterministic workflow",
            "--harness",
            "fake",
            "--json",
            extra_env=harness_env,
        ),
    )

    def commit_definition() -> str:
        repo = target / "repos" / "certified-consumer"
        _git(process, repo, "add", "-A")
        _git(process, repo, "commit", "-m", "specs: certify release definition")
        _git(process, repo, "push")
        return "definition committed and pushed for implementation preflight"

    check("workflow-definition-git-baseline", commit_definition)

    def implementation_chain() -> str:
        cli_expect_complete(
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--context",
            "certified-consumer",
            "--release-id",
            "v0.0.1",
            "--run-id",
            "cert-implementation",
            "--harness",
            "fake",
            "--json",
            extra_env=harness_env,
        )
        closure = consumer_specs / "releases" / "v0.0.1" / "CLOSURE.md"
        if not closure.is_file():
            raise RuntimeError("implementation-reviews completed but CLOSURE.md is missing")
        return "completed; implement→review→close ladder reached CLOSURE.md"

    check("workflow-implementation-reviews", implementation_chain)

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

    ok = all(item.status == "PASS" for item in checks)
    result = CertificationResult(
        schema_version="dadaia-certification-v1",
        ok=ok,
        workspace=str(target),
        checks=tuple(checks),
    )
    if not keep:
        shutil.rmtree(run_root, ignore_errors=True)
    return result
