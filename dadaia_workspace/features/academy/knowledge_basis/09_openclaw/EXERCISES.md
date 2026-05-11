# Exercicios e Checkpoints - Sessao 9 (OpenClaw)

## Exercicio 1 - Onboarding automatizado seguro

Objetivo: validar fluxo non-interactive minimo.

Passos:

1. Execute onboarding non-interactive com parametros explicitos.
2. Gere saida JSON de resumo.
3. Rode health e status profundo.

Criterio de validacao:

- onboarding conclui sem prompt interativo;
- `openclaw status --deep` retorna estado consistente;
- voce sabe onde ficou o `openclaw.json`.

## Exercicio 2 - Separacao de agentes

Objetivo: criar isolamento por agente/workspace.

Passos:

1. Crie agente `work` com workspace proprio.
2. Adicione binding `telegram:ops`.
3. Liste bindings em JSON.

Criterio de validacao:

- `agents list --bindings` mostra roteamento esperado;
- voce consegue explicar qual trafego cai em cada agente.

## Exercicio 3 - Diagnostico de modelos

Objetivo: validar auth/modelo por probe.

Passos:

1. Rode `openclaw models status --probe`.
2. Liste auth profiles do provider ativo.
3. Ajuste modelo default com `models set`.

Criterio de validacao:

- status mostra provider e modelo resolvidos;
- probe nao retorna erro de credencial.

## Exercicio 4 - Hooks e memoria

Objetivo: praticar automacao orientada a evento e memoria.

Passos:

1. Habilite `session-memory`.
2. Rode `memory status --deep`.
3. Faça uma busca de memoria e um preview de promote.

Criterio de validacao:

- hook aparece como enabled/ready;
- memoria indexada responde consultas.

## Exercicio 5 - Message CLI multi-canal

Objetivo: enviar uma mensagem controlada com parametros explicitos.

Passos:

1. Execute `message send` em um canal configurado.
2. Use target correto para esse canal.
3. Repita em dry-run quando aplicavel.

Criterio de validacao:

- envio funciona com canal/target corretos;
- voce sabe diagnosticar erro de target format.

## Checkpoint final

Voce concluiu o modulo se consegue:

- preparar ambiente e onboarding com seguranca;
- separar agentes e bindings com clareza;
- auditar modelo/auth/sessao pelo CLI;
- operar hooks/memoria/message sem abrir risco desnecessario.
