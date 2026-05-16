# Plan: Feature — Workspace Import

> **Status:** Aprovado
> **Referência:** [SPEC.md](./SPEC.md)

---

## Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Leitura do manifesto | Extrair apenas `export-manifest.json` via `tarfile` antes de extrair tudo | Phase 1 pode abortar sem side effects |
| Extração completa | `tarfile.extractall()` com filtro de membros | stdlib; sem dependências |
| Patch de paths | String replace de `<old-root>` por `<new-root>` em `specs_dir` | Os únicos campos com paths absolutos nos JSONs de estado |
| Bootstrap via subprocess | `subprocess.run(["dadaia", "init"])` no workspace root | Reutiliza exatamente o comportamento de `dadaia init`; evita duplicar lógica (RF-SLOPE-006) |
| Activate/promote via subprocess | `subprocess.run(["dadaia", "context", "activate", name])` etc. | Mesma razão — CLI como boundary |
| Workspace root default | `Path.cwd()` | Operador faz `cd <destino>` antes de importar — zero configuração |
| `--skip-mnt` filtro | Filtro de membros por prefixo antes de `extractall` | Não cria diretório `mnt/` desnecessário em máquina local |
| `*.env` protection | Filtro de membros por sufixo — skip + warning | Defesa em profundidade; export já exclui, mas import também garante |
| Idempotência | `dadaia init` é idempotente; `activate` pula clone se repo existe; patch de JSON é determinístico | Executar duas vezes é seguro |

---

## Sequência de Implementação

```
T01             → core/models/import_.py
T02             → features/import_/service.py: validate()
T03             → features/import_/service.py: extract()
T04             → features/import_/service.py: patch_state()
T05             → features/import_/service.py: bootstrap()
T06             → features/import_/service.py: restore_contexts()
T07             → features/import_/service.py: run() orquestrando T02–T06
T08             → cli/commands/import_.py
T09             → registrar no container.py e cli/main.py
T10             → teste e2e
```

---

## Arquitetura de Implementação

```
dadaia_workspace/
├── core/
│   └── models/
│       └── import_.py          ← T01: ImportOptions, ImportResult
├── features/
│   └── import_/
│       ├── __init__.py
│       └── service.py          ← T02–T07: ImportService
└── cli/
    └── commands/
        └── import_.py          ← T08: typer command
```

---

## ImportService — Design Interno

```python
class ImportService:
    def __init__(self, workspace_root: Path): ...

    def run(self, options: ImportOptions) -> ImportResult:
        manifest = self.validate(options.archive)
        if options.dry_run:
            self._print_dry_run(manifest, options)
            return ImportResult(...)

        self.extract(options.archive, options.workspace_root, options.skip_mnt)
        self.patch_state(
            workspace_root=options.workspace_root,
            old_root=Path(manifest.workspace_root),
        )
        self.bootstrap(options.workspace_root)
        errors = self.restore_contexts(manifest, options.skip_activate)
        return ImportResult(
            workspace_root=options.workspace_root,
            contexts_restored=[c["name"] for c in manifest.contexts if c["state"] == "ativo"],
            errors=errors,
        )

    def validate(self, archive: Path) -> ImportManifest:
        # Abre tarball, extrai export-manifest.json como bytes, parse JSON, valida campos

    def extract(self, archive: Path, dest: Path, skip_mnt: bool) -> None:
        # Filtra membros: skip mnt/ se skip_mnt; skip *.env (warn); extractall

    def patch_state(self, workspace_root: Path, old_root: Path) -> None:
        # Lê spec_contexts.json; reescreve specs_dir; reseta state/is_primary/activated_at
        # Deleta primary_context.json se existir

    def bootstrap(self, workspace_root: Path) -> None:
        # subprocess.run(["dadaia", "init"], cwd=workspace_root, check=True)

    def restore_contexts(self, manifest: ImportManifest, skip: bool) -> list[str]:
        # Para cada context ativo no manifesto: dadaia context activate <name>
        # Depois: dadaia context promote <primary>
        # Retorna lista de erros (não levanta exceção — NFR4)
```

---

## Patch de Paths — Detalhe

O único campo com path absoluto nos JSONs de estado é `specs_dir` em cada contexto dentro de `spec_contexts.json`.

```python
# Antes do patch (workspace_root do VPS)
"specs_dir": "/home/ubuntu/workspace/repos/dadaia-workspace/specs"

# Após o patch (workspace_root local)
"specs_dir": "/home/marco/workspace/repos/dadaia-workspace/specs"
```

O `old_root` vem de `export-manifest.json["workspace_root"]`.
O `new_root` é o workspace root de destino resolvido antes da extração.

---

## Filtro de Membros do Tarball

```python
def _member_filter(member: tarfile.TarInfo, skip_mnt: bool) -> tarfile.TarInfo | None:
    if member.name.startswith("mnt/") and skip_mnt:
        return None
    if member.name.endswith(".env"):
        typer.echo(f"WARNING: skipping .env file in archive: {member.name}", err=True)
        return None
    return member
```

---

## Risks e Mitigações

| Risco | Mitigação |
|---|---|
| `dadaia context activate` falha por sem acesso git no repo | FR17: captura exceção, registra erro, continua com demais |
| Workspace root de destino já tem conteúdo | `dadaia init` é idempotente; `extractall` sobrescreve arquivos (exceto `.env`); patch é determinístico |
| `old_root` e `new_root` iguais (import no mesmo servidor) | Patch é no-op; restante funciona normalmente |
| `export-manifest.json` ausente no artefato (arquivo não gerado por dadaia export) | Phase 1 aborta com erro claro antes de qualquer extração |
| Repo já clonado em `repos/<slug>/` antes do import | `dadaia context activate` detecta repo existente e pula clone |
