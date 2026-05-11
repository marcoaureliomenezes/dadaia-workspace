# 01. Modelo Mental e CLI

## Open Code parte de um pressuposto diferente

Open Code nao e apenas um terminal com AI embutida. Ele foi desenhado para ser um ambiente agentic configuravel, com CLI, TUI, server, commands, skills, custom tools e compatibilidade entre ecossistemas.

## O ponto de entrada padrao

Segundo a documentacao oficial, executar `opencode` sem argumentos abre o TUI por padrao.

Esse detalhe importa porque o TUI nao e um modo secundario. Ele e o modo normal de trabalho interativo.

## Tres modos que voce precisa distinguir

### 1. TUI interativo

Bom para investigacao, refino de prompt, leitura de diffs e uso iterativo do agente.

### 2. `opencode run`

Modo nao interativo para scripting, automacao e respostas diretas. Ideal quando voce quer encaixar o agente em um pipeline maior.

### 3. `serve` e `web`

Permitem subir um backend headless e, no caso de `web`, uma interface web. Isso e util para evitar cold start repetido ou para expor o ambiente em uma topologia diferente.

## Outros comandos estruturais do CLI

O CLI tambem expoe superficies relevantes para operacao real:

- `agent` para gerenciar agentes;
- `mcp` para configurar servidores MCP;
- `session` para listar sessoes;
- `stats` para observar uso e custo;
- `export` e `import` para mover sessoes;
- `auth` para credenciais de providers.

## O que isso muda no dia a dia

Open Code fica especialmente forte quando voce quer sair do uso puramente artesanal e passar para um modo mais programavel.

Se a pergunta for "como eu converso com o agente?", varias ferramentas resolvem.

Se a pergunta for "como eu transformo um workflow recorrente em infraestrutura leve de agente?", Open Code fica muito interessante.