"""T-44-5 — persona operative-directive emission in ``build_prompt_envelope`` (AC-2).

Two guarantees:

* **byte-stability (R5)** — a persona-LESS request produces the EXACT byte sequence the
  envelope produced before the persona field existed (the 9-field, indent=2, sort_keys
  payload). This byte-stability lock is the transport contract for every L2 worker.
* **operative directive** — a present persona is emitted wrapped in a directive that
  instructs the worker to ACT PER the mandate (the preamble), not merely as the bare
  mandate body, and the serialization stays sorted/indented and reproducible.
"""

from __future__ import annotations

import json

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRuntimeKind,
    GateEvidenceKind,
)
from dadaia_workspace.infrastructure.headless_adapter_base import build_prompt_envelope


def _request(*, persona: str | None = None) -> AgentRunRequest:
    return AgentRunRequest(
        role="product-engineer",
        prompt="do bounded work",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.44",
        task_id="run:spec_create",
        allowed_paths=("repos/dadaia-workspace/**",),
        forbidden_paths=("secrets.py",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
        persona=persona,
    )


def test_persona_less_envelope_is_byte_identical_to_pre_v0144() -> None:
    # The exact pre-persona payload: the 9 fields, indent=2, sort_keys=True. If the persona
    # field ever leaks into the persona-less path, this byte-equality assertion fails.
    expected = json.dumps(
        {
            "role": "product-engineer",
            "prompt": "do bounded work",
            "context": "dadaia-workspace",
            "release_id": "v0.1.44",
            "task_id": "run:spec_create",
            "allowed_paths": ["repos/dadaia-workspace/**"],
            "forbidden_paths": ["secrets.py"],
            "expected_schema": "agent-run-result-v1",
            "required_evidence": ["handoff"],
        },
        indent=2,
        sort_keys=True,
    )
    raw = build_prompt_envelope(_request(persona=None))
    assert raw == expected
    payload = json.loads(raw)
    assert "persona" not in payload
    assert set(payload) == {
        "role",
        "prompt",
        "context",
        "release_id",
        "task_id",
        "allowed_paths",
        "forbidden_paths",
        "expected_schema",
        "required_evidence",
    }


def test_present_persona_is_emitted_as_operative_directive_and_stays_serialization_stable() -> None:
    mandate = "You are acting as the product-engineer. Author the SPEC delta."
    raw = build_prompt_envelope(_request(persona=mandate))
    payload = json.loads(raw)
    assert "persona" in payload
    directive = payload["persona"]
    # The DIRECTIVE text — the "act per the mandate" instruction — must be present, not just
    # the mandate body. This is what makes the body operative rather than an inert sibling key.
    assert "OPERATIVE DIRECTIVE" in directive
    assert "act per the following role mandate" in directive
    assert "binding" in directive
    # The mandate body is still carried, after the directive preamble.
    assert mandate in directive
    assert directive.index("OPERATIVE DIRECTIVE") < directive.index(mandate)
    # sort_keys=True → "persona" sorts deterministically; re-dumping the parsed payload with
    # the same options reproduces the bytes.
    assert raw == json.dumps(payload, indent=2, sort_keys=True)
