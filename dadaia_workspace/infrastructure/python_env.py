"""Python venv manager — creates .dadaia/.venv/ idempotently.

Executable paths come from the platform door, so they are right on both POSIX
(``bin/python``) and Windows (``Scripts/python.exe``).
"""

import base64
import hashlib
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path

from packaging.version import Version

import dadaia_workspace
from dadaia_workspace.core import platform
from dadaia_workspace.core.exceptions import (
    BootstrapPackageError,
    WorkspaceVenvBootstrapError,
    WorkspaceVenvNewerError,
)
from dadaia_workspace.infrastructure.provider_version import provider_version

__all__ = [
    "VenvPythonEnvironmentManager",
    "WorkspaceVenvBootstrapError",
    "WorkspaceVenvNewerError",
    "repack_installed_wheel",
]


def repack_installed_wheel(
    dest_dir: Path, dist: "metadata.Distribution | None" = None
) -> Path | None:
    """Re-pack the RUNNING installed distribution into a wheel under *dest_dir*.

    A disposable venv bootstrap that pins ``dadaia-workspace==<running version>`` cannot
    resolve an unpublished candidate (or a yanked release, or any version on an offline
    host) from the index. The installed distribution itself is a reproducible source: a
    wheel is site-packages payload +
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
# ``venv.create()`` takes a new venv's base from the caller's ``sys._base_executable``,
# which a ``--copies`` venv re-derives from the host's unversioned ``python3`` (possibly an
# OLDER interpreter). Resolve and VERIFY an interpreter by executing it, then run
# ``python -m venv`` from THAT interpreter via subprocess.

_REQUIRES_PYTHON_CLAUSE_RE = re.compile(r"(>=|<=|==|!=|>|<)\s*([0-9]+(?:\.[0-9]+){0,2})")
_REQUIRES_PYTHON_FLOOR_RE = re.compile(r">=\s*3\.(\d+)")
_DEFAULT_FLOOR_MINOR = 12  # dadaia-workspace's floor today (pyproject.toml: python = "^3.12")


def build_digest(files: "Iterable[metadata.PackagePath] | None") -> str:
    """The payload's installed bytes digested — the build a version label cannot name, and a
    damaged file changes; the venv probe runs this same source, so both sides hash alike."""
    import hashlib
    from pathlib import Path

    digest = hashlib.sha256()
    for f in sorted(files or (), key=str):
        if f.parts[0] == "dadaia_workspace" and "__pycache__" not in f.parts:
            path = Path(f.locate())
            digest.update(f"{f}\n".encode())
            digest.update(hashlib.sha256(path.read_bytes() if path.is_file() else b"").digest())
    return digest.hexdigest()[:16]


def provider_build() -> str | None:
    """``"<version> <build digest>"`` of the running distribution, or ``None``."""
    version = provider_version()
    return version and f"{version} {build_digest(metadata.distribution('dadaia-workspace').files)}"


def _tail_lines(exc: subprocess.CalledProcessError, count: int = 5) -> str:
    """The last *count* whole lines of a failed installer's output — never cut mid-line."""
    return "\n".join((exc.stderr or exc.output or "").strip().split("\n")[-count:])


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


#: Bound on the interpreter-probe subprocess (CWE-426 sibling
#: hardening): a hung or interactive candidate must degrade to ``None``, never wedge
#: the bootstrap indefinitely.
_INTERPRETER_PROBE_TIMEOUT_SECONDS = 10


_VERSION_ARGS = ("-c", "import sys; print(*sys.version_info[:3])")


def _interpreter_version(executable: str) -> tuple[int, int, int] | None:
    """Best-effort: ask *executable* for its OWN ``sys.version_info`` by RUNNING it —
    never trust a name or a recorded config value without executing it. Any failure to
    do so (missing binary, not executable, unexpected output, a hang past the bound,
    or the process itself misbehaving) yields ``None`` — the candidate is simply
    skipped, never a hard failure.

    The probe is bounded (``timeout=``) and never inherits the caller's stdin
    (``stdin=subprocess.DEVNULL``) — an interactive or hanging
    candidate on an untrusted PATH must not wedge the whole bootstrap.
    """
    try:
        proc = platform.run(
            [executable, *_VERSION_ARGS],
            timeout=_INTERPRETER_PROBE_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _parsed_version(proc)


def _parsed_version(proc: "subprocess.CompletedProcess[str]") -> tuple[int, int, int] | None:
    """The ``(major, minor, micro)`` a :data:`_VERSION_ARGS` run printed, ``None`` when it failed."""
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

    CWE-426 (untrusted search path): ``pyvenv.cfg`` is a plain
    text file a caller could hand-edit or a compromised prior bootstrap could have
    written; its ``executable`` value is REJECTED here — before any caller can hand it
    to :func:`_interpreter_version` — unless it is an absolute path.
    """
    cfg = Path(sys.prefix) / "pyvenv.cfg"
    if not cfg.is_file():
        return None
    try:
        text = platform.decode(cfg.read_bytes())
    except OSError:
        return None
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "executable":
            candidate = value.strip()
            return candidate if platform.is_fully_qualified(candidate) else None
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

    CWE-426 (untrusted search path): ``shutil.which``
    can return a RELATIVE path when PATH itself carries a relative entry (e.g. a
    leading ``.`` — an untrusted or misconfigured PATH). A relative result is rejected
    here, before it can reach :func:`_interpreter_version`.
    """
    found: list[str] = []
    for minor in (min_minor + 1, min_minor):
        exe = shutil.which(f"python3.{minor}")
        if exe and platform.is_fully_qualified(exe):
            found.append(exe)
    return found


class VenvPythonEnvironmentManager:
    def _venv_path(self, workspace_root: str) -> Path:
        return platform.venv_dir(Path(workspace_root))

    def _dadaia_entrypoint(self, workspace_root: str) -> Path:
        return platform.workspace_cli_path(Path(workspace_root))

    def _install_spec(self, scratch_dir: str) -> str:
        """Resolve what to ``pip install`` so the venv mirrors the RUNNING distribution.

        A re-packed wheel is written under *scratch_dir*, which the caller deletes after
        the install (no wheel is left behind).

        Two paths, no index:

        * Self-hosting (the package importable from a source checkout with a
          ``pyproject.toml``): install that checkout editable, so the workspace venv
          tracks source edits.
        * Any other install (pipx, uvx, a git clone, PyPI): re-pack the running
          distribution into a local wheel and install THAT
          (:func:`repack_installed_wheel`) — the installed distribution is itself a
          reproducible source, so the venv gets the bootstrapper's own bytes.

        A package not importable from a checkout is never pinned from the index: an
        unpublished build declares the last published version, so an index pin would
        resolve to PyPI's bytes, not the bootstrapper's. The venv is installed from the
        re-packed running distribution instead.

        ``DADAIA_BOOTSTRAP_PACKAGE`` still names an explicit local wheel: it is the
        operator's override for validating a candidate build (see
        ``scripts/CONSUMER_VALIDATION_RECIPE.md``), not a bootstrap path of its own.
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
        repacked = repack_installed_wheel(Path(scratch_dir))
        if repacked is None:
            raise WorkspaceVenvBootstrapError(
                "workspace venv bootstrap cannot mirror the running distribution: "
                f"dadaia-workspace {provider_version()} is neither a "
                "source checkout nor a re-packable installed distribution. Point "
                "DADAIA_BOOTSTRAP_PACKAGE at a local wheel and retry, e.g. "
                "DADAIA_BOOTSTRAP_PACKAGE=/path/to/dadaia_workspace-X.Y.Z-py3-none-any.whl "
                "uvx dadaia-workspace init <dir> --harness <name>."
            )
        return str(repacked)

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        """Ensure a venv that satisfies doctor VENV-1: create it AND install the package.

        Idempotent repair, not exists-check-and-bail: an existing venv missing the
        ``dadaia`` entrypoint (the exact state doctor VENV-1 flags) is repaired by
        installing ``dadaia_workspace`` into it.
        """
        venv_dir = self._venv_path(workspace_root)
        if not venv_dir.exists():
            # Never hand venv.create() the implicit (and, on a --copies venv, provably degraded)
            # sys._base_executable resolution. Resolve and VERIFY an interpreter
            # explicitly, then create the child venv from THAT interpreter via
            # subprocess — it re-derives its own base correctly because it is not the
            # degraded binary this process may itself be running under. ``--copies``
            # preserved explicitly to match ``venv.create(..., with_pip=True)``'s prior
            # default (module-function default is copies, not symlinks).
            interpreter = self._resolve_child_venv_interpreter()
            try:
                platform.run([interpreter, "-m", "venv", "--copies", str(venv_dir)], check=True)
            except OSError as exc:
                # On a noexec mount the RESOLVED interpreter itself cannot be spawned or
                # run there. That filesystem limit is legitimate; every OSError surfaces as
                # one clean, actionable DadaiaError line naming the path and the likely
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
                # venv's own diagnostics name the cause: a base Python without
                # ensurepip (Debian's python3-venv split) says so; anything else is
                # most often the noexec class one level deeper (ensurepip executing
                # the freshly-copied interpreter inside a noexec target dir).
                stderr_tail = _tail_lines(exc)
                cause = (
                    "the base Python lacks the 'ensurepip'/'venv' modules (on Debian/"
                    "Ubuntu install python3-venv), then retry."
                    if "ensurepip is not available" in stderr_tail
                    else "the most common cause is a target filesystem mounted 'noexec' "
                    "(or lacking execute permission), where the venv's own python "
                    "cannot be run. Re-target the workspace onto an exec-capable "
                    "filesystem, or remount it without 'noexec', then retry."
                )
                raise WorkspaceVenvBootstrapError(
                    f"could not create the workspace venv at '{venv_dir}' with "
                    f"interpreter '{interpreter}': {cause} Diagnostics: {stderr_tail}"
                ) from exc
        if self.version_change(workspace_root)[2] != "same":
            # Post-condition (BEFORE any pip install): the venv's OWN python must
            # satisfy Requires-Python. Catches an interpreter mismatch from ANY path —
            # a fresh creation this method did not anticipate, or a pre-existing/
            # manually-created venv doctor's VENV-1 repair walks into — as an
            # actionable "interpreter mismatch", never pip's bare, rootless "requires a
            # different Python" failure.
            self._assert_child_interpreter_version(workspace_root)
            with tempfile.TemporaryDirectory(prefix="dadaia-wheel-") as scratch:
                spec = self._install_spec(scratch)
                # ONE pip transaction replaces any installed build (same label or not)
                # with its dependencies; on failure pip rolls back to the old build.
                install_cmd = ["-m", "pip", "install", "--quiet", "--force-reinstall"]
                editable = Path(spec).is_dir()
                if editable:
                    install_cmd.append("--editable")
                install_cmd.append(spec)
                # pip's stream is CAPTURED — a failure must not leak a raw "ERROR: Could not find a
                # version..." into init's output, where it reads as a masked broken bootstrap.
                try:
                    self._run_venv(workspace_root, *install_cmd, check=True)
                except subprocess.CalledProcessError as exc:
                    raise WorkspaceVenvBootstrapError(
                        f"workspace venv bootstrap failed installing '{spec}'. The "
                        "workspace venv resolves its dependencies from PyPI (network "
                        f"required). Installer output:\n{_tail_lines(exc)}"
                    ) from exc
            # Success is only reported after the venv provider VERIFIES independently
            # (clean env, no inherited PYTHONPATH). The re-packed path IS the running
            # distribution, so its exact version is required; an operator-chosen wheel
            # (env override) or a self-hosting editable checkout may legitimately
            # differ, so those verify import-integrity only.
            expected = (
                None
                if editable or os.environ.get("DADAIA_BOOTSTRAP_PACKAGE", "").strip()
                else provider_build()
            )
            self._verify_venv_provider(workspace_root, expected=expected)
        return str(venv_dir)

    def version_change(self, workspace_root: str) -> tuple[str | None, str | None, str]:
        """The ONE decider of which distribution the workspace runs: ``(before, after, action)``.

        The venv's identity is its build AND its binding: ``same`` only when the build
        equals the running distribution's and the ``dadaia`` entrypoint names THIS venv's
        python (a copied venv names the original's). ``action`` is ``install`` (no
        entrypoint), ``repair`` (its probe fails), ``upgrade`` (either differs; re-init is the
        upgrade) or ``same``; a venv with a NEWER version is refused before any write.
        """
        running = provider_build()
        after = running.split()[0] if running else None
        if not self._dadaia_entrypoint(workspace_root).exists():
            return None, after, "install"
        installed = self.installed_build(workspace_root)
        before = installed.split()[0] if installed else None
        if before is None or after is None:
            return before, after, "repair" if after else "same"
        if Version(before) > Version(after):
            raise WorkspaceVenvNewerError(before, after)
        # distlib writes the path after "#!", or after a double quote or a space (the
        # /bin/sh exec form for a spaced or over-long path); a copy names the original's.
        own = rb'(?<![^!"\s])' + re.escape(self.python_executable(workspace_root).encode("utf-8"))
        bound = re.search(own, self._dadaia_entrypoint(workspace_root).read_bytes())
        return before, after, "same" if installed == running and bound else "upgrade"

    def installed_build(self, workspace_root: str) -> str | None:
        """``"<version> <build digest>"`` the venv's own python reports, or ``None``."""
        if not self._dadaia_entrypoint(workspace_root).exists():
            return None
        try:
            proc = self._probe_provider(workspace_root)
        except WorkspaceVenvBootstrapError:
            return None
        return (proc.stdout or "").strip() or None if proc.returncode == 0 else None

    def _run_venv(
        self,
        workspace_root: str,
        *args: str,
        check: bool = False,
        env: dict[str, str] | None = None,
    ) -> "subprocess.CompletedProcess[str]":
        """Run the workspace venv's python.

        Args:
            workspace_root: The workspace whose venv python runs.
            *args: Its command-line arguments.
            check: Raise ``CalledProcessError`` on a non-zero exit.
            env: The child environment; ``None`` inherits this process's.

        Returns:
            The completed process, its output captured as text.

        Raises:
            WorkspaceVenvBootstrapError: The python cannot be started; its fix deletes the venv.
            subprocess.CalledProcessError: *check* and a non-zero exit.
        """
        try:
            return platform.run(
                [self.python_executable(workspace_root), *args], check=check, env=env
            )
        except OSError as exc:
            raise WorkspaceVenvBootstrapError(
                f"workspace venv python cannot run: {exc}.",
                f"Agent action: delete {platform.quote(str(self._venv_path(workspace_root)))} and run "
                f"`{platform.inline('uvx', 'dadaia-workspace', 'init', workspace_root)}`",
            ) from exc

    def _probe_provider(self, workspace_root: str) -> "subprocess.CompletedProcess[str]":
        """Ask the venv's own python, under a CLEAN env, which dadaia-workspace build it imports."""
        return self._run_venv(
            workspace_root,
            "-B",  # this probe writes no .pyc into an editable install's checkout
            "-c",
            f"{inspect.getsource(build_digest)}"
            "import dadaia_workspace, importlib.metadata as m\n"
            "d = m.distribution('dadaia-workspace')\n"
            "print(d.version, build_digest(d.files))",
            env={"PATH": os.environ.get("PATH", "")},
        )

    def _resolve_child_venv_interpreter(self) -> str:
        """Resolve an interpreter for a NEW child venv that provably satisfies the
        package's Requires-Python, never venv.create()'s implicit resolution (see the
        module-level note above ``_version_satisfies``).

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
            # Defense in depth (CWE-426): both source functions above already reject a
            # relative candidate, but the probe boundary itself never spawns a
            # non-fully-qualified path, however the candidate reached ``ordered``.
            if not platform.is_fully_qualified(candidate):
                diagnostics.append(f"{candidate}: relative path rejected")
                continue
            version = _interpreter_version(candidate)
            if version is None:
                diagnostics.append(f"{candidate}: not runnable")
                continue
            if _version_satisfies(version, required):
                return candidate
            diagnostics.append(f"{candidate}: Python {'.'.join(str(n) for n in version)}")

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
        "requires a different Python" failure.
        """
        required = self._running_requires_python()
        if required is None:
            return  # nothing to check against — fail open, matching provider_version()
        version = _parsed_version(self._run_venv(workspace_root, *_VERSION_ARGS))
        if version is None:
            return  # could not introspect — pip install remains the final authority
        if not _version_satisfies(version, required):
            raise WorkspaceVenvBootstrapError(
                f"workspace venv interpreter mismatch: the venv at "
                f"'{self._venv_path(workspace_root)}' carries Python "
                f"{'.'.join(str(n) for n in version)}, but dadaia-workspace requires Python "
                f"{required}. Recreate the venv with an interpreter that satisfies "
                "this requirement (delete the venv directory and re-run 'uvx "
                "dadaia-workspace init <dir>', or point DADAIA_BOOTSTRAP_PACKAGE at a matching build) and "
                "retry."
            )

    @staticmethod
    def _running_requires_python() -> str | None:
        try:
            return metadata.distribution("dadaia-workspace").metadata.get("Requires-Python")
        except metadata.PackageNotFoundError:
            return None

    def _verify_venv_provider(self, workspace_root: str, expected: str | None = None) -> None:
        """Prove the venv's provider stands on its own — never via inherited paths.

        A generated venv command can
        LOOK usable through an inherited PYTHONPATH / parent-workspace resolution while
        the venv itself is incomplete. The check imports ``dadaia_workspace`` with the
        venv's own interpreter under a CLEAN environment and, when *expected* is given,
        requires the exact version.
        """
        proc = self._probe_provider(workspace_root)
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
        return str(platform.python_in(self._venv_path(workspace_root)))
