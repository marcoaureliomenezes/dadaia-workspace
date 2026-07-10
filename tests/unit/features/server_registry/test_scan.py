"""Unit tests for scan_unregistered_listeners (v0.1.1 / Bug D).

Linux-only: these tests exercise /proc-dependent code paths.  Platform-guard
behaviour (non-Linux early-return) is covered in test_scan_platform_guard.py
which runs on all platforms.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.features.server_registry.scan import (
    scan_unregistered_listeners,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="scan.py /proc paths are Linux-only; platform-guard tests are in test_scan_platform_guard.py",
)

# A realistic `ss -tlnp` sample we can stub in.
_SS_OUTPUT = """State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0      5          127.0.0.1:4999       0.0.0.0:*    users:(("dadaia",pid=3440084,fd=4))
LISTEN 0      5            0.0.0.0:4000       0.0.0.0:*    users:(("python3",pid=1414778,fd=3))
LISTEN 0      5          127.0.0.1:8122       0.0.0.0:*    users:(("python",pid=1507281,fd=3))
LISTEN 0      4096         0.0.0.0:3968       0.0.0.0:*
LISTEN 0      4096       127.0.0.1:631        0.0.0.0:*
LISTEN 0      4096            [::]:34139         [::]:*    users:(("snap",pid=1234567,fd=5))
"""


def _entry(port: int, project: str = "demo") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-17T20:00:00Z",
        expires_at="2026-05-18T04:00:00Z",
    )


def _own_uid_provider() -> str:
    return _SS_OUTPUT


def _patch_uid_check_all_ours() -> Any:
    """Stub `_pid_belongs_to_current_user` to True for every pid in the sample."""
    return patch(
        "dadaia_workspace.features.server_registry.scan._pid_belongs_to_current_user",
        return_value=True,
    )


def _patch_read_proc(cmdline: str = "fake-cmd", cwd: str = "/tmp/fake") -> list[Any]:
    return [
        patch(
            "dadaia_workspace.features.server_registry.scan._read_cmdline",
            return_value=cmdline,
        ),
        patch(
            "dadaia_workspace.features.server_registry.scan._read_cwd",
            return_value=cwd,
        ),
    ]


# ---------------------------------------------------------------------------
# Kept: other-user pid filtering — privilege boundary
# ---------------------------------------------------------------------------


def test_scan_filters_listeners_owned_by_other_users() -> None:
    """When `_pid_belongs_to_current_user` returns False for a pid, the
    listener is dropped (system services owned by root, etc.)."""
    with (
        patch(
            "dadaia_workspace.features.server_registry.scan._pid_belongs_to_current_user",
            return_value=False,
        ),
        patch(
            "dadaia_workspace.features.server_registry.scan._read_cmdline",
            return_value="fake",
        ),
        patch(
            "dadaia_workspace.features.server_registry.scan._read_cwd",
            return_value="/tmp",
        ),
    ):
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    # All PIDed listeners filtered. Port 3968 (no pid in sample) is kept.
    assert all(r.pid is None for r in result)


# ---------------------------------------------------------------------------
# Filter/skip matrix over the realistic ss sample + degrade-on-bad-input — 1 param
# ---------------------------------------------------------------------------


def _scan_sample() -> list[Any]:
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        return scan_unregistered_listeners(
            [_entry(4999, "panel")], _output_provider=_own_uid_provider
        )


@pytest.mark.parametrize(
    ("case", "run", "assertion"),
    [
        pytest.param(
            "skips-ports-below-1024",
            _scan_sample,
            lambda result: all(r.port >= 1024 for r in result),
            id="skips-ports-below-1024",
        ),
        pytest.param(
            "skips-registered-ports",
            _scan_sample,
            lambda result: 4999 not in [r.port for r in result],
            id="skips-registered-ports",
        ),
        pytest.param(
            "skips-pidless-listeners",
            _scan_sample,
            lambda result: (
                3968 not in [r.port for r in result] and all(r.pid is not None for r in result)
            ),
            id="skips-pidless-listeners",
        ),
        pytest.param(
            "result-sorted-by-port",
            _scan_sample,
            lambda result: [r.port for r in result] == sorted(r.port for r in result),
            id="result-sorted-by-port",
        ),
        pytest.param(
            "empty-ss-output",
            lambda: scan_unregistered_listeners([], _output_provider=lambda: ""),
            lambda result: result == [],
            id="empty-ss-output-degrades-to-empty",
        ),
        pytest.param(
            "header-only-ss-output",
            lambda: scan_unregistered_listeners(
                [],
                _output_provider=lambda: (
                    "State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess\n"
                ),
            ),
            lambda result: result == [],
            id="header-only-ss-output-degrades-to-empty",
        ),
        pytest.param(
            "malformed-lines-skipped",
            lambda: scan_unregistered_listeners(
                [], _output_provider=lambda: "this is not a valid ss line\nLISTEN abc def ghi\n"
            ),
            lambda result: result == [],
            id="malformed-lines-skipped",
        ),
    ],
)
def test_scan_filter_and_degrade_matrix(case: str, run, assertion) -> None:  # type: ignore[no-untyped-def]
    result = run()
    assert assertion(result)


# ---------------------------------------------------------------------------
# LAN-exposed bind classification — 1 param (incl. 0.0.0.0/[::] from the realistic sample)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bind", "port", "expected_lan"),
    [
        ("127.0.0.1", 9000, False),
        ("0.0.0.0", 9000, True),
        ("::", 9000, True),
        ("::1", 9000, False),
        ("192.168.1.5", 9000, False),  # specific IP, not wildcard
        ("0.0.0.0", 4000, True),  # from the realistic sample
        ("127.0.0.1", 8122, False),  # from the realistic sample
        ("::", 34139, True),  # IPv6 wildcard, from the realistic sample
    ],
)
def test_lan_exposed_classification(bind: str, port: int, expected_lan: bool) -> None:
    """LAN-exposed = bind in {'0.0.0.0', '::'} only. Specific IPs (even non-loopback)
    are not flagged because the user explicitly chose them."""
    fake = f'LISTEN 0  5  {bind}:{port}  0.0.0.0:*  users:(("x",pid=42,fd=1))\n'
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=lambda: fake)
    assert len(result) == 1
    assert result[0].bind == bind
    assert result[0].lan_exposed is expected_lan
