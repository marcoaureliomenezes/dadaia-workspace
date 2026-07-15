"""Full-capability certification result contract."""

from __future__ import annotations

from dadaia_workspace.features.certification.service import (
    CertificationCheck,
    CertificationResult,
)


def test_certification_result_is_stable_and_failure_sensitive() -> None:
    passed = CertificationResult(
        schema_version="dadaia-certification-v1",
        ok=True,
        workspace="/tmp/disposable",
        checks=(CertificationCheck("capabilities", "PASS", "ok"),),
    )
    assert passed.to_dict()["checks"][0]["name"] == "capabilities"

    failed = CertificationResult(
        schema_version="dadaia-certification-v1",
        ok=False,
        workspace="/tmp/disposable",
        checks=(CertificationCheck("panel", "FAIL", "no response"),),
    )
    assert failed.to_dict()["ok"] is False
