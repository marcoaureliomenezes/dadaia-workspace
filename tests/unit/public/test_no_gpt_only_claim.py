"""T-44-15 doc-lint guardrail — no surviving "GPT-only" Layer-2 claim.

v0.1.44 (ADR-B amendment) relaxes the Layer-2 model law from *GPT-only by construction*
to **allowlist-validated** (a Layer-2 id must be in
``_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS``, and is **never** a ``claude-*`` id). Any
live-source or public-doc text still asserting Layer-2 is "GPT-only" now contradicts the
law and must not survive.

Scope (deliberately bounded so the assertion is satisfiable):

* **Included:** live production source + public assets under ``dadaia_workspace/`` —
  ``*.py`` and ``public/**/*.md`` (the rule/AGENTS/fragment/persona doc surface).
* **Excluded by construction:** ``specs/_archive/`` (FROZEN history), ``specs/memory/``
  (product-engineer-owned, updated at CLOSURE by T-44-18), the v0.1.44 ``specs/`` text,
  this test file itself, and the projected runtime trees (``.claude/`` etc.) — none live
  under ``dadaia_workspace/``.

A "GPT-only" occurrence is a violation **unless** it is negated ("not GPT-only"), which is
exactly how the corrected docstrings affirm the new law.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.helpers.scan_population import assert_populated

#: Repo root: tests/unit/public/<this file> → parents[3] == repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_ROOT = _REPO_ROOT / "dadaia_workspace"

#: Matches the "GPT-only" / "GPT only" claim, case-insensitive.
_CLAIM = re.compile(r"gpt[- ]only", re.IGNORECASE)


def _scanned_files() -> list[Path]:
    """Live Python source + public Markdown docs under ``dadaia_workspace/``."""
    files = list(_SOURCE_ROOT.rglob("*.py"))
    files += list((_SOURCE_ROOT / "public").rglob("*.md"))
    return sorted(files)


def _violations() -> list[str]:
    out: list[str] = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            for match in _CLAIM.finditer(lowered):
                idx = match.start()
                # Affirming the new law: "not GPT-only" is explicitly allowed.
                if lowered[max(0, idx - 4) : idx] == "not ":
                    continue
                rel = path.relative_to(_REPO_ROOT)
                out.append(f"{rel}:{lineno}: {line.strip()}")
    return out


def test_no_surviving_gpt_only_claim() -> None:
    # v0.4.5 FR5 (scan-test-vacuity-guard): non-empty alone would still miss a
    # partially mis-rooted walk; the sentinel half pins a real package file.
    assert_populated(_scanned_files(), sentinel=_SOURCE_ROOT / "__init__.py")

    violations = _violations()
    assert violations == [], (
        "live source / public docs still assert Layer-2 is 'GPT-only', contradicting the "
        "v0.1.44 allowlist-validated law (use 'allowlist-validated (no claude-*)'):\n"
        + "\n".join(violations)
    )
