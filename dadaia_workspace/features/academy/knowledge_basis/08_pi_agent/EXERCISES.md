# Exercicios e Checkpoints - Sessao 8 (Pi Agent)

## Exercicio 1 - Setup completo em 5 minutos

Objetivo: validar instalacao, autenticacao e primeiro prompt.

Passos:

1. Instale o Pi (curl ou npm).
2. Rode `pi` no diretorio de um projeto.
3. Autentique via `/login` ou API key.
4. Execute um prompt de resumo do repo.

Criterio de validacao:

- Pi inicia sem erro.
- Responde ao prompt.
- Sessao aparece em `/session`.

## Exercicio 2 - Controle de sessao

Objetivo: dominar ciclo de continuidade e ramificacao.

Passos:

1. Crie uma sessao e nomeie com `/name`.
2. Abra uma branch de conversa com `/fork`.
3. Volte e retome com `/resume`.

Criterio de validacao:

- Voce consegue navegar entre sessao original e fork.
- Entende quando usar `/new`, `/fork` e `/clone`.

## Exercicio 3 - Modo read-only

Objetivo: operar uma auditoria sem risco de escrita.

Passos:

```bash
pi --tools read,grep,find,ls -p "Review this repository and list top 5 risks"
```

Criterio de validacao:

- Nenhum arquivo foi alterado.
- Resultado trouxe paths concretos.

## Exercicio 4 - Customizacao minima

Objetivo: carregar somente uma extension local.

Passos:

```bash
pi --no-extensions -e ./my-extension.ts
```

Criterio de validacao:

- Startup mostra somente a extension carregada.
- Voce entende diferenca entre auto-discovery e load explicito.

## Checkpoint final

Voce concluiu o modulo se consegue:

- iniciar e autenticar sem tentativa-e-erro;
- controlar sessao com continuidade e ramificacao;
- operar auditoria em read-only;
- habilitar customizacao sem poluir o runtime.
