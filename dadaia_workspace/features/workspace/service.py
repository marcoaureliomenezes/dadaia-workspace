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
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_EMPTY_CONTEXTS = {"schema_version": "2", "contexts": []}
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
        hold: Callable[[Path, Path, str], str | None] = lambda *_: None,
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
        """Bootstrap .dadaia/ template. Idempotent. Returns the installed assets.

        *harnesses* names the Layer-1 entry harnesses to scaffold (their projection
        directories plus per-harness hook registration) and is REQUIRED — there is no
        implied full set (0.4.7 FR1: `init` takes exactly one `--harness`). Only the
        chosen harnesses' directories, hooks, and asset projections are created; the
        selected set is persisted through the profile store (the source of truth for
        profile-aware install/doctor scoping, v0.1.58 FR3).

        Bug init-harness-profile-silent-narrowing: init deletes no projection, so it must
        never un-manage one — a re-init with a harness subset MERGES into the persisted
        profile (canonical L1 order, unknown names appended sorted).
        """
        states_dir = workspace_root / ".dadaia" / "states"
        chosen = tuple(harnesses)
        chosen_set = set(chosen)

        # The venv manager owns `.dadaia/.venv` and runs before the zone pass: an empty
        # pre-made `.venv` would read to it as an already-built venv.
        self._python_env.ensure_workspace_venv(str(workspace_root))
        for zone in provisioned_zones():
            (workspace_root / ".dadaia" / zone.name).mkdir(parents=True, exist_ok=True)
        for name, seed in LEVEL1_SEEDS.items():  # the operator's from then on (ADR 0095)
            if not occupied(target := workspace_root / name):
                target.write_text(seed(workspace_root), encoding="utf-8")
        # The shared skills root is harness-independent — always created.
        (workspace_root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
        # Every harness directory is created by its own projection (the record's
        # `directory`), never by a branch here.

        # Initialize JSON state files (idempotent — never overwrite existing data)
        self._init_json_file(states_dir / "spec_contexts.json", _EMPTY_CONTEXTS)
        self._init_json_file(states_dir / "server_registry.json", _EMPTY_SERVER_REGISTRY)
        self._migrate_denylist(workspace_root, states_dir / "privacy_denylist.json")

        store = JsonHarnessProfileStore()
        persisted = store.read(states_dir)
        merged = chosen_set | (set(persisted.harnesses) if persisted is not None else set())
        ordered = tuple(h for h in L1_ENTRY_HARNESSES if h in merged) + tuple(
            sorted(merged - set(L1_ENTRY_HARNESSES))
        )
        store.write(states_dir, HarnessProfile.of(ordered))

        # Install public assets — only the chosen harness projections. Every hook wiring
        # (.claude/settings.json, .codex/hooks.json, kimi user hooks) is install's output:
        # `public install` is the ONE settings writer (bug
        # init-skip-assets-writes-gateless-claude-settings — init's own gateless
        # UserPromptSubmit-only writer was deleted). Skipping assets therefore leaves the
        # workspace ungated, and that state must be loud, never silent.
        installed: list[str] = []
        if not skip_assets:
            installed.extend(self._public_assets.stage(workspace_root))
            # The roster install resolves the chosen-harness SUBSET on its own: it reads
            # the profile persisted above to scope its harness targets (v0.1.58 FR3).
            installed.extend(self._public_assets.install(workspace_root))
        else:
            installed.append(
                "[warn] assets skipped — no hooks configured; the workspace is ungated "
                f"until '{fix_line(workspace_root, 'public', 'install')}' runs"
            )

        return installed

    def venv_change(self, workspace_root: Path) -> tuple[str | None, str | None, str]:
        """``(before, after, action)`` of the venv against the running distribution."""
        return self._python_env.version_change(str(workspace_root))

    def harnesses(self, workspace_root: Path) -> tuple[str, ...]:
        """The workspace's persisted harness profile — a re-init needs no ``--harness``."""
        states_dir = workspace_root / ".dadaia" / "states"
        return JsonHarnessProfileStore().resolve(states_dir, workspace_root).harnesses

    def _init_json_file(self, path: Path, empty: dict) -> None:  # type: ignore[type-arg]
        if not occupied(path):
            path.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    def _migrate_denylist(self, workspace_root: Path, path: Path) -> None:
        """A 0.4.7 list form (``["term"]`` or ``[["term", "reason"]]``, strings only) rewritten
        once as the one object form (ADR 0157): the converted file lands beside it first, then
        the original is held and the conversion moved into place, so no failed step leaves the
        terms unreadable. Any other content is left for the loader to refuse."""
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
