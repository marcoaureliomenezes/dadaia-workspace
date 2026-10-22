#!/usr/bin/env python3
"""Dev-server port registry — stdlib only, one JSON file.

Verbs: list | next | register | release | clean | scan. The registry is
``<workspace>/.dadaia/states/server_registry.json`` (walked up from cwd, or
``--registry``), written atomically by `_ledger.replace`. Exit 1 on a refused verb.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True  # the shared _ledger imports without a __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))
import _clock
import _platform
from _ledger import replace, workspace_of
from _platform import act, read_text, use_utf8_stdio
from _refusal import Refusal, report

DEFAULT_MIN_PORT = 3000
DEFAULT_MAX_PORT = 3999
DEFAULT_TTL_HOURS = 8
PORT_FLOOR = 1024


def _now() -> datetime:
    return datetime.fromisoformat(_clock.now_iso())


def _stamp(moment: datetime) -> str:
    """*moment* in the kernel clock's `...Z` form; `is_stale` reads that and the old `+00:00`."""
    return moment.isoformat().replace("+00:00", "Z")


def find_registry(start: Path) -> Path:
    if root := workspace_of(start):
        return root / ".dadaia" / "states" / "server_registry.json"
    report(
        "no workspace sentinel above the cwd",
        act("agent", "rerun with --registry and a registry file path, or from inside a workspace"),
    )
    raise SystemExit(1)


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "version": "1",
            "range": {"min_port": DEFAULT_MIN_PORT, "max_port": DEFAULT_MAX_PORT},
            "entries": [],
        }
    fix = act(
        "operator",
        f"delete {_platform.quote(str(path))} — the next registry.py run starts an empty registry",
    )
    return dict(json.loads(read_text(path, fix)))


def is_stale(entry: dict[str, Any]) -> bool:
    try:
        if datetime.fromisoformat(entry["expires_at"]) < _now():
            return True
    except (KeyError, ValueError):
        return True
    pid = entry.get("pid")
    return isinstance(pid, int) and not _platform.pid_alive(pid)


def status_of(entry: dict[str, Any]) -> str:
    return "stale" if is_stale(entry) else "active"


def base_port(project: str, lo: int, hi: int) -> int:
    digest = hashlib.md5(project.encode()).digest()  # noqa: S324 — a spread, not a secret
    return lo + int.from_bytes(digest[:2], "big") % (hi - lo + 1)


def save(path: Path, doc: dict[str, Any]) -> None:
    replace(path, json.dumps(doc, indent=2) + "\n")


def cmd_list(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    rows = [dict(e, status=status_of(e)) for e in doc["entries"]]
    if args.project:
        rows = [r for r in rows if r["project"] == args.project]
    if args.status != "all":
        rows = [r for r in rows if r["status"] == args.status]
    if args.json:
        print(json.dumps(rows, indent=2))
    elif not rows:
        print("No servers registered.")
    else:
        for r in rows:
            print(
                f"{r['port']}\t{r['project']}\t{r['url']}\t{r['status']}\t{r.get('description') or '-'}"
            )
    return 0


def cmd_next(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    live = [e for e in doc["entries"] if not is_stale(e)]
    mine = [e for e in live if e["project"] == args.project]
    if mine:
        port, is_base = mine[0]["port"], True
    else:
        occupied = {e["port"] for e in live}
        base = base_port(args.project, args.min_port, args.max_port)
        if base not in occupied:
            port, is_base = base, True
        else:
            free = [p for p in range(args.min_port, args.max_port + 1) if p not in occupied]
            if not free:
                report(
                    f"no free ports in [{args.min_port}, {args.max_port}]",
                    act("agent", "run registry.py clean, then rerun"),
                )
                return 1
            port, is_base = free[0], False
    url = f"http://localhost:{port}"
    if args.json:
        print(json.dumps({"port": port, "url": url, "is_base_port": is_base}, indent=2))
    else:
        print(f"{port}\t{url}" + ("" if is_base else "\t(base port occupied)"))
    return 0


def cmd_register(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    doc["entries"] = [e for e in doc["entries"] if not is_stale(e)]
    for e in doc["entries"]:
        if e["port"] == args.port:
            if e["project"] == args.project:
                print(f"port {args.port} already registered for '{args.project}' -> {e['url']}")
                save(path, doc)
                return 0
            report(
                f"port {args.port} is registered by project '{e['project']}' ({e['url']})",
                act("agent", "pick another port with registry.py next, then rerun"),
            )
            return 1
    now = _now()
    entry = {
        "port": args.port,
        "project": args.project,
        "url": args.url or f"http://localhost:{args.port}",
        "status": "active",
        "pid": args.pid,
        "reserved_at": _stamp(now),
        "expires_at": _stamp(now + timedelta(hours=args.ttl)),
        "description": args.description,
    }
    doc["entries"].append(entry)
    save(path, doc)
    print(f"port {args.port} registered for '{args.project}' -> {entry['url']}")
    return 0


def cmd_release(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    if args.port is None and args.project is None:
        report(
            "provide --port and/or --project",
            act("agent", "pass --port and/or --project, then rerun"),
        )
        return 1
    keep: list[dict[str, Any]] = []
    released: list[dict[str, Any]] = []
    for e in doc["entries"]:
        hit = (args.port is None or e["port"] == args.port) and (
            args.project is None or e["project"] == args.project
        )
        (released if hit else keep).append(e)
    if args.port is not None and not released:
        owner = next((e["project"] for e in doc["entries"] if e["port"] == args.port), None)
        why = (
            "is not registered"
            if owner is None
            else f"belongs to project '{owner}', not '{args.project}'"
        )
        report(
            f"port {args.port} {why}",
            act("agent", "run registry.py list to see the registered ports, then rerun"),
        )
        return 1
    doc["entries"] = keep
    save(path, doc)
    for e in released:
        print(f"released port {e['port']} ('{e['project']}')")
    if not released:
        print(f"no registered ports for project '{args.project}'")
    return 0


def cmd_clean(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    stale = [e for e in doc["entries"] if is_stale(e)]
    if not args.dry_run:
        doc["entries"] = [e for e in doc["entries"] if not is_stale(e)]
        save(path, doc)
    verb = "would remove" if args.dry_run else "removed"
    for e in stale:
        print(f"{verb}: port {e['port']} ('{e['project']}')")
    if not stale:
        print("No stale entries found.")
    return 0


def scan(doc: dict[str, Any], found: list[_platform.Listener] | None) -> list[dict[str, Any]]:
    registered = {e["port"] for e in doc["entries"]}
    return [
        dict(port=f.port, bind=f.bind, pid=f.pid, cmdline=f.cmdline, cwd=f.cwd,
             lan_exposed=f.bind in {"0.0.0.0", "::"})  # noqa: S104 — comparing, not binding
        for f in found or []
        if f.port >= PORT_FLOOR and f.port not in registered and f.pid is not None
    ]  # fmt: skip


def cmd_scan(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    findings = scan(doc, _platform.listeners())
    if args.json:
        print(json.dumps(findings, indent=2))
    elif not findings:
        print("No unregistered listeners.")
    else:
        for f in findings:
            print(
                f"{f['port']}\t{f['bind']}\tpid={f['pid']}\t{'LAN' if f['lan_exposed'] else 'local'}\t{f['cmdline']}"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dd-cli-library/scripts/registry.py", description=__doc__)
    p.add_argument(
        "--registry",
        type=Path,
        help="registry JSON path (default: <workspace>/.dadaia/states/server_registry.json)",
    )
    sub = p.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("list")
    s.add_argument("--project")
    s.add_argument("--status", choices=("active", "stale", "all"), default="active")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("next")
    s.add_argument("--project", required=True)
    s.add_argument("--min-port", type=int, default=DEFAULT_MIN_PORT)
    s.add_argument("--max-port", type=int, default=DEFAULT_MAX_PORT)
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("register")
    s.add_argument("--port", type=int, required=True)
    s.add_argument("--project", required=True)
    s.add_argument("--url", default="")
    s.add_argument("--pid", type=int)
    s.add_argument("--ttl", type=int, default=DEFAULT_TTL_HOURS)
    s.add_argument("--description")
    s = sub.add_parser("release")
    s.add_argument("--port", type=int)
    s.add_argument("--project")
    s = sub.add_parser("clean")
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("scan")
    s.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    args = build_parser().parse_args(argv)
    path = args.registry or find_registry(Path.cwd())
    verbs = {"list": cmd_list, "next": cmd_next, "register": cmd_register}
    verbs |= {"release": cmd_release, "clean": cmd_clean, "scan": cmd_scan}
    try:
        return verbs[args.verb](load(path), args, path)
    except Refusal as refusal:
        report(refusal, refusal.fix)
        return 1


if __name__ == "__main__":
    sys.exit(main())
