"""Unit tests for scan_unregistered_listeners (v0.1.1 / Bug D).

Linux-only: these tests exercise /proc-dependent code paths.  Platform-guard
behaviour (non-Linux early-return) is covered in test_scan_platform_guard.py
which runs on all platforms.
"""

from __future__ import annotations

import sys
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


def _patch_uid_check_all_ours():
    """Stub `_pid_belongs_to_current_user` to True for every pid in the sample."""
    return patch(
        "dadaia_workspace.features.server_registry.scan._pid_belongs_to_current_user",
        return_value=True,
    )


def _patch_read_proc(cmdline: str = "fake-cmd", cwd: str = "/tmp/fake"):
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


def test_scan_returns_empty_when_ss_unavailable() -> None:
    """If the output provider returns None (e.g. ss not found), scan returns []."""
    result = scan_unregistered_listeners([], _output_provider=lambda: None)
    assert result == []


def test_scan_skips_ports_below_1024() -> None:
    """Port 631 (CUPS) is in the sample. Must be skipped."""
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    assert all(r.port >= 1024 for r in result)


def test_scan_skips_registered_ports() -> None:
    """Port 4999 in the sample is in the registry — must be filtered out."""
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners(
            [_entry(4999, "panel")],
            _output_provider=_own_uid_provider,
        )
    assert 4999 not in [r.port for r in result]


def test_scan_marks_lan_exposed_for_0_0_0_0_bind() -> None:
    """Port 4000 binds 0.0.0.0 → lan_exposed=True. Port 8122 binds 127.0.0.1 → False."""
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    by_port = {r.port: r for r in result}
    assert by_port[4000].lan_exposed is True
    assert by_port[4000].bind == "0.0.0.0"
    assert by_port[8122].lan_exposed is False
    assert by_port[8122].bind == "127.0.0.1"


def test_scan_marks_lan_exposed_for_ipv6_wildcard() -> None:
    """``[::]`` IPv6 wildcard means listening on all interfaces — also LAN-exposed."""
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    ipv6 = next((r for r in result if r.port == 34139), None)
    assert ipv6 is not None
    assert ipv6.bind == "::"
    assert ipv6.lan_exposed is True


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


def test_scan_skips_pidless_listeners() -> None:
    """Listeners without an attributable pid (NFS, Docker swarm, kernel
    sockets) are filtered out — they're noise for the operator and not
    actionable from the panel."""
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    # Port 3968 in the sample has no pid → must be absent from result
    assert 3968 not in [r.port for r in result]
    # All survivors must have a pid
    assert all(r.pid is not None for r in result)


def test_scan_result_is_sorted_by_port() -> None:
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=_own_uid_provider)
    ports = [r.port for r in result]
    assert ports == sorted(ports)


def test_scan_handles_empty_ss_output() -> None:
    result = scan_unregistered_listeners([], _output_provider=lambda: "")
    assert result == []


def test_scan_handles_header_only_ss_output() -> None:
    header = "State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess\n"
    result = scan_unregistered_listeners([], _output_provider=lambda: header)
    assert result == []


def test_scan_handles_malformed_lines_gracefully() -> None:
    """Lines that don't match the expected ss format are skipped silently."""
    bad = "this is not a valid ss line\nLISTEN abc def ghi\n"
    result = scan_unregistered_listeners([], _output_provider=lambda: bad)
    assert result == []


@pytest.mark.parametrize(
    ("bind", "expected_lan"),
    [
        ("127.0.0.1", False),
        ("0.0.0.0", True),
        ("::", True),
        ("::1", False),
        ("192.168.1.5", False),  # specific IP, not wildcard
    ],
)
def test_lan_exposed_classification(bind: str, expected_lan: bool) -> None:
    """LAN-exposed = bind in {'0.0.0.0', '::'} only. Specific IPs (even non-loopback)
    are not flagged because the user explicitly chose them."""
    fake = f'LISTEN 0  5  {bind}:9000  0.0.0.0:*  users:(("x",pid=42,fd=1))\n'
    with _patch_uid_check_all_ours(), _patch_read_proc()[0], _patch_read_proc()[1]:
        result = scan_unregistered_listeners([], _output_provider=lambda: fake)
    assert len(result) == 1
    assert result[0].lan_exposed is expected_lan
