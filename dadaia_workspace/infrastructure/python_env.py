"""Python venv manager — creates .dadaia/.venv/ idempotently.

Executable paths are constructed using ``PLATFORM.venv_scripts_dir`` and
``PLATFORM.venv_exe_suffix`` so that the paths are correct on both POSIX
(``bin/python``) and Windows (``Scripts/python.exe``).
"""

import base64
import hashlib
import ntpath
import os
import re
import shutil
import subprocess
import sys
import zipfile
from importlib import metadata
from pathlib import Path

import dadaia_workspace
from dadaia_workspace.core.exceptions import (
    BootstrapPackageError,
    WorkspaceVenvBootstrapError,
)
from dadaia_workspace.core.platform import PLATFORM

__all__ = [
    "VenvPythonEnvironmentManager",
    "WorkspaceVenvBootstrapError",
    "repack_installed_wheel",
]


def repack_installed_wheel(
    dest_dir: Path, dist: "metadata.Distribution | None" = None
) -> Path | None:
    """Re-pack the RUNNING installed distribution into a wheel under *dest_dir*.

    Bug certify-cannot-install-installed-provider: a disposable venv bootstrap that pins
    ``dadaia-workspace==<running version>`` cannot resolve an UNPUBLISHED candidate (or a
    yanked release, or any version on an offline host) from the index. The installed
    distribution itself IS a reproducible source: a wheel is site-packages payload +
    dist-info, so the exact running version is re-packed file-for-file with a regenerated
    RECORD (pip verifies those hashes at install time).

    Returns ``None`` — never raises — when there is nothing honest to re-pack: no
    installed distribution, or an editable/source install (its RECORD carries only a
    ``.pth`` redirect, not the package payload).
    """
    if dist is None:
        try:
            dist = metadata.distribution("dadaia-workspace")
        except metadata.PackageNotFoundError:
            return None
    files = dist.files or []
    dist_info_prefix: str | None = None
    entries: list[tuple[str, bytes]] = []
    try:
        for packed in files:
            rel = packed.as_posix()
            if rel.endswith(".pyc") or "__pycache__" in rel:
                continue
            if rel.startswith(".."):
                # Scripts/data installed OUTSIDE site-packages (bin/dadaia): pip
                # regenerates console scripts from entry_points at install time.
                continue
            first = rel.split("/", 1)[0]
            if first.endswith(".dist-info"):
                dist_info_prefix = first
                if rel.split("/")[-1] == "RECORD":
                    continue  # regenerated below with fresh hashes
            entry_path = Path(str(dist.locate_file(packed)))
            if not entry_path.is_file():
                continue
            entries.append((rel, entry_path.read_bytes()))
    except OSError:
        return None
    if dist_info_prefix is None:
        return None
    payload = [
        rel
        for rel, _data in entries
        if not rel.startswith(dist_info_prefix)
        and not rel.endswith(".pth")
        and not rel.startswith("__editable__")
    ]
    if not payload:
        return None  # editable/source install: only the dist-info + .pth redirect
    version = dist.version
    name = dist_info_prefix[: -len(".dist-info")].rsplit("-", 1)[0]
    wheel_path = dest_dir / f"{name}-{version}-py3-none-any.whl"
    dest_dir.mkdir(parents=True, exist_ok=True)
    record_lines: list[str] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel, data in entries:
            zf.writestr(rel, data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
            record_lines.append(f"{rel},sha256={digest.decode()},{len(data)}")
        record_lines.append(f"{dist_info_prefix}/RECORD,,")
        zf.writestr(f"{dist_info_prefix}/RECORD", "\n".join(record_lines) + "\n")
    return wheel_path


# ── requires-python interpreter resolution ────────────────────────────────────────
#
# Bug init-venv-bootstrap-inherits-degraded-base-python: stdlib ``venv.create()``
# resolves a NEW venv's base interpreter through ``sys._base_executable`` of the
# CALLING process. On a venv created with ``symlinks=False`` ("--copies" — exactly
# what ``venv.create(..., with_pip=True)`` used here without an explicit ``symlinks``
# argument), CPython's getpath.c re-derives that value via a landmark search for the
# OS-level *unversioned* ``python3`` name inside the recorded ``home`` directory — NOT
# the version-pinned ``executable`` its own ``pyvenv.cfg`` records. When the host's
# unversioned ``/usr/bin/python3`` is a symlink to an OLDER interpreter than the one
# actually running (e.g. a Debian/Ubuntu host that keeps 3.10 as the OS default
# alongside an installed 3.12), every child venv silently degrades and the subsequent
# package install fails opaquely with "requires a different Python". Reproduced on
# this exact host class: a `.dadaia/.venv` built with `--copies` reports
# `sys._base_executable == "/usr/bin/python3"` (a symlink to 3.10) while its own
# `pyvenv.cfg` `executable` field correctly names `/usr/bin/python3.12` (the
# interpreter that actually built it), and the running interpreter is itself 3.12.
#
# The fix: never trust that implicit resolution. Resolve and VERIFY an interpreter
# explicitly (by executing each candidate and checking ITS reported version), then
# hand it to ``python -m venv`` via subprocess — which re-derives its OWN base
# correctly because IT is not the degraded ``--copies`` binary.

_REQUIRES_PYTHON_CLAUSE_RE = re.compile(r"(>=|<=|==|!=|>|<)\s*([0-9]+(?:\.[0-9]+){0,2})")
_REQUIRES_PYTHON_FLOOR_RE = re.compile(r">=\s*3\.(\d+)")
_DEFAULT_FLOOR_MINOR = 12  # dadaia-workspace's floor today (pyproject.toml: python = "^3.12")


def _version_satisfies(version: tuple[int, ...], spec: str | None) -> bool:
    """Check *version* (major, minor[, micro]) against a comma-separated, PEP
    440-shaped ``Requires-Python`` specifier (e.g. ``'>=3.12,<4.0'``) — release-segment
    comparison operators only (Requires-Python never uses pre-release/local segments in
    practice). An empty/unparsable spec, or an unparsable clause within it, is treated
    as satisfied: this gate is a fast, actionable pre-check, never the final authority
    — the actual ``pip install`` remains that.
    """
    text = (spec or "").strip()
    if not text:
        return True
    for raw_clause in text.split(","):
        clause = raw_clause.strip()
        if not clause:
            continue
        match = _REQUIRES_PYTHON_CLAUSE_RE.match(clause)
        if not match:
            continue
        op, ver_str = match.groups()
        bound = tuple(int(p) for p in ver_str.split("."))
        width = max(len(version), len(bound))
        v = version + (0,) * (width - len(version))
        b = bound + (0,) * (width - len(bound))
        if op == ">=" and not v >= b:
            return False
        if op == "<=" and not v <= b:
            return False
        if op == ">" and not v > b:
            return False
        if op == "<" and not v < b:
            return False
        if op == "==" and v != b:
            return False
        if op == "!=" and v == b:
            return False
    return True


#: Bound on the interpreter-probe subprocess (v0.4.3 T-043-13/A9.2, CWE-426 sibling
#: hardening): a hung or interactive candidate must degrade to ``None``, never wedge
#: the bootstrap indefinitely.
_INTERPRETER_PROBE_TIMEOUT_SECONDS = 10


def _interpreter_version(executable: str) -> tuple[int, int, int] | None:
    """Best-effort: ask *executable* for its OWN ``sys.version_info`` by RUNNING it —
    never trust a name or a recorded config value without executing it. Any failure to
    do so (missing binary, not executable, unexpected output, a hang past the bound,
    or the process itself misbehaving) yields ``None`` — the candidate is simply
    skipped, never a hard failure.

    The probe is bounded (``timeout=``) and never inherits the caller's stdin
    (``stdin=subprocess.DEVNULL``, v0.4.3 T-043-13/A9.2) — an interactive or hanging
    candidate on an untrusted PATH must not wedge the whole bootstrap.
    """
    try:
        proc = subprocess.run(
            [executable, "-c", "import sys; print(*sys.version_info[:3])"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_INTERPRETER_PROBE_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    parts = proc.stdout.split()
    if len(parts) < 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def _current_venv_pyvenv_executable() -> str | None:
    """The ``executable`` field of the ``pyvenv.cfg`` governing the RUNNING
    interpreter, when the running interpreter is itself inside a venv. This is the
    value ``venv.create()`` fails to honor for a NEW child venv (see module note
    above) — it was written by the interpreter that actually built THIS venv, so it
    is authoritative regardless of any later OS-level symlink drift.

    CWE-426 (untrusted search path, v0.4.3 T-043-13/A9.1): ``pyvenv.cfg`` is a plain
    text file a caller could hand-edit or a compromised prior bootstrap could have
    written; its ``executable`` value is REJECTED here — before any caller can hand it
    to :func:`_interpreter_version`/``subprocess.run`` — unless it is an absolute path.
    """
    cfg = Path(sys.prefix) / "pyvenv.cfg"
    if not cfg.is_file():
        return None
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "executable":
            candidate = value.strip()
            return candidate if os.path.isabs(candidate) else None
    return None


def _min_floor_minor(spec: str | None) -> int:
    """Extract the '>=3.N' floor minor from a Requires-Python spec, defaulting to the
    package's current floor when unparsable — drives how far above the floor
    ``_path_candidates`` looks for a version-pinned interpreter on PATH.
    """
    if spec:
        match = _REQUIRES_PYTHON_FLOOR_RE.search(spec)
        if match:
            return int(match.group(1))
    return _DEFAULT_FLOOR_MINOR


def _path_candidates(min_minor: int) -> list[str]:
    """Version-pinned ``pythonX.Y`` executables found on PATH, newest-first, from one
    minor above *min_minor* down to *min_minor* itself — the common case of an OS
    whose unversioned ``python3`` is degraded but a version-pinned interpreter sits
    alongside it (e.g. ``/usr/bin/python3.12`` next to a ``python3 -> python3.10``
    symlink).

    CWE-426 (untrusted search path, v0.4.3 T-043-13/A9.1): on POSIX, ``shutil.which``
    can return a RELATIVE path when PATH itself carries a relative entry (e.g. a
    leading ``.`` — an untrusted or misconfigured PATH). A relative result is rejected
    here, before it can reach :func:`_interpreter_version`/``subprocess.run``.
    """
    found: list[str] = []
    for minor in (min_minor + 1, min_minor):
        exe = shutil.which(f"python3.{minor}")
        if exe and os.path.isabs(exe):
            found.append(exe)
    return found


def _is_fully_qualified(candidate: str) -> bool:
    """True iff *candidate* is unambiguously rooted regardless of the current working
    directory OR (on Windows) the current drive (v0.4.3 T-043-23 security-review
    rework, LOW residual, CWE-426).

    ``os.path.isabs`` alone is not enough at the probe boundary: on Python 3.12,
    ``ntpath.isabs`` treats a DRIVE-RELATIVE path — exactly one leading separator, no
    drive letter, e.g. ``\\tools\\python.exe`` — as absolute, even though it resolves
    against whatever drive happens to be current, not a fully qualified location.
    (Python 3.13 tightened ``ntpath.isabs`` to require a drive too; this project pins
    ``python = \"^3.12\"``, so the probe cannot rely on that yet.)

    Routed through the ``ntpath`` module explicitly — never the host-bound ``os.path``
    — when ``os.name == \"nt\"``: this makes the Windows-specific check provable on any
    host OS (``ntpath`` is a pure-Python module, always importable regardless of the
    running platform), and is exactly what real Windows already does (there,
    ``os.path`` IS ``ntpath``). POSIX (``os.name != \"nt\"``) is unaffected — plain
    ``os.path.isabs`` has no such gap there.
    """
    if os.name == "nt":
        return ntpath.isabs(candidate) and ntpath.splitdrive(candidate)[0] != ""
    return os.path.isabs(candidate)


class VenvPythonEnvironmentManager:
    def _venv_path(self, workspace_root: str) -> Path:
        return Path(workspace_root) / ".dadaia" / ".venv"

    def _dadaia_entrypoint(self, workspace_root: str) -> Path:
        return (
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"dadaia{PLATFORM.venv_exe_suffix}"
        )

    def _install_spec(self) -> str:
        """Resolve what to ``pip install`` so the venv mirrors the running distribution.

        Self-hosting (the package importable from a source checkout with a
        ``pyproject.toml``): install that checkout editable, so the workspace venv tracks
        source edits. Otherwise (wheel install, e.g. pipx/PyPI): pin the exact running
        version from the index.
        """
        candidate = os.environ.get("DADAIA_BOOTSTRAP_PACKAGE", "").strip()
        if candidate:
            candidate_path = Path(candidate).expanduser().resolve()
            if not candidate_path.is_file() or candidate_path.suffix != ".whl":
                raise BootstrapPackageError.for_value(candidate)
            return str(candidate_path)
        src_root = Path(dadaia_workspace.__file__).resolve().parent.parent
        if (src_root / "pyproject.toml").is_file():
            return str(src_root)
        return f"dadaia-workspace=={metadata.version('dadaia-workspace')}"

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        """Ensure a venv that satisfies doctor VENV-1: create it AND install the package.

        Idempotent repair, not exists-check-and-bail: an existing venv missing the
        ``dadaia`` entrypoint (the exact state doctor VENV-1 flags) is repaired by
        installing ``dadaia_workspace`` into it (bug
        init-venv-never-installs-dadaia-workspace).
        """
        venv_dir = self._venv_path(workspace_root)
        if not venv_dir.exists():
            # Bug init-venv-bootstrap-inherits-degraded-base-python: never hand
            # venv.create() the implicit (and, on a --copies venv, provably degraded)
            # sys._base_executable resolution. Resolve and VERIFY an interpreter
            # explicitly, then create the child venv from THAT interpreter via
            # subprocess — it re-derives its own base correctly because it is not the
            # degraded binary this process may itself be running under. ``--copies``
            # preserved explicitly to match ``venv.create(..., with_pip=True)``'s prior
            # default (module-function default is copies, not symlinks).
            interpreter = self._resolve_child_venv_interpreter()
            try:
                subprocess.run(
                    [interpreter, "-m", "venv", "--copies", str(venv_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except OSError as exc:
                # Bug r3b-portability-import-venv-permission (F-16/F-22 class): on a
                # noexec mount, the RESOLVED interpreter itself cannot be spawned/run
                # there. The filesystem limit is legitimate; the ~40-line raw traceback
                # that used to reach the operator was not. Surface every OSError as one
                # clean, actionable DadaiaError line naming the path and the likely
                # cause.
                raise WorkspaceVenvBootstrapError(
                    f"could not create the workspace venv at '{venv_dir}' with "
                    f"interpreter '{interpreter}': {exc}. "
                    "The most common cause is a target filesystem mounted 'noexec' "
                    "(or lacking execute permission), where the venv's own python "
                    "cannot be run — /tmp is mounted this way on many hardened hosts "
                    "and containers. Re-target the workspace onto an exec-capable "
                    "filesystem, or remount it without 'noexec', then retry."
                ) from exc
            except subprocess.CalledProcessError as exc:
                # Same noexec class, one level deeper: the interpreter spawns fine (it
                # lives outside the noexec mount) but venv's internal ensurepip step
                # fails EXECUTING the freshly-copied interpreter inside the
                # noexec-mounted target dir, surfacing here as a non-zero child exit
                # rather than an OSError on our own spawn.
                stderr_tail = (exc.stderr or exc.output or "").strip()[-500:]
                raise WorkspaceVenvBootstrapError(
                    f"could not create the workspace venv at '{venv_dir}' with "
                    f"interpreter '{interpreter}': venv creation failed. "
                    "The most common cause is a target filesystem mounted 'noexec' "
                    "(or lacking execute permission), where the venv's own python "
                    "cannot be run — /tmp is mounted this way on many hardened hosts "
                    "and containers. Re-target the workspace onto an exec-capable "
                    "filesystem, or remount it without 'noexec', then retry. "
                    f"Diagnostics: {stderr_tail}"
                ) from exc
        if not self._dadaia_entrypoint(workspace_root).exists():
            # Post-condition (BEFORE any pip install): the venv's OWN python must
            # satisfy Requires-Python. Catches an interpreter mismatch from ANY path —
            # a fresh creation this method did not anticipate, or a pre-existing/
            # manually-created venv doctor's VENV-1 repair walks into — as an
            # actionable "interpreter mismatch", never pip's bare, rootless "requires a
            # different Python" failure.
            self._assert_child_interpreter_version(workspace_root)
            spec = self._install_spec()
            pip = self.pip_executable(workspace_root)
            install_cmd = [pip, "install", "--quiet"]
            editable = Path(spec).is_dir()
            if editable:
                install_cmd.append("--editable")
            install_cmd.append(spec)
            # Bug init-succeeds-after-provider-bootstrap-failure: pip's stream is
            # CAPTURED — a resolvable-from-fallback index miss must not leak a raw
            # "ERROR: Could not find a version..." into init's output, where it reads
            # as a masked broken bootstrap.
            try:
                subprocess.run(install_cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                # Unpublished candidate wheels are the consumer-validation norm: the
                # exact-version pin cannot resolve from the index (bug
                # certify-cannot-install-installed-provider). The RUNNING installed
                # distribution is itself a reproducible source — re-pack it as a wheel
                # and install THAT, so init/certify/reconcile bootstrap the exact
                # installed version with no index and no env var.
                repacked = repack_installed_wheel(
                    Path(workspace_root) / ".dadaia" / "tmp" / "bootstrap-wheel"
                )
                if repacked is not None:
                    print(
                        f"[bootstrap] index could not resolve '{spec}'; installing the "
                        f"re-packed running distribution ({repacked.name}) instead"
                    )
                    try:
                        subprocess.run(
                            [pip, "install", "--quiet", str(repacked)],
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                        self._ensure_ci_toolchain(pip)
                        self._verify_venv_provider(workspace_root, expected=self._running_version())
                        return str(venv_dir)
                    except subprocess.CalledProcessError:
                        pass
                # Name the escape hatch that exists for exactly this case (a raw
                # CalledProcessError traceback pointed nowhere — validation-028 cascade).
                pip_tail = ((exc.stderr or exc.output or "") if exc else "").strip()[-400:]
                raise WorkspaceVenvBootstrapError(
                    f"workspace venv bootstrap failed installing '{spec}' (and the "
                    "running distribution could not be re-packed as a local wheel). If "
                    "this version is not published on the index (e.g. a candidate wheel "
                    "under validation) or the index is unreachable, point "
                    "DADAIA_BOOTSTRAP_PACKAGE at the local wheel file and retry, e.g. "
                    "DADAIA_BOOTSTRAP_PACKAGE=/path/to/dadaia_workspace-X.Y.Z-py3-none-any.whl "
                    f"dadaia init. Installer output: {pip_tail}"
                ) from exc
            self._ensure_ci_toolchain(pip)
            # Success is only reported after the venv provider VERIFIES independently
            # (clean env, no inherited PYTHONPATH). The exact running version is
            # required for the pin path; an operator-chosen wheel (env override) or a
            # self-hosting editable checkout may legitimately differ, so those verify
            # import-integrity only.
            expected = (
                None
                if editable or os.environ.get("DADAIA_BOOTSTRAP_PACKAGE", "").strip()
                else self._running_version()
            )
            self._verify_venv_provider(workspace_root, expected=expected)
        return str(venv_dir)

    def _resolve_child_venv_interpreter(self) -> str:
        """Resolve an interpreter for a NEW child venv that PROVABLY satisfies the
        package's Requires-Python — never venv.create()'s implicit resolution (bug
        init-venv-bootstrap-inherits-degraded-base-python; see the module-level note
        above ``_version_satisfies`` for the root cause).

        Candidates are tried in order; the first whose OWN reported version satisfies
        Requires-Python wins:

        1. ``sys._base_executable`` — correct on a non-degraded host (including the
           common "not running inside any venv at all" case, where it simply equals
           ``sys.executable``); cheap to check first.
        2. The ``executable`` recorded in the RUNNING venv's own ``pyvenv.cfg`` — the
           value venv.create() itself failed to honor for a child venv, and
           authoritative because it was written by the interpreter that built THIS
           venv.
        3. A version-pinned ``pythonX.Y`` found on PATH.
        """
        required = self._running_requires_python()
        ordered: list[str] = []
        base = getattr(sys, "_base_executable", None)
        if base:
            ordered.append(base)
        pyvenv_exe = _current_venv_pyvenv_executable()
        if pyvenv_exe:
            ordered.append(pyvenv_exe)
        ordered.extend(_path_candidates(_min_floor_minor(required)))

        seen: set[str] = set()
        diagnostics: list[str] = []
        for candidate in ordered:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            # Defense in depth (CWE-426, v0.4.3 T-043-13/A9.1): both source functions
            # above already reject a relative candidate, but the probe boundary itself
            # never spawns a non-absolute path either, regardless of how it got here.
            # v0.4.3 T-043-23 security-review rework: :func:`_is_fully_qualified`,
            # not bare ``os.path.isabs`` — see its own docstring for the Windows
            # drive-relative gap this closes. The two source-function filters above
            # are left as their original ``os.path.isabs`` form (per the handoff's
            # own recommendation) — this probe boundary is the one call site that
            # must never spawn a non-fully-qualified path, regardless of how a
            # candidate reached ``ordered``.
            if not _is_fully_qualified(candidate):
                diagnostics.append(f"{candidate}: relative path rejected")
                continue
            version = _interpreter_version(candidate)
            if version is None:
                diagnostics.append(f"{candidate}: not runnable")
                continue
            if _version_satisfies(version, required):
                return candidate
            diagnostics.append(f"{candidate}: Python {'.'.join(map(str, version))}")

        raise WorkspaceVenvBootstrapError(
            "could not resolve a Python interpreter satisfying dadaia-workspace's "
            f"required version ({required or 'unknown'}) to bootstrap a workspace "
            f"venv. Checked: {'; '.join(diagnostics) if diagnostics else 'no candidates found'}. "
            "Install a matching Python interpreter (a version-pinned 'pythonX.Y' on "
            "PATH is sufficient) and retry."
        )

    def _assert_child_interpreter_version(self, workspace_root: str) -> None:
        """Post-condition, checked BEFORE any pip install: the venv's OWN python must
        satisfy Requires-Python. Catches an interpreter mismatch left by ANY path that
        could produce one — a fresh creation this method did not anticipate, or a
        pre-existing/manually-created venv doctor's VENV-1 repair walks into — and
        names it as an actionable "interpreter mismatch", never pip's bare, rootless
        "requires a different Python" failure (bug
        init-venv-bootstrap-inherits-degraded-base-python).
        """
        required = self._running_requires_python()
        if required is None:
            return  # nothing to check against — fail open, matching _running_version()
        version = _interpreter_version(self.python_executable(workspace_root))
        if version is None:
            return  # could not introspect — pip install remains the final authority
        if not _version_satisfies(version, required):
            raise WorkspaceVenvBootstrapError(
                f"workspace venv interpreter mismatch: the venv at "
                f"'{self._venv_path(workspace_root)}' carries Python "
                f"{'.'.join(map(str, version))}, but dadaia-workspace requires Python "
                f"{required}. Recreate the venv with an interpreter that satisfies "
                "this requirement (delete the venv directory and re-run 'dadaia "
                "init', or point DADAIA_BOOTSTRAP_PACKAGE at a matching build) and "
                "retry."
            )

    @staticmethod
    def _ensure_ci_toolchain(pip: str) -> None:
        """Best-effort install of the CI/validation toolchain the product promises.

        Bug implementation-review-approves-unexecuted-validation: the generated venv
        could not even run ``python -m pytest`` — yet ``dadaia ci preflight`` and the
        executed-test close gate both depend on it. pytest ships with every bootstrap;
        failure to fetch it is a clean one-line warning, never a bootstrap failure (the
        close gate reports loudly when tests cannot run).
        """
        try:
            subprocess.run(
                [pip, "install", "--quiet", "pytest"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            print(
                "[bootstrap] warning: could not install pytest into the workspace venv; "
                "test validation (ci preflight, closure gate) will report it missing"
            )

    @staticmethod
    def _running_version() -> str | None:
        try:
            return metadata.version("dadaia-workspace")
        except metadata.PackageNotFoundError:
            return None

    @staticmethod
    def _running_requires_python() -> str | None:
        try:
            return metadata.distribution("dadaia-workspace").metadata.get("Requires-Python")
        except metadata.PackageNotFoundError:
            return None

    def _verify_venv_provider(self, workspace_root: str, expected: str | None = None) -> None:
        """Prove the venv's provider stands on its own — never via inherited paths.

        Bug init-succeeds-after-provider-bootstrap-failure: a generated venv command can
        LOOK usable through an inherited PYTHONPATH / parent-workspace resolution while
        the venv itself is incomplete. The check imports ``dadaia_workspace`` with the
        venv's own interpreter under a CLEAN environment and, when *expected* is given,
        requires the exact version.
        """
        clean_env = {"PATH": os.environ.get("PATH", "")}
        proc = subprocess.run(
            [
                self.python_executable(workspace_root),
                "-c",
                "import dadaia_workspace, importlib.metadata as m; "
                "print(m.version('dadaia-workspace'))",
            ],
            capture_output=True,
            text=True,
            env=clean_env,
            check=False,
        )
        if proc.returncode != 0:
            raise WorkspaceVenvBootstrapError(
                "workspace venv provider verification failed: the venv python cannot "
                "import dadaia_workspace on its own (no inherited paths). Installer "
                f"diagnostics: {(proc.stderr or proc.stdout or '').strip()[-400:]}"
            )
        installed = (proc.stdout or "").strip()
        if expected is not None and installed != expected:
            raise WorkspaceVenvBootstrapError(
                f"workspace venv provider verification failed: venv carries "
                f"dadaia-workspace {installed or '<unknown>'} but the running "
                f"distribution is {expected}. The bootstrap must converge on the exact "
                "running version."
            )

    def python_executable(self, workspace_root: str) -> str:
        return str(
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"python{PLATFORM.venv_exe_suffix}"
        )

    def pip_executable(self, workspace_root: str) -> str:
        return str(
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"pip{PLATFORM.venv_exe_suffix}"
        )
