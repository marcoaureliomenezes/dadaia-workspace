# Exercicios e Checkpoints - Sessao 10 (Hermes Agent)

## Exercicio 1 - Baseline funcional

Objetivo: sair do zero para chat funcional.

Passos:

1. Instale Hermes.
2. Rode `hermes model` e selecione provider/modelo.
3. Inicie `hermes` e execute um prompt verificavel.

Criterio de validacao:

- resposta sem erro de auth;
- modelo certo no banner;
- conversa continua no segundo turno.

## Exercicio 2 - Continuidade de sessao

Objetivo: validar persistencia e retomada.

Passos:

1. finalize uma conversa curta;
2. rode `hermes --continue`;
3. confirme retomada no contexto esperado.

Criterio de validacao:

- mesma sessao retomada sem perder contexto recente.

## Exercicio 3 - Gateway controlado

Objetivo: subir gateway sem abrir risco desnecessario.

Passos:

1. rode `hermes gateway setup`;
2. configure um canal de teste;
3. valide status e health;
4. envie/receba uma mensagem de teste.

Criterio de validacao:

- gateway responde;
- canal processa mensagem;
- voce sabe desfazer e reconfigurar se algo quebrar.

## Exercicio 4 - Recovery toolkit

Objetivo: praticar retorno rapido para estado saudavel.

Passos:

Execute em ordem:

1. `hermes doctor`
2. `hermes model`
3. `hermes setup`
4. `hermes sessions list`
5. `hermes --continue`

Criterio de validacao:

- voce consegue explicar qual comando resolve cada classe de problema.

## Checkpoint final

Voce concluiu o modulo se consegue:

- instalar/configurar sem bloqueio recorrente;
- operar e retomar sessoes;
- subir gateway com criterio de seguranca;
- aplicar playbook de recovery sem improviso.
