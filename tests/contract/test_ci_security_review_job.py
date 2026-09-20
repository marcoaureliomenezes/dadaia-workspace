"""Intent: CONTRACT — the PR gate is the official security-review Action (0.4.7 c5 FR5,
ADR 0016): one job, pinned to a sha, on both PR edges, fed by the CLAUDE_API_KEY secret.
Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

_CI_YML = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_security_review_job_is_the_pinned_official_action() -> None:
    jobs = yaml.safe_load(_CI_YML.read_text(encoding="utf-8"))["jobs"]
    assert "security-review" in jobs
    assert not {name for name in jobs if "verdict" in name}, "verdict jobs must be gone"
    job = jobs["security-review"]
    assert "pull_request" in job["if"] and "develop" in job["if"] and "main" in job["if"]
    uses = [step.get("uses", "") for step in job["steps"]]
    action = next(u for u in uses if u.startswith("anthropics/claude-code-security-review@"))
    sha = action.split("@", 1)[1].split()[0]
    assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), action
    step = next(s for s in job["steps"] if s.get("uses", "") == action)
    assert step["with"]["claude-api-key"] == "${{ secrets.CLAUDE_API_KEY }}"
