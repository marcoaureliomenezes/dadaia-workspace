"""Panel API views — report discovery, retention, and identity-injected serving.

Endpoints:
- GET /api/reports — list human-readable HTML reports enriched from handoffs.
- POST mark/unmark important — report retention protection.
- GET reports serve — serve a report HTML file (dadaia identity stylesheets injected).
- DELETE report — remove a report and its referencing handoffs.

Security (OWASP A01, A03): report paths are canonicalised with Path.resolve() and
boundary-checked with relative_to() (no string ops); error messages stay generic.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.features.panel.service import PanelService

logger = logging.getLogger(__name__)


def render_api_reports(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return ``GET /api/reports`` view — list human-readable HTML reports.

    Reports are discovered from rendered artifacts under
    ``<workspace_root>/.dadaia/reports/`` and enriched from canonical handoffs in
    ``.dadaia/handoff/`` plus legacy adjacent handoffs in ``.dadaia/reports/``.
    Malformed handoffs are skipped with a WARNING log.

    Response shape: {"reports": [{title, agent, context, created_at, path, findings_summary}]}
    findings_summary: {"CRITICAL": N, "HIGH": N, "MEDIUM": N, "LOW": N}
    """
    _log = logging.getLogger(__name__)

    def _severity_counts(findings: object) -> dict[str, int]:
        counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        if not isinstance(findings, list):
            return counts
        for f in findings:
            if not isinstance(f, dict):
                continue
            sev = f.get("severity", "").upper()
            if sev in counts:
                counts[sev] += 1
        return counts

    def _created_at_from_file(path: Path) -> str:
        match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{6}Z)", path.name)
        if match:
            raw = match.group(1)
            return f"{raw[:13]}:{raw[13:15]}:{raw[15:]}"
        return (
            datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _empty_counts() -> dict[str, int]:
        return {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def _row_from_report(report: Path, reports_root: Path) -> dict[str, object]:
        route_path = report.relative_to(reports_root).as_posix()
        parts = Path(route_path).parts
        return {
            "title": report.stem,
            "agent": parts[1] if len(parts) > 1 else "",
            "context": parts[0] if parts else "",
            "created_at": _created_at_from_file(report),
            "path": route_path,
            "findings_summary": _empty_counts(),
        }

    def _iter_handoffs(reports_root: Path) -> list[Path]:
        handoffs: list[Path] = []
        for root in (service.workspace_root / ".dadaia" / "handoff", reports_root):
            if root.exists():
                handoffs.extend(root.rglob("*.handoff.json"))
        return handoffs

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        retention = service.get_report_retention()
        try:
            retention.cleanup()
        except Exception as exc:  # noqa: BLE001
            _log.warning("Report retention cleanup skipped: %s", exc)
        retention_by_route = {
            record.artifact_path.removeprefix(".dadaia/reports/"): record
            for record in retention.list_reports()
        }
        results_by_path: dict[str, dict[str, object]] = {}
        if reports_root.exists():
            for report in reports_root.rglob("*.html"):
                if report.is_file():
                    row = _row_from_report(report, reports_root)
                    results_by_path[str(row["path"])] = row

            for handoff in _iter_handoffs(reports_root):
                try:
                    data = json.loads(handoff.read_text(encoding="utf-8"))
                    artifact = data.get("artifact", {})
                    if not isinstance(artifact, dict):
                        continue
                    artifact_path = str(artifact.get("path", ""))
                    if not artifact_path.startswith(".dadaia/reports/"):
                        continue
                    report_path = _report_route_path(artifact_path)
                    report_file = (reports_root / report_path).resolve()
                    try:
                        report_file.relative_to(reports_root)
                    except ValueError:
                        continue
                    if not report_file.is_file() or report_file.suffix.lower() != ".html":
                        continue
                    row = results_by_path.setdefault(
                        report_path,
                        _row_from_report(report_file, reports_root),
                    )
                    row["agent"] = data.get("agent") or row["agent"]
                    row["context"] = data.get("context") or row["context"]
                    row["created_at"] = data.get("produced_at") or row["created_at"]
                    row["findings_summary"] = _severity_counts(data.get("findings", []))
                except Exception as exc:  # noqa: BLE001
                    _log.warning("Skipping malformed handoff %s: %s", handoff, exc)

        results = list(results_by_path.values())
        now = datetime.datetime.now(tz=datetime.UTC)
        for row in results:
            record = retention_by_route.get(str(row["path"]))
            if record is None:
                row["important"] = False
                row["expires_at"] = None
                row["is_expired"] = False
                row["retention_reason"] = None
                row["retention_status"] = "unknown"
                continue
            expires_at = record.effective_timestamp + datetime.timedelta(hours=48)
            is_expired = expires_at <= now
            row["important"] = record.important
            row["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
            row["is_expired"] = is_expired
            if record.important:
                row["retention_status"] = "important"
                row["retention_reason"] = "Marked important"
            elif is_expired:
                row["retention_status"] = "expired"
                row["retention_reason"] = "Expired after 48h"
            else:
                row["retention_status"] = "expires"
                row["retention_reason"] = "Expires after 48h"
        results.sort(key=lambda r: str(r["created_at"]), reverse=True)
        body = json.dumps({"reports": results}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def mark_report_important(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Mark a report important from the Reports panel."""

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        retention = service.get_report_retention()
        try:
            artifact = retention.mark_important(path)
        except ValueError as exc:
            body = json.dumps({"error": "invalid_path", "message": str(exc)}).encode("utf-8")
            return (400, "application/json; charset=utf-8", body)
        body = json.dumps({"important": True, "artifact_path": artifact}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def unmark_report_important(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Remove important protection from a report from the Reports panel."""

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        retention = service.get_report_retention()
        try:
            artifact = retention.unmark_important(path)
        except ValueError as exc:
            body = json.dumps({"error": "invalid_path", "message": str(exc)}).encode("utf-8")
            return (400, "application/json; charset=utf-8", body)
        body = json.dumps({"important": False, "artifact_path": artifact}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def _report_route_path(artifact_path: str) -> str:
    prefix = ".dadaia/reports/"
    if artifact_path.startswith(prefix):
        return artifact_path[len(prefix) :]
    return artifact_path


# ---------------------------------------------------------------------------
# Report identity injection (operator demand 2026-06-11)
#
# Agent-authored reports carry arbitrary inline styles, frequently unreadable.
# At serve time we inject the dadaia identity stylesheets into the <head> so
# every report inherits the visual identity regardless of how it was authored.
# The link tags reference /static/tokens.css (palette + theme) and
# /static/reports-doc.css (base identity + a readability override that WINS
# over agent styling for body fg/bg). Only text/html bodies are mutated.
# ---------------------------------------------------------------------------

_REPORT_IDENTITY_HEAD = (
    "<script>(function(){var t=localStorage.getItem('dadaia-panel-theme');"
    "if(t&&(t==='mint'||t==='sage'||t==='warm')){document.documentElement.dataset.theme=t;}})();</script>"
    '<link rel="stylesheet" href="/static/tokens.css">'
    '<link rel="stylesheet" href="/static/reports-doc.css">'
)

_HEAD_OPEN_RE = re.compile(r"<head[^>]*>", re.IGNORECASE)
_HTML_OPEN_RE = re.compile(r"<html[^>]*>", re.IGNORECASE)

_REPORT_ASSET_MIME: dict[str, str] = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".json": "application/json; charset=utf-8",
}


def _report_content_type(suffix: str) -> str:
    """Content-type for a non-HTML report asset (default text/html for legacy)."""
    return _REPORT_ASSET_MIME.get(suffix, "text/html; charset=utf-8")


def _inject_report_identity(html: str) -> str:
    """Inject the dadaia identity stylesheets into a report's HTML <head>.

    Insertion makes inheritance win for base readability: the base layer is
    injected right after ``<head>`` (before any agent ``<style>`` inside head),
    and the reports-doc.css override layer uses ``!important`` on body fg/bg so
    it still wins regardless of agent inline styles.

    Falls back to inserting after ``<html>`` or prepending a ``<head>`` block
    when the report has no ``<head>``. Idempotent: a report already carrying the
    marker link is left unchanged.
    """
    if "/static/reports-doc.css" in html:
        return html
    head_match = _HEAD_OPEN_RE.search(html)
    if head_match is not None:
        idx = head_match.end()
        return html[:idx] + _REPORT_IDENTITY_HEAD + html[idx:]
    html_match = _HTML_OPEN_RE.search(html)
    if html_match is not None:
        idx = html_match.end()
        return html[:idx] + "<head>" + _REPORT_IDENTITY_HEAD + "</head>" + html[idx:]
    return "<head>" + _REPORT_IDENTITY_HEAD + "</head>" + html


def serve_report_file(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Serve a report HTML file with path-traversal guard.

    Resolves the requested path under ``<workspace_root>/.dadaia/reports/``.
    Returns 403 if the resolved path escapes the boundary.
    Returns 404 if the file does not exist.

    For ``text/html`` reports, the dadaia identity stylesheets are injected into
    the ``<head>`` at serve time (operator demand 2026-06-11) so every report
    inherits the visual identity. Non-HTML report assets are served verbatim.

    Security (OWASP A01, A03): Path.resolve() is used to canonicalise the
    requested path; relative_to() enforces the boundary without string ops.
    """

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        requested = (service.workspace_root / ".dadaia" / "reports" / path).resolve()
        # Path-traversal guard (OWASP A01)
        try:
            requested.relative_to(reports_root)
        except ValueError:
            return (403, "text/plain; charset=utf-8", b"403 Forbidden")
        if not requested.exists() or not requested.is_file():
            return (404, "text/plain; charset=utf-8", b"404 Not Found")
        content = requested.read_bytes()
        # Only mutate HTML reports; serve every other asset byte-verbatim.
        if requested.suffix.lower() in (".html", ".htm"):
            try:
                injected = _inject_report_identity(content.decode("utf-8"))
                return (200, "text/html; charset=utf-8", injected.encode("utf-8"))
            except UnicodeDecodeError:
                # Non-UTF-8 HTML — serve verbatim rather than corrupt bytes.
                return (200, "text/html; charset=utf-8", content)
        return (200, _report_content_type(requested.suffix.lower()), content)

    return _view


def delete_report_file(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Delete a report HTML file and handoffs that reference it.

    Path-traversal guard: resolves path under .dadaia/reports/.
    Returns 403 if outside boundary, 404 if not found, 200 on success.

    Security (OWASP A01, A03): same boundary check as serve_report_file.
    Deletes handoff JSON files under .dadaia/handoff/ and legacy adjacent
    handoffs under .dadaia/reports/ whose artifact.path points at the target
    report.
    """

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        target = (service.workspace_root / ".dadaia" / "reports" / path).resolve()
        try:
            target.relative_to(reports_root)
        except ValueError:
            return (403, "application/json; charset=utf-8", b'{"error": "forbidden"}')
        if not target.exists():
            return (404, "application/json; charset=utf-8", b'{"error": "not found"}')
        target.unlink()
        target_ref = target.relative_to(service.workspace_root).as_posix()
        for handoff_root in (
            service.workspace_root / ".dadaia" / "handoff",
            service.workspace_root / ".dadaia" / "reports",
        ):
            if not handoff_root.exists():
                continue
            for handoff in handoff_root.rglob("*.handoff.json"):
                try:
                    data = json.loads(handoff.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    continue
                artifact = data.get("artifact", {})
                if isinstance(artifact, dict) and artifact.get("path") == target_ref:
                    handoff.unlink()
        return (200, "application/json; charset=utf-8", b'{"deleted": true}')

    return _view
