# specs/releases/_ideas/ — Release Ideas

Scope: this directory only.

## 1. Rules

- An idea is a release candidate the operator has named but not yet defined.
- Shape: `_ideas/<M.m.p>/SPEC.md` in `Draft`, nothing else.
- Promotion moves the draft to `specs/releases/<M.m.p>/` in the commit where `dadaia release new <id>` creates `_RELEASE.json`.
- The pre-push chokepoint refuses `_ideas/` paths on a PR branch.
- No other file lives here.
