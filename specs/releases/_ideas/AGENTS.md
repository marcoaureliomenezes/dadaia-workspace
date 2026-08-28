# specs/releases/_ideas/ — Release Ideas

Scope: this directory only. An idea is a release candidate the operator has named but
not yet defined: `_ideas/<M.m.p>/SPEC.md` in `Draft`, nothing else. Promotion is a
`git mv` to `specs/releases/<M.m.p>/` in the commit that creates the release fold
(`RELEASE.jsonl`); the PR verdict gate refuses `_ideas/` paths. No other file lives here.
