# Exemplo Pratico - Montando o Mapa Mental do Seu Workspace

O objetivo deste exemplo nao e usar uma feature exotica. E construir um mapa mental correto do workspace em poucos minutos, porque quase todo erro com agentes nasce de um mapa mental errado do ambiente.

## Cenario

Voce acabou de iniciar ou receber um workspace baseado em `dadaia-workspace` e quer validar se entendeu a estrutura antes de pedir qualquer implementacao a um agente.

## Passo 1: Identifique o runtime do usuario

Confirme quais pastas representam runtime duravel e quais representam comportamento do agente:

```bash
ls -la .dadaia
ls -la .claude
```

O que voce deve esperar conceitualmente:

- `.dadaia/` guarda estado, runtime, contextos, venv e agora a Academy.
- `.claude/` guarda commands, rules e skills instalados para o ambiente de agentes.

## Passo 2: Entenda o que e duravel e o que e efemero

Procure estas areas:

- `.dadaia/data/` para o banco do workspace.
- `.dadaia/contexts/` para contextos materializados.
- `.dadaia/tmp/python/` e `.dadaia/tmp/json/` para artefatos efemeros.
- `.dadaia/academy/` para o material base de aprendizado.

Pergunta de validacao:

Se um agente criar um script de apoio, ele deve ir para `.dadaia/tmp/python/` ou para `.dadaia/academy/`?

Resposta correta:

- script transitorio: `.dadaia/tmp/python/`
- material didatico duravel: `.dadaia/academy/`

## Passo 3: Consulte o contexto atual do produto

Quando a CLI estiver disponivel no seu ambiente, o comando canonico para agentes e ferramentas e:

```bash
dadaia context show --json
```

Esse comando responde perguntas como:

- qual contexto esta ativo;
- onde esta o `specs_dir` relevante;
- qual repo principal foi materializado;
- quais repos secundarios fazem parte do foco atual.

## Passo 4: Leia a Academy como parte do runtime

Agora abra a estrutura da Academy:

```bash
find .dadaia/academy -maxdepth 2 -type f | sort
```

O objetivo aqui e internalizar uma regra:

> aprender o workspace nao e algo separado do runtime; a aprendizagem faz parte do proprio ambiente de operacao.

## O que este exemplo demonstra em profundidade

Este exemplo parece simples, mas ele fixa quatro conceitos que evitam muitos erros:

1. `dadaia-workspace` separa runtime do usuario e repo da biblioteca.
2. `.claude/` e o ambiente de comportamento dos agentes; `.dadaia/` e o ambiente de estado e operacao do workspace.
3. A CLI e a fronteira canonica de automacao; acessos diretos a arquivos internos sao fallback, nao o caminho principal.
4. A Academy e parte do ambiente duravel, nao um conjunto avulso de notas.

## Como reutilizar este padrao

Use este mesmo checklist sempre que:

- iniciar um novo workspace;
- onboardar um novo membro do time;
- preparar um agente para atuar no projeto;
- revisar se um slash command ou skill esta escrevendo no lugar certo.