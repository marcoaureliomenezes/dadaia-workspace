"""Fragment-guard: both halves of Drift 2/3 die in shared/output-handoff.md (A3 / C1).

Pins the v0.1.32 canonical worker-output contract at the fragment source level:

- A3 (Drift 3): the ``shared/output-handoff.md`` BODY contains NO ``schema_version`` field
  and instructs exactly ``schema`` = the transport id ``agent-run-result-v1`` as the field
  to emit.
- A3 (Drift 2): the BODY carries NO residual "conform to the ``output_schema``" emit-framing
  — the worker is never told to emit/conform-to the fragment's domain schema as the emitted
  field.
- The frontmatter ``output_schema: handoff-v1.1`` (a distinct concept — the fragment's own
  id, not the worker-emitted field) stays UNCHANGED.
- A5: no fragment under ``public/lifecycle_fragments/`` instructs ``schema_version``; no
  ``create_handoff`` fragment exists; ``shared.output_handoff`` is the single output contract.

Source-grep on the fragment file, but the goldens don't pin THIS property (regen would
silently accept drift) — kept as source-level tests, not folded into the goldens.
"""

from __future__ import annotations

from pathlib import Path

_FRAGMENTS = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "lifecycle_fragments"
)
_OUTPUT_HANDOFF = _FRAGMENTS / "shared" / "output-handoff.md"

_TRANSPORT_SCHEMA = "agent-run-result-v1"


def _split_frontmatter_body(text: str) -> tuple[str, str]:
    assert text.startswith("---\n"), "fragment must open with YAML frontmatter"
    end = text.index("\n---", 4)
    return text[: end + 4], text[end + 4 :]


# --- ① output-handoff body contract ----------------------------------------------------


def test_output_handoff_body_contract() -> None:
    text = _OUTPUT_HANDOFF.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter_body(text)

    # Drift 3: no schema_version field name in the body; instructs exactly `schema` =
    # the transport id.
    assert "schema_version" not in body
    assert "`schema`" in body
    assert _TRANSPORT_SCHEMA in body

    # Drift 2: no "conform to the output_schema" emit-framing in the body — the worker is
    # not told to emit/conform-to the fragment's domain schema as the emitted field.
    lowered = body.lower()
    assert "output_schema" not in lowered
    assert "conform" not in lowered or "output schema" not in lowered

    # The fragment's own id is a distinct concept and stays unchanged.
    assert "output_schema: handoff-v1.1" in frontmatter


# --- ② library-wide: no fragment instructs schema_version + single output contract -----


def test_library_wide_no_schema_version_instruction_and_single_output_contract() -> None:
    offenders = [
        str(path.relative_to(_FRAGMENTS))
        for path in _FRAGMENTS.rglob("*.md")
        if "schema_version" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"fragments still instruct schema_version: {offenders}"

    md = list(_FRAGMENTS.rglob("*.md"))
    assert not [p for p in md if "create_handoff" in p.name], "no create_handoff fragment may exist"
    # The single shared output contract is shared/output-handoff.md.
    assert _OUTPUT_HANDOFF.exists()
    shared_output = [p for p in (_FRAGMENTS / "shared").glob("*.md") if "output" in p.name]
    assert shared_output == [_OUTPUT_HANDOFF]
