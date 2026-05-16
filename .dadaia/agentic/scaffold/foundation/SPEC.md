# Spec: Foundation — Arquitetura e Qualidade de Software

> **Status:** Em revisão (Draft v1.0)
> **Versão:** 1.0
> **Referências:** `specs/constitution.md`

---

## Contexto

Esta spec define a arquitetura de implementação do projeto. Ela existe para prevenir slope code causado por inconsistências estruturais entre specs e por camadas paralelas criadas para acomodar ambiguidades.

---

## Requisitos de Arquitetura

### RF-ARCH-001: Estrutura de camadas

<!-- Defina as camadas e suas dependências. Exemplo:

```
CLI  →  Features  →  Core  ←  Infrastructure
           \                  /
            └── container ───┘
```

- `cli/` depende de `features/` e `core/`
- `features/` depende apenas de `core/`
- `infrastructure/` implementa Protocols de `core/`
- `core/` não depende de nenhuma outra camada
-->

### RF-ARCH-002: Estrutura oficial do pacote

<!-- Descreva a estrutura canônica de arquivos do pacote aqui. -->

### RF-ARCH-003: Protocol-first

Every infrastructure dependency used by a feature shall first be expressed as a `Protocol` in `core/protocols/`.

---

## Guardrails Anti-Slope Code

### RF-SLOPE-001: Sem wrappers vazios

The implementation shall not introduce classes or functions that only delegate to another class or function with no additional policy.

### RF-SLOPE-002: Novos módulos exigem justificativa real

New modules are justified only by a new Protocol, a new infrastructure implementation, a new feature service, or a new CLI command module.

### RF-SLOPE-003: Sem reabrir contratos no código

If the implementation encounters a missing or conflicting behavior contract, it shall stop and update the specs instead of inventing behavior in code.

---

## Requisitos de Qualidade

### RF-QA-001: Pirâmide de testes

The implementation shall follow a testing pyramid with `unit/`, `integration/`, and `e2e/` tests.

### RF-QA-002: Fakes para features

Unit tests for feature services shall use fake implementations of Protocols rather than mocks.

### RF-QA-003: Type hints completos

All public functions and methods shall pass the project's type checker in strict mode.
