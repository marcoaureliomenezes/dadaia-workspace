# `features/panel/views` — per-domain API view modules

**Release origin:** v0.1.55 (Architecture Decomposition, FR2). This module graph is the
canonical picture of the decomposed panel API surface: the former 1,279-line
`features/panel/views/api.py` god module split into **seven per-domain view modules**, one
responsibility each. `api.py` is **deleted** — there is no facade, barrel, or re-export shim.
`container.py` imports each `render_api_*` function from its per-domain module via explicit
named imports (extending the incumbent named-import pattern shared with
`panel.views.workflow_policy`).

Every module imports **only** `features.panel.service` (`PanelService`) plus `core.models` —
zero cross-feature / infrastructure edges — so FR2 changed no `setup.cfg` ignore edge.

```mermaid
classDiagram
    class PanelService {
        <<service>>
    }
    class container {
        <<composition root>>
        build_panel_views()
    }
    class api_servers {
        <<view module>>
        render_api_servers()
    }
    class api_contexts {
        <<view module>>
        render_api_contexts()
    }
    class api_agents {
        <<view module>>
        render_api_agents_canonical()
        render_api_agent_prompt()
    }
    class api_sessions {
        <<view module>>
        render_api_sessions()
    }
    class api_academy {
        <<view module>>
        render_api_academy()
    }
    class api_reports {
        <<view module>>
        render_api_reports()
        serve_report_file()
        mark_report_important()
        unmark_report_important()
        delete_report_file()
    }
    class api_health {
        <<view module>>
        render_health()
    }

    container ..> api_servers : named import
    container ..> api_contexts : named import
    container ..> api_agents : named import
    container ..> api_sessions : named import
    container ..> api_academy : named import
    container ..> api_reports : named import
    container ..> api_health : named import
    api_servers ..> PanelService
    api_contexts ..> PanelService
    api_agents ..> PanelService
    api_sessions ..> PanelService
    api_academy ..> PanelService
    api_reports ..> PanelService
    api_health ..> PanelService

    note for container "no facade / no api.py barrel — api.py is DELETED; each render_api_* named-imported from its domain module"
```

**Regeneration law.** Regenerate at the closure of every structural release (any rename,
split, or merge of a panel `api_*` view module or its public render functions). The module
and function names above are pinned by the introspection drift-guard
`tests/contract/test_architecture_diagrams_current.py`, which imports the live
`features.panel.views.api_*` modules and fails if a diagrammed name goes stale or a live
render function is missing.
