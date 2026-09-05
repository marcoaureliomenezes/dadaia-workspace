"""WorkspaceService — bootstrap and management of the .dadaia/ template."""

import json
from pathlib import Path

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.workspace import Workspace
from dadaia_workspace.core.workspace_layout import Creator, zones_created_by
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
    ) -> None:
        self._public_assets = public_assets
        self._python_env = python_env

    def init(
        self,
        workspace_root: Path,
        skip_assets: bool = False,
        harnesses: tuple[str, ...] | None = None,
    ) -> tuple[Workspace, list[str]]:
        """Bootstrap .dadaia/ template. Idempotent. Returns (workspace, installed_assets).

        *harnesses* selects which Layer-1 entry harnesses to scaffold (the ``.claude``/
        ``.codex``/``.kimi-code`` projections plus per-harness hook registration).
        ``None`` ⇒ the full harness set (back-compat with pre-v0.1.58 init). Only the
        chosen harnesses' directories, hooks, and asset projections are created; the
        selected set is persisted through the profile store (the source of truth for
        profile-aware install/doctor scoping, v0.1.58 FR3).

        Bug init-harness-profile-silent-narrowing: init deletes no projection, so it must
        never un-manage one — a re-init with a harness subset MERGES into the persisted
        profile (canonical L1 order, unknown names appended sorted).
        """
        workspace = Workspace.from_root(workspace_root)
        chosen = tuple(harnesses) if harnesses is not None else L1_ENTRY_HARNESSES
        chosen_set = set(chosen)

        # The venv manager owns `.dadaia/.venv` and runs before the zone pass: an empty
        # pre-made `.venv` would read to it as an already-built venv.
        self._python_env.ensure_workspace_venv(str(workspace_root))
        for zone in zones_created_by(Creator.INIT):
            (workspace.dadaia_dir / zone.name).mkdir(parents=True, exist_ok=True)
        # The shared skills root is harness-independent — always created.
        (workspace.root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
        # Per-harness projection directories — only for the chosen set.
        if "claude" in chosen_set:
            workspace.claude_dir.mkdir(parents=True, exist_ok=True)
        if "codex" in chosen_set:
            (workspace.root / ".codex").mkdir(parents=True, exist_ok=True)
        # `.kimi-code/` is materialised by its install target below (no
        # bare mkdir).

        # Initialize JSON state files (idempotent — never overwrite existing data)
        self._init_json_file(workspace.states_dir / "spec_contexts.json", _EMPTY_CONTEXTS)
        self._init_json_file(workspace.states_dir / "server_registry.json", _EMPTY_SERVER_REGISTRY)

        store = JsonHarnessProfileStore()
        persisted = store.read(workspace.states_dir)
        merged = chosen_set | (set(persisted.harnesses) if persisted is not None else set())
        ordered = tuple(h for h in L1_ENTRY_HARNESSES if h in merged) + tuple(
            sorted(merged - set(L1_ENTRY_HARNESSES))
        )
        store.write(workspace.states_dir, HarnessProfile.of(ordered))

        # Install public assets — only the chosen harness projections. Every hook wiring
        # (.claude/settings.json, .codex/hooks.json, kimi user hooks) is install's output:
        # `public install` is the ONE settings writer (bug
        # init-skip-assets-writes-gateless-claude-settings — init's own gateless
        # UserPromptSubmit-only writer was deleted). Skipping assets therefore leaves the
        # workspace ungated, and that state must be loud, never silent.
        installed: list[str] = []
        if not skip_assets:
            installed.extend(self._public_assets.stage(workspace_root))
            # `target="all"` resolves the chosen-harness SUBSET on its own: it reads the
            # profile persisted above to scope its harness targets (v0.1.58 FR3).
            installed.extend(self._public_assets.install(workspace_root, target="all"))
        else:
            installed.append(
                "[warn] assets skipped — no hooks configured; the workspace is ungated "
                "until 'dadaia public install' runs"
            )

        return workspace, installed

    def is_initialized(self, workspace_root: Path) -> bool:
        return (workspace_root / ".dadaia" / "states" / "spec_contexts.json").exists()

    def _init_json_file(self, path: Path, empty: dict) -> None:  # type: ignore[type-arg]
        if not path.exists():
            path.write_text(json.dumps(empty, indent=2), encoding="utf-8")
