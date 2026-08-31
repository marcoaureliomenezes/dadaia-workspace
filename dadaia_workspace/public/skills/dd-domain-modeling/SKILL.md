---
name: dd-domain-modeling
description: >
  Build and sharpen the project's domain language against the repo's CONTEXT.md. Use
  when writing or reading a term that has a glossary entry, naming a new concept,
  discussing codebase terminology, stress-testing domain relationships, or when a
  decision worth recording crystallises mid-session.
---

# dd-domain-modeling

One word carrying several meanings is how notes, grep-homonym patches and review
confusion breed. The remedy is one bounded-context file — `CONTEXT.md`, one definition
per term, explicit non-meanings — consumed inline while writing and actively sharpened
while designing. Format: [`CONTEXT-FORMAT.md`](CONTEXT-FORMAT.md).

## Consuming the language (any agent, any prose)

1. Use the canonical sense exactly as `CONTEXT.md` defines it; pick the canonical term
   over anything in its _Avoid_ list.
2. When a sentence could be read in a colliding sense, name the collision explicitly
   ("scaffold — the specs scaffold, not the SCAFFOLD test tier").
3. When two live senses genuinely coexist, qualify EVERY use ("test-quarantine" vs
   "quarantined bug") — an unqualified homonym in new text is a finding.
4. A term used in a sense `CONTEXT.md` does not carry is either a mistake (fix the
   text) or a new concept (add the entry — one definition, its non-meanings, in the
   same change that introduces the term).
5. This repo's known homonyms live in `CONTEXT.md` §Homonyms — **scaffold · sentinel ·
   quarantine · context · workflow** — read them before writing any of these words.

## Sharpening the model (design, grill, spec and review sessions)

- **Challenge against the glossary.** When the operator or a spec uses a term that
  conflicts with `CONTEXT.md`, call it out immediately: "the glossary defines
  'candidate' as X, but this sentence means Y — which is it?"
- **Sharpen fuzzy language.** When a term is vague or overloaded, propose a precise
  canonical term and its _Avoid_ list.
- **Stress-test with concrete scenarios.** When domain relationships are being
  discussed, invent edge-case scenarios that force precision about the boundary
  between concepts.
- **Cross-reference with code.** When someone states how something works, check
  whether the code agrees; surface any contradiction as a question, not a silent fix.
- **Update `CONTEXT.md` inline.** Capture a resolved term the moment it crystallises;
  create the file lazily at the first resolved term. `CONTEXT.md` is a glossary and
  nothing else — product truth stays in `specs/memory/`, decisions in `specs/ADRs/`.

## Offering a decision record

Offer an ADR (`specs/ADRs/decisions.jsonl`, shape in `specs/ADRs/AGENTS.md`; only the
operator flips it to `accepted`) only when all three hold:

1. **Hard to reverse** — changing course later costs something real.
2. **Surprising without context** — a future reader would ask "why this way?".
3. **A real trade-off** — genuine alternatives existed and one was picked for reasons.

Any missing leg: skip the record and keep the reasoning in the session's artifact.

## Where the file lives

- This repo: `CONTEXT.md` at the repo root. A consumer repo without one starts it at
  the first resolved term.
- Multi-context repos carry a root `CONTEXT-MAP.md` naming each context's own
  `CONTEXT.md`; infer the context the topic belongs to, and ask when unclear.

## References

- [`CONTEXT-FORMAT.md`](CONTEXT-FORMAT.md) — the glossary file's structure and rules.
- `dd-codebase-design` — the design vocabulary (module, seam, depth) the glossary
  builds on; domain terms name the seams.
