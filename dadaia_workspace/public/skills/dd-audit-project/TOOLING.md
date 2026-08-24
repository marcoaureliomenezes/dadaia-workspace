# TOOLING — dd-audit-project dead-code detection commands

Disclosed reference reached from `SKILL.md`'s Dead-Code Detection section — the concrete
tool invocations behind the "flag unreachable/unused code" step of the audit.

**Pinning rule (inherited by every third-party install this skill or any quality
tooling prescribes):** every install command names an exact version or hash — never a
floating `latest`, an unpinned `pip install <name>`, or an unpinned `npx <name>` — the
same supply-chain discipline production dependencies already follow. A future tool
addition (audit or quality) pins on introduction by reading this rule; it never needs
restating.

## Unused Python Symbols

```bash
# vulture: find unused code
pip install vulture==2.14
vulture <src-dir> --min-confidence 80

# or with ruff
ruff check <src-dir> --select F401,F811,F841
```

## Unused TypeScript/JavaScript Exports

```bash
# ts-prune: find unused exports
npx ts-prune@0.10.3 --project tsconfig.json

# or knip
npx knip@5.36.3
```

## Dangling Imports

```bash
# Python
grep -rn "^import \|^from " <src-dir> | sort | uniq
# Cross-reference against actual usage; an import with no usage in the file is drift

# Node
npx depcheck@1.4.7 --json
```

## Unreachable Layers

A layer is "unreachable" if no other layer imports from it AND it is not an
entry point. Detect with:

```bash
# Python import graph
pip install pydeps==3.0.1
pydeps <src-dir> --max-bacon 3 --show-deps
```

Flag any module with zero importers and no declared entry-point role as a
dead-layer candidate.
