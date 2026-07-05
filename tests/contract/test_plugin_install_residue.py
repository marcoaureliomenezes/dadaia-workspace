"""Plugin-install command contract — INVERTED at v0.1.60 (T-60-30).

**History.** At v0.1.11, ADR-4 resolved bug ``plugin-install-command-missing`` by an
*honest relabel*: no plugin pack assets existed under ``dadaia_workspace/``, so there was
nothing to install, and this contract pinned **zero** ``plugin install`` references in the
public asset tree (the wording routed plugin-domain work to the operator).

**Inversion (v0.1.60, FR2/FR5 — fate-ledger INVERTS).** v0.1.60 ships the real
``dadaia plugin install <pack>`` command plus the in-package ``frontend-design`` / ``devops``
packs, consuming the backlog entry ``plugin-packs-and-install-command``. The ADR-4 premise is
therefore reversed: the command **exists**, and the ``plugin-scope`` rule is rewritten to be
install-gated (FR5). This contract inverts to pin the new law — the canonical ``plugin-scope``
rule **names** ``dadaia plugin install`` and the retired ``not yet distributed`` /
``no install command exists`` wording is **gone** — so the honest-relabel wording can never
silently creep back now that packs are installable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_ROOT = _REPO_ROOT / "dadaia_workspace" / "public"
_PLUGIN_SCOPE = _PUBLIC_ROOT / "rules" / "plugin-scope.md"

# The install-gated command the rewritten rule must name (v0.1.60 FR2/FR5).
_INSTALL_COMMAND = "dadaia plugin install"

# The relabel wording retired by v0.1.60 — must be absent from the canonical rule.
_RETIRED_WORDING = ("not yet distributed", "no install command exists")


def test_plugin_scope_names_install_command() -> None:
    """The canonical ``plugin-scope`` rule names ``dadaia plugin install`` (v0.1.60 FR5)."""
    assert _PLUGIN_SCOPE.is_file(), f"plugin-scope rule missing: {_PLUGIN_SCOPE}"
    text = _PLUGIN_SCOPE.read_text(encoding="utf-8")
    assert _INSTALL_COMMAND in text, (
        "the plugin-scope rule must name the install command "
        f"'{_INSTALL_COMMAND}' now that packs are installable (v0.1.60 FR2/FR5)"
    )


def test_plugin_scope_dropped_retired_relabel_wording() -> None:
    """The retired ADR-4 honest-relabel wording is gone from the canonical rule (v0.1.60)."""
    text = _PLUGIN_SCOPE.read_text(encoding="utf-8").lower()
    offenders = [phrase for phrase in _RETIRED_WORDING if phrase in text]
    assert not offenders, (
        "plugin-scope still carries the retired 'not yet distributed'/'no install command "
        f"exists' wording superseded by v0.1.60: {offenders}"
    )
