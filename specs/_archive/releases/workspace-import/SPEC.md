# Spec: Feature — Workspace Import

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, `specs/foundation/SPEC.md`, `specs/features/workspace-export/SPEC.md`

---

## Contexto

O operador exporta o workspace no VPS via `dadaia export`, obtendo um arquivo
`.tar.gz` portátil. Em seguida copia o arquivo para a máquina local e precisa
restaurar o ambiente completo com um único comando CLI — sem sequências manuais de
bash.

O fluxo de migração completo é:

```
[VPS]
  dadaia export --exclude-mnt        → .dadaia/dist/workspace-<ts>.tar.gz
  scp workspace-<ts>.tar.gz local:/  ← transferência manual (fora do escopo)

[máquina local]
  git clone <dadaia-workspace-repo>
  cd dadaia-workspace && pip install -e .
  cd <workspace-root-alvo>
  dadaia import /path/to/workspace-<ts>.tar.gz
```

O comando `dadaia import` é a única etapa CLI necessária após instalar o pacote.

---

## Glossário

| Termo | Definição |
|---|---|
| **Artefato** | Arquivo `.tar.gz` gerado por `dadaia export` |
| **Manifesto de export** | `export-manifest.json` embutido no artefato, descrevendo conteúdo e metadados |
| **Workspace root de origem** | Path absoluto onde o workspace foi exportado (campo `workspace_root` no manifesto) |
| **Workspace root de destino** | Path absoluto onde `dadaia import` é executado (ou valor de `--workspace`) |
| **Patch de paths** | Reescrita de paths absolutos nos JSONs de estado para refletir o novo workspace root |

---

## Fluxo Completo (6 fases)

```
Phase 1: VALIDATE   → abre o artefato, extrai e valida export-manifest.json
Phase 2: EXTRACT    → extrai conteúdo para workspace root de destino
Phase 3: PATCH      → reescreve paths absolutos nos JSONs; reseta estados
Phase 4: BOOTSTRAP  → executa `dadaia init` (cria .venv, propaga assets públicos)
Phase 5: RESTORE    → ativa + promove contexts conforme manifesto
Phase 6: REPORT     → exibe resumo do que foi restaurado
```

---

## CLI Interface

```bash
# Importar para o diretório atual como workspace root
dadaia import <archive>

# Importar para diretório específico
dadaia import <archive> --workspace <dir>

# Pular extração de mnt/ (útil em máquina local sem containers VPS)
dadaia import <archive> --skip-mnt

# Pular ativação de contextos (só extrai + init; não clona repos)
dadaia import <archive> --skip-activate

# Dry-run: mostra o que seria feito sem alterar nada
dadaia import <archive> --dry-run
```

### Defaults

| Flag | Default | Justificativa |
|---|---|---|
| `--workspace` | cwd | Operador executa `cd <destino> && dadaia import <arquivo>` |
| `--skip-mnt` | `False` | Preserva comportamento completo; operador opta por pular |
| `--skip-activate` | `False` | Experiência completa por padrão |
| `--dry-run` | `False` | Não-destrutivo quando explicitado |

---

## Comportamento por Fase

### Phase 1 — Validate

1. Verifica que o arquivo existe e tem extensão `.tar.gz`.
2. Abre o tarball e extrai apenas `export-manifest.json` (sem descompactar tudo).
3. Valida campos obrigatórios: `version`, `exported_at`, `workspace_root`, `contexts`.
4. Se inválido: aborta com mensagem indicando o campo ausente e `dadaia export` como ação de geração.

### Phase 2 — Extract

1. Extrai todos os membros do tarball para `<workspace-root-destino>/`.
2. Se `--skip-mnt`: filtra membros cujo path começa com `mnt/`.
3. Nunca sobrescreve `*.env` — emite warning se algum membro do artefato tiver esse padrão (não deve acontecer pois export os exclui, mas importa garantir).
4. Não extrai `repos/` (não está no artefato por design).
5. Se `--dry-run`: lista os membros que seriam extraídos e para sem alterar disco.

### Phase 3 — Patch State

Após extração, os JSONs de estado em `.dadaia/states/` contêm paths absolutos do workspace de origem. O patch corrige isso.

#### 3a — Rewrite `spec_contexts.json`

Para cada contexto:
- `specs_dir`: substituir prefixo `<workspace-root-origem>` por `<workspace-root-destino>`.
- `state`: forçar para `"inativo"` — repos não estão em disco ainda.
- `is_primary`: forçar para `false`.
- `activated_at`: forçar para `null`.
- `current_branch`: **preservar** — é lido pelo `activate` para fazer `git checkout <branch>` após o clone.

Escrever atomicamente (`.tmp` → `os.replace()`).

#### 3b — Delete `primary_context.json`

Remover se existir — será recriado por `dadaia context promote` na Phase 5.

#### 3c — Preservar `academy.json` e `repos.xlsx`

Esses arquivos não têm paths absolutos — sem alteração.

### Phase 4 — Bootstrap

Executar `dadaia init` via subprocess no workspace root de destino.

Isso:
- Cria `.dadaia/.venv/` com dependências do pacote instalado.
- Executa `dadaia public stage` + `dadaia public install --target all` (sem `--force` — não sobrescreve customizações já extraídas).
- Cria dirs ausentes sem destruir conteúdo existente.

Se `--skip-activate` + `--dry-run`: pular Phase 4 também.

### Phase 5 — Restore Contexts

Usando os dados do manifesto (não do JSON patchado, para evitar races):

1. Para cada contexto onde `state == "ativo"` no manifesto:
   - Executar `dadaia context activate <name>` — clona o repo em `repos/<slug>/`.
   - `activate` lê `current_branch` do estado (preservado na Phase 3a) e faz `git checkout <branch>` automaticamente após o clone — não é necessária nenhuma ação extra aqui.
   - Se repo já existe em disco (ex: usuário já tinha clonado `dadaia-workspace`): `activate` detecta e pula o clone.

2. Após todas as ativações, promover o contexto primário:
   - Executar `dadaia context promote <primary-name>` onde `primary-name` é o contexto com `is_primary == true` no manifesto.

3. Se `--skip-activate`: pular esta fase inteiramente.

### Phase 6 — Report

Exibir ao operador:

```
✓ Workspace importado em /home/marco/workspace
  Origem:   /home/ubuntu/workspace (VPS, exportado em 2026-05-12T10:00:00)
  Versão:   dadaia-workspace 4.0.0

Contextos restaurados:
  ✓ dadaia-workspace  [primário]
  ✓ dadaia-agents
  ✓ workflow-tools

Academy:
  0 cursos (nenhum exportado ou todos já presentes)

Próximos passos:
  - Adicione secrets em services/conf/*.env (não foram exportados)
  - Execute "dadaia doctor" para verificar consistência
```

---

## Requisitos Funcionais

| ID | Requisito |
|---|---|
| FR1 | `dadaia import <archive>` extrai o artefato para o workspace root de destino (cwd por padrão) |
| FR2 | `dadaia import` lê e valida `export-manifest.json` antes de qualquer operação destrutiva |
| FR3 | Se `export-manifest.json` ausente ou inválido, o comando aborta sem alterar o workspace |
| FR4 | `dadaia import` reescreve paths absolutos em `spec_contexts.json` trocando o workspace root de origem pelo de destino |
| FR5 | `dadaia import` reseta todos os contextos para `inativo` e `is_primary=false` após o patch |
| FR6 | `dadaia import` deleta `primary_context.json` antes do bootstrap |
| FR7 | `dadaia import` executa `dadaia init` no workspace root de destino após o patch |
| FR8 | `dadaia import` executa `dadaia context activate <name>` para cada contexto que estava `ativo` no manifesto |
| FR9 | `dadaia import` executa `dadaia context promote <primary>` para o contexto marcado `is_primary=true` no manifesto |
| FR10 | Se `repos/<slug>/` já existir em disco, `activate` pula o clone sem erro |
| FR11 | `--skip-mnt` omite extração de qualquer membro cujo path começa com `mnt/` |
| FR12 | `--skip-activate` pula as Phases 5 (activate + promote) |
| FR13 | `--dry-run` exibe o que seria feito sem modificar disco, JSONs ou executar subprocess |
| FR14 | `--workspace <dir>` define o workspace root de destino; cria o diretório se ausente |
| FR15 | Nenhum arquivo `*.env` é extraído — se detectado no artefato, emite warning e pula |
| FR16 | Ao final, exibe resumo com: origem, destino, versão exportada, contextos restaurados, cursos e próximos passos |
| FR17 | Se algum `dadaia context activate` falhar (ex: sem acesso git), reporta o erro e continua com os demais |

---

## Requisitos Não-Funcionais

| ID | Requisito |
|---|---|
| NFR1 | Import sem `mnt/` deve completar em < 60 segundos (excluindo tempo de clone de repos) |
| NFR2 | O comando é idempotente: executar duas vezes no mesmo workspace não corrompe o estado |
| NFR3 | Nenhum `*.env` é extraído, mesmo que presente no artefato por engano |
| NFR4 | Falha em qualquer clone individual não aborta os demais — todos os erros são reportados ao final |
| NFR5 | O comando usa o Python do sistema (não do workspace .venv) — é executado antes do bootstrap |

---

## Arquitetura de Implementação

Seguindo as 4 camadas do dadaia-workspace:

```
CLI layer:
  dadaia_workspace/cli/commands/import_.py
  → typer command, parse flags, resolve workspace root, call ImportService

Feature layer:
  dadaia_workspace/features/import_/service.py
  → ImportService.run(options: ImportOptions) → ImportResult
  → validate(archive)
  → extract(archive, workspace_root, skip_mnt)
  → patch_state(workspace_root, old_root, new_root)
  → bootstrap(workspace_root)
  → restore_contexts(manifest, workspace_root, skip_activate)

Core layer:
  dadaia_workspace/core/models/import_.py
  → ImportOptions (dataclass: archive, workspace, skip_mnt, skip_activate, dry_run)
  → ImportResult (dataclass: workspace_root, contexts_restored, errors)

Infrastructure layer:
  Sem nova infraestrutura — usa stdlib: tarfile, json, subprocess, os, shutil
```

**Nota:** `bootstrap()` e `restore_contexts()` chamam o CLI `dadaia` via `subprocess` para reusar exatamente o mesmo comportamento que o operador teria ao executar manualmente. Isso respeita RF-SLOPE-006.

---

## Critérios de Aceite

1. `dadaia import workspace-<ts>.tar.gz` em diretório vazio restaura o workspace completo.
2. `dadaia context list` após import mostra os mesmos contextos do workspace de origem.
3. `dadaia context show --json` mostra o contexto primário correto.
4. `dadaia doctor` após import não reporta inconsistências.
5. `dadaia import --dry-run` não altera nenhum arquivo.
6. `dadaia import --skip-mnt` restaura tudo exceto `mnt/`.
7. `dadaia import --skip-activate` deixa todos os contextos como `inativo`.
8. Executar `dadaia import` duas vezes no mesmo diretório não corrompe o estado.

---

## Fora de Escopo

- Download automático do artefato de storage remoto (S3, GCS, SFTP)
- Restore seletivo de contextos individuais
- Merge entre workspaces (import sobre workspace existente com dados diferentes)
- Verificação de integridade via hash do artefato
- Criptografia/decriptografia do artefato
