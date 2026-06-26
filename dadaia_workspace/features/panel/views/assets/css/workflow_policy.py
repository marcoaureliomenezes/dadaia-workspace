"""Workflow model-governance editor CSS for the Dadaia Workspace Panel (Wave C, D-5).

Styles the first-class Workflows tab control plane: the per-workflow step matrix
(Step | Role | Harness | Model profile | Concrete model | Fragments | Gate | diff), the
segmented codex/pi harness control, the harness-filtered profile dropdown, the
default-vs-effective diff flag, the validate-before-save banner, and the run-snapshot
evidence tables. Tokens come from tokens.css; this module adds only layout + state.
"""

WORKFLOW_POLICY_CSS: str = """
.wfp-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.wfp-banner {
  margin: 0.5rem 0;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
}
.wfp-banner--info { background: var(--surface-2, #eef); color: var(--text, #223); }
.wfp-banner--ok { background: #e6f6ea; color: #1c6b30; }
.wfp-banner--error { background: #fdecea; color: #9b1c1c; }

.wfp-workflow { margin: 1.25rem 0; }
.wfp-workflow-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.wfp-workflow-title { margin: 0; font-size: 1.05rem; }

.wfp-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.wfp-matrix th, .wfp-matrix td {
  text-align: left;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--border, #ddd);
  vertical-align: middle;
}
.wfp-step-row--overridden { background: var(--surface-accent, #fff8e6); }
.wfp-diff { font-size: 0.8rem; color: var(--text-muted, #667); }
.wfp-diff--none { opacity: 0.6; }

.wfp-seg { display: inline-flex; border: 1px solid var(--border, #ccc); border-radius: 6px; overflow: hidden; }
.wfp-seg-btn {
  border: 0;
  background: transparent;
  padding: 0.2rem 0.55rem;
  cursor: pointer;
  font-size: 0.82rem;
}
.wfp-seg-btn--active { background: var(--accent, #2b6cb0); color: #fff; }

.wfp-profile-select { max-width: 16rem; }
.wfp-effort { color: var(--text-muted, #778); }
.wfp-gate { color: var(--accent, #b06a00); }

.wfp-reset-btn {
  font-size: 0.75rem;
  margin-left: 0.4rem;
  cursor: pointer;
}
.wfp-reset-btn[disabled] { opacity: 0.4; cursor: default; }

.wfp-runs { margin-top: 0.6rem; padding: 0.5rem; background: var(--surface-2, #f6f7fb); border-radius: 6px; }
.wfp-run { margin-bottom: 0.6rem; }
.wfp-run-head { font-size: 0.82rem; color: var(--text-muted, #667); margin-bottom: 0.25rem; }
.wfp-run-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.wfp-run-table th, .wfp-run-table td {
  text-align: left;
  padding: 0.25rem 0.4rem;
  border-bottom: 1px solid var(--border, #e5e5e5);
}
.wfp-error { color: #9b1c1c; }
"""
