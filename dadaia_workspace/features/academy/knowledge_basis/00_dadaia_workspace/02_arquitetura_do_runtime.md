# 02. Arquitetura do Runtime

## Duas camadas que nao devem ser confundidas

O primeiro erro comum e misturar:

- o repo da biblioteca `dadaia-workspace/`; e
- o runtime do usuario em `<workspace-root>/`.

O repo da biblioteca guarda codigo, specs e o source of truth versionado dos assets do produto.

O runtime do usuario guarda a execucao viva do workspace.

## O papel de `.dadaia/`

`.dadaia/` e a raiz operacional do workspace. Pense nela como o sistema nervoso local do ambiente.

### Subareas principais

#### `.dadaia/.venv/`

Ambiente Python isolado do workspace. Tudo que for automacao Python do workspace deve preferir esta venv.

#### `.dadaia/data/`

Estado duravel do workspace, incluindo o banco local.

#### `.dadaia/contexts/`

Materializacao gerenciada dos `Spec Context Projects`.

#### `.dadaia/tmp/python/` e `.dadaia/tmp/json/`

Area efemera. Serve para scripts transitorios e saidas estruturadas temporarias.

#### `.dadaia/academy/`

Area duravel de aprendizagem. Aqui vivem o material base da Academy e os cursos vivos que futuramente poderao ser gerados pelo slash command `/dadaia-academy`.

## O papel de `.claude/`

`.claude/` nao e o lugar do runtime do produto. E o lugar do ambiente de agentes instalado no workspace do usuario.

Aqui entram, por exemplo:

- `rules/`
- `skills/`
- `commands/`

Esses arquivos moldam como o agente se comporta. Eles nao substituem `.dadaia/`, que continua sendo o runtime duravel do workspace.

## Onde entram as specs

As `specs/` do projeto ativo nao pertencem ao produto em abstrato. Elas pertencem ao contexto de trabalho ou ao repositorio principal associado ao contexto.

Por isso, o comando canonico para descoberta do foco atual e:

```bash
dadaia context show --json
```

O objetivo desse contrato e evitar que agentes tentem adivinhar o projeto, o repo ou o `specs_dir` correto.

## O papel da Academy nessa arquitetura

A Academy ocupa um espaco especifico:

- nao e efemera como `.tmp/`;
- nao e apenas comportamento de agente como `.claude/`;
- nao e uma spec de feature de um projeto de negocio;
- e um material operacional de capacitacao dentro do runtime.

Essa decisao e importante porque o aprendizado vira parte do sistema, nao um apendice externo.

## Heuristica rapida para nao se perder

Use esta tabela mental:

| Area | Pergunta que responde |
|---|---|
| `.dadaia/` | Onde o runtime e o estado do workspace vivem? |
| `.claude/` | Como os agentes se comportam nesse workspace? |
| `specs/` | Qual e a intencao e o contrato daquilo que estou construindo? |
| `.dadaia/academy/` | Como o usuario aprende a operar esse ambiente? |

Se voce mantiver essa separacao, ja evita uma grande classe de erros conceituais.