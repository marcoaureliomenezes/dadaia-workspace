"""WorkspaceService — bootstrap and management of the .dadaia/ template."""

import json
from pathlib import Path

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.workspace import Workspace
from dadaia_workspace.core.protocols.runtime_env import PythonEnvironmentManager
from dadaia_workspace.core.protocols.storage import PublicAssetManager

# Durable directories — must not be cleared by maintenance routines
_DADAIA_DURABLE_DIRS = [
    "academy",
    "agentic",
    "reports",
    "scripts",
    "states",
]

# Ephemeral directories — can be recreated or cleared at any time
_DADAIA_EPHEMERAL_DIRS = [
    "tmp/python",
    "tmp/json",
]

_DADAIA_DIRS = _DADAIA_DURABLE_DIRS + _DADAIA_EPHEMERAL_DIRS

_EMPTY_CONTEXTS = {"schema_version": "2", "contexts": []}
_EMPTY_ACADEMY = {"version": "1", "courses": []}
_EMPTY_SERVER_REGISTRY = {
    "version": "1",
    "range": {"min_port": 3000, "max_port": 3999},
    "entries": [],
}


class WorkspaceService:
    def __init__(
        self,
        public_assets: PublicAssetManager,
        python_env: PythonEnvironmentManager,
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
        selected set is persisted to ``.dadaia/states/harness_profile.json`` (the source
        of truth for profile-aware install/doctor scoping, v0.1.58 FR3).
        """
        workspace = Workspace.from_root(workspace_root)
        chosen = tuple(harnesses) if harnesses is not None else L1_ENTRY_HARNESSES
        chosen_set = set(chosen)

        # Create .dadaia/ directory structure (harness-independent).
        for subdir in _DADAIA_DIRS:
            (workspace.dadaia_dir / subdir).mkdir(parents=True, exist_ok=True)
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
        self._init_json_file(workspace.dadaia_dir / "academy" / "academy.json", _EMPTY_ACADEMY)
        self._init_json_file(workspace.states_dir / "server_registry.json", _EMPTY_SERVER_REGISTRY)

        # Persist the harness profile (schema v1) — inline like the state bootstraps above.
        self._write_harness_profile(workspace, chosen)

        # Create .venv (idempotent)
        self._python_env.ensure_workspace_venv(str(workspace_root))

        # Install public assets — only the chosen harness projections. Every hook wiring
        # (.claude/settings.json, .codex/hooks.json, kimi user hooks) is install's output:
        # `public install` is the ONE settings writer (bug
        # init-skip-assets-writes-gateless-claude-settings — init's own gateless
        # UserPromptSubmit-only writer was deleted). Skipping assets therefore leaves the
        # workspace ungated, and that state must be loud, never silent.
        installed: list[str] = []
        if not skip_assets:
            installed.extend(self._public_assets.stage(workspace_root))
            installed.extend(self._install_for_harnesses(workspace_root, chosen))
        else:
            installed.append(
                "[warn] assets skipped — no hooks configured; the workspace is ungated "
                "until 'dadaia public install' runs"
            )

        return workspace, installed

    def _install_for_harnesses(self, workspace_root: Path, chosen: tuple[str, ...]) -> list[str]:
        """Install only the chosen harnesses' projections.

        The full all-four set preserves the single ``target="all"`` install verbatim
        (byte-identical back-compat). For a subset, install the shared ``agents`` skills
        root plus one projection per chosen harness — ``target="all"`` is never used for a
        subset (it would scaffold unchosen harnesses). Profile-aware ``install(target="all")``
        is the v0.1.58 W3 concern; W2 stays self-contained via per-target install. Duplicate
        install-report lines (shared assets touched by each per-target call, hash-compare
        no-ops) are de-duplicated for a clean caller-facing list.
        """
        if set(chosen) == set(L1_ENTRY_HARNESSES):
            return self._public_assets.install(workspace_root, target="all")
        installed: list[str] = []
        seen: set[str] = set()
        for target in ("agents", *chosen):
            for item in self._public_assets.install(workspace_root, target=target):
                if item not in seen:
                    seen.add(item)
                    installed.append(item)
        return installed

    def _write_harness_profile(self, workspace: Workspace, harnesses: tuple[str, ...]) -> None:
        """Write .dadaia/states/harness_profile.json inline (like ``_init_json_file``).

        Uses the pure ``HarnessProfile`` core model to shape the payload; the identical
        shape is produced by ``infrastructure/json_harness_profile_store.py`` (the W3 read
        side), so the two writers never fork. Idempotent — no spurious rewrite when the
        on-disk bytes already match (satisfies AC-4's re-run-is-a-no-op).

        Bug init-harness-profile-silent-narrowing: init deletes no projection, so it must
        never un-manage one — a re-init with a harness subset MERGES into the persisted
        profile (canonical L1 order, unknown names appended sorted). Narrowing the
        managed set is a deliberate operator state edit, never an init side effect;
        before this, adding one harness silently dropped the others out of
        install/doctor scope ([warn] out-of-profile) and their projections rotted.
        """
        merged = set(harnesses) | self._persisted_profile_harnesses(workspace)
        ordered = tuple(h for h in L1_ENTRY_HARNESSES if h in merged) + tuple(
            sorted(merged - set(L1_ENTRY_HARNESSES))
        )
        profile = HarnessProfile.of(ordered)
        payload = {
            "schema_version": profile.schema_version,
            "harnesses": list(profile.harnesses),
        }
        path = workspace.states_dir / "harness_profile.json"
        new_text = json.dumps(payload, indent=2)
        if path.exists() and path.read_text(encoding="utf-8") == new_text:
            return
        path.write_text(new_text, encoding="utf-8")

    def _persisted_profile_harnesses(self, workspace: Workspace) -> set[str]:
        """Read the harness set already persisted in the profile (empty on absence/corruption).

        Inline read mirroring the inline write above (the infrastructure store stays the
        W3 read side for install/doctor). A corrupt or unreadable profile contributes
        nothing — init then persists exactly the requested set, the pre-merge behavior.
        """
        path = workspace.states_dir / "harness_profile.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return set()
        raw = data.get("harnesses", []) if isinstance(data, dict) else []
        if not isinstance(raw, list):
            return set()
        return {str(h) for h in raw}

    def is_initialized(self, workspace_root: Path) -> bool:
        return (workspace_root / ".dadaia" / "states" / "spec_contexts.json").exists()

    def _init_json_file(self, path: Path, empty: dict) -> None:  # type: ignore[type-arg]
        if not path.exists():
            path.write_text(json.dumps(empty, indent=2), encoding="utf-8")
