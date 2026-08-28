# specs/releases/_ideas/ — Release Ideas

Scope: this directory only. An idea is a release candidate the operator has named but
not yet defined: `_ideas/<M.m.p>/SPEC.md` in `Draft`, nothing else. Promotion is a
`git mv` to `specs/releases/<M.m.p>/` in the commit that creates `RELEASE.json`; the
pre-push chokepoint refuses `_ideas/` paths on a PR branch. No other file lives here.
