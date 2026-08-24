# PARAMETERS — dadaia-test-stewardship declared defaults

Disclosed reference reached from `SKILL.md`'s references to "PARAMETERS.md" (§C, §H, and
the module intro). Every value below is this workspace's declared default, not a
universal constant — a consumer workspace re-parameterizes without forking the doctrine
in `SKILL.md`.

| Parameter | This repo's value | Abstract default |
|---|---|---|
| LARGE (E2E) cap | 30 (current ~84 — companion-release remediation target) | 12–15 per module |
| Flake rate | target < 0.5 % of runs | hard ceiling 1 % |
| Quarantine cap | max 8 tests | — |
| Quarantine escalation | 30 d unresolved → `disabled`; 30 clean days → restored | — |
| Deletion after disable | `disabled` + 1 release with no plan → deleted | — |
| Per-test timeout | unit 10 s / contract 30 s / integration 60 s / e2e 120 s | tier ratio holds |
| Wall-clock budget | frozen at the current baseline per job | freeze-then-ratchet |
| Mutation cadence | 1×/release, off the push path | same |
| Skip/disabled expiry | > 1 release, no registered plan → deleted | same |
