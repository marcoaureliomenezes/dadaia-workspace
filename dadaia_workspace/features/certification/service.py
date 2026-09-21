"""Built-artifact certification of assembled dadaia-workspace capabilities."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from typing import Any

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.redaction import Redactor
from dadaia_workspace.infrastructure.certification_process import SubprocessCertificationProcess


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


def _git(process: SubprocessCertificationProcess, cwd: Path, *args: str) -> None:
    proc = process.run(
        ["git", "-c", "user.email=certify@dadaia.invalid", "-c", "user.name=dadaia-certify", *args],
        cwd=cwd,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"git {args} failed")


class _CertificationSkip(Exception):
    """An honest, non-failing degrade for one certification check (A22.4).

    Raised when the runtime dependency a check would exercise is genuinely
    unavailable in this environment — absent entirely (e.g. no Codex CLI on PATH), or
    installed but unusable (e.g. signed in without the plan/model entitlement the
    check needs) — never for a real failure. ``certify``'s ``check`` wrapper records
    this as ``SKIP``, never ``FAIL``; a caller that runs the same check outside
    ``certify`` (e.g. a live pytest sentinel) catches it and skips honestly too.
    """


#: One live probe: ``(process, cwd, harness, binary) -> detail``.
_LiveProbe = Callable[[SubprocessCertificationProcess, Path, str, str], str]


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


#: The CLI binary each registered harness installs. It is NOT a field on
#: ``HarnessRecord``: the record describes what the workspace PROJECTS for a harness, and
#: nothing in the projection depends on the binary's name — only this probe does, so the
#: fact lives with its one consumer instead of widening a core dataclass.
_HARNESS_PROBE_BINARIES: dict[str, str] = {
    "claude": "claude",
    "codex": "codex",
    "kimi-code": "kimi",
    "cursor": "cursor-agent",
    "devin": "devin",
    "copilot": "copilot",
}

#: A record with a probe deeper than "the binary answers" names it here; every other
#: record falls back to :func:`_version_probe_detail`. There is NO version floor: the
#: workspace derives the same four behaviours into every harness and pins no release of
#: any of them, so a version comparison would assert a policy that does not exist.
_DEEP_LIVE_PROBES: dict[str, _LiveProbe] = {}


def _installed_binary(
    process: SubprocessCertificationProcess, cwd: Path, harness: str, binary: str
) -> tuple[str, str]:
    """Return ``(resolved path, version line)`` for *binary*, or degrade honestly.

    Raises :class:`_CertificationSkip` when the binary is absent: an optional local
    runtime that is not installed leaves the claim UNVERIFIED for this environment, which
    is an honest degrade and never a certification failure. A binary that IS installed but
    cannot answer ``--version`` is a genuine failure and raises.
    """
    resolved = shutil.which(binary)
    if resolved is None:
        raise _CertificationSkip(
            f"UNVERIFIED: no {binary!r} binary on PATH, so the {harness} runtime claim is "
            "unproven in this environment (A22.4 honest degrade; the projection tests "
            "validate file shape only, never runtime behavior)"
        )
    proc = process.run([resolved, "--version"], cwd=cwd, timeout=_CODEX_VERSION_PROBE_TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{binary} --version exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()}"
        )
    return resolved, proc.stdout.strip()


def _version_probe_detail(
    process: SubprocessCertificationProcess, cwd: Path, harness: str, binary: str
) -> str:
    """The default live probe: the harness's own CLI is installed and answers."""
    _resolved, version = _installed_binary(process, cwd, harness, binary)
    return f"{binary} installed and answering: {version}"


def _codex_live_probe_detail(
    process: SubprocessCertificationProcess, cwd: Path, harness: str, binary: str
) -> str:
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
    codex_bin, version = _installed_binary(process, cwd, harness, binary)
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


_DEEP_LIVE_PROBES["codex"] = _codex_live_probe_detail


def _all_checks_ok(checks: Iterable[CertificationCheck]) -> bool:
    """PASS and SKIP are both acceptable certification outcomes (A22.4).

    An honest degrade for an absent OPTIONAL runtime dependency (e.g. no installed
    Codex CLI on this host) must never turn a certification run RED — only a genuine
    FAIL does.
    """
    return all(item.status in ("PASS", "SKIP") for item in checks)


#: The doctor sections the certification tree owns — the `workspace` section reads the
#: sandbox itself and belongs to `exact-version-reconciliation`'s own step.
_OWNED_DOCTOR_SECTIONS = ("specs", "ledgers")


def _owned_doctor_sections_clean(stdout: str) -> str:
    """The verdict on a `dadaia doctor --json` payload: both owned sections, no findings.

    An absent section is a FAILURE, never a silent pass: a renamed or dropped section
    means the check saw nothing, and "clean" about nothing is not a verdict.
    """
    sections = json.loads(stdout)["sections"]
    missing = [name for name in _OWNED_DOCTOR_SECTIONS if name not in sections]
    if missing:
        raise RuntimeError(
            f"doctor payload carries no {', '.join(missing)} section — this check judges "
            f"{', '.join(_OWNED_DOCTOR_SECTIONS)} and cannot vouch for a section it never read"
        )
    owned = {name: sections[name]["findings"] for name in _OWNED_DOCTOR_SECTIONS}
    if any(owned.values()):
        raise RuntimeError(f"doctor not clean: {json.dumps(owned, sort_keys=True)}")
    return "specs and ledgers sections clean"


def certify(
    workspace_root: Path, process: SubprocessCertificationProcess, *, keep: bool = False
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

    def doctor_clean(*args: str) -> str:
        """`dadaia doctor` over the tree these arguments NAME, judged on the sections
        that tree owns: `specs` and `ledgers`.

        The `workspace` section reads the certification sandbox itself, which
        `exact-version-reconciliation`'s own `workspace-doctor` step already owns — so
        judging it here would make two checks fail for one defect, in a tree neither
        argument names. The doctor's exit code is that whole-workspace verdict, hence
        the direct run: a non-zero exit is not this check's failure to report.
        """
        proc = process.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", "doctor", *args, "--json"],
            cwd=target,
            env=env,
            timeout=180,
        )
        if not proc.stdout.strip():
            raise RuntimeError(f"doctor emitted no payload: {(proc.stderr or '').strip()}")
        return _owned_doctor_sections_clean(proc.stdout)

    check(
        "workspace-init",
        lambda: (
            cli("init", str(target), "--harness", "claude", cwd=run_root)
            and "workspace initialized with the claude projection"
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
            and doctor_clean("--specs-dir", str(standalone_specs))
        ),
    )

    bare = run_root / "consumer.git"

    def empty_remote() -> str:
        _git(process, run_root, "init", "--bare", str(bare))
        cli(
            "context",
            "create",
            "certified-consumer",
            "--main-repo",
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

    def bind() -> str:
        output = cli("context", "bind", "certified-consumer", extra_env=harness_env)
        if "certified-consumer" not in output:
            raise RuntimeError(output)
        return "caller-owned bind"

    check("context-bind", bind)
    check(
        "context-specs-doctor",
        lambda: doctor_clean("--context", "certified-consumer"),
    )

    def handoff_validation() -> str:
        path = target / ".dadaia" / "handoff" / "certified-consumer" / "cert.handoff.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "handoff-v1.2",
                    "self_pull": {"refs": ["specs/memory/QUALITY.md"]},
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
        cli("reports", "validate", str(path), "--json")
        return "reports validate accepted a handoff-v1.2 record"

    check("reports-handoff-validation", handoff_validation)

    def context_round_trip() -> str:
        cli("context", "dead", "certified-consumer", "--commit")
        cli("context", "alive", "certified-consumer")
        cli("context", "dead", "certified-consumer")
        cli("context", "delete", "certified-consumer")
        rows = json.loads(cli("context", "list", "--json"))
        if rows:
            raise RuntimeError(f"context delete left entries: {rows}")
        return "release, dead, alive, dead, delete"

    check("context-dead-alive-delete-roundtrip", context_round_trip)

    # One `<harness>-live-probe` per REGISTERED record, by iteration — a
    # harness that joins the registry is probed without a line here. Static projection
    # tests attest file shape only; these attest that the runtime answers. An absent
    # binary leaves the claim UNVERIFIED (honest SKIP), never a FAIL.
    for harness in L1_ENTRY_HARNESSES:
        binary = _HARNESS_PROBE_BINARIES[harness]
        probe = _DEEP_LIVE_PROBES.get(harness, _version_probe_detail)
        check(f"{harness}-live-probe", partial(probe, process, target, harness, binary))

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
