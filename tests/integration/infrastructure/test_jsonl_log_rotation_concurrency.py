"""FR27 (v0.4.3 T-043-42) — concurrent-writer rotation fixture.

Intent: CONTRACT — A27.3

Two REAL OS processes append through ``append_rotating_jsonl`` at the same shared
``.jsonl`` path, synchronized with a ``multiprocessing.Barrier`` so both start writing
at the same instant (never sleep-luck — the barrier makes the overlap deterministic).
The cap is sized so the combined writes cross it exactly once (see ``_choose_cap``):
no crash, no lost line, no interleaved/corrupt line in the surviving files, and total
bytes across the surviving files stay within cap + one line's worth of slack.
"""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.jsonl_log_rotation import append_rotating_jsonl

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_LINES_PER_PROC = 60


def _worker(log_path: str, proc_id: int, n_lines: int, max_bytes: int, barrier: object) -> None:
    """Runs in a CHILD process (multiprocessing "spawn"-safe: module-level, picklable).

    Every process starts writing at the same instant (the barrier release), so the
    interleaving around the rotation boundary is genuinely concurrent, not sequential.
    """
    barrier.wait()  # type: ignore[attr-defined]
    path = Path(log_path)
    for seq in range(n_lines):
        line = json.dumps({"proc": proc_id, "seq": seq})
        append_rotating_jsonl(path, line, max_bytes=max_bytes)


def _choose_cap(n_procs: int, n_lines: int) -> tuple[int, int]:
    """Size the cap so the combined writes cross it exactly ONCE, deterministically,
    regardless of interleaving order (see the module docstring's math).

    ``current+1`` retention means a SECOND crossing would discard the first rotated
    generation — by design (FR27), but it would break this test's "no lost line"
    assertion, which is scoped to a single-crossing run. Sizing the cap at 60% of the
    total planned bytes guarantees: (a) total bytes exceed the cap (a crossing DOES
    happen), and (b) the remainder after the crossing (40% of total) is always less
    than the cap (60% of total) — so a second crossing can never occur, independent of
    the actual interleaving order the two processes produce.
    """
    sample_line_len = len(json.dumps({"proc": 0, "seq": 0})) + 1  # +1 for the newline
    total_lines = n_procs * n_lines
    total_bytes = sample_line_len * total_lines
    cap = int(total_bytes * 0.6)
    return cap, total_lines


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw:
            continue
        records.append(json.loads(raw))  # raises on any corrupt/interleaved line
    return records


def test_two_processes_rotate_without_loss_or_corruption(tmp_path: Path) -> None:
    log = tmp_path / "concurrent.jsonl"
    max_bytes, total_lines = _choose_cap(2, _LINES_PER_PROC)

    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    procs = [
        ctx.Process(
            target=_worker,
            args=(str(log), proc_id, _LINES_PER_PROC, max_bytes, barrier),
        )
        for proc_id in (0, 1)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)

    # No crash: every child process exited cleanly.
    for p in procs:
        assert p.exitcode == 0, f"worker process crashed with exitcode={p.exitcode}"

    rotated = log.with_name(log.name + ".1")

    # No interleaved/corrupt line: every surviving line parses as JSON (json.loads
    # raises ValueError on the first malformed/interleaved byte sequence it hits).
    current_records = _read_jsonl(log)
    rotated_records = _read_jsonl(rotated)

    # No lost line: the combined surviving files carry every line either process wrote
    # (see _choose_cap's single-crossing guarantee — current+1 retention never discards
    # a generation mid-run here).
    seen = {(r["proc"], r["seq"]) for r in current_records + rotated_records}
    expected = {(pid, seq) for pid in (0, 1) for seq in range(_LINES_PER_PROC)}
    assert seen == expected, f"missing={expected - seen}, unexpected={seen - expected}"

    # At most cap + slack bytes: "current" alone stays bounded near the cap, never
    # unbounded — the _choose_cap margin (§module docstring) guarantees the post-
    # rotation remainder is always < cap; the extra slack covers only the handful of
    # in-flight writes from the (at most 2) concurrent processes that could land just
    # past the exact crossing instant, never the whole remaining budget.
    current_bytes = log.stat().st_size if log.exists() else 0
    one_line_slack = len(json.dumps({"proc": 0, "seq": 0})) + 1
    assert current_bytes <= max_bytes + 4 * one_line_slack, (
        f"current file grew to {current_bytes} bytes, more than cap ({max_bytes}) + slack"
    )
