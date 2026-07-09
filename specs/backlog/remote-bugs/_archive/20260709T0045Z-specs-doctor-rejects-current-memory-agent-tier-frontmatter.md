# Specs doctor rejects current memory atoms because of `agent_tier` frontmatter

- Bug ID: `specs-doctor-rejects-current-memory-agent-tier-frontmatter`
- Severity: HIGH
- Context: `dd-chain-capture`
- Release: `v0.2.0`
- Component: `dadaia specs doctor` / memory atom schema
- Reported: 2026-07-09T00:45Z

## Symptom

`dadaia specs doctor` fails on the current `dd-chain-capture` memory atoms because every
atom uses `agent_tier` in frontmatter, but the installed doctor schema rejects that key.

Command:

```bash
DADAIA_CONTEXT=dd-chain-capture \
<workspace>/.dadaia/.venv/bin/dadaia specs doctor --json
```

Observed summary:

```json
{
  "summary": {
    "errors": 1,
    "warnings": 6
  }
}
```

The error is `LINT-1`, with repeated frontmatter schema violations:

```text
ERROR: Frontmatter schema violation: Additional properties are not allowed ('agent_tier' was unexpected)
```

Affected atoms include:

```text
specs/memory/architecture.md
specs/memory/quality-assurance.md
specs/memory/tech-stack.md
specs/memory/product/hermes-capture.md
specs/memory/product/s3-delivery.md
specs/memory/product/smoke-scraper.md
specs/memory/product/streaming-pipeline.md
specs/memory/product/vps-deployment.md
```

## Why this blocks dd-chain-capture

The active workspace skills and memory bootstrap contract use `agent_tier` as part of
the memory atom shape. The doctor for the installed editable `dadaia-workspace` rejects
that same shape as invalid. That means the release cannot get a clean specs doctor result
without either editing product memory during implementation or bypassing the doctor.

## Expected

The memory atom schema accepted by `dadaia specs doctor` should match the memory atom
shape emitted/consumed by the current workspace runtime, including `agent_tier` if it is
now part of the atom contract.

