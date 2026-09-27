"""One secret matcher: the pre-push scan and the baseline / ``dead --commit`` preflight
give the same verdict on every fixture, because both run ONE engine over ONE registry.

Intent: CONTRACT — AC5.6 / sa-pre-push-and-publish-scan-disagree-on-secret-shapes

Every secret-shaped value is composed at run time (``tests/helpers/privacy_fixtures``
doctrine): no tracked literal carries a shape the push scan or gitleaks matches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.container import (
    load_denylist_baseline_patterns,
    load_denylist_terms,
    scan_publish_candidates,
)
from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
from dadaia_workspace.features.spec_context.service import (
    DeadSecretFoundError,
    SpecContextService,
)
from tests.fakes import FakeContextStore, FakeGitClient, register_dead

_DASHES = "-" * 5
_TERM = "zz" + "fixtureterm"

#: (case, file name, content, expected verdict: True = refused). The expectation is
#: the SPEC's (AC5.6 and the bug's expected line), never either engine's output.
_MATRIX: list[tuple[str, str, str | bytes, bool]] = [
    ("pem-block", "k.txt", _DASHES + "BEGIN RSA " + "PRIVATE KEY" + _DASHES + "\n", True),
    ("key-file-suffix", "server.p12", b"\x00opaque\xff", True),
    ("asia", "a.txt", "id=" + "AS" + "IA" + "Z" * 16 + "\n", True),
    ("ghs", "g.txt", "t=" + "gh" + "s_" + "a" * 36 + "\n", True),
    ("ghp-odd-length", "g2.txt", "t=" + "gh" + "p_" + "b" * 30 + "\n", True),
    ("glpat", "gl.txt", "t=" + "gl" + "pat-" + "c" * 20 + "\n", True),
    ("sk-live", "st.txt", "t=" + "sk" + "_live_" + "d" * 24 + "\n", True),
    ("password", "p.txt", "pass" + "word=" + "hunter2hunter\n", True),
    ("upper-api-key", "k2.txt", "API" + "_KEY=" + "e" * 30 + "\n", True),
    ("short-value", "s.txt", "sec" + "ret=" + "f" * 10 + "\n", True),
    ("email", "e.txt", "mail: zz.fixture" + "@" + "acme-fixture.com\n", True),
    ("product-identity", "w.txt", "dadaia" + "@" + "workspace.local\n", False),
    ("control-char-term", "c.txt", _TERM[:5] + "\x1b" + _TERM[5:] + "\n", True),
    ("clean", "n.txt", "nothing to see here\n", False),
    ("quoted-literal", "q.txt", "pass" + "word = '" + "g" * 8 + "'\n", True),
    # Review 7 R8-2: ordinary code names a secret without holding one — never refused.
    ("kwarg-passthrough", "db.py", "driver.connect(user=user, pass" + "word=password)\n", False),
    ("annotation", "cfg.py", "api" + "_key: Optional[str] = None\n", False),
    ("call", "c1.py", "pass" + "word = get_password()\n", False),
    ("attribute", "c2.py", "api" + "_key = settings.api_key\n", False),
    ("call-arg", "c3.py", "private" + "_key = load_private_key(path)\n", False),
    ("subscript", "c4.py", "access" + '_token = response.json()["t"]\n', False),
    ("aws-runtime", "c5.py", "aws_secret" + '_access_key=runtime_value("x")\n', False),
    ("terraform-attr", "m.tf", "CLIENT_" + "SECRET = some_resource.attr\n", False),
    ("public-cert-crt", "ca.crt", b"\x00cert\xff", False),
    ("public-cert-cer", "server.cer", b"\x00cert\xff", False),
]


@pytest.fixture(autouse=True)
def _operator_term(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    denylist = tmp_path / "denylist.json"
    denylist.write_text(json.dumps({_TERM: "fixture term"}))
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(denylist))


def _pre_push_refuses(name: str, content: str | bytes) -> bool:
    """The pre-push side: the blob as the git object reader hands it over."""
    if isinstance(content, bytes):
        obj = ScannedObject(name, "0" * 7, "", decodable=False)
    else:
        obj = ScannedObject(name, "0" * 7, content, decodable=True)
    outcome = scan_objects([obj], load_denylist_terms(), load_denylist_baseline_patterns())
    return bool(outcome.hits)


def _dead_commit_refuses(root: Path, name: str, content: str | bytes) -> bool:
    """The publish side: ``dead --commit`` over the same file, untracked in its repo."""
    (root / "repos").mkdir()
    git = FakeGitClient()
    service = SpecContextService(
        context_store=FakeContextStore(),
        git_client=git,
        workspace_root=root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )
    register_dead(service, "proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    repo = root / "repos" / "my-repo"
    git._has_remote.add(repo)
    target = repo / name
    target.write_bytes(content) if isinstance(content, bytes) else target.write_text(content)
    git._untracked[repo] = [name]
    try:
        service.dead("proj", commit=True)
    except DeadSecretFoundError:
        return True
    return False


@pytest.mark.parametrize(
    ("case", "name", "content", "refused"), _MATRIX, ids=[m[0] for m in _MATRIX]
)
def test_pre_push_and_publish_preflight_agree(
    tmp_path: Path, case: str, name: str, content: str | bytes, refused: bool
) -> None:
    verdicts = (_pre_push_refuses(name, content), _dead_commit_refuses(tmp_path, name, content))
    assert verdicts == (refused, refused), case
