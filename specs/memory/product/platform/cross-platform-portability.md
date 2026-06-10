---
slug: cross-platform-portability
title: cross-platform-portability
category: product
tldr: dadaia-workspace runs on Linux/macOS/Windows via a core/platform.py seam + port/adapter boundary + 3-tier resilience; governance hooks are Python (no bash).
summary: Establishes the cross-platform foundation for dadaia-workspace v0.1.8 — a
  PLATFORM singleton (sole sys.platform call site), typed platform exceptions, 4 protocol
  ports, 9 infrastructure adapters, a Python governance hooks package, and a hard-gated
  3-OS CI matrix. Defines the 3-tier resilience contract (fail-loud for security,
  degrade-with-log for non-security, unsupported-platform at construction). As of 0.1.8
  rc-2 the Windows + macOS CI legs are GREEN and HARD-GATED (no continue-on-error;
  branch-protection required); classifier is POSIX::Linux + MacOS + Microsoft::Windows.
tags:
- platform
- cross-platform
- portability
- windows
- macos
- linux
- hooks
- security
agent_tier: self-pull
token_estimate: 900
last_updated: '2026-06-09'
release_origin: 0.1.8
---

## Propósito

Documenta o modelo de portabilidade de plataforma do dadaia-workspace. A release 0.1.8 fechou
o gap entre o classificador PyPI `OS Independent` e a realidade Linux-only, estabelecendo uma
fronteira port/adapter para todos os domínios OS-sensíveis e um contrato de resiliência em 3
tiers que governa o comportamento em plataformas não-Linux.

A fundação é o seam `core/platform.py`: um singleton `PLATFORM` que é o único site autorizado
para a chamada `sys.platform` em todo o codebase. Nenhum outro arquivo pode ler `sys.platform`
diretamente (exceto durante guards transitionals em function bodies, per ADR-1, cada um anotado
com `# TODO: Replace with PLATFORM.has_<flag>`).

## Fluxo de uso

  1. `container.py` lê `PLATFORM` na startup e seleciona os adapters concretos para cada domínio
     OS-sensível (file lock, telemetry lock, file permissions, process probe, signal handling).
  2. `features/` recebem os adapters injetados via Protocol — zero `import fcntl` / `import signal`
     / `os.chmod` direto em features.
  3. Em um Windows runner: `python -c "import dadaia_workspace"` exits 0. `dadaia --help` exits 0.
  4. Governance hooks (`sdd_gate`, `root_whitelist`, `ctx_inject`, `sdd_post_gate`) rodam como
     `python -m dadaia_workspace.hooks.<name>` — sem bash dependency.
  5. CI importability-smoke job (Windows/macOS) confirma portabilidade a cada push.

## Trigger típico

Quando uma nova plataforma (Windows ou macOS) precisa executar dadaia-workspace, ou quando um
agente precisa verificar que uma funcionalidade OS-sensível degrada corretamente em vez de crashar.

## Diferencial

Sem a plataforma seam, o CLI crashava no Windows antes de executar qualquer comando (`import fcntl`
top-level, `ModuleNotFoundError`). Com a seam, o CLI importa e executa em todos os três OS. O
modelo port/adapter garante que adições futuras de suporte a Windows seguem um padrão claro
sem espalhar `sys.platform` checks pelo codebase.

## Plataforma seam — `core/platform.py`

`Capabilities` frozen dataclass com `detect()` classmethod. Flags:

| Flag | Linux | macOS | Windows |
|------|-------|-------|---------|
| `has_fcntl` | True | True | False |
| `has_proc_fs` | True | False | False |
| `has_posix_chmod` | True | True | False |
| `has_sigterm` | True | True | False |
| `venv_scripts_dir` | `bin` | `bin` | `Scripts` |
| `venv_exe_suffix` | `""` | `""` | `.exe` |
| `tmp_dir` | `Path(tempfile.gettempdir())` | idem | idem |

Singleton `PLATFORM` é acessado via `from dadaia_workspace.core.platform import PLATFORM`.
`detect()` nunca é chamado diretamente — apenas `PLATFORM` é consumido.

## Contrato de resiliência — 3 tiers

**TIER 1 — FAIL LOUD (controles de segurança; silent no-op proibido):**
- `WindowsFilePermissionSetter.restrict_to_owner()` — aplica ACL via `icacls <parent_dir> /inheritance:r /grant:r "<user>:(OI)(CI)F"` ANTES de criar o token file. `icacls` com `shell=False`. Username via `getpass.getuser()`. Falha → `PlatformSecurityError` (nunca warn-and-continue). O panel NÃO inicia com token desprotegido.
- `WindowsFileLock.acquire()` — usa `msvcrt.locking` (stdlib). Se `msvcrt` ausente → `PlatformCapabilityError`. Silent no-op é proibido (cria falsa confiança de serialização).

**TIER 2 — DEGRADE COM INFO LOG (features não-security):**
- `/proc` scan → não-Linux retorna `[]` + INFO "orphan detection disabled". Panel mostra "Scan unavailable on this platform."
- `signal.SIGTERM` no Windows → registra SIGINT only + INFO log.
- `WindowsTelemetryRefreshLock` → always-acquire no-op + INFO log. Seguro porque SQLite WAL mode provê serialização própria de writes. Se WAL for desabilitado, este adapter deve ser revisado.
- `WindowsFilePermissionSetter` em telemetry/lease dirs → Tier 2 (log INFO + continua). Apenas o token do panel auth é Tier 1.
- `os.chmod(db_path, 0o600)` em `features/telemetry/service.py` (1 site) — sem guard `PLATFORM.has_posix_chmod`; silent no-op no Windows. Tier-2 aceitável (telemetry DB não é credencial de segurança). Guard é follow-up de baixa prioridade.
- `script.chmod(0o755)` em `infrastructure/public_assets.py` (1 site) — executability bit; sem guard; silent no-op no Windows. Tier-2 aceitável. Guard é follow-up de baixa prioridade.

**TIER 3 — UNSUPPORTED PLATFORM at construction.** Onde não existe degradação, `PlatformCapabilityError` / `PlatformSecurityError` é raised em `container.py` na construção do serviço, não na hora da chamada.

## Portos e adapters (4 + 9)

**Protocol ports em `core/protocols/`:**
- `file_lock.py` — `WorkspaceLock`, `ContextLock`
- `telemetry_lock.py` — `TelemetryRefreshLock`
- `platform_services.py` — `FilePermissionSetter`
- `shutdown_handler.py` — `ShutdownHandler`

**Adapters em `infrastructure/`:**
- `file_lock_posix.py`, `file_lock_windows.py`
- `telemetry_lock_posix.py`, `telemetry_lock_windows.py`
- `file_permission_posix.py`, `file_permission_windows.py`
- `process_probe_adapter.py` (POSIX; `OsProcessProbe` movido de `core/`)
- `signal_shutdown_posix.py`, `signal_shutdown_windows.py`

## Python governance hooks package

`dadaia_workspace/hooks/` — 6 módulos: `__init__`, `_common`, `sdd_gate`, `root_whitelist`,
`ctx_inject`, `sdd_post_gate`. Cada módulo (exceto `__init__`) tem entrypoint
`if __name__ == '__main__': sys.exit(main())`.

Invariantes de paridade (parity contract com os hooks bash anteriores):
- `sdd_gate.py` delega a `gate_policy.evaluate()` / `gate_policy.classify_path()` — não re-deriva política. `.dadaia/sessions/**` é PROTECTED (fail-closed, SEC-01).
- Context-slug é derivado PATH-first do write target: write sob `repos/B/...` adquire o context de `repos/B`, nunca de `repos/A` (first-ALIVE).
- `ctx_inject.py` preserva o sentinel once-per-session keyed no session id nativo do harness. Sentinel path byte-idêntico ao sentinel bash (`.dadaia/tmp/ctx-inject-fired-<sessionId>`).
- `sdd_post_gate.py` usa `os.replace` atomic renewal + `[A-Za-z0-9_-]` session-id strip.
- Fail-open: qualquer erro não-PROTECTED → ALLOW. PROTECTED é o único fail-closed path.

`runtime_config.py` emite o comando Python para `.claude/settings.json` e `.codex/hooks.json`.
`workspace/service.py` reconhece tanto o caminho `.sh` antigo quanto o novo comando Python para
evitar dupla-registro em workspaces migrados.

OpenCode (`sdd-gate.ts` + `ctx-inject.ts`) chama os Python hooks via subprocess. Resolução do
binário venv: `.dadaia/.venv/bin/python` → `.dadaia/.venv/Scripts/python.exe` → bare `python`.
Propagação de env (`DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT`) via Bun cross-platform `.env()` API
— governado em Windows.

`pre_push_ci.py` NÃO está no pacote. O hook `.sh` pre-push é retido (git-for-Windows ships bash).

## CI matrix 3-OS (graduated — hard-gated)

A matrix 3-OS está **HARD-GATED** desde rc-2 (0.1.8). Todos os `continue-on-error` foram
removidos e o comentário `# GRADUATION-GATE:` foi eliminado. As legs Windows e macOS são
agora required checks na branch-protection (6 contextos adicionados via API).

O classificador PyPI foi ampliado de `POSIX :: Linux` para
`POSIX :: Linux + MacOS + Microsoft :: Windows` (não mais "OS Independent" provisório).

**Jobs com cobertura 3-OS (Linux/macOS/Windows):** `importability-smoke`, `unit-fast`,
`contract-coverage` — todos hard-gated. Qualquer falha em Windows ou macOS bloqueia o merge.

**Linux-only by design (nunca adicionar Win/macOS):** `integration`, `e2e-python`, `e2e-panel`.
Dependem de `/proc` e `ss` — documentado no docstring de `scan.py`.

**Linux-only by design (nunca adicionar Win/macOS):** integration, e2e-python, e2e-panel.
Dependem de `/proc` e `ss` — documentado no docstring de `scan.py`.

## Estado runtime tocado

- `dadaia_workspace/core/platform.py` — singleton `PLATFORM` instanciado em module load
- `dadaia_workspace/hooks/` — pacote Python; executados como subprocess pelo harness
- `.dadaia/scripts/*.sh` — scripts bash legados; ainda presentes mas não mais os hooks registrados
  (exceto `pre-push-ci-gate.sh` que permanece ativo)
- `.claude/settings.json` + `.codex/hooks.json` — entradas de hook com comando Python

## Dependências

- Depende de [[workspace-init]] (cria `.venv`, registra os hooks, provisiona o pacote Python)
- [[context-management]] usa os protocolos `WorkspaceLock`/`ContextLock` para Lock-1/Lock-2
- [[sdd-gate-v3]] descreve o comportamento do gate; a implementação Python é `hooks/sdd_gate.py`
- [[architecture]] descreve o layering invariant e os contratos de layer que enforcement depende
