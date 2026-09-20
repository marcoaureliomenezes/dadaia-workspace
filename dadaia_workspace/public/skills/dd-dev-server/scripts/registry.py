#!/usr/bin/env python3
"""Dev-server port registry — stdlib only, one JSON file.

Verbs: list | next | register | release | clean | scan. The registry lives at
``<workspace>/.dadaia/states/server_registry.json`` (found by walking up from cwd,
or given with ``--registry``). Exit 0 on success, 1 on a refused verb.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_MIN_PORT = 3000
DEFAULT_MAX_PORT = 3999
DEFAULT_TTL_HOURS = 8
PORT_FLOOR = 1024
_LOCAL_ADDR_RE = re.compile(r"^(?P<bind>.+):(?P<port>\d+)$")
_USERS_PID_RE = re.compile(r'\("(?P<exe>[^"]+)",pid=(?P<pid>\d+)')


def _now() -> datetime:
    return datetime.now(tz=UTC)


def find_registry(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".dadaia").is_dir():
            return candidate / ".dadaia" / "states" / "server_registry.json"
    raise SystemExit("error: no .dadaia/ above the current directory; pass --registry <path>")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "version": "1",
            "range": {"min_port": DEFAULT_MIN_PORT, "max_port": DEFAULT_MAX_PORT},
            "entries": [],
        }
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


def save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def pid_alive(pid: int) -> bool:
    if os.name != "posix":
        return True  # no safe liveness probe without the POSIX signal-0 idiom
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def is_stale(entry: dict[str, Any]) -> bool:
    try:
        if datetime.fromisoformat(entry["expires_at"]) < _now():
            return True
    except (KeyError, ValueError):
        return True
    pid = entry.get("pid")
    return isinstance(pid, int) and not pid_alive(pid)


def status_of(entry: dict[str, Any]) -> str:
    return "stale" if is_stale(entry) else "active"


def base_port(project: str, lo: int, hi: int) -> int:
    digest = hashlib.md5(project.encode()).digest()  # noqa: S324 — a spread, not a secret
    return lo + int.from_bytes(digest[:2], "big") % (hi - lo + 1)


def cmd_list(doc: dict[str, Any], args: argparse.Namespace) -> int:
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


def cmd_next(doc: dict[str, Any], args: argparse.Namespace) -> int:
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
                print(
                    f"error: no free ports in [{args.min_port}, {args.max_port}]; run clean",
                    file=sys.stderr,
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
            print(
                f"error: port {args.port} is registered by project '{e['project']}' ({e['url']})",
                file=sys.stderr,
            )
            return 1
    now = _now()
    entry = {
        "port": args.port,
        "project": args.project,
        "url": args.url or f"http://localhost:{args.port}",
        "status": "active",
        "pid": args.pid,
        "reserved_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=args.ttl)).isoformat(),
        "description": args.description,
    }
    doc["entries"].append(entry)
    save(path, doc)
    print(f"port {args.port} registered for '{args.project}' -> {entry['url']}")
    return 0


def cmd_release(doc: dict[str, Any], args: argparse.Namespace, path: Path) -> int:
    if args.port is None and args.project is None:
        print("error: provide --port and/or --project", file=sys.stderr)
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
        if owner is None:
            print(f"error: port {args.port} is not registered", file=sys.stderr)
        else:
            print(
                f"error: port {args.port} belongs to project '{owner}', not '{args.project}'",
                file=sys.stderr,
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


def _ss_output() -> str | None:
    if not Path("/proc").is_dir():
        return None
    try:
        result = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True, timeout=5, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def parse_ss_line(line: str) -> tuple[int, str, int | None] | None:
    if not line or line.startswith("State"):
        return None
    parts = line.split()
    if len(parts) < 4:
        return None
    m = _LOCAL_ADDR_RE.match(parts[3])
    if not m:
        return None
    bind = m.group("bind").lstrip("[").rstrip("]")
    bind = "0.0.0.0" if bind == "*" else bind  # noqa: S104 — parsing, not binding
    pid = None
    if len(parts) >= 6:
        pm = _USERS_PID_RE.search(" ".join(parts[5:]))
        pid = int(pm.group("pid")) if pm else None
    return int(m.group("port")), bind, pid


def scan(doc: dict[str, Any], raw: str | None) -> list[dict[str, Any]]:
    if raw is None:
        return []
    registered = {e["port"] for e in doc["entries"]}
    findings: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parsed = parse_ss_line(line)
        if parsed is None:
            continue
        port, bind, pid = parsed
        if port < PORT_FLOOR or port in registered or pid is None:
            continue
        cmdline, cwd = "", ""
        try:
            cmdline = (
                Path(f"/proc/{pid}/cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode(errors="replace")
                .strip()[:200]
            )
            cwd = os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            pass
        findings.append(
            {
                "port": port,
                "bind": bind,
                "pid": pid,
                "cmdline": cmdline,
                "cwd": cwd,
                "lan_exposed": bind in {"0.0.0.0", "::"},
            }
        )
    return sorted(findings, key=lambda f: f["port"])


def cmd_scan(doc: dict[str, Any], args: argparse.Namespace) -> int:
    findings = scan(doc, _ss_output())
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
    p = argparse.ArgumentParser(prog="registry.py", description=__doc__)
    p.add_argument(
        "--registry",
        type=Path,
        help="registry JSON path (default: nearest .dadaia/states/server_registry.json)",
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
    args = build_parser().parse_args(argv)
    path = args.registry or find_registry(Path.cwd())
    doc = load(path)
    if args.verb == "list":
        return cmd_list(doc, args)
    if args.verb == "next":
        return cmd_next(doc, args)
    if args.verb == "register":
        return cmd_register(doc, args, path)
    if args.verb == "release":
        return cmd_release(doc, args, path)
    if args.verb == "clean":
        return cmd_clean(doc, args, path)
    return cmd_scan(doc, args)


if __name__ == "__main__":
    sys.exit(main())
