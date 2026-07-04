---
name: fanout-repo-slug-containment
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.58 closure backlog return (FR4 hardening — security LOW)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/workspace_guardrail.py#_install_guardrail_pair" }
    change: "harden the consumer-repo fan-out against a hostile/malformed repo_slug: v0.1.58 (FR4) derives repos/<repo_slug>/ from spec_contexts.json in _consumer_repos_for_root and _install_guardrail_pair then WRITES the workspace-law AGENTS.md/CLAUDE.md pair to each derived dir. Before writing, assert the resolved path is contained INSIDE the workspace repos/ root (e.g. Path.resolve().is_relative_to(repos_dir)) or REJECT a multi-component / traversal slug (a slug containing '/', '..', or an absolute component). Today a malformed spec_contexts.json repo_slug could theoretically direct a write outside repos/; the containment guard makes the fan-out write path defensively safe."
---

# BACKLOG — Consumer fan-out repo-slug containment guard

**Priority:** LOW (security hardening). v0.1.58 (R10) redesigned the consumer `AGENTS.md`
fan-out to detect Spec Context repos from `.dadaia/states/spec_contexts.json` (defensive
`json.loads`) and then WRITE the workspace-law pair to each derived `repos/<repo_slug>/`. The
registry is workspace-owned and normally trustworthy, so this is a hardening item, not an
open vulnerability — but the derived-dir WRITE currently trusts `repo_slug` verbatim.

Add a containment guard on the write path (`_install_guardrail_pair`, where the derived repo
dirs are consumed): assert each resolved consumer dir is `is_relative_to(<workspace>/repos)`,
or reject a `repo_slug` that carries a path separator, a `..` traversal, or an absolute
component. This closes the theoretical "a malformed/hostile `spec_contexts.json` `repo_slug`
directs a write outside `repos/`" hole surfaced during the FR4 review, symmetric with the
`repos_dir` join derivation in `_consumer_repos_for_root`.

**Override:** if the operator judges `spec_contexts.json` a fully trusted first-party surface
(only PM/CLI writes it), this may be closed as `REJECTED — trusted-input` rather than
implemented.
