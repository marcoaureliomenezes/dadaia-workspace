# Tasks: Feature — Workspace Export

> **Status:** Aprovado
> **Referência:** [PLAN.md](./PLAN.md) | [SPEC.md](./SPEC.md)

---

## Pre-Implementation Checklist

- [x] SPEC.md marcado como Aprovado
- [x] PLAN.md marcado como Aprovado
- [ ] `specs/foundation/SPEC.md` lido (arquitetura 4 camadas)
- [ ] `specs/constitution.md` lido
- [ ] Python executado via `/home/ubuntu/workspace/.dadaia/.venv/bin/python`
- [ ] Scripts temporários em `.dadaia/tmp/python/`

---

## T01 — Criar modelos de domínio em core/models/export.py

**Arquivo:** `dadaia_workspace/core/models/export.py`

**Criar dataclasses:**
```python
@dataclass
class ExportOptions:
    output: Path | None = None
    include_reports: bool = False
    exclude_mnt: bool = False
    list_only: bool = False

@dataclass
class ExportManifest:
    version: str
    exported_at: str          # ISO 8601
    workspace_root: str
    dadaia_version: str
    contexts: list[dict]      # [{name, repo_url, is_primary, state}]
    includes: list[str]
    mnt_included: bool
    reports_included: bool
    total_size_bytes: int

@dataclass
class ExportResult:
    path: Path
    size: int
    manifest: ExportManifest
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.core.models.export import ExportOptions, ExportManifest, ExportResult
print('OK:', ExportOptions(), ExportManifest.__dataclass_fields__.keys())
"
```

---

## T02 — Implementar resolve_includes() em ExportService

**Arquivo:** `dadaia_workspace/features/export/service.py`

**Criar `ExportService` com método `resolve_includes(options: ExportOptions) -> list[tuple[Path, str]]`:**

- Retorna lista de `(src_absolute_path, archive_relative_name)` tuples
- Inclui apenas paths que existem no filesystem
- Segue a tabela de paths do PLAN.md
- Adiciona `.dadaia/reports/` se `options.include_reports`
- Adiciona `mnt/` se existir e não `options.exclude_mnt`
- Emite warning (stderr) para qualquer `*.env` encontrado — não inclui

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
import sys; sys.path.insert(0, 'repos/dadaia-workspace')
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.core.models.export import ExportOptions
from pathlib import Path
svc = ExportService(workspace_root=Path('/home/ubuntu/workspace'))
includes = svc.resolve_includes(ExportOptions())
for src, arc in includes[:5]:
    print(f'{arc} <- {src}')
print(f'Total: {len(includes)} entradas')
"
```

---

## T03 — Implementar build_manifest()

**No mesmo `ExportService`:**

```python
def build_manifest(self, includes, options) -> ExportManifest:
    # Lê contexts via StateManager (spec_contexts.json + primary_context.json)
    # Se StateManager falhar: contexts = [], emite warning
    # Calcula total_size_bytes: sum(src.stat().st_size for src, _ in includes if src.is_file())
    # dadaia_version: lê de dadaia_workspace/__version__.py ou importlib.metadata
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.core.models.export import ExportOptions
from pathlib import Path
import json
svc = ExportService(workspace_root=Path('/home/ubuntu/workspace'))
opts = ExportOptions()
includes = svc.resolve_includes(opts)
manifest = svc.build_manifest(includes, opts)
print(json.dumps({'contexts': manifest.contexts, 'includes': manifest.includes[:3]}, indent=2))
"
```

---

## T04 — Implementar create_archive()

**No mesmo `ExportService`:**

```python
def create_archive(self, includes, manifest, output_dir) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    archive_path = output_dir / f"workspace-{timestamp}.tar.gz"

    def exclude_fn(tarinfo):
        # Bloquear: .env files, mnt/ caches (EXCLUDED_MNT_PATTERNS)
        # Retorna None para excluir, tarinfo para incluir

    with tarfile.open(archive_path, "w:gz") as tar:
        # Adicionar export-manifest.json como bytes em memória
        manifest_bytes = json.dumps(asdict(manifest), indent=2).encode()
        manifest_info = tarfile.TarInfo(name="export-manifest.json")
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

        # Adicionar cada include
        for src, arc_name in includes:
            tar.add(src, arcname=arc_name, recursive=True, filter=exclude_fn)

    return archive_path
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.core.models.export import ExportOptions
from pathlib import Path
svc = ExportService(workspace_root=Path('/home/ubuntu/workspace'))
opts = ExportOptions(list_only=False, exclude_mnt=True)
includes = svc.resolve_includes(opts)
manifest = svc.build_manifest(includes, opts)
path = svc.create_archive(includes, manifest, Path('/tmp/dadaia-test-export'))
print('Criado:', path)
import subprocess
subprocess.run(['tar', 'tzf', str(path)], check=True)
"
```

---

## T05 — Implementar ExportService.run() orquestrando as fases

**No mesmo `ExportService`:**

```python
def run(self, options: ExportOptions) -> ExportResult:
    output_dir = options.output or (self.workspace_root / ".dadaia/dist")
    output_dir.mkdir(parents=True, exist_ok=True)

    includes = self.resolve_includes(options)
    manifest = self.build_manifest(includes, options)

    if options.list_only:
        # Imprime manifest como JSON e retorna sem criar arquivo
        print(json.dumps(asdict(manifest), indent=2))
        return ExportResult(path=None, size=0, manifest=manifest)

    archive_path = self.create_archive(includes, manifest, output_dir)
    manifest.total_size_bytes = archive_path.stat().st_size

    return ExportResult(path=archive_path, size=manifest.total_size_bytes, manifest=manifest)
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/python -c "
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.core.models.export import ExportOptions
from pathlib import Path
svc = ExportService(workspace_root=Path('/home/ubuntu/workspace'))
result = svc.run(ExportOptions(list_only=True, exclude_mnt=True))
print('list_only OK — sem arquivo criado')
"
```

---

## T06 — Criar comando CLI dadaia export

**Arquivo:** `dadaia_workspace/cli/commands/export.py`

**Implementar com typer:**

```python
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer()

@app.command()
def export(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    include_reports: bool = typer.Option(False, "--include-reports", help="Include .dadaia/reports/"),
    exclude_mnt: bool = typer.Option(False, "--exclude-mnt", help="Exclude mnt/ volumes"),
    list_only: bool = typer.Option(False, "--list", help="Dry-run: print manifest without creating file"),
):
    """Export workspace state to a portable .tar.gz archive."""
    from dadaia_workspace.features.export.service import ExportService
    from dadaia_workspace.core.models.export import ExportOptions
    # ... resolver workspace_root, criar service, chamar run(), imprimir resultado
```

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia export --help
# Deve mostrar: Usage: dadaia export [OPTIONS]
# Com flags: --output, --include-reports, --exclude-mnt, --list
```

---

## T07 — Registrar ExportService e comando export no CLI

**Arquivos a editar:**
- `dadaia_workspace/cli/app.py` (ou equivalente onde comandos são registrados)
- DI container se existir

**Ação:** Adicionar `export` ao grupo de comandos do typer principal, garantindo que
`dadaia export` funciona via o entrypoint instalado.

**Verificação:**
```bash
/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia --help
# `export` deve aparecer na lista de comandos disponíveis
```

---

## T08 — Garantir criação automática de .dadaia/dist/

Já coberto no `ExportService.run()` com `output_dir.mkdir(parents=True, exist_ok=True)`.

**Verificação adicional (idempotência — FR17):**
```bash
# Remover dist/ temporariamente para testar auto-criação
rm -rf /home/ubuntu/workspace/.dadaia/dist
/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia export --exclude-mnt
ls /home/ubuntu/workspace/.dadaia/dist/
# dist/ deve ter sido criado e conter workspace-*.tar.gz
```

---

## T09 — Teste end-to-end: export, inspeção e verificação de critérios de aceite

**Executar os critérios de aceite do SPEC.md:**

```bash
# 1. Export padrão
/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia export --exclude-mnt

# Capturar nome do arquivo
ARCHIVE=$(ls -t /home/ubuntu/workspace/.dadaia/dist/workspace-*.tar.gz | head -1)
echo "Arquivo: $ARCHIVE"

# 2. Verificar inclusão de states/
tar tzf "$ARCHIVE" | grep states/
# Deve retornar pelo menos uma linha

# 3. Verificar exclusão de .venv, repos/, /tmp/
tar tzf "$ARCHIVE" | grep -E "\.venv|/repos/|/tmp/"
# Deve retornar vazio

# 4. Verificar manifest presente
tar tzf "$ARCHIVE" | grep export-manifest.json
# Deve retornar: export-manifest.json

# 5. Verificar manifest válido
tar xzf "$ARCHIVE" -O export-manifest.json | python3 -c "
import sys, json
m = json.load(sys.stdin)
print('version:', m['version'])
print('contexts:', len(m['contexts']))
print('includes:', len(m['includes']))
"

# 6. Dry-run sem criar arquivo
COUNT_BEFORE=$(ls /home/ubuntu/workspace/.dadaia/dist/ | wc -l)
/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia export --list --exclude-mnt
COUNT_AFTER=$(ls /home/ubuntu/workspace/.dadaia/dist/ | wc -l)
[ "$COUNT_BEFORE" = "$COUNT_AFTER" ] && echo "OK: --list não cria arquivo" || echo "FAIL"

# 7. Export com mnt/ (se mnt/ existir)
if [ -d /home/ubuntu/workspace/mnt ]; then
    /home/ubuntu/workspace/.dadaia/.venv/bin/dadaia export
    ARCHIVE_MNT=$(ls -t /home/ubuntu/workspace/.dadaia/dist/workspace-*.tar.gz | head -1)
    tar tzf "$ARCHIVE_MNT" | grep -E "\.npm|\.cache|linuxbrew"
    # Deve retornar vazio — caches excluídos
fi
```

---

## Critérios de Aceite Finais

| Critério | Comando de verificação |
|---|---|
| FR1: arquivo em dist/ com timestamp | `ls .dadaia/dist/workspace-*.tar.gz` |
| FR2: states/ incluídos | `tar tzf <arquivo> \| grep states/` |
| FR9: .venv e repos/ excluídos | `tar tzf <arquivo> \| grep -E "\.venv\|/repos/"` → vazio |
| FR10: caches mnt/ excluídos | `tar tzf <arquivo> \| grep -E "\.npm\|\.cache\|linuxbrew"` → vazio |
| FR12: manifest presente e válido | `tar xzf <arquivo> -O export-manifest.json \| python3 -m json.tool` |
| FR13: --list sem criar arquivo | contagem de arquivos antes/depois idêntica |
| FR17: dist/ auto-criado | remover dist/ → export → dist/ recriado |
| NFR4: sem *.env | `tar tzf <arquivo> \| grep "\.env$"` → vazio |
