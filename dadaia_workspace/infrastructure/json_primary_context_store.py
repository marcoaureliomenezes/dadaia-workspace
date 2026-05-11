"""JsonPrimaryContextStore — atomic read/write/clear for primary_context.json."""

import json
import os
from pathlib import Path


class JsonPrimaryContextStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "primary_context.json"

    def write(self, name: str, repo_slug: str, specs_dir: Path) -> None:
        payload = {
            "name": name,
            "repo_slug": repo_slug,
            "specs_dir": str(specs_dir),
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        os.replace(tmp, self._path)

    def read(self) -> dict[str, str] | None:
        if not self._path.exists():
            return None
        with self._path.open() as f:
            return json.load(f)  # type: ignore[no-any-return]

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
