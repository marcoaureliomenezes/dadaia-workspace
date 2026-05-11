# 03. Operacao Segura e Produtiva

## Produtividade sem controle piora o resultado

Claude Code pode editar arquivos, rodar comandos, observar logs, consultar a web e delegar partes do trabalho.

Isso e poderoso. E exatamente por isso precisa de disciplina.

## O que a documentacao de tools deixa claro

### `Bash`

Comandos shell rodam em processos separados. O diretorio de trabalho pode persistir na sessao principal quando o `cd` continua dentro do projeto, mas variaveis de ambiente exportadas em um comando nao persistem automaticamente para o proximo.

Consequencia pratica: nao assuma que um `export` feito agora ainda vai existir depois.

### `LSP`

Quando configurado, o `LSP` devolve inteligencia semantica e erros depois de edicoes. Isso reduz dependencia de builds manuais para checagens basicas.

### `Monitor`

Permite vigiar logs, jobs e scripts longos em background sem congelar a conversa principal.

### `WebFetch`

Ajuda a trazer contexto externo verificavel, em vez de depender de memoria difusa do modelo.

## Heuristicas de uso maduro

### Entre em plan mode quando houver arquitetura, ambiguidade ou impacto cruzado

Se a tarefa cruza varios arquivos, contratos ou repos, `plan mode` quase sempre vale o custo.

### Peca leitura antes de edicao

Prompts melhores costumam pedir explicitamente:

- leitura da spec;
- leitura da arquitetura;
- leitura de arquivos afetados;
- depois implementacao minima.

### Valide logo apos editar

Depois da mudanca, peca verificacao objetiva: testes, lint, typecheck, diff review ou leitura semantica.

### Use permissoes como camada de seguranca

O menu `/permissions` existe para controlar o atrito sem abrir mao do controle. Se a sessao fizer sempre o mesmo conjunto seguro de leituras, permita isso. Se houver risco, mantenha `ask` ou `deny`.

## Anti-padroes comuns

1. Pedir uma grande implementacao sem framing nenhum.
2. Confiar na resposta final sem olhar diff ou validacao.
3. Colocar instrucoes importantes so no chat, em vez de persistir onde faz sentido.
4. Deixar o contexto inflar sem usar `/compact` quando necessario.
5. Tratar toda friccao de permissao como problema, quando parte dela e protecao util.

## Regra final

Claude Code entrega melhor quando voce trata a sessao como um ambiente de engenharia assistida, nao como uma caixa magica de geracao de respostas.