# Tasks: Feature — Workspace Import

> **Status:** Aprovado
> **Referência:** [PLAN.md](./PLAN.md) | [SPEC.md](./SPEC.md)

---

## Pre-Implementation Checklist

- [x] SPEC.md marcado como Aprovado
- [x] PLAN.md marcado como Aprovado
- [x] `specs/foundation/SPEC.md` lido (arquitetura 4 camadas)
- [x] `specs/constitution.md` lido
- [x] Python executado via `/home/ubuntu/workspace/.dadaia/.venv/bin/python`
- [x] Scripts temporários em `.dadaia/tmp/python/`

---

## [x] T01 — Criar modelos de domínio em core/models/import_.py

**Arquivo:** `dadaia_workspace/core/models/import_.py`

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ImportOptions:
    archive: Path
    workspace: Path
    skip_mnt: bool = False
    skip_activate: bool = False
    dry_run: bool = False

@dataclass
class ImportManifest:
    version: str
    exported_at: str
    workspace_root: str        # path absoluto na origem
    dadaia_version: str
    contexts: list[dict]       # [{name, repo_url, is_primary, state}]
    includes: list[str]
    mnt_included: bool
    reports_included: bool

@dataclass
class ImportResult:
    workspace_root: Path
    contexts_restored: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.core.models.import_ import ImportOptions, ImportManifest, ImportResult
from pathlib import Path
print('OK:', ImportOptions.__dataclass_fields__.keys())
"
```

---

## [x] T02 — Implementar ImportService.validate()

**Arquivo:** `dadaia_workspace/features/import_/service.py`

Criar `ImportService` com método `validate(archive: Path) -> ImportManifest`:

- Verifica que `archive` existe e termina em `.tar.gz`
- Abre o tarball com `tarfile.open(archive, "r:gz")`
- Extrai apenas o membro `export-manifest.json` como bytes (sem extrair para disco)
- Parse JSON; valida campos obrigatórios: `version`, `exported_at`, `workspace_root`, `contexts`
- Retorna `ImportManifest`; levanta `ValueError` com mensagem clara se inválido

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
import sys; sys.path.insert(0, 'repos/dadaia-workspace')
from dadaia_workspace.features.import_.service import ImportService
from pathlib import Path
# Use um artefato gerado por 'dadaia export --exclude-mnt' se disponível
archive = list(Path('/home/ubuntu/workspace/.dadaia/dist').glob('workspace-*.tar.gz'))
if archive:
    svc = ImportService(workspace_root=Path('/tmp/dadaia-test-import'))
    m = svc.validate(archive[0])
    print('workspace_root:', m.workspace_root)
    print('contexts:', [c['name'] for c in m.contexts])
else:
    print('Nenhum artefato encontrado — execute dadaia export --exclude-mnt primeiro')
"
```

---

## [x] T03 — Implementar ImportService.extract()

**No mesmo `ImportService`:**

```python
def extract(self, archive: Path, dest: Path, skip_mnt: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            if member.name.startswith("mnt/") and skip_mnt:
                continue
            if member.name.endswith(".env"):
                typer.echo(f"WARNING: .env skipped: {member.name}", err=True)
                continue
            members.append(member)
        tar.extractall(path=dest, members=members)
```

**Verificação:**
```bash
rm -rf /tmp/dadaia-test-import && mkdir /tmp/dadaia-test-import
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.import_.service import ImportService
from pathlib import Path
archive = list(Path('/home/ubuntu/workspace/.dadaia/dist').glob('workspace-*.tar.gz'))[0]
svc = ImportService(workspace_root=Path('/tmp/dadaia-test-import'))
svc.extract(archive, Path('/tmp/dadaia-test-import'), skip_mnt=True)
import os
for root, dirs, files in os.walk('/tmp/dadaia-test-import/.dadaia/states'):
    for f in files: print(f)
"
```

---

## [x] T04 — Implementar ImportService.patch_state()

**No mesmo `ImportService`:**

- Lê `.dadaia/states/spec_contexts.json`
- Para cada contexto:
  - Substitui prefixo de `specs_dir` de `old_root` por `new_root`
  - Seta `state = "inativo"`, `is_primary = False`, `activated_at = None`
- Escreve atomicamente (`.tmp` → `os.replace()`)
- Deleta `.dadaia/states/primary_context.json` se existir

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
import json
from pathlib import Path
state_file = Path('/tmp/dadaia-test-import/.dadaia/states/spec_contexts.json')
data = json.loads(state_file.read_text())
for ctx in data['contexts']:
    print(ctx['name'], '|', ctx['state'], '|', ctx['is_primary'], '|', ctx.get('specs_dir',''))
"
```

---

## [x] T05 — Implementar ImportService.bootstrap()

**No mesmo `ImportService`:**

```python
def bootstrap(self, workspace_root: Path) -> None:
    import subprocess
    subprocess.run(["dadaia", "init"], cwd=workspace_root, check=True)
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.import_.service import ImportService
from pathlib import Path
svc = ImportService(workspace_root=Path('/tmp/dadaia-test-import'))
svc.bootstrap(Path('/tmp/dadaia-test-import'))
print('bootstrap OK')
"
```

---

## [x] T06 — Implementar ImportService.restore_contexts()

**No mesmo `ImportService`:**

```python
def restore_contexts(self, manifest: ImportManifest, skip: bool) -> list[str]:
    if skip:
        return []
    errors = []
    ativo_contexts = [c for c in manifest.contexts if c["state"] == "ativo"]
    primary = next((c["name"] for c in ativo_contexts if c["is_primary"]), None)

    for ctx in ativo_contexts:
        result = subprocess.run(
            ["dadaia", "context", "activate", ctx["name"]],
            cwd=self.workspace_root, capture_output=True, text=True,
        )
        if result.returncode != 0:
            errors.append(f"{ctx['name']}: {result.stderr.strip()}")

    if primary and not errors:
        subprocess.run(
            ["dadaia", "context", "promote", primary],
            cwd=self.workspace_root, check=True,
        )
    return errors
```

**Verificação:**
```bash
# Executar após T04 e T05
dadaia context list  # deve mostrar os contextos do manifesto
```

---

## [x] T07 — Implementar ImportService.run() orquestrando as fases

**No mesmo `ImportService`:**

```python
def run(self, options: ImportOptions) -> ImportResult:
    manifest = self.validate(options.archive)

    if options.dry_run:
        self._print_dry_run(manifest, options)
        return ImportResult(workspace_root=options.workspace, contexts_restored=[], errors=[])

    self.extract(options.archive, options.workspace, options.skip_mnt)
    self.patch_state(
        workspace_root=options.workspace,
        old_root=Path(manifest.workspace_root),
    )
    self.bootstrap(options.workspace)
    errors = self.restore_contexts(manifest, options.skip_activate)
    restored = [c["name"] for c in manifest.contexts if c["state"] == "ativo"]
    return ImportResult(
        workspace_root=options.workspace,
        contexts_restored=restored,
        errors=errors,
    )
```

---

## [x] T08 — Criar comando CLI dadaia import

**Arquivo:** `dadaia_workspace/cli/commands/import_.py`

```python
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer()

@app.command("import")
def import_workspace(
    archive: Path = typer.Argument(..., help="Path to the .tar.gz archive generated by dadaia export"),
    workspace: Optional[Path] = typer.Option(None, "--workspace", "-w", help="Workspace root (default: cwd)"),
    skip_mnt: bool = typer.Option(False, "--skip-mnt", help="Do not extract mnt/ from archive"),
    skip_activate: bool = typer.Option(False, "--skip-activate", help="Skip context activation after extract"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen without changing anything"),
):
    """Import a workspace from a dadaia export archive."""
    from dadaia_workspace.features.import_.service import ImportService
    from dadaia_workspace.core.models.import_ import ImportOptions

    resolved_workspace = (workspace or Path.cwd()).resolve()
    options = ImportOptions(
        archive=archive.resolve(),
        workspace=resolved_workspace,
        skip_mnt=skip_mnt,
        skip_activate=skip_activate,
        dry_run=dry_run,
    )
    svc = ImportService(workspace_root=resolved_workspace)
    result = svc.run(options)
    # ... imprimir relatório (Phase 6 do SPEC)
```

**Verificação:**
```bash
dadaia import --help
# Deve mostrar: Usage: dadaia import [OPTIONS] ARCHIVE
# Com flags: --workspace, --skip-mnt, --skip-activate, --dry-run
```

---

## [x] T09 — Registrar no container.py e cli/main.py

**Arquivos a editar:**
- `dadaia_workspace/cli/main.py`: importar `import_` command e registrar no app Typer
- `dadaia_workspace/container.py`: adicionar `ImportService` se necessário

**Verificação:**
```bash
dadaia --help
# `import` deve aparecer na lista de comandos
```

---

## [x] T10 — Teste end-to-end

```bash
# Pré-requisito: ter um artefato gerado
dadaia export --exclude-mnt
ARCHIVE=$(ls -t /home/ubuntu/workspace/.dadaia/dist/workspace-*.tar.gz | head -1)
echo "Artefato: $ARCHIVE"

# Dry-run
dadaia import "$ARCHIVE" --workspace /tmp/test-import --dry-run
# Não deve criar nada em /tmp/test-import

# Import real (sem mnt/, sem ativar contextos)
dadaia import "$ARCHIVE" --workspace /tmp/test-import --skip-mnt --skip-activate

# Verificar extração
ls /tmp/test-import/.dadaia/states/
# spec_contexts.json deve existir

# Verificar patch de paths
python3 -c "
import json; data = json.load(open('/tmp/test-import/.dadaia/states/spec_contexts.json'))
for c in data['contexts']:
    print(c['name'], c['state'], c.get('specs_dir',''))
"
# Todos devem estar inativo, specs_dir apontando para /tmp/test-import/...

# Import completo com ativação
dadaia import "$ARCHIVE" --workspace /tmp/test-import2 --skip-mnt
dadaia --workspace-root /tmp/test-import2 context list  # ou cd /tmp/test-import2 && dadaia context list
dadaia doctor  # sem inconsistências

# Verificar critérios de aceite do SPEC
dadaia context show --json  # primário correto
```

---

## Critérios de Aceite Finais

| Critério | Verificação |
|---|---|
| FR1: import para cwd por padrão | `cd /tmp/x && dadaia import archive.tar.gz` → workspace em `/tmp/x` |
| FR2–FR3: validate aborta sem extração | Artefato sem manifest → erro antes de qualquer escrita |
| FR4–FR5: patch de paths e estados | `spec_contexts.json` com new root, state=inativo para todos |
| FR6: primary_context.json deletado | `ls .dadaia/states/` não mostra primary_context.json após patch |
| FR7: bootstrap executa init | `.dadaia/.venv/` criado após import |
| FR8–FR9: contexts ativados e primário promovido | `dadaia context list` mostra ativo + primário correto |
| FR11: --skip-mnt sem mnt/ | `ls /tmp/x/mnt` → não existe |
| FR12: --skip-activate sem clone | todos os contexts inativo após import |
| FR13: --dry-run sem efeitos | nenhum arquivo criado, nenhum subprocess executado |
| FR15: *.env nunca extraído | `find /tmp/x -name "*.env"` → vazio |
