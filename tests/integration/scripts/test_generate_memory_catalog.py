"""Integration tests for dadaia_workspace/public/scripts/generate-memory-catalog.py.

Merged per plan-integration.md (14 -> 2). The in-process fns calling the imported
``generate_catalog``/``generate_index_md``/``main`` functions directly (no subprocess,
no server) relocated to tests/unit/scripts/test_generate_memory_catalog.py — this file
keeps only the two integration-tier proofs:

  1. subprocess exit-code contract: valid dir -> exit 0; bad frontmatter -> exit 1.
  2. one end-to-end fn: multi-atom catalog shape + ranks + wikilink depends_on +
     index.md TOC + idempotency (as phases sharing one seeded product dir).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "generate-memory-catalog.py"


def _make_memory_dir(tmp_path: Path) -> tuple[Path, Path]:
    memory_dir = tmp_path / "memory"
    product_dir = memory_dir / "product"
    product_dir.mkdir(parents=True)
    return memory_dir, product_dir


def _make_product_atom(product_dir: Path, slug: str, body: str = "## Propósito\n\nBody.\n") -> Path:
    fm = {
        "slug": slug,
        "title": "Test Feature",
        "category": "product",
        "tldr": "Short description under 160 chars.",
        "summary": "One-sentence summary.",
        "tags": ["test"],
        "agent_tier": "self-pull",
        "token_estimate": 50,
        "last_updated": "2026-06-01",
        "release_origin": "memory-markdown-source-v1",
    }
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v!r}")
    lines.append("---")
    lines.append("")
    content = "\n".join(lines) + "\n" + body
    md_path = product_dir / f"{slug}.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


def test_subprocess_valid_exits_zero_bad_frontmatter_exits_one(tmp_path: Path) -> None:
    """Script exits 0 for a directory with valid atoms; exits 1 for missing frontmatter."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="workspace-init")
    out_path = tmp_path / "catalog.json"

    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--memory-dir", str(memory_dir), "--out", str(out_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert out_path.exists(), "catalog.json should be written"

    bad_memory_dir, bad_product_dir = _make_memory_dir(tmp_path / "bad")
    content = (
        "---\n"
        "slug: bad-feature\n"
        # title missing
        "category: product\n"
        "tldr: Short.\n"
        "summary: Summary.\n"
        "tags: []\n"
        "agent_tier: self-pull\n"
        "token_estimate: 50\n"
        "last_updated: '2026-06-01'\n"
        "release_origin: test\n"
        "---\n\n## Propósito\n\nBody.\n"
    )
    (bad_product_dir / "bad-feature.md").write_text(content, encoding="utf-8")
    bad_out_path = tmp_path / "bad" / "catalog.json"

    result2 = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--memory-dir",
            str(bad_memory_dir),
            "--out",
            str(bad_out_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 1, (
        f"Expected exit 1.\nstdout: {result2.stdout!r}\nstderr: {result2.stderr!r}"
    )


def test_end_to_end_multi_atom_catalog_shape_ranks_wikilinks_index_and_idempotency(
    tmp_path: Path,
) -> None:
    """One seeded product dir; multi-atom catalog shape, ranks, wikilink depends_on,
    index.md TOC, and idempotency, all as phases against the real script module via
    a subprocess-produced catalog.json + a direct main() call for index.md."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="aaa-feature")
    _make_product_atom(
        product_dir,
        slug="bbb-feature",
        body="## Propósito\n\nSee [[aaa-feature]] and again [[aaa-feature]].\n",
    )
    sdd_dir = product_dir / "sdd"
    sdd_dir.mkdir()
    _make_product_atom(sdd_dir, slug="ccc-feature")

    out_path = tmp_path / "catalog.json"
    index_out = tmp_path / "index.md"

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
            "--index-out",
            str(index_out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )

    import json

    catalog = json.loads(out_path.read_text(encoding="utf-8"))
    features = catalog["features"]
    assert len(features) == 3
    slugs = [f["slug"] for f in features]
    assert slugs == sorted(slugs)
    ranks = [f["rank"] for f in features]
    assert ranks == [1, 2, 3]

    bbb = next(f for f in features if f["slug"] == "bbb-feature")
    # Deduplicated wikilink, appearing once despite being referenced twice.
    assert bbb["depends_on"].count("aaa-feature") == 1

    index_md = index_out.read_text(encoding="utf-8")
    assert "aaa-feature" in index_md
    assert "ccc-feature" in index_md
    assert "## Catálogo de features" in index_md
    assert "### product" in index_md
    assert "### sdd" in index_md

    # Idempotency: a second run produces the same features (modulo generated_at).
    result2 = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
            "--index-out",
            str(index_out),
        ],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0
    catalog2 = json.loads(out_path.read_text(encoding="utf-8"))
    assert catalog2["features"] == features
