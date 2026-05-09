# Spec: Feature — dadaia-academy

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`, `specs/foundation/SPEC.md`

---

## Contexto

A dadaia-academy é a feature de aprendizagem do dadaia-workspace. Ela organiza cursos de estudo AI-native dentro do runtime do usuário, usando um catálogo de módulos versionados no pacote (`knowledge_basis`) como base e o agente Claude como motor de personalização e tutoria.

### Divisão de responsabilidades

| Componente | Responsabilidade |
|---|---|
| `dadaia academy` CLI | CRUD de cursos (criar, listar, deletar, atualizar) — Python puro, sem LLM |
| `/dadaia-academy` slash command | O agente Claude lê o conteúdo do curso e personaliza/tutora com base no prompt do usuário |
| `knowledge_basis/` | Fonte canônica de módulos — versionada dentro do pacote Python, não copiada para o workspace |
| `.dadaia/academy/<slug>/` | Cópia de trabalho do curso no workspace do usuário |
| `.dadaia/states/academy.json` | Estado persistido de todos os cursos criados |

### Knowledge Basis (catálogo de módulos)

| Número | Nome do módulo |
|---|---|
| 1 | `01_o_que_e_o_dadaia_workspace` |
| 2 | `02_claude_code_quick_start` |
| 3 | `03_open_code_quick_start` |
| 4 | `04_sdd_quick_start` |
| 5 | `05_agents_e_multi_agent_orchestration_quick_start` |
| 6 | `06_specify_e_implementacao_por_spec` |

Cada módulo contém: `README.md`, `EXAMPLE.md`, `EXERCISES.md`, `REFERENCES.md` + 3 arquivos de conteúdo numerados.

---

## Glossário

| Termo | Definição |
|---|---|
| **Course** | Cópia de trabalho de um módulo do knowledge_basis registrada em `academy.json` |
| **slug** | Identificador único do curso no workspace; usado como nome de pasta em `.dadaia/academy/` |
| **knowledge_basis** | Catálogo de módulos versionado em `dadaia_workspace/features/academy/knowledge_basis/` |
| **module_number** | Número do módulo (1–6); identifica qual pasta do knowledge_basis copiar |
| **academy.json** | Arquivo JSON em `.dadaia/states/`; fonte da verdade de todos os cursos |
| **curso ativo** | Qualquer curso presente em `academy.json` com sua pasta em `.dadaia/academy/<slug>/` |

---

## Usuários e Goals

### US-001: Listar cursos disponíveis

**Critérios de Aceite:**
- Dado que existem cursos em `academy.json`, quando executo `dadaia academy list`, então o sistema exibe tabela com `slug`, `name` e `module_name`.
- Dado que `academy.json` está vazio, quando executo `dadaia academy list`, então o sistema informa que não há cursos e sugere `dadaia academy create`.

### US-002: Criar um curso a partir do knowledge basis

**Critérios de Aceite:**
- Dado um slug único e módulo válido (1–6), quando executo `dadaia academy create <slug> --module <n>`, então o sistema copia o diretório do módulo para `.dadaia/academy/<slug>/`, registra o curso em `academy.json` e confirma com o `course_dir` resultante.
- Dado um slug já existente em `academy.json`, quando executo `create`, então o sistema rejeita com erro claro.
- Dado um número de módulo inválido (fora de 1–6), quando executo `create`, então o sistema rejeita e lista os módulos disponíveis.
- Dado `--name` não fornecido, quando executo `create`, então o sistema usa o `module_name` como nome padrão.

### US-003: Deletar um curso

**Critérios de Aceite:**
- Dado um slug existente, quando executo `dadaia academy delete <slug>`, então o sistema remove `.dadaia/academy/<slug>/` do disco e a entrada de `academy.json`.
- Dado um slug inexistente, quando executo `delete`, então o sistema retorna erro informativo.
- Dado que `.dadaia/academy/<slug>/` não existe mas a entrada está no JSON (estado inconsistente), quando executo `delete`, então o sistema remove a entrada do JSON e emite aviso.

### US-004: Atualizar um curso com outro módulo

**Critérios de Aceite:**
- Dado um slug existente e módulo válido, quando executo `dadaia academy update <slug> --module <n>`, então o sistema substitui o conteúdo de `.dadaia/academy/<slug>/` pelo módulo escolhido e atualiza `academy.json`.
- Dado um slug inexistente, quando executo `update`, então o sistema retorna erro informativo orientando a usar `create`.
- Dado um número de módulo inválido, quando executo `update`, então o sistema rejeita e lista os módulos disponíveis.

### US-005: Usar um curso com o agente Claude

**Critérios de Aceite:**
- Dado um curso existente, quando o operador invoca `/dadaia-academy`, então o agente lista os cursos via `dadaia academy list`, lê os arquivos de `.dadaia/academy/<slug>/` e responde às perguntas e personalizações do usuário.
- O agente não executa `dadaia academy create`, `delete` nem `update` diretamente — orienta o usuário a usar a CLI quando necessário.
- O agente usa os arquivos do curso como contexto primário de aprendizagem, nunca o knowledge_basis do pacote diretamente.

---

## Requisitos Funcionais

### CLI `dadaia academy`

- FR-001: The system shall provide a `dadaia academy` command group with subcommands: `list`, `create`, `delete`, and `update`.
- FR-002: `dadaia academy list` shall display a table with `slug`, `name`, and `module_name` for all courses in `academy.json`.
- FR-003: If `academy.json` is empty, `list` shall state that no courses exist and suggest `dadaia academy create`.
- FR-004: `dadaia academy create <slug> --module <n> [--name <name>]` shall copy the knowledge_basis module directory to `.dadaia/academy/<slug>/`, register the course in `academy.json`, and display the resulting `course_dir`.
- FR-005: `create` shall reject if `slug` already exists in `academy.json`.
- FR-006: `create` shall reject if `module_number` is not in range 1–6, listing available modules.
- FR-007: If `--name` is not provided, `create` shall use the module directory name as the course name.
- FR-008: `dadaia academy delete <slug>` shall remove `.dadaia/academy/<slug>/` from disk and the course entry from `academy.json`.
- FR-009: `delete` shall return an informative error if `slug` does not exist in `academy.json`.
- FR-010: If `.dadaia/academy/<slug>/` is absent but the JSON entry exists (inconsistent state), `delete` shall remove the JSON entry and emit a warning.
- FR-011: `dadaia academy update <slug> --module <n>` shall replace `.dadaia/academy/<slug>/` with the selected knowledge_basis module and update the corresponding `academy.json` entry.
- FR-012: `update` shall return an informative error if `slug` does not exist, suggesting `create`.
- FR-013: `update` shall reject if `module_number` is not in range 1–6, listing available modules.

### Knowledge Basis

- FR-014: The knowledge basis shall live exclusively in `dadaia_workspace/features/academy/knowledge_basis/` inside the installed Python package. It is never copied to the user's workspace.
- FR-015: The CLI shall resolve the knowledge_basis path via `importlib.resources` or `Path(__file__)` relative to the installed package, not from an env var or user-configurable path.
- FR-016: `dadaia academy modules` shall list available modules by reading the `knowledge_basis/` directory dynamically via `importlib.resources`. Output shall display module number and folder name only — no absolute paths.

### Persistência JSON

- FR-017: All writes to `academy.json` shall be atomic: write to `.tmp` file then `os.replace()`.
- FR-018: `academy.json` shall include a `version` field for future schema evolution.
- FR-019: `dadaia init` shall create `.dadaia/academy/` directory and an empty `academy.json` (`{"version": "1", "courses": []}`) if they do not exist.

### Slash command `/dadaia-academy`

- FR-020: The `/dadaia-academy` command shall be an agent command in `.claude/commands/dadaia-academy.md`.
- FR-021: The command shall use `dadaia academy list` as the discovery mechanism for existing courses.
- FR-022: The command shall read course files from `.dadaia/academy/<slug>/` as primary context for tutoring.
- FR-023: The command shall not call `dadaia academy create`, `delete`, or `update` autonomously — it shall present CLI instructions to the user when state changes are needed.
- FR-024: The command source shall live at `dadaia_workspace/public/commands/dadaia-academy.md` and be installed via `dadaia public install`.

### Help e Erros

- FR-025: `dadaia academy --help` shall list exactly: `list`, `create`, `delete`, `update`, and `modules`.
- FR-026: Each subcommand shall have help text documenting required arguments and expected outcomes.
- FR-027: Error messages shall identify the failed capability, the relevant resource, and the next safe recovery action.

---

## Requisitos Não-Funcionais

- NFR-001: [Atomicidade] Toda escrita em `academy.json` é atômica via `os.replace()`. Estado corrompido por escrita parcial é proibido.
- NFR-002: [Segurança] O CLI nunca executa código do knowledge_basis — apenas copia arquivos markdown para o disco do usuário.
- NFR-003: [Portabilidade] O CLI resolve o path do knowledge_basis via o pacote instalado; funciona em qualquer workspace sem variáveis de ambiente adicionais.
- NFR-004: [Idempotência] `dadaia init` pode ser executado múltiplas vezes sem duplicar `academy.json` ou `.dadaia/academy/`.
- NFR-005: [Feedback] Cada subcomando emite confirmação, warning ou erro legível ao usuário.

---

## Modelo de Domínio

### `Course` (Python dataclass)

```python
@dataclass(frozen=True)
class Course:
    slug: str           # unique identifier; folder name in .dadaia/academy/
    name: str           # human-readable name
    module_number: int  # 1–6
    module_name: str    # e.g. "04_sdd_quick_start"
    created_at: str     # ISO 8601
    course_dir: Path    # absolute path: .dadaia/academy/<slug>/
```

### `academy.json` (formato canônico)

```json
{
  "version": "1",
  "courses": [
    {
      "slug": "sdd-intro",
      "name": "SDD Introduction",
      "module_number": 4,
      "module_name": "04_sdd_quick_start",
      "created_at": "2026-05-09T10:00:00Z",
      "course_dir": "/workspace/.dadaia/academy/sdd-intro"
    }
  ]
}
```

---

## Estrutura de Arquivos

### Pacote (fonte canônica)

```
dadaia_workspace/
  features/
    academy/
      __init__.py
      service.py           ← AcademyService
      knowledge_basis/
        01_o_que_e_o_dadaia_workspace/
        02_claude_code_quick_start/
        03_open_code_quick_start/
        04_sdd_quick_start/
        05_agents_e_multi_agent_orchestration_quick_start/
        06_specify_e_implementacao_por_spec/
  public/
    commands/
      dadaia-academy.md    ← slash command source
```

### Runtime workspace

```
<workspace-root>/
  .dadaia/
    academy/
      <slug>/              ← cópia de trabalho do curso
        README.md
        EXAMPLE.md
        EXERCISES.md
        REFERENCES.md
        01_*.md
        02_*.md
        03_*.md
    states/
      academy.json         ← estado persistido dos cursos
  .claude/
    commands/
      dadaia-academy.md    ← slash command instalado
```

---

## Fora de Escopo (v1.0)

- Geração de conteúdo via LLM API pelo CLI Python
- Múltiplos módulos por curso (composite courses)
- Versionamento de cursos (snapshots)
- Progresso do usuário por curso (exercícios completados, notas)
- Compartilhamento de cursos entre workspaces
- `dadaia academy create` interativo (seleção via menu — usa flags explícitas)
