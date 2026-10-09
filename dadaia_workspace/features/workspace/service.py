"""WorkspaceService — bootstrap and management of the .dadaia/ template."""

import json
import os
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.workspace_layout import LEVEL1_SEEDS, occupied, provisioned_zones
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_EMPTY_SERVER_REGISTRY = {
    "version": "1",
    "range": {"min_port": 3000, "max_port": 3999},
    "entries": [],
}


class WorkspaceService:
    def __init__(
        self,
        public_assets: FileSystemPublicAssetManager,
        python_env: VenvPythonEnvironmentManager,
        hold: Callable[[Path, Path, str], object] = lambda *_: None,
    ) -> None:
        self._public_assets = public_assets
        self._python_env = python_env
        self._hold = hold

    def init(
        self,
        workspace_root: Path,
        harnesses: tuple[str, ...],
        skip_assets: bool = False,
    ) -> list[str]:
        """Bootstrap ``.dadaia/`` and return installed assets.

        Re-init merges required *harnesses* because init deletes no projection."""
        states_dir = workspace_root / ".dadaia" / "states"
        chosen_set = set(harnesses)

        # Run the venv manager before zone creation so an empty directory cannot look provisioned.
        self._python_env.ensure_workspace_venv(str(workspace_root))
        for zone in provisioned_zones():
            (workspace_root / ".dadaia" / zone.name).mkdir(parents=True, exist_ok=True)
        for name, seed in LEVEL1_SEEDS.items():  # the operator's from then on (ADR 0095)
            if not occupied(target := workspace_root / name):
                target.write_text(seed(workspace_root), encoding="utf-8")
        # Harness directories come from projections; only the shared skills root is eager.
        (workspace_root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)

        JsonContextStore(states_dir).seed_if_absent()
        server_registry = states_dir / "server_registry.json"
        if not occupied(server_registry):
            server_registry.write_text(
                json.dumps(_EMPTY_SERVER_REGISTRY, indent=2), encoding="utf-8"
            )
        self._migrate_denylist(workspace_root, states_dir / "privacy_denylist.json")

        store = JsonHarnessProfileStore()
        persisted = store.read(states_dir)
        merged = chosen_set | (set(persisted.harnesses) if persisted is not None else set())
        ordered = tuple(h for h in L1_ENTRY_HARNESSES if h in merged) + tuple(
            sorted(merged - set(L1_ENTRY_HARNESSES))
        )
        store.write(states_dir, HarnessProfile.of(ordered))

        # Public install owns every hook setting; skipping it must report an ungated workspace.
        if not skip_assets:
            return self._public_assets.install(workspace_root)
        return [
            "[warn] assets skipped — no hooks configured; the workspace is ungated "
            f"until '{fix_line(workspace_root, 'public', 'install')}' runs"
        ]

    def venv_change(self, workspace_root: Path) -> tuple[str | None, str | None, str]:
        """``(before, after, action)`` of the venv against the running distribution."""
        return self._python_env.version_change(str(workspace_root))

    def harnesses(self, workspace_root: Path) -> tuple[str, ...]:
        """The workspace's persisted harness profile — a re-init needs no ``--harness``."""
        states_dir = workspace_root / ".dadaia" / "states"
        return JsonHarnessProfileStore().resolve(states_dir, workspace_root).harnesses

    def _migrate_denylist(self, workspace_root: Path, path: Path) -> None:
        """Rewrite the legacy string-pair list as the object form.

        Stage before holding the original so failure never leaves the terms unreadable."""
        staged = path.with_name(f"{path.name}.migrating")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            pairs = [[e, ""] if isinstance(e, str) else e for e in raw]
            if not isinstance(raw, list) or not all(
                isinstance(p, list) and len(p) == 2 and all(isinstance(x, str) for x in p)
                for p in pairs
            ):
                return
            atomic_write(staged, json.dumps(dict(pairs), indent=2))
            if self._hold(workspace_root, path, path.name):
                os.replace(staged, path)
        except (OSError, ValueError, TypeError):
            return
