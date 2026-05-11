# Spec: Feature — Workspace Export

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, `specs/foundation/SPEC.md`

---

## Contexto

O operador precisa conseguir migrar o workspace inteiro para um novo VPS sem perda de estado.
Os repos estão no git — esses são restauráveis. O que não está no git e se perderia sem um
artefato de export:

- Estado dos Spec Context Projects (quais repos, qual é primário, estados de ativação)
- Conteúdo de cursos da academy ativos
- Scripts de hooks instalados
- Catálogo de repos (repos.xlsx)
- Configuração dos três tools de AI (Claude Code, OpenCode, Codex)
- Dados críticos dos containers em `mnt/` (redacted-infra config, redacted-infra config, TLS certs)

Esta spec define o comando `dadaia export` que empacota tudo isso em um único `.tar.gz`.

---

## Glossário

| Termo | Definição |
|---|---|
| **Artefato de export** | Arquivo `.tar.gz` com todo o estado restaurável do workspace |
| **Dado durable** | Estado que deve sobreviver à migração (contexts, academy, configs) |
| **Dado efêmero** | Estado que pode ser recriado (venv, tmp, cache) |
| **Dado de git** | Código e specs em repos — restaurável com clone, não precisa do export |
| **Manifest** | JSON interno ao artefato descrevendo o conteúdo e metadados de restore |

---

## O que o artefato inclui

```
workspace-YYYY-MM-DD-HHMMSS.tar.gz
├── export-manifest.json          ← metadados + lista de contexts + URLs dos repos
├── .dadaia/
│   ├── states/                   ← spec_contexts.json, primary_context.json (CRÍTICO)
│   ├── academy/                  ← conteúdo de cursos ativos
│   ├── scripts/                  ← ctx-inject.sh, sdd-spec-gate.sh
│   ├── agentic/                  ← manifest e staging de assets agentic
│   └── src/                      ← repos.xlsx (catálogo de repos)
├── CLAUDE.md                     ← contexto VPS para Claude Code
├── AGENTS.md                     ← regras universais
├── opencode.json                 ← config do opencode-serve
├── .agents/
│   └── skills/                   ← skills universais instaladas
├── .claude/
│   ├── settings.json             ← hooks + permissions
│   ├── settings.local.json       ← permissões locais (se existir)
│   └── rules/                    ← regras SDD workspace-specific
├── .codex/
│   ├── config.toml               ← config Codex projetada
│   ├── hooks.json                ← hooks do Codex (se existir)
│   └── rules/                    ← rules Codex projetadas
├── .opencode/
│   ├── agents/
│   ├── commands/
│   └── skills/
└── mnt/                          ← volumes críticos de containers (se mnt/ existir)
    ├── redacted-infra/data/              ← config e logs do redacted-infra
    ├── redacted-infra/data/.redacted-infra/  ← config crítica do redacted-infra
    └── traefik/letsencrypt/      ← certificados TLS
```

## O que NÃO inclui (com justificativa)

| Caminho | Motivo da exclusão |
|---|---|
| `.dadaia/.venv/` | Recriável com `dadaia init` |
| `.dadaia/tmp/` | Efêmero por design |
| `.dadaia/contexts/` | Deprecated (213MB de resquícios) |
| `.dadaia/reports/` | Opcional via `--include-reports` |
| `repos/` | Gerenciados por git; URLs em spec_contexts.json |
| `mnt/redacted-infra/data/.npm/` | Cache npm, recriável |
| `mnt/redacted-infra/data/.cache/` | Cache linux/node, recriável |
| `mnt/redacted-infra/data/linuxbrew/` | Package manager, recriado pelo container |
| `mnt/redacted-infra/data/.codex/` | State CLI Codex, recriável |
| `*.env` | Secrets — nunca exportar tokens e API keys |

---

## CLI Interface

```bash
# Export padrão → .dadaia/dist/workspace-YYYY-MM-DD-HHMMSS.tar.gz
dadaia export

# Output em path customizado
dadaia export --output /tmp/backup/

# Incluir reports (excluídos por padrão)
dadaia export --include-reports

# Excluir mnt/ (útil quando mnt/ ainda não foi populado)
dadaia export --exclude-mnt

# Dry-run: listar o que seria incluído sem criar o arquivo
dadaia export --list
```

---

## Manifest (export-manifest.json)

```json
{
  "version": "1",
  "exported_at": "2026-05-09T12:00:00+00:00",
  "workspace_root": "/home/ubuntu/workspace",
  "dadaia_version": "4.0.0",
  "contexts": [
    {
      "name": "dadaia-workspace",
      "repo_url": "https://github.com/marcoaureliomenezes/dadaia-workspace.git",
      "is_primary": true,
      "state": "ativo"
    },
    {
      "name": "dadaia-agents",
      "repo_url": "https://github.com/marcoaureliomenezes/dadaia-agents.git",
      "is_primary": false,
      "state": "inativo"
    }
  ],
  "includes": [
    ".dadaia/states/",
    ".dadaia/academy/",
    ".dadaia/scripts/",
    ".dadaia/agentic/manifest.json",
    ".dadaia/src/",
    "CLAUDE.md",
    "AGENTS.md",
    "opencode.json",
    ".agents/skills/",
    ".claude/settings.json",
    ".claude/rules/",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".codex/rules/",
    ".opencode/",
    "mnt/"
  ],
  "mnt_included": true,
  "reports_included": false,
  "total_size_bytes": 0
}
```

---

## Procedimento de Restore em Novo VPS

```bash
# Pré-requisitos: Python 3.12+, git, docker, dadaia-workspace instalado

# 1. Extrair o artefato
mkdir -p /home/ubuntu/workspace
tar -xzf workspace-2026-05-09-120000.tar.gz -C /home/ubuntu/workspace/

# 2. Instalar dadaia-workspace (lib, não estado)
pip install dadaia-workspace  # ou: cd repos/dadaia-workspace && pip install -e .

# 3. Re-inicializar o workspace (recria .venv, propaga public assets, configura hooks)
dadaia init --workspace /home/ubuntu/workspace

# 4. Clonar os repos registrados (as URLs estão no manifest e em spec_contexts.json)
dadaia context activate dadaia-workspace
dadaia context activate dadaia-agents
# ... demais contexts conforme spec_contexts.json

# 5. Restaurar containers (usando dados de mnt/ já extraídos)
cd /home/ubuntu/workspace/repos/dadaia-agents
docker compose -f services/docker-compose.yml up -d
```

---

## Requisitos Funcionais

| ID | Requisito |
|---|---|
| FR1 | `dadaia export` gera `.dadaia/dist/workspace-<timestamp>.tar.gz` |
| FR2 | O artefato inclui todos os estados JSON de `.dadaia/states/` |
| FR3 | O artefato inclui `.dadaia/academy/` com conteúdo de cursos ativos |
| FR4 | O artefato inclui `.dadaia/scripts/` e `.dadaia/src/` |
| FR5 | O artefato inclui arquivos de configuração do workspace root: CLAUDE.md, AGENTS.md, opencode.json |
| FR6 | O artefato inclui projeções runtime: `.agents/skills/`, `.claude/`, `.codex/`, `.opencode/` e `opencode.json` |
| FR7 | O artefato inclui `.dadaia/agentic/manifest.json` para diagnóstico de versão/hashes |
| FR8 | O artefato inclui `mnt/` com excludes de cache definidos (se mnt/ existir e --exclude-mnt não usado) |
| FR9 | O artefato EXCLUI `.dadaia/.venv/`, `.dadaia/tmp/`, `.dadaia/contexts/`, `repos/` |
| FR10 | O artefato EXCLUI dentro de mnt/: `.npm/`, `.cache/`, `linuxbrew/`, `.codex/` (caches redacted-infra) |
| FR11 | O artefato EXCLUI qualquer arquivo `*.env` (secrets protection) — emitir warning se detectar |
| FR12 | `export-manifest.json` é gerado dentro do artefato com: timestamp, version, contexts+URLs, includes, sizes |
| FR13 | `dadaia export --list` imprime o manifest em stdout sem criar o arquivo |
| FR14 | `dadaia export --include-reports` adiciona `.dadaia/reports/` ao artefato |
| FR15 | `dadaia export --output <dir>` salva o arquivo no diretório especificado |
| FR16 | `dadaia export --exclude-mnt` omite o diretório `mnt/` inteiro |
| FR17 | `.dadaia/dist/` é criado automaticamente se não existir |

---

## Requisitos Não-Funcionais

| ID | Requisito |
|---|---|
| NFR1 | Export sem mnt/ deve completar em < 30 segundos |
| NFR2 | O artefato é legível e restaurável com apenas `tar` e `dadaia init` |
| NFR3 | O manifest é JSON válido e human-readable |
| NFR4 | Nenhum `*.env` ou arquivo com secrets é incluído; avisar se detectado |
| NFR5 | O comando é idempotente: rodar duas vezes gera dois arquivos com timestamps diferentes |
| NFR6 | O export segue a política de execução Python: usa `.dadaia/.venv/bin/python` |

---

## Arquitetura de Implementação

Seguindo a arquitetura de 4 camadas do dadaia-workspace:

```
CLI layer:
  dadaia_workspace/cli/commands/export.py
  → typer command, parse flags, call ExportService

Feature layer:
  dadaia_workspace/features/export/service.py
  → ExportService.run(options) → ExportResult
  → resolve_includes() → lista de paths a incluir
  → build_manifest() → dict
  → create_archive(paths, manifest, output_path) → Path

Core layer:
  dadaia_workspace/core/models/export.py
  → ExportOptions (dataclass: output, include_reports, exclude_mnt, list_only)
  → ExportResult (dataclass: path, size, manifest)
  → ExportManifest (dataclass: version, exported_at, contexts, includes, ...)

Infrastructure layer:
  Sem nova infraestrutura — usa stdlib: tarfile, json, os, datetime, shutil
```

**Nota:** O export usa `tarfile` da stdlib Python, sem dependências externas.

---

## Critérios de Aceite

1. `dadaia export` cria arquivo em `.dadaia/dist/workspace-<timestamp>.tar.gz`
2. `tar tzf <arquivo> | grep states/` confirma inclusão dos JSON states
3. `tar tzf <arquivo> | grep -E "\.venv|/tmp/|/repos/"` retorna vazio (excluídos)
4. `tar tzf <arquivo> | grep "\.npm"` retorna vazio (cache excluído)
5. `tar tzf <arquivo> | grep export-manifest.json` confirma manifest presente
6. `python3 -c "import tarfile; f=tarfile.open('<arquivo>'); f.extract('export-manifest.json', '/tmp/'); import json; print(json.load(open('/tmp/export-manifest.json'))['contexts'])"` lista os contexts corretamente
7. `dadaia export --list` imprime manifest sem criar arquivo
8. Extrair em /tmp/ + `dadaia init --workspace /tmp/restored/` funciona sem erros

---

## Fora de Escopo

- Restore automatizado com um único comando (o procedimento de restore é manual, documentado aqui)
- Backup automatizado periódico (cron job — feature separada)
- Criptografia do artefato (o operador é responsável pela segurança do arquivo)
- Upload automático para cloud storage (S3, GCS) — feature separada
- Export incremental (sempre full snapshot)
- Compressão diferencial
