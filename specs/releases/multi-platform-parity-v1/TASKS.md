# Tasks: Release — multi-platform-parity-v1

> **Status:** Aprovado
> **Release ID:** multi-platform-parity-v1
> **Owner:** product-engineer (CLOSURE tasks); software-engineer (implementation); qa-engineer (E2E if escalated)
> **SPEC:** `specs/releases/multi-platform-parity-v1/SPEC.md` (Aprovado)
> **PLAN:** `specs/releases/multi-platform-parity-v1/PLAN.md` (Aprovado)
> **Created:** 2026-05-17

Esta release está **enfileirada** (queued): `specs/releases/ACTIVE.md` continua
`release: none / phase: none`. Nenhuma task abaixo pode ser reservada
(`[ ]` → `[-]`) antes do operador editar `ACTIVE.md` para apontar para
`multi-platform-parity-v1` (phase `IMPLEMENTATION`).

---

## Convenções

Protocolo `dadaia-task-manager` (skill homônima) — 3 markers de estado:

| Marker | Estado | Semântica |
|---|---|---|
| `[ ]` | OPEN | Task declarada, ninguém trabalhando. Default no commit inicial. |
| `[-]` | IN PROGRESS | Algum agente reservou. Trabalho ativo. |
| `[x]` | DONE | Implementada, verificada, commitada. |

**Regra invariante:** nunca dois `[-]` simultâneos no mesmo `TASKS.md`. Se
encontrar dois `[-]` ao começar uma sessão, **pare** e reporte ao operador.

**Reservation protocol (Conventional Commit obrigatório):** antes de tocar
qualquer arquivo de produção, mude o marker da task de `[ ]` para `[-]` e
commit isoladamente:

```
chore(tasks): start T-MPP-N.M
```

Ao concluir, mude `[-]` → `[x]` e commit junto com o trabalho final usando
Conventional Commit do tipo correto (`feat`, `fix`, `test`, `chore`, etc.):

```
feat(public-assets): T-PB-3 — emit [not-applicable] doctor status for Codex workflows (T-MPP-1.1 .. 1.4)
```

**ID naming:** `T-MPP-<phase>.<seq>` para tasks de phase; `T-MPP-CC-<seq>` para
cross-cutting / PR-level gates.

`[parallel: yes/no]` flags whether a task may run concurrently with another
`[-]` task in a separate session (disjoint write-sets). Phase order is strict
(ADR-ENG-3): Phase 2 cannot start until Phase 1 is `[x]`; Phase 3 cannot start
until Phase 2 is `[x]`.

Implementation only starts after SPEC + PLAN + TASKS reach `**Status:** Aprovado`
AND `specs/releases/ACTIVE.md` flips to this release.

---

## Mapeamento phases ↔ commits

| Phase | Commit | Tasks (impl) | Tema | Risco |
|-------|--------|--------------|------|-------|
| 1 | C1 | T-MPP-1.1 .. T-MPP-1.4 | T-PB-3 — `[not-applicable]` doctor status + cyan CLI styling | Baixo (additive) |
| 2 | C2 | T-MPP-2.1 .. T-MPP-2.12 | T-PB-1 + T-PB-4 — Codex `[agents.<name>]` blocks + `[skills]` table + `_atomic_write_text()` helper | Médio (novo TOML emit) |
| 3 | C3 | T-MPP-3.1 .. T-MPP-3.5 | T-PB-2 — Remove `_copy_tree(... workflows ...)` + cleanup com `onerror=_log_cleanup_error` | Baixo (deletion) |

Cross-cutting (T-MPP-CC-*) é PR-level: verificado uma vez antes do merge final
da release branch.

---

## Phase 1 — C1 — T-PB-3 `[not-applicable]` doctor status + CLI cyan styling

**Phase 1 commit message (final, includes [x] markers):**

```
feat(public-assets): T-PB-3 — emit [not-applicable] doctor status for Codex workflows (T-MPP-1.1 .. 1.4)
```

---

- [x] **T-MPP-1.1** `[parallel: no]` Extend `_classify_workflows()` with `[not-applicable]` branch for Codex workflows.
  - **Owner:** software-engineer
  - **Effort:** S (~12 LoC added, ~2 removed)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (lines 240–256, function `_classify_workflows()`)
  - **Mudanças:** novo branch que emite `[not-applicable] codex:workflows/<wf>` para todo workflow em Codex (linear OU paralelo). OpenCode mantém `[ok]`/`[partial]`. Sem novos helpers privados nesta phase — classification permanece dentro do mesmo método.
  - **Acceptance ref:** AC-6 (Codex `[not-applicable]`), AC-7 (OpenCode `[partial]` preservado); ADR-ARCH-4 (Pillar 3 scope), ADR-ENG-3 (Phase 1 first).
  - **Sequence:** must precede T-MPP-1.2 (CLI styling consumes the new status string).
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "classify_workflows" -q
    grep -n "not-applicable" dadaia_workspace/infrastructure/public_assets.py | grep -c "codex:workflows"
    # expect: ≥1
    ```

- [x] **T-MPP-1.2** `[parallel: no]` Add CLI styling branch for `[not-applicable]` in `dadaia public doctor` output.
  - **Owner:** software-engineer
  - **Effort:** S (~4 LoC added)
  - **Files MODIFIED:**
    - `dadaia_workspace/cli/commands/public.py` (lines 70–76)
  - **Mudanças:** novo branch `elif item.startswith("[not-applicable]"):` antes do branch `[unsupported]`, com `style="cyan"` (ADR-ENG-1 — reuse `[unsupported]` color).
  - **Acceptance ref:** AC-8 (CLI styling cyan applied); ADR-ENG-1.
  - **Sequence:** depends on T-MPP-1.1 (the status string must exist before styling it).
  - **Verification:**
    ```bash
    grep -n 'not-applicable' dadaia_workspace/cli/commands/public.py
    # expect: 1 match around line 70-76, with style="cyan"
    ```

- [x] **T-MPP-1.3** `[parallel: yes]` Add 4 unit tests for `_classify_workflows()` (parametrize-on-dict, 4 quadrants).
  - **Owner:** software-engineer
  - **Effort:** S (~30 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py` (append 4 parametrize tests; no `tmp_path`)
  - **Mudanças:** 4 testes cobrindo Codex×Linear → `[not-applicable]`, Codex×Parallel → `[not-applicable]`, OpenCode×Linear → `[ok]`, OpenCode×Parallel → `[partial]`. Pattern: parametrize-on-dict per ADR-ENG-4.
  - **Acceptance ref:** AC-6, AC-7; ADR-ENG-4 (test pattern); AC-12 (coverage floor — combined with T-MPP-2.x tests).
  - **Sequence:** can run in parallel with T-MPP-1.2; both depend only on T-MPP-1.1 being `[x]`.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "classify_workflows" -q
    # expect: 4 passed
    ```

- [x] **T-MPP-1.4** `[parallel: no]` Phase 1 close — verify all AC slices, flip markers `[x]`, single Conventional Commit.
  - **Owner:** software-engineer
  - **Effort:** S (verification only — no LoC delta)
  - **Files MODIFIED:**
    - `specs/releases/multi-platform-parity-v1/TASKS.md` (flip T-MPP-1.1 .. 1.4 markers from `[-]` → `[x]`)
  - **Mudanças:** end-to-end smoke per PLAN § Phase 1 verification block; commit message conforme cabeçalho desta phase.
  - **Acceptance ref:** AC-6, AC-7, AC-8.
  - **Sequence:** after T-MPP-1.1, T-MPP-1.2, T-MPP-1.3 all green.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "classify_workflows" -q
    dadaia public doctor 2>&1 | grep -E "^\[(not-applicable|partial|ok)\] (codex|opencode):workflows/"
    # expect: codex lines all [not-applicable]; opencode parallel lines [partial]
    ```

---

## Phase 2 — C2 — T-PB-1 + T-PB-4 + ADR-ENG-6 — Codex `[agents.<name>]` + `[skills]` + atomic writes

**Phase 2 commit message (final, includes [x] markers + DELETEd test + 12 new tests):**

```
feat(public-assets): T-PB-1 + T-PB-4 — render Codex [agents.<name>] blocks + [skills] table + atomic config writes (T-MPP-2.1 .. 2.12)
```

---

- [x] **T-MPP-2.1** `[parallel: no]` Add `_atomic_write_text()` helper (ADR-ENG-6) and refactor `_write_generated()` to use it.
  - **Owner:** software-engineer
  - **Effort:** S (~10 LoC new helper + 3 LoC refactor)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level helper `_atomic_write_text(dst: Path, content: str) -> None` via `dst.with_suffix(dst.suffix + ".tmp")` + `os.replace()`; refactor `_write_generated()` lines 469–475 to call it instead of `dst.write_text(...)`).
  - **Mudanças:** constitution L105 atomic-write pattern aplicado a TODOS os generated files (`.codex/config.toml`, `.claude/settings.json`, `.codex/hooks.json`, `opencode.json`). Pre-condition para Phase 2 byte-identity in `_compare_content()`.
  - **Acceptance ref:** ADR-ENG-6; Defensive coding policy floor #3 (atomic file writes); AC-12 (coverage ≥80%).
  - **Sequence:** must be first task of Phase 2 — T-MPP-2.6 / T-MPP-2.7 / T-MPP-2.12 depend on this helper existing.
  - **Verification:**
    ```bash
    grep -n "_atomic_write_text" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥2 (definition + call from _write_generated)
    ```

- [x] **T-MPP-2.2** `[parallel: yes]` Add `_parse_agent_frontmatter()` helper (regex stdlib-only, no pyyaml).
  - **Owner:** software-engineer
  - **Effort:** M (~25 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level `_parse_agent_frontmatter(text: str) -> dict`; consistent with `_prepare_agent_for_opencode()` at `:62-97`).
  - **Mudanças:** parser de YAML frontmatter usando `re` + string slicing. Whitelist via `_TOML_SAFE_AGENT_FIELDS = {"name", "description", "model", "tools"}` (module constant). Sem pyyaml (constitution L17–28; R3 mitigation).
  - **Acceptance ref:** AC-2 (hyphenated names extracted); AC-12 (coverage); R3 (stdlib-only); ADR-ENG-2.
  - **Sequence:** can run in parallel with T-MPP-2.3 and T-MPP-2.1; consumed by T-MPP-2.4.
  - **Verification:**
    ```bash
    grep -n "_parse_agent_frontmatter\|_TOML_SAFE_AGENT_FIELDS" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥2 (function + whitelist constant)
    ```

- [x] **T-MPP-2.3** `[parallel: yes]` Add `_toml_escape()` helper.
  - **Owner:** software-engineer
  - **Effort:** S (~15 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level `_toml_escape(value: str) -> str`).
  - **Mudanças:** escape `"`, `\`, `\n`, `\\`, and `]` for safe TOML basic-string emission. Foundation para T-PB-1 #7/#8 adversarial tests (T-MPP-2.10).
  - **Acceptance ref:** Defensive coding policy floor #1 (adversarial input testing); R5 (correctness floor); ADR-ENG-2.
  - **Sequence:** parallel with T-MPP-2.1 / T-MPP-2.2; consumed by T-MPP-2.4.
  - **Verification:**
    ```bash
    grep -n "_toml_escape" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1 (function definition)
    ```

- [x] **T-MPP-2.4** `[parallel: no]` Add `_render_agent_toml_block(name, fm)` (assembles `[agents.<name>]` block).
  - **Owner:** software-engineer
  - **Effort:** M (~25 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level `_render_agent_toml_block(name: str, fm: dict) -> str`).
  - **Mudanças:** assembla bloco `[agents.<name>]` — quote keys com hyphens/special chars via `_toml_escape`; emite `description` em `"""..."""` (folded YAML safe); emite `tools` como array literal; drops fields fora do whitelist; drops bloco se `name` ausente.
  - **Acceptance ref:** AC-1, AC-2; ADR-ARCH-2 (sub-tables convention).
  - **Sequence:** depends on T-MPP-2.2 (`_TOML_SAFE_AGENT_FIELDS`) and T-MPP-2.3 (`_toml_escape`).
  - **Verification:**
    ```bash
    grep -n "_render_agent_toml_block" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1 (definition)
    ```

- [ ] **T-MPP-2.5** `[parallel: no]` Add `_render_agents_into_codex_config(agents_dir)`.
  - **Owner:** software-engineer
  - **Effort:** S (~12 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level `_render_agents_into_codex_config(agents_dir: Path) -> str`).
  - **Mudanças:** itera agents em `agents_dir`, chama `_parse_agent_frontmatter` + `_render_agent_toml_block` per agent. Whitelist via `_TOML_SAFE_AGENT_FIELDS`.
  - **Acceptance ref:** AC-1 (10 `[agents.<name>]` blocks rendered).
  - **Sequence:** depends on T-MPP-2.4.
  - **Verification:**
    ```bash
    grep -n "_render_agents_into_codex_config" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1 (definition)
    ```

- [ ] **T-MPP-2.6** `[parallel: no]` Wire T-PB-1 into `_codex_config()` + remove `(None, …, "codex:agents", False)` tuple + add `codex:config.toml` to `_compare_content()`.
  - **Owner:** software-engineer
  - **Effort:** M (~18 LoC modified across 3 sites)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py`:
      - `_codex_config()` (lines 528–546): append output of `_render_agents_into_codex_config(agents_dir)` (10 `[agents.<name>]` blocks).
      - `_runtime_expectations()` (line 432): REMOVE tuple `(None, …, "codex:agents", False)`.
      - `_install_codex()`: ensure it calls `_codex_config()` then `_write_generated(...)` (which now goes through `_atomic_write_text` from T-MPP-2.1).
      - `doctor()` consumer: add `codex:config.toml` to `_compare_content()` set.
  - **Acceptance ref:** AC-1 (10 agents blocks), AC-3 (`[ok] codex:config.toml`); ADR-ARCH-2; ADR-ARCH-3.
  - **Sequence:** depends on T-MPP-2.5 (calls `_render_agents_into_codex_config`) AND T-MPP-2.1 (depends on atomic writer for byte-identity guarantee).
  - **Verification:**
    ```bash
    grep -n "_render_agents_into_codex_config\|codex:agents" dadaia_workspace/infrastructure/public_assets.py
    # expect: _render_agents_into_codex_config ≥1 call; "codex:agents" tuple removed (only the new key codex:config.toml remains)
    ```

- [ ] **T-MPP-2.7** `[parallel: no]` Wire T-PB-4 into `_codex_config()` — `[skills]` table emission.
  - **Owner:** software-engineer
  - **Effort:** S (~6 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (`_codex_config()` — append `[skills]\npaths = [".agents/skills"]` block AFTER the agents blocks).
  - **Mudanças:** ordering `agents → skills` enforced (matches T-MPP-2.11 #2 assertion).
  - **Acceptance ref:** AC-9 (`[skills]` table present with `paths = [".agents/skills"]`).
  - **Sequence:** depends on T-MPP-2.6 (`_codex_config()` already touched in same commit; sequenced to avoid merge conflict in same function).
  - **Verification:**
    ```bash
    grep -n '"\[skills\]"\|paths = \[".agents/skills"\]' dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1
    ```

- [ ] **T-MPP-2.8** `[parallel: yes]` DELETE the test at `tests/unit/test_public_assets.py:69` that locks `[unsupported] codex:agents` (per PLAN R5 — DELETE, NOT adjust).
  - **Owner:** software-engineer
  - **Effort:** S (~5 LoC removed)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py` (DELETE assertion `assert "[unsupported] codex:agents" in output`; remove enclosing test function if it no longer asserts anything meaningful).
  - **Mudanças:** após T-MPP-2.6, `codex:agents` deixa de existir como path em `_runtime_expectations()`. Esse teste fica logicamente impossível. NÃO ajustar para outro status — DELETE (R5 mitigation). Substituído pelos novos 12 tests (T-MPP-2.9 .. 2.12).
  - **Acceptance ref:** R5 (no dead test lock-in); AC-3 (replaced by `codex:config.toml` `[ok]` assertion).
  - **Sequence:** can run in parallel with T-MPP-2.2 / T-MPP-2.3 (test file disjoint from production code). Code review gate verifies `git log -p tests/unit/test_public_assets.py` shows deletion (not adjustment).
  - **Verification:**
    ```bash
    grep -c "\[unsupported\] codex:agents" tests/unit/test_public_assets.py
    # expect: 0
    ```

- [ ] **T-MPP-2.9** `[parallel: yes]` Add 6 unit tests for T-PB-1 (parse + render happy paths, no adversarial yet).
  - **Owner:** software-engineer
  - **Effort:** M (~60 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py`:
      - T-PB-1 #1 — `test_parse_agent_frontmatter_extracts_whitelisted_fields`
      - T-PB-1 #2 — `test_render_agent_toml_block_quotes_hyphenated_name` (`software-engineer` → `[agents."software-engineer"]`)
      - T-PB-1 #3 — `test_render_agent_toml_block_emits_triple_quoted_description` (folded YAML `>` → `"""..."""`)
      - T-PB-1 #4 — `test_render_agent_toml_block_drops_unknown_fields`
      - T-PB-1 #5 — `test_render_agent_toml_block_drops_missing_name`
      - T-PB-1 #6 — `test_render_agent_toml_block_emits_tools_array_literal` (`tools: [Read, Edit]` → `tools = ["Read", "Edit"]`)
  - **Mudanças:** parametrize-on-dict, sem `tmp_path`. Coverage de helpers privados.
  - **Acceptance ref:** AC-1, AC-2; ADR-ENG-4 (test pattern); AC-12 (coverage floor).
  - **Sequence:** depends on T-MPP-2.4 (renders) and T-MPP-2.2 (parser); parallel with T-MPP-2.10, 2.11, 2.12 (disjoint test functions).
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "render_agent_toml_block or parse_agent_frontmatter" -q
    # expect: 6 passed (T-PB-1 #1..#6)
    ```

- [ ] **T-MPP-2.10** `[parallel: yes]` Add 2 unit tests for T-PB-1 adversarial inputs (concern #1).
  - **Owner:** software-engineer
  - **Effort:** M (~30 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py`:
      - T-PB-1 #7 — `test_render_agent_toml_block_escapes_quote_in_name` — input `{"name": "a\"]\nb", "description": "x"}` → assert (a) output passes `tomllib.loads()` round-trip; (b) key contains `\"` and escaped `]`; (c) `\n` does not break the block.
      - T-PB-1 #8 — `test_render_agent_toml_block_escapes_triple_quote_in_description` — input `{"name": "x", "description": "a\"\"\"b"}` → assert (a) output passes `tomllib.loads()` round-trip; (b) description does not break `"""..."""` block; (c) fallback to basic string with `\n` escape if needed.
  - **Mudanças:** floor obrigatório por Defensive coding policy #1 (adversarial input testing) — mesmo input sendo lib-controlled (Q1), escape é o floor.
  - **Acceptance ref:** Defensive coding policy floor #1; R5 (correctness floor).
  - **Sequence:** depends on T-MPP-2.3 (`_toml_escape`) and T-MPP-2.4 (`_render_agent_toml_block`); parallel with T-MPP-2.9, 2.11, 2.12.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "escapes_quote_in_name or escapes_triple_quote_in_description" -q
    # expect: 2 passed
    ```

- [ ] **T-MPP-2.11** `[parallel: yes]` Add 2 unit tests for T-PB-4 (`[skills]` table emit).
  - **Owner:** software-engineer
  - **Effort:** S (~15 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py`:
      - T-PB-4 #1 — `test_skills_table_emits_paths_array_literal` — assert output contains `[skills]\npaths = [".agents/skills"]`.
      - T-PB-4 #2 — `test_skills_table_appears_once_after_agents_blocks` — regex-anchored assert ordering: `agents → skills`.
  - **Mudanças:** parametrize-on-dict (sem `tmp_path`).
  - **Acceptance ref:** AC-9.
  - **Sequence:** depends on T-MPP-2.7 (`[skills]` emit wired into `_codex_config()`); parallel with T-MPP-2.9, 2.10, 2.12.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "skills_table" -q
    # expect: 2 passed
    ```

- [ ] **T-MPP-2.12** `[parallel: yes]` Add 1 integration test for T-PB-1 (manager real on `tmp_path` with 2 fixture agents).
  - **Owner:** software-engineer
  - **Effort:** M (~40 LoC test code)
  - **Files MODIFIED:**
    - `tests/integration/test_public_assets.py` (NEW file, or appended to existing integration test file): integration test exercising full pipeline parse → render → `_atomic_write_text` → diff. Asserts (a) `<dst>.tmp` does NOT exist after success; (b) `dst` contains expected content byte-by-byte; (c) `tomllib.loads(dst.read_text())` does not raise.
  - **Mudanças:** end-to-end byte-identity proves ADR-ENG-6 helper integrates correctly with `_write_generated()`.
  - **Acceptance ref:** AC-1, AC-3, AC-12; ADR-ENG-4 (1 integration per patch); ADR-ENG-6 (atomic write verification).
  - **Sequence:** depends on T-MPP-2.1 (atomic helper) + T-MPP-2.6 (`_codex_config` wiring); parallel with T-MPP-2.9, 2.10, 2.11.
  - **Verification:**
    ```bash
    pytest tests/integration/ -k "public_assets" -q
    # expect: 1 passed (this new integration test)
    ```

---

## Phase 3 — C3 — T-PB-2 — Stop copying workflows to `.codex/workflows/` + safe cleanup

**Phase 3 commit message (final, includes [x] markers):**

```
feat(public-assets): T-PB-2 — stop copying workflows to .codex/workflows/ + safe cleanup with onerror=_log_cleanup_error (T-MPP-3.1 .. 3.5)
```

---

- [ ] **T-MPP-3.1** `[parallel: no]` Remove `_copy_tree(... workflows ...)` from `_install_codex()`.
  - **Owner:** software-engineer
  - **Effort:** S (~2 LoC removed)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (DELETE line `self._copy_tree(agentic_dir / "workflows", codex_dir / "workflows", force, installed)` at `_install_codex():322`).
  - **Mudanças:** após Phase 1 reportar `[not-applicable]`, a cópia é redundante e incorreta (G3 Pillar 3 violation).
  - **Acceptance ref:** AC-4 (`.codex/workflows/` does not exist after install); ADR-ARCH-4 (Codex has no workflow runtime).
  - **Sequence:** first in Phase 3 — T-MPP-3.3 cleanup block goes in same call site.
  - **Verification:**
    ```bash
    grep -n 'codex_dir / "workflows"' dadaia_workspace/infrastructure/public_assets.py
    # expect: only the cleanup rmtree call (from T-MPP-3.3), not _copy_tree
    ```

- [ ] **T-MPP-3.2** `[parallel: yes]` Add `_log_cleanup_error(func, path, exc_info)` module-level helper (concern #2 fix).
  - **Owner:** software-engineer
  - **Effort:** S (~5 LoC)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (new module-level `_log_cleanup_error(func, path, exc_info)` writing `[cleanup-warning] {path}: {exc}\n` to `sys.stderr`; returns without re-raising).
  - **Mudanças:** substitui o anti-pattern `ignore_errors=True` (que silencia `PermissionError`/`OSError`) por warning visível em stderr (Defensive coding policy floor #2).
  - **Acceptance ref:** Defensive coding policy floor #2 (visible failure modes); ADR-ENG-2 (cleanup helper rationale).
  - **Sequence:** can run in parallel with T-MPP-3.1; consumed by T-MPP-3.3.
  - **Verification:**
    ```bash
    grep -n "_log_cleanup_error" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1 (definition)
    ```

- [ ] **T-MPP-3.3** `[parallel: no]` Add cleanup block in `_install_codex()` — log `[removed]` line + `shutil.rmtree(..., onerror=_log_cleanup_error)`.
  - **Owner:** software-engineer
  - **Effort:** S (~9 LoC added)
  - **Files MODIFIED:**
    - `dadaia_workspace/infrastructure/public_assets.py` (`_install_codex()` at former line 322 site): add unconditional cleanup — log line `[removed] {path} (not-applicable: codex has no workflow runtime)` listing files to delete, then `shutil.rmtree(codex_dir / "workflows", onerror=_log_cleanup_error)`. Cleanup is unconditional (does NOT respect `force`) because dead files are always incorrect when asset type is removed.
  - **Acceptance ref:** AC-5 (cleanup removes legacy `.codex/workflows/legacy.workflow.md`); ADR-ENG-2-amended; Defensive coding policy floor #2.
  - **Sequence:** depends on T-MPP-3.1 (line removed) AND T-MPP-3.2 (`_log_cleanup_error` exists).
  - **Verification:**
    ```bash
    grep -n "rmtree.*onerror=_log_cleanup_error" dadaia_workspace/infrastructure/public_assets.py
    # expect: ≥1 (cleanup call wired)
    ```

- [ ] **T-MPP-3.4** `[parallel: yes]` Add 2 base unit tests for T-PB-2 (cleanup removes existing dir + log `[removed]` line emitted).
  - **Owner:** software-engineer
  - **Effort:** M (~20 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py`:
      - (a) `test_install_codex_removes_existing_workflows_dir` — pre-create `.codex/workflows/legacy.workflow.md` in `tmp_path`; assert post-install `.codex/workflows/` does not exist.
      - (b) `test_install_codex_logs_removed_line_listing_files` — assert log/stderr/output contains `[removed]` line listing deleted files BEFORE rmtree.
  - **Mudanças:** usa `tmp_path` para pré-criar fixture.
  - **Acceptance ref:** AC-4, AC-5.
  - **Sequence:** depends on T-MPP-3.3 (cleanup block wired); parallel with T-MPP-3.5.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "workflows_removed or removed_line" -q
    # expect: 2 passed
    ```

- [ ] **T-MPP-3.5** `[parallel: yes]` Add 1 adversarial test for T-PB-2 #3 — permission-error path warns to stderr without raising.
  - **Owner:** software-engineer
  - **Effort:** M (~12 LoC test code)
  - **Files MODIFIED:**
    - `tests/unit/test_public_assets.py` (`test_cleanup_warns_on_permission_error_does_not_raise`): pre-create `.codex/workflows/legacy.workflow.md` in `tmp_path`; `os.chmod(parent_dir, 0o000)`; capture stderr via `capsys`; assert install completes successfully AND stderr contains literal `[cleanup-warning]`.
  - **Mudanças:** floor obrigatório por Defensive coding policy #2 (visible failure modes). Concern #2 verification.
  - **Acceptance ref:** Defensive coding policy floor #2; ADR-ENG-2.
  - **Sequence:** depends on T-MPP-3.2 (`_log_cleanup_error`) AND T-MPP-3.3 (cleanup block); parallel with T-MPP-3.4.
  - **Verification:**
    ```bash
    pytest tests/unit/test_public_assets.py -k "cleanup_warns_on_permission_error" -q
    # expect: 1 passed
    ```

---

## Cross-cutting / PR-level gates

These tasks run at PR-level once Phase 1 + 2 + 3 are all `[x]`. They are
verification-only — no production code changes — and gate the merge into `main`.

- [ ] **T-MPP-CC-1** `[parallel: yes]` AC-10 — verify zero new runtime dependencies.
  - **Owner:** software-engineer
  - **Effort:** S (verification only)
  - **Verification:**
    ```bash
    git diff main -- pyproject.toml
    # expect: empty diff (no new deps)
    ```
  - **Acceptance ref:** AC-10; NFR-4 (stdlib-only).

- [ ] **T-MPP-CC-2** `[parallel: yes]` AC-11 — verify `core/`, `features/`, `container.py` are untouched.
  - **Owner:** software-engineer
  - **Effort:** S (verification only)
  - **Verification:**
    ```bash
    git diff --name-only main..HEAD -- dadaia_workspace/core/ dadaia_workspace/features/ dadaia_workspace/container.py
    # expect: empty
    ```
  - **Acceptance ref:** AC-11; NFR-5; ADR-ARCH-3.

- [ ] **T-MPP-CC-3** `[parallel: yes]` AC-13 + AC-15 — verify `handoff_validator.py` and `agent-comms-v1` archive untouched.
  - **Owner:** software-engineer
  - **Effort:** S (verification only)
  - **Verification:**
    ```bash
    git diff --name-only main..HEAD -- dadaia_workspace/core/protocols/handoff_validator.py specs/_archive/releases/agent-comms-v1/
    # expect: empty
    ```
  - **Acceptance ref:** AC-13, AC-15; NFR-8 (zero overlap with agent-comms-v1).

- [ ] **T-MPP-CC-4** `[parallel: yes]` AC-12 — coverage ≥80% on `infrastructure.public_assets`.
  - **Owner:** software-engineer
  - **Effort:** S (verification only)
  - **Verification:**
    ```bash
    pytest --cov=dadaia_workspace.infrastructure.public_assets --cov-fail-under=80 tests/
    # expect: exit 0
    ```
  - **Acceptance ref:** AC-12; constitution L131.

- [ ] **T-MPP-CC-5** `[parallel: yes]` AC-14 — `dadaia specs doctor` reports 0 errors, 0 warnings.
  - **Owner:** software-engineer
  - **Effort:** S (verification only)
  - **Verification:**
    ```bash
    dadaia specs doctor 2>&1 | tail -5
    # expect: 0 errors, 0 warnings on multi-platform-parity-v1 context (dadaia-workspace)
    ```
  - **Acceptance ref:** AC-14.

- [ ] **T-MPP-CC-6** `[parallel: no]` CLOSURE — author CLOSURE.md + flip ACTIVE.md.
  - **Owner:** product-engineer (CLOSURE — gate v3 allows memory writes only during CLOSURE)
  - **Effort:** M
  - **Files NEW:**
    - `specs/releases/multi-platform-parity-v1/CLOSURE.md` (with 4 mandatory sections: Resumo / Evidências / Drifts / Próximos passos; evidence triples for AC-1..AC-15 — command + expected + observed).
    - `specs/memory/product/multi-platform-parity.html` (NEW — feature card documenting current state of Pillar 3 parity: Codex agents/skills/`[not-applicable]` workflows).
  - **Files MODIFIED:**
    - `specs/memory/product/index.html` (append catalog entry for new memory).
    - `specs/backlog/candidates.md` (append `agents-md-hierarchical-v1` candidate per PLAN § Dependencies / sequence — G4 deferred successor).
    - `specs/releases/ACTIVE.md` (flip to `release: multi-platform-parity-v1 / phase: CLOSURE` while writing; flip to `release: none / phase: none` after archive).
  - **Files MOVED (via `git mv`):**
    - `specs/releases/multi-platform-parity-v1/` → `specs/_archive/releases/multi-platform-parity-v1/`
  - **Mudanças:** CLOSURE.md com Drifts (qualquer divergência do PLAN observada em execução), Validation block com os 15 ACs como evidence triples, Memory updates atomicity per constitution L106 (10 asset types including memory). After signed: `git mv` release dir to `_archive/releases/`.
  - **Acceptance ref:** all 15 ACs verified; release-lifecycle CLOSURE protocol.
  - **Sequence:** depends on T-MPP-CC-1..T-MPP-CC-5 all `[x]` + explicit operator approval.
  - **Verification:**
    ```bash
    cat specs/releases/ACTIVE.md
    # expect: release: none / phase: none (after archive)
    ls specs/_archive/releases/multi-platform-parity-v1/CLOSURE.md
    # expect: file exists with **Status:** Aprovado
    dadaia specs doctor 2>&1 | tail -5
    # expect: 0 errors, 0 warnings
    ```

---

## Definition of Done per task

Cada task individual só pode ser marcada `[x]` quando, simultaneamente:

- ✅ Testes locais green (`pytest tests/ -x` no escopo da task).
- ✅ Slice de AC declarada na task verificada via comando do bloco Verification.
- ✅ Zero novas dependências runtime (`git diff main -- pyproject.toml` empty).
- ✅ Zero edits fora do escopo declarado em Files MODIFIED / Files NEW.
- ✅ `ruff check && mypy --strict` clean nos arquivos tocados.
- ✅ Marker `[-]` → `[x]` no commit final junto com o trabalho (Conventional Commit).

---

## Definition of Done — release-wide

A release `multi-platform-parity-v1` só pode entrar em CLOSURE quando, simultaneamente:

- ✅ CI green (full `pytest tests/ -x` em main branch após merge).
- ✅ `dadaia specs doctor` reporta 0 errors, 0 warnings.
- ✅ 18/18 testes novos passing (4 T-PB-3 + 9 T-PB-1 + 2 T-PB-4 + 3 T-PB-2).
- ✅ Cobertura ≥80% no `dadaia_workspace.infrastructure.public_assets` (AC-12).
- ✅ Todas as 15 ACs (AC-1..AC-15) verificadas com evidence triples no CLOSURE.md.
- ✅ Teste deletado em `tests/unit/test_public_assets.py:69` (R5 — `git log -p` mostra deletion).
- ✅ `find .codex -name "*.tmp"` empty após install (ADR-ENG-6 atomic write smoke).
- ✅ `python3 -c "import tomllib; tomllib.loads(open('.codex/config.toml').read())"` sem exception (adversarial round-trip).
- ✅ `ACTIVE.md` flipped para `release: multi-platform-parity-v1 / phase: CLOSURE` durante CLOSURE; depois para `release: none / phase: none` (ou próxima release) após archive.
- ✅ Release dir movida para `specs/_archive/releases/multi-platform-parity-v1/` via `git mv`.
- ✅ Memory HTML novo `specs/memory/product/multi-platform-parity.html` criado e linkado em `index.html`.

---

## Cross-phase gates (per `dadaia-task-manager`)

Antes de qualquer commit nesta release:

1. `pytest tests/ -x` — green.
2. `ruff format --check && ruff check && mypy --strict` — clean.
3. `dadaia specs doctor` — `0 errors`; warnings must not regress from baseline `0 errors, 0 warnings`.
4. Task marker é `[-]` para a task sendo trabalhada; single `[-]` per `TASKS.md`.

Closing commit pattern (per `dadaia-task-manager`):

```
chore(tasks): start T-MPP-<id>      # before the work (lock observable)
<type>(<scope>): <summary> (T-MPP-<id>) # after the work, includes [x] marker flip
```

---

## Resumo da matriz de paralelismo

```
Phase 1 (serial within phase, ~SD):
  T-MPP-1.1  →  T-MPP-1.2  ∥  T-MPP-1.3   →  T-MPP-1.4 (close)

Phase 2 (mixed):
  T-MPP-2.1  ∥  T-MPP-2.2  ∥  T-MPP-2.3   →  T-MPP-2.4 (dep 2.2, 2.3)
                                              →  T-MPP-2.5 (dep 2.4)
                                                  →  T-MPP-2.6 (dep 2.1, 2.5)
                                                      →  T-MPP-2.7 (dep 2.6, same function)
  T-MPP-2.8 (test delete, ∥ to all above; test file disjoint from production code)
  T-MPP-2.9  ∥  T-MPP-2.10  ∥  T-MPP-2.11  ∥  T-MPP-2.12 (all dep on respective production tasks)

Phase 3 (mixed):
  T-MPP-3.1  ∥  T-MPP-3.2   →  T-MPP-3.3 (dep both)
  T-MPP-3.4  ∥  T-MPP-3.5 (both dep 3.3)

Cross-cutting (PR-level after all Phase 1+2+3 [x]):
  T-MPP-CC-1 ∥ T-MPP-CC-2 ∥ T-MPP-CC-3 ∥ T-MPP-CC-4 ∥ T-MPP-CC-5   →   T-MPP-CC-6 (CLOSURE)
```

Esforço total estimado: **~6 working hours** (LoC delta ~148, 18 tests, helpers
already scoped). Wall-clock potencialmente ~4h com paralelização Phase 2 (3
helpers em paralelo + 4 test functions em paralelo).

Nesta sessão (criação de TASKS) **nenhuma task acima é executada** — todas
começam OPEN (`[ ]`). A reserva (`[ ]` → `[-]`) acontece em sessão futura após
operador flipar `ACTIVE.md` para `multi-platform-parity-v1 / phase: IMPLEMENTATION`.
