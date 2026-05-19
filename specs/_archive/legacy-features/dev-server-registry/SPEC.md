# Spec: Feature — Dev Server Port Registry

> **Status:** Draft
> **Versão:** 0.1
> **Autor:** Marco Menezes
> **Referências:** `specs/constitution.md`, `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, `specs/foundation/SPEC.md`, `specs/SPEC.md`

---

## Contexto

O workspace dadaia-workspace gerencia 8 Spec Context Projects, cada um podendo ter agentes subindo servidores de desenvolvimento (Flask, Vite, Django runserver, Storybook, etc.) em portas arbitrárias durante sessões de trabalho. Sem um registro centralizado, três problemas acumulam:

1. **Conflito de portas:** `redacted-slug` e `redacted-slug-wave6` ambos usam Flask:8000 e Vite:8080 por padrão. O segundo agente falha ao tentar subir o servidor sem saber o motivo.
2. **URL perdida:** O operador não sabe qual porta está servindo qual projeto e precisa pedir o link a cada sessão nova.
3. **Não-determinismo:** Cada nova sessão escolhe uma porta diferente (3000, 3001, 3002...) porque não há memória compartilhada entre sessões de agente.

Esta feature endereça os três problemas via um **registro de portas durável em JSON**, operável por CLI oficial (`dadaia server`) e consultável por agentes via skill universal (`dev-server-registry`). O registro não requer daemon; funciona como leitura/escrita atômica sobre `.dadaia/states/server_registry.json`.

---

## Glossário

| Termo | Definição |
|---|---|
| **PortEntry** | Registro de uma porta reservada: porta, projeto, PID, URL, timestamps e status |
| **ServerRegistry** | O conjunto de todas as `PortEntry`s persistidas em `server_registry.json` |
| **port reservation** | Ato de registrar intenção de uso de uma porta por um projeto antes de subir o servidor |
| **stale entry** | `PortEntry` cujo processo registrado não está mais rodando — detectado por PID (`os.kill`) ou TTL expirado |
| **deterministic port** | Porta derivada de forma determinística do nome do projeto (`hash(name) % range`) para que sessões repetidas tentem sempre a mesma porta base |
| **port range** | Intervalo `[min_port, max_port]` dentro do qual o registry aloca portas livres; default `[3000, 3999]` |
| **conflict** | Tentativa de reservar uma porta já registrada como `active` por outro projeto |
| **TTL** | Tempo de vida de uma `PortEntry`; default 8h. Após expiração, a entrada é elegível para limpeza por `dadaia server clean` |

---

## Escopo

### O que esta feature faz

- Mantém um arquivo JSON durável em `.dadaia/states/server_registry.json` como fonte da verdade de portas em uso.
- Fornece CLI `dadaia server {list, next, register, release, show, clean}` para operação humana e por agente.
- Calcula portas determinísticas por projeto (o mesmo projeto sempre obtém a mesma porta base quando disponível).
- Detecta e limpa entradas obsoletas (stale) via `dadaia server clean`.
- Distribui a skill `dev-server-registry` via `dadaia public install --target all`, ensinando agentes o protocolo de consulta e reserva de portas.
- `dadaia init` cria `server_registry.json` vazio se ausente.

### O que esta feature NÃO faz

- Não sobe nem gerencia processos de servidor — não é um process manager.
- Não requer daemon ou processo de background sempre ativo.
- Não monitora portas em tempo real via polling automático.
- Não faz port forwarding nem proxy.
- Não interage com Docker ou docker-compose diretamente — o agente usa a CLI para registrar após subir o container.
- Não impede fisicamente que um servidor ocupe uma porta fora do registry — é um protocolo de cooperação entre agentes.
- Não valida `project` contra `spec_contexts.json` — campo é string livre para permitir servidores de ferramentas de infra.

---

## User Stories

### US-REG-001: Reservar uma porta antes de subir um servidor

- **Como** agente de IA trabalhando no contexto `redacted-slug`
- **Quero** registrar a porta que vou usar antes de subir o servidor de desenvolvimento
- **Para** que outros agentes saibam que aquela porta está ocupada e não causem conflito

**Critérios de Aceite:**

- Dado que a porta 3000 está livre no registry, quando executo `dadaia server register --port 3000 --project redacted-slug`, então o sistema cria uma `PortEntry` em `server_registry.json` com `status: "active"`, `reserved_at: <ISO 8601 UTC>`, `project: "redacted-slug"`, `port: 3000`.
- Dado que a porta 3000 já tem uma entrada `active` para o projeto `dadaia-agents`, quando executo `dadaia server register --port 3000 --project redacted-slug`, então o sistema rejeita com erro identificando o conflito: porta, projeto ocupante e URL atual.
- Dado que a porta 3000 tem uma entrada stale (PID morto ou TTL expirado), quando executo `dadaia server register --port 3000 --project redacted-slug`, então o sistema registra com sucesso após limpar automaticamente a entrada stale.
- Dado `dadaia server register --port 3000 --project redacted-slug --pid 12345`, então o campo `pid` é persistido para futura detecção de stale via `os.kill(pid, 0)`.
- Dado `dadaia server register --port 3000 --project redacted-slug --description "Vite dev server"`, então o campo `description` é persistido e exibido em `dadaia server list`.
- Dado `dadaia server register --port 3000 --project redacted-slug --ttl 4`, então `expires_at` é `reserved_at + 4h` (não o default de 8h).
- Dado `dadaia server register --port 3000 --project redacted-slug --url http://0.0.0.0:3000`, então o campo `url` é persistido; se `--url` não for fornecido, o default é `http://localhost:<port>`.

---

### US-REG-002: Obter a próxima porta livre de forma determinística

- **Como** agente de IA iniciando uma nova sessão de trabalho no projeto `redacted-slug`
- **Quero** obter uma porta disponível sem precisar escolher manualmente
- **Para** nunca escolher uma porta ocupada e sempre retornar à mesma porta base quando possível

**Critérios de Aceite:**

- Dado que o projeto `redacted-slug` nunca teve porta registrada, quando executo `dadaia server next --project redacted-slug`, então o sistema calcula a porta determinística do projeto via `int.from_bytes(hashlib.md5(b"redacted-slug").digest()[:2], "big") % (max_port - min_port + 1) + min_port` e retorna aquela porta se livre.
- Dado que a porta determinística de `redacted-slug` está ocupada por outro projeto, quando executo `dadaia server next --project redacted-slug`, então o sistema retorna a próxima porta livre no range via incremento linear, com aviso indicando que a porta base estava ocupada.
- Dado que `redacted-slug` já tem uma entrada `active` no registry, quando executo `dadaia server next --project redacted-slug`, então o sistema retorna a porta já registrada — idempotente, sem criar duplicata.
- Dado `dadaia server next --project redacted-slug --json`, então o output é `{"port": 3042, "url": "http://localhost:3042", "is_base_port": true}`.
- Dado `dadaia server next --project redacted-slug --min-port 4000 --max-port 4099`, então a busca ocorre no range `[4000, 4099]`.
- Dado que todas as portas do range estão ocupadas, quando executo `dadaia server next`, então o sistema falha com erro claro sugerindo `dadaia server clean` para liberar entradas stale.

---

### US-REG-003: Consultar o registro completo de portas

- **Como** operador ou agente de IA
- **Quero** ver a lista completa de portas registradas e seus projetos
- **Para** saber quais URLs estão disponíveis sem precisar pedir ao agente que está rodando o servidor

**Critérios de Aceite:**

- Dado que existem entradas no registry, quando executo `dadaia server list`, então o sistema exibe tabela com colunas: `port`, `project`, `url`, `status`, `pid`, `expires_at`.
- Dado que não há entradas no registry, quando executo `dadaia server list`, então o sistema exibe mensagem `No servers registered.` sem erro.
- Dado `dadaia server list --json`, então o sistema retorna JSON array com todos os campos de cada `PortEntry`.
- Dado `dadaia server list --project redacted-slug`, então o sistema filtra e exibe apenas entradas do projeto `redacted-slug`.
- Dado `dadaia server list --status stale`, então o sistema exibe apenas entradas stale (PID morto ou TTL expirado).
- Dado `dadaia server list --status all`, então o sistema exibe entradas active e stale sem filtro.
- Dado que uma entrada tem PID morto, quando executo `dadaia server list`, então o sistema exibe aquela entrada com `status: stale` (detecção em leitura, sem modificar o arquivo).

---

### US-REG-004: Liberar uma porta quando o servidor é encerrado

- **Como** agente de IA encerrando o servidor de desenvolvimento do projeto `redacted-slug`
- **Quero** remover o registro da porta que estava em uso
- **Para** que o slot fique disponível para outros projetos e sessões futuras

**Critérios de Aceite:**

- Dado uma entrada `active` para porta 3002 projeto `redacted-slug`, quando executo `dadaia server release --port 3002`, então o sistema remove a `PortEntry` de `server_registry.json` e exibe confirmação.
- Dado uma entrada `active` para `redacted-slug` na porta 3002 (não `redacted-slug`), quando executo `dadaia server release --port 3002 --project redacted-slug`, então o sistema rejeita com erro claro sem alterar o registry.
- Dado uma porta não registrada, quando executo `dadaia server release --port 9999`, então o sistema retorna aviso (não erro fatal) informando que a porta não estava registrada.
- Dado `dadaia server release --project redacted-slug` sem especificar porta, então o sistema libera todas as entradas do projeto `redacted-slug` e exibe lista de portas liberadas.

---

### US-REG-005: Consultar a URL de um projeto específico

- **Como** operador que esqueceu em qual porta está rodando o projeto `redacted-slug-explorer`
- **Quero** obter a URL do servidor de um projeto diretamente
- **Para** abrir o browser ou passar o link para outro colaborador sem precisar lembrar a porta

**Critérios de Aceite:**

- Dado uma entrada `active` para `redacted-slug-explorer` na porta 3003, quando executo `dadaia server show --project redacted-slug-explorer`, então o sistema exibe a URL `http://localhost:3003` e os demais campos da `PortEntry`.
- Dado `dadaia server show --project redacted-slug-explorer --json`, então o sistema retorna JSON com todos os campos da `PortEntry` para consumo por agentes.
- Dado que o projeto tem mais de uma entrada ativa (ex: backend e frontend), quando executo `dadaia server show --project redacted-slug`, então o sistema exibe todas as entradas do projeto.
- Dado que o projeto não tem servidor registrado, quando executo `dadaia server show --project redacted-slug-explorer`, então o sistema retorna mensagem clara e sugere `dadaia server next --project redacted-slug-explorer` para obter uma porta.

---

### US-REG-006: Limpar entradas obsoletas automaticamente

- **Como** agente de IA iniciando uma sessão de trabalho
- **Quero** que entradas de servidores que não estão mais rodando sejam detectadas e removidas
- **Para** não bloquear portas que estão fisicamente disponíveis

**Critérios de Aceite:**

- Dado uma `PortEntry` com `pid` registrado cujo processo não existe mais (`os.kill(pid, 0)` levanta `ProcessLookupError`), quando executo `dadaia server clean`, então o sistema remove a entrada e exibe lista de entradas limpas.
- Dado uma `PortEntry` sem `pid` mas com `expires_at` no passado, quando executo `dadaia server clean`, então o sistema remove a entrada como stale.
- Dado que não há entradas stale, quando executo `dadaia server clean`, então o sistema exibe `No stale entries found.` sem erro.
- Dado `dadaia server clean --dry-run`, então o sistema lista as entradas que seriam removidas sem modificar `server_registry.json`.
- Dado que `dadaia server register` é executado, então o sistema chama `clean` internamente antes de verificar conflitos, para que entradas stale não bloqueiem novas reservas.

---

### US-REG-007: Skill orienta agentes a usar o registry antes de subir servidores

- **Como** agente de IA (software-engineer, devops-engineer ou qualquer outro) que precisa subir um servidor
- **Quero** uma skill que me ensine o protocolo correto de consulta e reserva de porta
- **Para** nunca subir um servidor sem registrar a porta primeiro, evitando conflitos silenciosos

**Critérios de Aceite:**

- A skill `dev-server-registry` existe em `dadaia_workspace/public/skills/dev-server-registry/SKILL.md`.
- A skill define o protocolo de 4 passos: (1) `dadaia server list` para inspecionar estado atual; (2) `dadaia server next --project <nome>` para obter porta segura; (3) subir o servidor na porta retornada; (4) `dadaia server release --port <porta>` ao encerrar.
- A skill define o invariante: nunca subir servidor sem ter registrado a porta primeiro via `dadaia server register`.
- `dadaia public install --target all` projeta a skill para `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`.
- `dadaia public doctor` retorna `[ok]` para `skills/dev-server-registry` em todos os alvos suportados.

---

### US-REG-008: Dashboard web com índice de servidores ativos

- **Como** operador que mantém múltiplos projetos com servidores rodando
- **Quero** uma URL fixa que possa salvar como favorito no browser
- **Para** ver de uma vez quais servidores estão ativos, com links clicáveis, sem precisar lembrar porta ou pedir ao agente

**Critérios de Aceite:**

- Dado que executo `dadaia server dashboard`, então o sistema inicia um servidor HTTP minimal em `http://localhost:4999` (porta padrão), exibe a URL no terminal e abre o browser automaticamente.
- Dado `dadaia server dashboard --port 5500`, então o servidor inicia na porta 5500.
- Dado `dadaia server dashboard --no-open`, então o servidor inicia mas o browser **não** é aberto automaticamente — útil em ambientes sem display.
- Dado que acesso `http://localhost:4999` no browser, então a página exibe um índice HTML com: nome do projeto, URL clicável, status (`● running` / `○ stale`), campo `description` quando presente.
- Dado que um projeto não tem servidor registrado, então ele **não** aparece no índice — apenas servidores com entradas `active` ou `stale` são listados.
- Dado que a página é recarregada (manual ou automático a cada 5 segundos), então ela reflete o estado atual do `server_registry.json` — sem cache.
- Dado Ctrl+C no terminal, então o servidor HTTP para limpo sem deixar processo órfão.
- O servidor de dashboard **não** cria entrada em `server_registry.json` — ele é o leitor do registry, não um servidor de projeto.
- A implementação usa exclusivamente Python stdlib: `http.server`, `webbrowser`, `json`, `os` — sem nova dependência.

---

## Schema JSON: `server_registry.json`

**Localização:** `<workspace-root>/.dadaia/states/server_registry.json`

```json
{
  "version": "1",
  "range": {
    "min_port": 3000,
    "max_port": 3999
  },
  "entries": [
    {
      "port": 3000,
      "project": "redacted-slug",
      "url": "http://localhost:3000",
      "status": "active",
      "pid": 14832,
      "reserved_at": "2026-05-16T10:00:00Z",
      "expires_at": "2026-05-16T18:00:00Z",
      "description": "Vite dev server"
    }
  ]
}
```

### Campos de `PortEntry`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `port` | `int` | Sim | Número da porta TCP |
| `project` | `str` | Sim | Nome do projeto (string livre; tipicamente o repo slug) |
| `url` | `str` | Não | URL completa; default `http://localhost:<port>` |
| `status` | `"active"` | Sim | Sempre `"active"` em disco; `"stale"` é calculado em runtime na leitura |
| `pid` | `int \| null` | Não | PID do processo servidor; `null` quando não fornecido |
| `reserved_at` | `str` | Sim | ISO 8601 UTC; imutável após criação |
| `expires_at` | `str` | Sim | ISO 8601 UTC; `reserved_at + TTL`; default TTL = 8h |
| `description` | `str \| null` | Não | Texto livre (ex: `"Vite dev server"`, `"Django runserver"`) |

**Nota sobre `status`:** O valor persistido em disco é sempre `"active"`. O valor `"stale"` é computado em runtime durante leitura quando: (a) `pid` está presente e `os.kill(pid, 0)` levanta `ProcessLookupError`; ou (b) `expires_at < now()`. Esse design evita escrita desnecessária — o arquivo só muda em `register`, `release` e `clean`.

---

## Superfície CLI

```
dadaia server list      [--project <nome>] [--status active|stale|all] [--json]
dadaia server next      --project <nome>   [--min-port <n>] [--max-port <n>] [--json]
dadaia server register  --port <n> --project <nome> [--url <url>] [--pid <n>] [--ttl <h>] [--description <txt>]
dadaia server release   --port <n> [--project <nome>]
dadaia server show      --project <nome>   [--json]
dadaia server clean     [--dry-run]
dadaia server dashboard [--port 4999] [--no-open]
```

`dadaia server next` **apenas sugere** a porta — não registra. O agente deve chamar `dadaia server register` explicitamente após subir o servidor. Isso mantém o audit trail claro: a porta só aparece como `active` depois que o servidor está rodando.

---

## Requisitos Funcionais

| ID | Requisito |
|---|---|
| FR-REG-001 | O sistema shall persistir o registry em `.dadaia/states/server_registry.json` com escrita atômica via `os.replace()`. |
| FR-REG-002 | `dadaia init` shall criar `server_registry.json` vazio (`{"version":"1","range":{"min_port":3000,"max_port":3999},"entries":[]}`) se o arquivo não existir, sem destruir arquivo existente. |
| FR-REG-003 | `dadaia server register` shall rejeitar com `PortConflictError` se a porta já está registrada como `active` (após sweep de stale) por outro projeto, com mensagem identificando projeto, porta e URL do conflito. |
| FR-REG-004 | `dadaia server register` shall chamar sweep interno de stale (PID + TTL) antes de verificar conflito. |
| FR-REG-005 | `dadaia server next` shall calcular porta determinística via `int.from_bytes(hashlib.md5(project.encode()).digest()[:2], "big") % (max_port - min_port + 1) + min_port`. |
| FR-REG-006 | `dadaia server next` shall retornar a porta já registrada se o projeto tem entrada `active` (idempotente). |
| FR-REG-007 | `dadaia server next` shall retornar a próxima porta livre no range via incremento linear quando a porta base está ocupada, com aviso ao operador. |
| FR-REG-008 | `dadaia server next` shall falhar com erro orientador quando todas as portas do range estão ocupadas, sugerindo `dadaia server clean`. |
| FR-REG-009 | `dadaia server release` shall remover a entrada sem alterar outras entradas. |
| FR-REG-010 | `dadaia server release` com `--project` errado para a porta especificada shall rejeitar com erro sem alterar o registry. |
| FR-REG-011 | `dadaia server clean` shall detectar stale por: (a) `os.kill(pid, 0)` lança `ProcessLookupError` (quando pid presente) e (b) `expires_at < now()`. |
| FR-REG-012 | `dadaia server clean --dry-run` shall listar entradas stale sem modificar o arquivo. |
| FR-REG-013 | `dadaia server list --json` shall retornar JSON array com todos os campos de `PortEntry` mais o campo `status` calculado em runtime. |
| FR-REG-014 | `dadaia server show` shall emitir sugestão `dadaia server next --project <nome>` quando o projeto não tem entradas registradas. |
| FR-REG-015 | A skill `dev-server-registry` shall existir em `dadaia_workspace/public/skills/dev-server-registry/SKILL.md`. |
| FR-REG-016 | `dadaia public install --target all` shall projetar `skills/dev-server-registry` para `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`. |
| FR-REG-017 | Todos os comandos shall ter `--help` autodocumentado via Typer. |
| FR-REG-018 | `specs/foundation/SPEC.md` RF-ARCH-002 shall ser atualizado para incluir os novos arquivos de implementação e `skills/dev-server-registry`. |
| FR-REG-019 | `specs/SPEC.md` US-001 shall ser atualizado para incluir `server_registry.json` na lista de arquivos criados por `dadaia init`. |
| FR-REG-020 | `dadaia server dashboard` shall iniciar um servidor HTTP em `http://localhost:<port>` (default 4999), abrir o browser via `webbrowser.open()` (exceto com `--no-open`) e bloquear o terminal até Ctrl+C. |
| FR-REG-021 | A página HTML servida pelo dashboard shall: (a) listar todas as entradas do registry com nome do projeto, URL clicável, status e `description`; (b) auto-refrescar a cada 5 segundos via `<meta http-equiv="refresh" content="5">`; (c) ler `server_registry.json` a cada requisição sem cache; (d) exibir mensagem `No servers registered.` quando o registry está vazio. |
| FR-REG-022 | O servidor de dashboard shall **não** criar entrada em `server_registry.json` — ele é leitor do registry, não um projeto registrado. |
| FR-REG-023 | `dadaia server dashboard` shall usar exclusivamente Python stdlib: `http.server`, `webbrowser`, `json`, `os` — sem nova dependência no `pyproject.toml`. |

---

## Requisitos Não-Funcionais

| ID | Requisito |
|---|---|
| NFR-REG-001 | [Disponibilidade] Nenhum daemon requerido. Toda operação é one-shot de leitura/escrita JSON. |
| NFR-REG-002 | [Offline] O registry funciona inteiramente offline. Nenhuma rede é consultada. |
| NFR-REG-003 | [Performance] Todos os comandos `dadaia server *` completam em menos de 500 ms em disco local. |
| NFR-REG-004 | [Atomicidade] Toda escrita em `server_registry.json` usa o padrão `os.replace()` já estabelecido no workspace. |
| NFR-REG-005 | [Dependências] A feature usa apenas stdlib Python: `json`, `os`, `hashlib`, `datetime`. Nenhuma dependência nova no `pyproject.toml`. |
| NFR-REG-006 | [Não-bloqueante] Esta feature não bloqueia nenhuma outra feature em desenvolvimento paralelo. |
| NFR-REG-007 | [Cobertura] `features/server_registry/service.py` deve ter cobertura ≥ 80% via fakes em pytest. |
| NFR-REG-008 | [Qualidade] `ruff format`, `ruff check` e `mypy --strict` passam sem erros novos. |

---

## Arquitetura de Implementação

Seguindo a arquitetura de 4 camadas canônica (RF-ARCH-001):

```
CLI layer:
  dadaia_workspace/cli/commands/server.py
  → Typer app, grupo `dadaia server`, 7 subcomandos (inclui `dashboard`)

Feature layer:
  dadaia_workspace/features/server_registry/
    __init__.py
    service.py           → ServerRegistryService
                           métodos: register(), release(), list_entries(),
                                    next_port(), show_project(), clean()
    dashboard.py         → DashboardHandler (http.server.BaseHTTPRequestHandler)
                           render_html(): lê registry e retorna HTML completo

Core layer:
  dadaia_workspace/core/models/server_registry.py
    → PortEntry (frozen dataclass)
    → ServerRegistry (frozen dataclass: version, range, entries)
    → PortStatus (StrEnum: ACTIVE, STALE)

  dadaia_workspace/core/protocols/server_registry_store.py
    → ServerRegistryStore Protocol

  dadaia_workspace/core/exceptions.py
    → PortConflictError   (NOVA)
    → PortNotRegisteredError  (NOVA)

Infrastructure layer:
  dadaia_workspace/infrastructure/json_server_registry_store.py
    → JsonServerRegistryStore implementando ServerRegistryStore
      (escrita atômica via os.replace, detecção de stale por PID e TTL)

Public asset:
  dadaia_workspace/public/skills/dev-server-registry/
    SKILL.md             → protocolo de 4 passos para agentes

Container:
  dadaia_workspace/container.py
    → + build_server_registry_service()

CLI main:
  dadaia_workspace/cli/main.py
    → + app.add_typer(server.app, name="server")
```

---

## Estratégia de Testes

### Novos fakes em `tests/fakes.py`

```python
class FakeServerRegistryStore:
    """In-memory ServerRegistryStore — keyed by port number."""
    def __init__(self) -> None:
        self._store: dict[int, PortEntry] = {}
    # save, update, get, list_all, delete, count

class FakeProcessProbe:
    """Controllable probe — populate _alive_pids to control liveness."""
    def __init__(self) -> None:
        self._alive_pids: set[int] = set()
    def is_pid_alive(self, pid: int) -> bool: ...
```

`FakeProcessProbe` abstrai `os.kill(pid, 0)` para que nenhum teste precise de processos reais. CI-safe.

### Arquivos de teste

| Arquivo | Tipo | Conteúdo |
|---|---|---|
| `tests/unit/test_server_registry_models.py` | Unit | Domain model puro: criação, round-trip serialização, enum values |
| `tests/unit/test_server_registry_service.py` | Unit | Service com fakes: register, release, next_port, clean, conflict, stale |
| `tests/unit/test_json_server_registry_store.py` | Unit | Infra com `tmp_path`: save, get, delete, atomic write, corrupt JSON |
| `tests/integration/test_cli_server.py` | Integration | CliRunner + workspace real em `tmp_path`: todos os 6 subcomandos |
| `tests/e2e/features/test_server_port_registry.py` | E2E | 7 cenários mapeados 1:1 com US-REG-001 a US-REG-007 |

Nenhum teste usa socket real, `lsof`, `netstat` ou qualquer recurso de rede — toda liveness passa por `FakeProcessProbe`.

---

## Decisões Arquiteturais

### ADR-REG-001: Registry como JSON puro, sem daemon

Um daemon de monitoramento de portas seria mais robusto para detecção em tempo real, mas introduziria complexidade operacional (startup, shutdown, estado de daemon). A abordagem JSON-on-demand alinha com o princípio RF-ARCH-007 ("Estado persistido e sem globais") e funciona offline e sem coordenação de processos.

### ADR-REG-002: Porta determinística via hash MD5 do nome do projeto

Permite que sessões repetidas sempre tentem a mesma porta base sem exigir que o operador memorize números. O MD5 é usado apenas como função hash determinística (não criptográfica) — sem implicações de segurança. Se a porta base estiver ocupada, o fallback linear garante que sempre há uma porta disponível no range.

### ADR-REG-003: `dadaia server next` sugere, não registra

Manter os dois passos (next → register) explícitos garante que a porta só aparece como `active` após o servidor estar de fato rodando. Isso torna o audit trail correto e evita "phantom reservations" de servidores que falharam ao subir.

### ADR-REG-004: `status` calculado em runtime, não persistido como stale

Escrever `"stale"` em disco toda vez que um PID morre causaria escrita desnecessária a cada leitura. Calculando em runtime mantém o arquivo minimal e o comportamento correto. A exceção é `dadaia server clean`, que efetivamente remove as entradas stale do arquivo.

### ADR-REG-005: `project` como string livre

Validar `project` contra `spec_contexts.json` restringiria o uso a projetos registrados como contextos, impossibilitando o registro de servidores de ferramentas de infra (MinIO, Traefik, etc.). String livre é mais composível e o operador mantém controle semântico.

### ADR-REG-006: Skill, não hook PreToolUse automático

Interceptar comandos como `npm run dev` ou `flask run` em `PreToolUse` seria frágil — o parsing de comandos shell é sensível ao contexto. A skill é suficiente: ensina o protocolo ao agente, que já tem contexto semântico para decidir quando aplicar. Um hook `Stop` para auto-sweep pode ser adicionado em v0.2 como melhoria incremental.

---

## Riscos e Mitigações

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| R1 | Agente ignora a skill e sobe servidor sem registrar | Alta | `dadaia server list` no início de sessão torna o problema imediatamente visível; skill em todos os runtimes facilita adoção |
| R2 | PID reutilizado pelo OS para outro processo após encerramento | Baixa | TTL é o mecanismo primário de expiração; PID é verificação adicional, não exclusiva |
| R3 | Race condition: dois agentes registram a mesma porta simultaneamente | Baixa | Escrita atômica via `os.replace()` garante que só um vence; o segundo lê o estado atualizado e detecta conflito |
| R4 | Port range `[3000, 3999]` esgotado em workspaces com muitos servidores | Baixa | Range de 1000 slots é suficiente para 8 projetos; `dadaia server clean` libera slots; `--min-port/--max-port` permite expansão |

---

## Questões Abertas

- Deve `dadaia server next` aceitar `--role backend|frontend|docker` para projetos com múltiplos servidores (ex: Flask + Vite)? V0.1 não incluiu `role` para manter o schema simples — pode ser adicionado em v0.2 se o operador precisar distinguir servidores por tipo dentro do mesmo projeto.

---

## Arquivos a Criar/Modificar

```
dadaia_workspace/
  cli/commands/server.py                          ← NOVO: grupo `dadaia server`
  core/models/server_registry.py                  ← NOVO: PortEntry, ServerRegistry, PortStatus
  core/protocols/server_registry_store.py         ← NOVO: ServerRegistryStore Protocol
  core/exceptions.py                              ← AMEND: +PortConflictError, +PortNotRegisteredError
  features/server_registry/
    __init__.py                                   ← NOVO
    service.py                                    ← NOVO: ServerRegistryService
    dashboard.py                                  ← NOVO: DashboardHandler + render_html()
  infrastructure/json_server_registry_store.py    ← NOVO: JsonServerRegistryStore
  public/skills/dev-server-registry/
    SKILL.md                                      ← NOVO: protocolo para agentes
  container.py                                    ← AMEND: +build_server_registry_service()
  cli/main.py                                     ← AMEND: +app.add_typer(server.app, name="server")

specs/features/dev-server-registry/
  SPEC.md                                         ← NOVO (este documento)
  PLAN.md                                         ← pendente aprovação desta spec
  TASKS.md                                        ← pendente aprovação desta spec

specs/SPEC.md                                     ← AMEND: US-001 +server_registry.json em dadaia init
specs/foundation/SPEC.md                          ← AMEND: RF-ARCH-002 +novos arquivos e skills/dev-server-registry

tests/fakes.py                                    ← AMEND: +FakeServerRegistryStore, +FakeProcessProbe
tests/unit/test_server_registry_models.py         ← NOVO
tests/unit/test_server_registry_service.py        ← NOVO
tests/unit/test_json_server_registry_store.py     ← NOVO
tests/integration/test_cli_server.py              ← NOVO
tests/e2e/features/test_server_port_registry.py   ← NOVO
```

---

## Critérios de Aceite da Spec (DoD para aprovação)

- [ ] `dadaia server register --port 3000 --project redacted-slug` cria entrada em `server_registry.json`
- [ ] `dadaia server register --port 3000 --project outro` com porta ocupada falha com mensagem de conflito
- [ ] `dadaia server next --project redacted-slug --json` retorna JSON `{"port": N, "url": "http://localhost:N", "is_base_port": true|false}`
- [ ] `dadaia server next --project redacted-slug` executado duas vezes retorna a mesma porta quando já registrada (idempotente)
- [ ] `dadaia server list --json` retorna JSON array com todas as entradas e campo `status` calculado
- [ ] `dadaia server release --port 3000` remove a entrada
- [ ] `dadaia server clean` remove entradas com `expires_at` expirado ou PID morto
- [ ] `dadaia server clean --dry-run` não modifica `server_registry.json`
- [ ] `dadaia init` cria `server_registry.json` vazio se ausente
- [ ] `dadaia public install --target all` projeta `skills/dev-server-registry`
- [ ] `dadaia public doctor` retorna `[ok]` para `skills/dev-server-registry`
- [ ] `dadaia server dashboard` inicia HTTP server em `http://localhost:4999` e abre o browser
- [ ] `dadaia server dashboard --no-open` inicia o servidor sem abrir o browser
- [ ] Página do dashboard exibe entradas do registry com nome, URL clicável e status
- [ ] Página do dashboard auto-refresca a cada 5 segundos
- [ ] `dadaia server dashboard` não cria entrada em `server_registry.json`
- [ ] Cobertura ≥ 80% em `features/server_registry/service.py` via pytest com fakes
- [ ] `ruff format`, `ruff check`, `mypy --strict` passam sem erros novos
