# Plan: Feature — Workspace Export

> **Status:** Aprovado
> **Referência:** [SPEC.md](./SPEC.md)

---

## Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Compressão | `tarfile` stdlib Python | Sem dependências externas; NFR6 exige uso do .venv; stdlib é suficiente |
| Formato do artefato | `.tar.gz` (tarfile mode `w:gz`) | Restaurável com apenas `tar`; compatível com qualquer Linux |
| Manifest | `export-manifest.json` dentro do artefato | Human-readable; inspecionável sem extrair (via `tar xzf -O`) |
| Output padrão | `.dadaia/dist/workspace-<timestamp>.tar.gz` | Dentro do workspace; fora do git; `dist/` é convenção Python |
| Secrets protection | Scan por `*.env` antes de criar o artefato; warning + exclusão forçada | NFR4; nunca incluir tokens mesmo que o operador esqueça |
| Arquitetura | 4 camadas: CLI → Feature → Core ← Infra | Padrão do dadaia-workspace; consistente com outras features |
| Criação de `dist/` | Dentro do `ExportService.run()` antes de criar o artefato | FR17; idempotente — `os.makedirs(exist_ok=True)` |
| `resolve_includes()` | Retorna lista de `(src_path, archive_name)` tuples | Separa lógica de inclusão da lógica de compressão; testável isoladamente |
| Exclusão de caches mnt/ | Passada via `tarfile.add(exclude=...)` callback | Mais limpo que rsync excludes; sem dependências externas |
| Leitura de contexts | Via `StateManager` (já existe na feature foundation) | Reutiliza o subsistema de state; não duplica leitura de JSON |

---

## Sequência de Implementação

```
T01 → T02 → T03 → T04 → T05    (camada Core + Feature)
T06 → T07                        (camada CLI)
T08                               (dist/ auto-criação)
T09                               (teste e2e)
```

---

## Arquitetura de Implementação

```
dadaia_workspace/
├── core/
│   └── models/
│       └── export.py             ← T01: ExportOptions, ExportResult, ExportManifest
├── features/
│   └── export/
│       ├── __init__.py
│       └── service.py            ← T02-T05: ExportService
└── cli/
    └── commands/
        └── export.py             ← T06: typer command
```

**Registro no DI container:** `T07` — adicionar `ExportService` ao container e `export` ao CLI.

---

## ExportService — Design Interno

```python
class ExportService:
    def run(self, options: ExportOptions) -> ExportResult:
        # T08: garante dist/ existe
        output_dir = options.output or workspace_root / ".dadaia/dist"
        output_dir.mkdir(parents=True, exist_ok=True)

        # T02: resolve includes
        includes = self.resolve_includes(options)

        # T03: build manifest
        manifest = self.build_manifest(includes, options)

        # T04: create archive
        archive_path = self.create_archive(includes, manifest, output_dir)

        return ExportResult(path=archive_path, size=archive_path.stat().st_size, manifest=manifest)

    def resolve_includes(self, options) -> list[tuple[Path, str]]:
        # Retorna lista de (src_path, archive_name)
        # Inclui dirs e arquivos individuais definidos no SPEC FR1-FR8

    def build_manifest(self, includes, options) -> ExportManifest:
        # Lê spec_contexts.json via StateManager para popular contexts[]
        # Inclui timestamp, dadaia_version, includes list

    def create_archive(self, includes, manifest, output_dir) -> Path:
        # Escreve manifest como JSON temporário, inclui no tarball
        # Para cada (src, arc_name): tarfile.add(src, arcname=arc_name, exclude=exclude_fn)
        # exclude_fn filtra: .env, .npm, .cache, linuxbrew, .codex, .venv, tmp, contexts
```

---

## Paths Incluídos (resolve_includes output)

| Origem (workspace_root-relative) | Nome no artefato | Condição |
|---|---|---|
| `.dadaia/states/` | `.dadaia/states/` | sempre |
| `.dadaia/academy/` | `.dadaia/academy/` | sempre |
| `.dadaia/scripts/` | `.dadaia/scripts/` | sempre |
| `.dadaia/agentic/manifest.json` | `.dadaia/agentic/manifest.json` | se existir |
| `.dadaia/src/` | `.dadaia/src/` | sempre |
| `.dadaia/reports/` | `.dadaia/reports/` | `--include-reports` |
| `CLAUDE.md` | `CLAUDE.md` | sempre (se existir) |
| `AGENTS.md` | `AGENTS.md` | sempre (se existir) |
| `opencode.json` | `opencode.json` | sempre (se existir) |
| `.agents/skills/` | `.agents/skills/` | sempre (se existir) |
| `.claude/settings.json` | `.claude/settings.json` | sempre (se existir) |
| `.claude/settings.local.json` | `.claude/settings.local.json` | se existir |
| `.claude/rules/` | `.claude/rules/` | sempre (se existir) |
| `.codex/config.toml` | `.codex/config.toml` | se existir |
| `.codex/hooks.json` | `.codex/hooks.json` | se existir |
| `.codex/rules/` | `.codex/rules/` | se existir |
| `.opencode/` | `.opencode/` | se existir |
| `mnt/` | `mnt/` | se existir e não `--exclude-mnt` |

---

## Exclusões em mnt/ (exclude callback)

Paths dentro de `mnt/` que são bloqueados pelo callback de exclusão do `tarfile.add`:

```python
EXCLUDED_MNT_PATTERNS = [
    ".npm", ".npm-global", ".cache", ".local",
    "linuxbrew", ".codex",
]
```

Qualquer `*.env` encontrado emite warning e é excluído (em qualquer path).

---

## Risks e Mitigações

| Risco | Mitigação |
|---|---|
| mnt/ grande (> 1GB) causa timeout | `resolve_includes` calcula tamanho antes; avisar se > 500MB; `--exclude-mnt` disponível |
| *.env incluído acidentalmente | Callback de exclusão do tarfile verifica padrão `*.env` em todos os paths |
| StateManager não inicializado | Wrap try/except: se contexts não lidos, manifest.contexts = [] com warning |
| dist/ cheio de exports antigos | Fora de escopo (NFR5 — idempotente gera timestamps diferentes; limpeza é responsabilidade do operador) |
| Arquivo já existe com mesmo timestamp | Timestamps têm segundos; praticamente impossível; sem tratamento especial |
