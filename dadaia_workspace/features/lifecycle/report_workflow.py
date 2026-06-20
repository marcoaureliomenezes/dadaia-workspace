"""Lifecycle report workflow proof using canonical runtime files."""

from __future__ import annotations

import datetime as dt
import html
import json
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneSnapshot
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort, RuntimeFileRef
from dadaia_workspace.features.lifecycle.hygiene import (
    HygieneCleanupResult,
    LifecycleHygieneService,
)
from dadaia_workspace.features.reports_validation.service import (
    ReportsValidationService,
    ValidationResult,
)


@dataclass(frozen=True)
class LifecycleReportWorkflowResult:
    """Artifacts emitted by one lifecycle report workflow run."""

    report: RuntimeFileRef
    handoff: RuntimeFileRef
    baseline_snapshot: RuntimeFileRef
    final_snapshot: RuntimeFileRef
    cleanup: HygieneCleanupResult
    validation: ValidationResult


class LifecycleReportWorkflow:
    """Write a report, matching handoff, hygiene evidence, and optional cleanup."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        runtime_files: RuntimeFilePort,
        hygiene: LifecycleHygieneService,
        validation: ReportsValidationService,
        now: dt.datetime | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._runtime_files = runtime_files
        self._hygiene = hygiene
        self._validation = validation
        self._now = now

    def run(
        self,
        *,
        context: str,
        release_id: str,
        run_id: str,
        apply_cleanup: bool = False,
    ) -> LifecycleReportWorkflowResult:
        produced_at = self._timestamp()
        filename_slug = self._safe_filename_slug(run_id)
        baseline = self._write_snapshot(
            label="baseline",
            context=context,
            release_id=release_id,
            run_id=run_id,
            timestamp=produced_at,
        )
        report = self._runtime_files.write_report(
            context=context,
            agent="lifecycle",
            filename=f"{filename_slug}.html",
            html=self._render_report(context=context, release_id=release_id, run_id=run_id),
        )
        handoff = self._runtime_files.write_handoff(
            context=context,
            filename=f"{filename_slug}.handoff.json",
            payload={
                "schema_version": "handoff-v1.1",
                "agent": "lifecycle",
                "context": context,
                "release_id": release_id,
                "produced_at": produced_at,
                "artifact": {
                    "type": "report",
                    "path": report.path,
                    "content_hash": report.content_hash,
                },
                "scope": "lifecycle-report",
                "metrics": {"cleanup_apply": str(apply_cleanup).lower()},
            },
        )
        validation = self._validation.validate_file(self._workspace_root / handoff.path)
        cleanup = self._hygiene.cleanup(dry_run=not apply_cleanup)
        final = self._write_snapshot(
            label="final",
            context=context,
            release_id=release_id,
            run_id=run_id,
            timestamp=self._timestamp(),
        )
        return LifecycleReportWorkflowResult(
            report=report,
            handoff=handoff,
            baseline_snapshot=baseline,
            final_snapshot=final,
            cleanup=cleanup,
            validation=validation,
        )

    def _write_snapshot(
        self,
        *,
        label: str,
        context: str,
        release_id: str,
        run_id: str,
        timestamp: str,
    ) -> RuntimeFileRef:
        snapshot = HygieneSnapshot(
            schema_version="hygiene-snapshot-v1",
            timestamp=timestamp,
            context=context,
            release_id=release_id,
            run_id=run_id,
            policy=self._hygiene.policy,
            counters=self._hygiene.status(),
            candidates=self._hygiene.cleanup(dry_run=True).candidates,
        )
        content = json.dumps(snapshot.to_dict(), indent=2, sort_keys=True)
        return self._runtime_files.write_run_artifact(
            run_id=run_id,
            filename=f"{label}-hygiene-snapshot.json",
            content=content,
        )

    def _timestamp(self) -> str:
        now = self._now or dt.datetime.now(dt.UTC)
        return now.isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _render_report(*, context: str, release_id: str, run_id: str) -> str:
        escaped_context = html.escape(context)
        escaped_release_id = html.escape(release_id)
        escaped_run_id = html.escape(run_id)
        return (
            '<!doctype html><html><head><meta charset="utf-8">'
            "<title>Lifecycle Report</title></head><body>"
            f"<h1>Lifecycle Report</h1><p>Context: {escaped_context}</p>"
            f"<p>Release: {escaped_release_id}</p><p>Run: {escaped_run_id}</p>"
            "</body></html>"
        )

    @staticmethod
    def _safe_filename_slug(run_id: str) -> str:
        return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in run_id)
