---
name: dadaia-glossary
description: >
  Sharpen terms inline against the repo's CONTEXT.md (the bounded-context file: one
  definition per term, explicit non-meanings). Use when writing or reading a term that
  has a glossary entry — use the canonical sense and name the other sense explicitly —
  and especially on the known homonyms: scaffold, sentinel, quarantine, context,
  workflow. Every agent that writes prose, specs, reports or code comments.
tldr: "One term, one sense: use CONTEXT.md's canonical definition inline and name the colliding sense explicitly."
applyTo: "**"
---

# dadaia-glossary

The same word carrying several meanings is how notes, grep-homonym patches and review
confusion breed. The remedy is not more notes — it is sharpening INLINE, backed by one
bounded-context file.

## 1. When

- Writing or reading a term that has a `CONTEXT.md` entry — anywhere: specs, reports,
  code comments, commit messages, reviews.
- Naming a NEW concept: check `CONTEXT.md` first; add the entry (with its non-meanings)
  in the same change that introduces the term.

## 2. The procedure — sharpen inline

1. Use the canonical sense exactly as `CONTEXT.md` defines it; never a listed _Avoid_ term.
2. When a sentence could be read in a colliding sense, name the collision explicitly
   ("scaffold — the specs scaffold, not the SCAFFOLD test tier").
3. When two live senses genuinely coexist, qualify EVERY use ("test-quarantine" vs
   "quarantined bug") — an unqualified homonym in new text is a finding.
4. A term used in a sense `CONTEXT.md` does not carry is either a mistake (fix the text)
   or a new concept (add the entry — one definition, its non-meanings, same change).

## 3. The five known homonyms

`CONTEXT.md` §Homonyms carries the canonical senses: **scaffold** · **sentinel** ·
**quarantine** · **context** · **workflow**. Read them before writing any of these words.

## 4. Where the file lives

- This repo: `CONTEXT.md` at the repo root (the code glossary; `specs/memory/` stays
  product truth). A consumer repo without one starts it at first need.
- Decision records are NOT this skill's format: ADRs live in `specs/ADRs/decisions.jsonl`
  under their own canon.

## 5. References

- `CONTEXT.md` — the bounded-context file this skill sharpens against.
- `dadaia-codebase-design` — the design vocabulary (module, seam, depth) CONTEXT.md builds on.
