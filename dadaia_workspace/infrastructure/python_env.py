"""Python venv manager — creates .dadaia/.venv/ idempotently.

Executable paths are constructed using ``PLATFORM.venv_scripts_dir`` and
``PLATFORM.venv_exe_suffix`` so that the paths are correct on both POSIX
(``bin/python``) and Windows (``Scripts/python.exe``).
"""

import base64
import hashlib
import logging
import os
import subprocess
import venv
import zipfile
from collections.abc import Callable
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


def bootstrap_failure_message(
    *, spec: str, repack: str | None, pip_tail: str, spec_from_operator: bool
) -> str:
    """Describe a venv bootstrap failure by what actually happened.

    Two facts vary independently and the operator needs both: whether re-packing the
    running distribution produced a wheel (``repack``), and whether the spec being
    installed already came from the ``DADAIA_BOOTSTRAP_PACKAGE`` escape hatch
    (``spec_from_operator``). Asserting one fixed story for every combination sent the
    consumer validator chasing a re-pack that had in fact succeeded, and prescribed the
    very env var that was already set.
    """
    if repack is None:
        cause = "and the running distribution could not be re-packed as a local wheel"
    else:
        cause = f"and the re-packed running distribution ('{repack}') failed to install too"
    if spec_from_operator:
        # The wheel itself is already local; what is left unresolvable is its
        # dependencies, so name the way to make THOSE reachable.
        remedy = (
            "DADAIA_BOOTSTRAP_PACKAGE already points at a local wheel, so the wheel is "
            "not what is missing — its dependencies are. Make them reachable: either "
            "restore access to a package index, or pre-download them once and install "
            "from that directory, e.g. `pip download dadaia-workspace -d <dir>` on a "
            "connected host, then re-run with PIP_FIND_LINKS=<dir> (pip's --find-links)."
        )
    else:
        remedy = (
            "If this version is not published on the index (e.g. a candidate wheel under "
            "validation) or the index is unreachable, point DADAIA_BOOTSTRAP_PACKAGE at "
            "the local wheel file and retry, e.g. "
            "DADAIA_BOOTSTRAP_PACKAGE=/path/to/dadaia_workspace-X.Y.Z-py3-none-any.whl "
            "dadaia init."
        )
    return f"workspace venv bootstrap failed installing '{spec}' ({cause}). {remedy} Installer output: {pip_tail}"


class VenvPythonEnvironmentManager:
    def _upgrade_pip(
        self, pip_executable: Path | str, *, runner: Callable[..., object] | None = None
    ) -> None:
        """Best-effort upgrade of the venv's bundled pip. NEVER a gate.

        ``venv.create(with_pip=True)`` leaves whatever pip the host interpreter bundles,
        and an old one carries real advisories — path traversal when extracting a wheel,
        symlink escape when extracting a tar, mishandling of concatenated archives. A
        consumer workspace's venv goes on to install other packages with that pip, so the
        exposure is not theoretical (bug ``workspace-venv-ships-vulnerable-pip``).

        It is deliberately best-effort: the offline-first bootstrap is a documented
        property, so an unreachable index, a proxy, or any other failure is a SILENT
        no-op. An air-gapped ``init`` keeps working exactly as before — it just keeps the
        pip it had.
        """
        import subprocess as _sp

        run: Callable[..., object] = runner if runner is not None else _sp.check_call
        try:
            run(
                [str(pip_executable), "install", "--quiet", "--upgrade", "pip"],
                timeout=120,
            )
        except Exception:  # noqa: BLE001 — best-effort by design; never fail the bootstrap
            logging.getLogger(__name__).debug(
                "pip upgrade skipped (no index reachable or upgrade refused)"
            )

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
            try:
                venv.create(str(venv_dir), with_pip=True)
            except OSError as exc:
                # Bug r3b-portability-import-venv-permission (F-16/F-22 class): on a
                # noexec mount, venv.create writes bin/python and then dies inside
                # ensurepip because that interpreter cannot be EXECUTED there. The
                # filesystem limit is legitimate; the ~40-line raw traceback that used
                # to reach the operator was not. Surface every OSError as one clean,
                # actionable DadaiaError line naming the path and the likely cause.
                raise WorkspaceVenvBootstrapError(
                    f"could not create the workspace venv at '{venv_dir}': {exc}. "
                    "The most common cause is a target filesystem mounted 'noexec' "
                    "(or lacking execute permission), where the venv's own python "
                    "cannot be run — /tmp is mounted this way on many hardened hosts "
                    "and containers. Re-target the workspace onto an exec-capable "
                    "filesystem, or remount it without 'noexec', then retry."
                ) from exc
        if not self._dadaia_entrypoint(workspace_root).exists():
            spec = self._install_spec()
            pip = self.pip_executable(workspace_root)
            self._upgrade_pip(pip)
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
                # Report the outcome that actually happened, and never prescribe the
                # remedy the operator already applied (validation-028 cascade; bug
                # init-offline-bootstrap-repack-misdiagnosed-as-repack-failure).
                pip_tail = ((exc.stderr or exc.output or "") if exc else "").strip()[-400:]
                raise WorkspaceVenvBootstrapError(
                    bootstrap_failure_message(
                        spec=spec,
                        repack=repacked.name if repacked is not None else None,
                        pip_tail=pip_tail,
                        spec_from_operator=bool(
                            os.environ.get("DADAIA_BOOTSTRAP_PACKAGE", "").strip()
                        ),
                    )
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
