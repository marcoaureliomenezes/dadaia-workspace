# 01. Codex Hello World

Consulta oficial: 2026-05-09.

Este guia e o primeiro mapa mental para operar Codex sem se perder em modelo, permissao, rules, skills, commands e agents. A ideia nao e decorar tudo: e saber onde olhar, como iniciar uma sessao segura e como diagnosticar por que o Codex fez ou deixou de fazer algo.

## O que e Codex

Codex e o agente de engenharia da OpenAI para trabalhar em repositorios reais. Ele consegue ler arquivos, propor mudancas, editar codigo, rodar comandos e coordenar subagents quando voce pede explicitamente.

Voce pode usar Codex em algumas superficies:

- **CLI** — terminal local, melhor para trabalho direto no repo.
- **IDE extension** — fluxo dentro do editor.
- **Codex app / cloud** — delegacao de tarefas em ambiente remoto.
- **SDK** — controle programatico de threads Codex em automacoes.

No dia a dia do dadaia Workspace, pense primeiro em **CLI local**: ele ve o filesystem, respeita o sandbox, segue `AGENTS.md` e permite validar tudo com comandos reais.

## Comandos basicos

Instalacao e autenticacao dependem do ambiente. Em uma maquina nova, o caminho comum e:

```bash
npm install -g @openai/codex
codex
```

Iniciar uma sessao com modelo especifico:

```bash
codex -m gpt-5.5
```

Rodar uma tarefa nao interativa:

```bash
codex exec "revise este repositorio e liste riscos de seguranca"
```

Dentro da CLI, os slash commands mais importantes sao:

- **/status** — mostra estado da sessao e limites restantes quando disponivel.
- **/model** — troca o modelo ativo na thread local.
- **/permissions** — ajusta o que Codex pode fazer sem pedir.
- **/agent** — alterna para threads de subagents.
- **/diff** — mostra o diff antes de aceitar/fechar trabalho.

A documentacao oficial tambem lista comandos como `/compact`, `/mcp`, `/mention`, `/plugins`, `/fast`, `/plan`, `/ps` e `/stop`.

## Permissoes e sandbox

Codex opera com uma combinacao de:

- **sandbox** — define o que ele pode ler/escrever/executar.
- **approvals** — define quando precisa pedir sua aprovacao.
- **rules** — permitem controlar prefixos de comando fora do sandbox.
- **instrucoes** — definem comportamento, guardrails e estilo.

Regra pratica:

- Use modo mais restrito para exploracao, auditoria e aprendizado.
- Libere escrita quando a tarefa ja estiver bem definida.
- Exija aprovacao para comandos com rede, instalacao, deploy, remocao ou acesso fora do workspace.
- Nunca aprove comandos destrutivos se voce nao entendeu exatamente o impacto.

As rules oficiais do Codex ficam em arquivos `.rules` dentro de pastas `rules/` em camadas de configuracao ativas. Um caso comum e `~/.codex/rules/default.rules`, onde Codex pode salvar allowlists aprovadas pela UI.

## AGENTS.md e instrucoes persistentes

`AGENTS.md` e o arquivo principal de orientacao do projeto. Ele serve para dizer ao Codex:

- qual e o papel dele naquele repo;
- qual idioma e tom usar;
- quais arquivos sao sensiveis;
- qual fluxo de desenvolvimento seguir;
- quando pode ou nao implementar.

No dadaia Workspace, `AGENTS.md` tem peso operacional. Se ele diz que uma area exige SDD aprovado, o Codex deve obedecer antes de editar.

Boas praticas:

- Coloque regras estaveis no `AGENTS.md`.
- Coloque conhecimento reutilizavel em skills.
- Coloque comandos repetitivos em commands ou scripts.
- Evite duplicar regras contraditorias em varios lugares.

## Skills

Skills sao capacidades reutilizaveis. Uma skill e uma pasta com `SKILL.md` e, opcionalmente:

- `scripts/`
- `references/`
- `assets/`
- `agents/`

Codex carrega primeiro apenas nome, descricao e caminho. So le o `SKILL.md` completo quando decide usar a skill. Isso economiza contexto.

Voce pode acionar skills de duas formas:

- **explicita** — citando a skill no prompt ou usando `/skills` ou `$`.
- **implicita** — quando a descricao da skill combina com a tarefa.

Locais onde Codex procura skills:

- `$CWD/.agents/skills`
- pastas `.agents/skills` acima do cwd ate a raiz do repo
- `$REPO_ROOT/.agents/skills`
- `$HOME/.agents/skills`
- `/etc/codex/skills`
- skills de sistema distribuidas com Codex

Regra pratica:

- Use **skill** para workflow reutilizavel com criterio de ativacao.
- Use **AGENTS.md** para regra persistente do projeto.
- Use **slash command** para controle rapido da sessao.
- Use **SDK** quando quiser automatizar Codex por codigo.

## Commands

No Codex CLI, "commands" aparecem principalmente como slash commands. Eles controlam a sessao interativa sem sair do terminal.

Exemplos de uso:

```bash
/model
/status
/permissions
/agent
/diff
/compact
```

O mais importante e entender que slash command nao substitui instrucao. Ele controla estado da sessao. Se voce quer mudar o comportamento duradouro do agente no projeto, edite `AGENTS.md` ou crie uma skill.

## Como pedir trabalho corretamente

Prompt fraco:

```bash
melhore isso
```

Prompt bom:

```bash
Leia a spec em specs/features/audio-cleaning. Verifique se SPEC, PLAN e TASKS estao aprovados. Se estiverem, implemente somente T01 e T02. Nao edite docker-compose. Ao final rode os testes relevantes e resuma arquivos alterados.
```

Checklist mental antes de pedir:

- O escopo esta claro?
- O Codex sabe quais arquivos ler?
- Existem guardrails?
- A tarefa exige implementacao ou so plano?
- O criterio de pronto esta claro?

## Checklist rapido

- **Comecar simples** — use CLI local e uma tarefa pequena.
- **Ver modelo** — use `/model` quando custo/qualidade importar.
- **Ver consumo** — use `/status` durante sessoes longas.
- **Ver diff** — use `/diff` antes de confiar na mudanca.
- **Usar rules/skills com criterio** — regra persistente vai em `AGENTS.md`; workflow reutilizavel vira skill.

## Referencias oficiais

- Codex CLI: https://developers.openai.com/codex/cli
- Slash commands: https://developers.openai.com/codex/cli/slash-commands
- Rules: https://developers.openai.com/codex/rules
- Skills: https://developers.openai.com/codex/skills
- Subagents: https://developers.openai.com/codex/subagents
