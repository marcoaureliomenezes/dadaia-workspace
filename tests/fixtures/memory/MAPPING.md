# Field → Template Variable Mapping

This document is the **renderer spec** for T-MSS-03. The C-2 renderer implementer must
use this mapping to produce the correct template variables for each YAML atom type.

All templates live in `dadaia_workspace/public/templates/memory-*.html.j2`.
Meta variables (`project_name`, `context_name`, `today`, `last_updated_iso`,
`last_release_id`) are render-time context supplied by the renderer CLI — NOT schema
fields.

---

## memory-architecture-v1 → `memory-architecture.html.j2`

| YAML field | Template variable | Notes |
|---|---|---|
| `overview` | `architecture_overview` | Rendered as `<p>` prose inside `<section id="overview">`. |
| `layers` (array of `{name, description}`) | `layers_html` | Renderer must produce `<div class="layer"><strong>{{name}}</strong> — {{description}}</div>` for each item. |
| `dependency_rules_diagram` | `dependency_rules_mermaid` | Raw mermaid source; template wraps in `<pre class="mermaid">`. |
| `data_flow_diagram` | `data_flow_mermaid` | Raw mermaid source; template wraps in `<pre class="mermaid">`. Multiple diagram sections may be embedded as a single string with `<section>` HTML or as a multi-subsection string — renderer passes as-is. |
| `contracts` (array of `{from, to, contract_type, notes}`) | `contracts_rows` | Renderer must produce `<tr><td>{{from}}</td><td>{{to}}</td><td>{{contract_type}}</td><td>{{notes}}</td></tr>` for each item. |
| `runtime_state` (array of strings) | `runtime_state_bullets` | Renderer must produce `<li>{{item}}</li>` for each string. |
| `screenshots` (optional array of `{src, alt, caption?}`) | `screenshots_html` | Renderer produces `<img src="..." alt="..."><p>caption</p>` per item. If absent, template default `<p>Sem evidências visuais.</p>` applies. |

**Meta variables (render-time, not schema):**
- `project_name` / `context_name` — from CLI context or `--name` flag
- `today` / `last_updated_iso` — current date, ISO format
- `last_release_id` — active release id at render time

---

## memory-tech-stack-v1 → `memory-tech-stack.html.j2`

| YAML field | Template variable | Notes |
|---|---|---|
| `languages` (array of `{language, version, usage}`) | `languages_rows` | Renderer: `<tr><td>{{language}}</td><td>{{version}}</td><td>{{usage}}</td></tr>` per item. |
| `runtimes` (array of `{tool, version, role}`) | `runtimes_rows` | Renderer: `<tr><td>{{tool}}</td><td>{{version}}</td><td>{{role}}</td></tr>` per item. |
| `dependencies` (array of `{dependency, version, layer, justification}`) | `dependencies_rows` | Renderer: `<tr><td>{{dependency}}</td><td>{{version}}</td><td>{{layer}}</td><td>{{justification}}</td></tr>` per item. |
| `constraints` (array of strings) | `constraints_bullets` | Renderer: `<li>{{item}}</li>` per string. |
| `canonical_commands` (string) | `canonical_commands` | Passed as-is; template wraps in `<pre><code>`. |

**Note:** tech-stack template does NOT have a mermaid section. The CDN script tag in
the `<head>` is harmless even when no diagram is rendered.

**Meta variables:** same as architecture (project_name, today, last_release_id).

---

## memory-product-index-v1 → `memory-product-index.html.j2`

| YAML field | Template variable | Notes |
|---|---|---|
| `vision_oneliner` | `product_vision_oneliner` | Rendered as `<p>` in `<section id="vision">`. May be bold-wrapped by renderer. |
| `vision_paragraph` | `product_vision_paragraph` | Second `<p>` in vision section. |
| `users` (array of `{name, description}`) | `users_bullets` | Renderer: `<li><strong>{{name}}</strong> — {{description}}</li>` per item. |
| `catalog` (array of `{slug, title, summary, rank, keywords}`) | `catalog_items` | Renderer: `<li><a href="{{slug}}.html">{{title}}</a><span class="desc">— {{summary}}</span></li>` per item, ordered by `rank` ascending. `rank` and `keywords` are schema-required for Phase-1 catalog.json but not directly rendered into visible HTML (they are machine-readable metadata). |
| `capability_map_diagram` | `capability_map_mermaid` | Raw mermaid source; template wraps in `<pre class="mermaid">`. |
| `non_goals` (array of strings) | `explicit_non_goals` | Renderer: `<li>{{item}}</li>` per string. |
| `screenshots` (optional) | `screenshots_html` | Same pattern as architecture. |

**Catalog sort note:** renderer MUST sort `catalog` by `rank` ascending before rendering
`catalog_items` to guarantee stable output (determinism D-4).

**Phase-1 machine consumption:** `rank` and `keywords` fields from each catalog entry
are the inputs to `dadaia memory catalog generate` (Phase-1 `catalog.py`). The renderer
does NOT need to emit them as visible HTML — they are structural metadata on the source
atom only.

**Meta variables:** same as above.

---

## memory-product-feature-v1 → `memory-product-feature.html.j2`

| YAML field | Template variable | Notes |
|---|---|---|
| `feature_name` (optional) | `feature_name` | If absent, renderer derives from YAML filename stem (e.g. `workspace-init.yaml` → `workspace-init`). |
| `feature_subtitle` (optional) | `feature_subtitle` | If absent, renderer uses empty string or slug. |
| `purpose` (required) | `purpose_paragraphs` | Renderer splits on double-newlines and wraps each paragraph in `<p>`. |
| `flow_steps` (required, array of strings) | `flow_steps` | Renderer: `<li>{{item}}</li>` per string for the `<ol class="flow">`. |
| `diagram` (optional) | `flow_mermaid_optional` | If present: `<pre class="mermaid">{{diagram}}</pre>`. If absent: empty string (template renders nothing). |
| `typical_trigger` (required) | `typical_trigger` | Rendered as `<p>` in `<section id="trigger">`. |
| `differential` (required) | `differential` | Rendered as `<p>` in `<section id="differential">`. |
| `runtime_state` (required, array of strings) | `runtime_state_bullets` | Renderer: `<li>{{item}}</li>` per string. |
| `dependencies` (required, array of strings) | `dependencies_bullets` | Renderer: `<li>{{item}}</li>` per string. |

**Section IDs that must be present (AC-C2-2):**
- `<section id="purpose">`
- `<section id="flow">`
- `<section id="trigger">`
- `<section id="differential">`
- `<section id="runtime-state">`
- `<section id="dependencies">`

**Meta variables (render-time):**
- `feature_name` — derived from YAML field or filename stem
- `feature_subtitle` — derived from YAML field or slug
- `context_name` — from CLI context
- `last_updated_iso` — current date, ISO format
- `last_release_id` — active release id at render time

---

## Render-time context variables (all types)

The renderer CLI (`dadaia memory render <path.yaml>`) must supply these at render time.
They are NOT schema fields (meta fields are optional or absent from schemas).

| Variable | Source | Default |
|---|---|---|
| `project_name` | `--name` CLI flag or context name | `'Projeto'` |
| `context_name` | active context from `dadaia context show` | `'Projeto'` |
| `today` | `datetime.date.today().isoformat()` | today's ISO date |
| `last_updated_iso` | same as `today` at render time | today's ISO date |
| `last_release_id` | active release from `specs/releases/ACTIVE.md` or `'none'` | `'none'` |

---

## Design forks flagged

1. **`data_flow_diagram` in architecture**: the existing `architecture.html` contains
   TWO mermaid diagram sections under `<section id="data-flow">` — the pipeline asset
   chain AND the gate v3 SDD sequence diagram. The schema uses a single `data_flow_diagram`
   string field. The renderer must handle this by accepting a multi-section string (with
   newlines separating diagram blocks) or by the product-engineer embedding both diagrams
   as a single YAML block scalar. This is a known limitation: the C-6 migration will need
   to decide if the architecture atom gets a `data_flow_diagrams` (array) or keeps a
   single long string. For now the schema is `string` to keep it simple — the renderer
   passes it through unchanged.

2. **`layers_html` richness**: the existing `architecture.html` has very rich layer
   descriptions with `<ul>`, `<li>`, `<code>`, and `<strong>` inline HTML tags. Since the
   schema field is a plain string, the product-engineer must embed HTML-escaped or raw HTML
   in the YAML `description` field when needed. The renderer passes the `description` string
   through Jinja2 `| safe` filter to allow inline HTML. This is a deliberate trade-off
   between schema purity and migration fidelity.

3. **`catalog_items` rendering**: the template variable `catalog_items` in
   `memory-product-index.html.j2` is raw HTML (`{{ catalog_items | default('') }}`).
   The renderer must build the HTML string. Renderer must mark it `| safe` or pass it
   pre-built. The `rank` and `keywords` fields on catalog entries are NOT rendered into
   visible HTML — they are metadata for Phase-1 catalog.json consumption only.
