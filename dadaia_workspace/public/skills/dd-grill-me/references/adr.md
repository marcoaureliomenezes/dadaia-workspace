# ADR stage — dd-grill-me

## Threshold

The ADR threshold: `specs/ADRs/AGENTS.md`, heading "Shape".

## Question bank

Ask only what inspection leaves open, one question at a time.

- Reversibility: what undoing this costs, and by when it stops being cheap.
- Decision drivers: the forces that rank the options.
- Quality-attribute scenario: stimulus, environment, response; the response measure becomes `measured_by`.
- The surface's bug history: what prior fixes there say about the structure.
- Ownership and coupling: who owns the fact, what now depends on it.
- Reuse: the existing owner or pattern that already answers part of it.
- Failure and rollback: how it fails, how it is backed out.
- Cost: build, run and migration.
- Security: what trust boundary it moves.
- What it lets us delete.
- The accepted drawback: the option's cost the operator takes knowingly.
- Open issues: what stays unknown, and who decides later.

## Record

- The record's shape and the ruling rule: `specs/ADRs/AGENTS.md`, headings "Shape" and "Acceptance law (operator-only)".
