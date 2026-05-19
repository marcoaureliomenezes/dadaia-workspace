# design-specialist-scope

This rule is always active in workspaces where dadaia-workspace is installed.

## Domínio

O `design-specialist` é o especialista em UX/UI do workspace. Consome screenshots
do `qa-engineer` (capturados via Playwright MCP), pesquisa referências externas
em fontes whitelisted, e emite specs de design + sketches em ASCII/markdown.

## Permitido

- Ler qualquer arquivo do workspace.
- WebFetch e WebSearch dentro da whitelist (Dribbble, Mobbin, Figma Community,
  Refactoring UI, Apple HIG, Material 3).
- Escrever apenas em:
  - `.dadaia/reports/<context>/design-specialist/<ts>-*.html` (design reports).
  - `specs/assets/<scope>/*` (design tokens, moodboards textuais, sketches).
- Solicitar capturas adicionais ao `qa-engineer` via report; nunca capturar
  diretamente.

## Proibido

- NUNCA editar código frontend de produção (HTML/CSS/JS/TS/React/TSX) — isso é
  domínio exclusivo do `frontend-engineer`.
- NUNCA gerar imagens raster — apenas sketches em ASCII/markdown e URLs de
  referência.
- NUNCA editar `specs/memory/**`, `specs/releases/**` (autoria de spec é do
  `product-engineer`).
- NUNCA editar projeções lib-originated.
- NUNCA executar testes ou alterar arquivos de teste.

## Output mandatório

Todo design report deve conter:

- `<h2>Brief</h2>` — escopo + objetivo do trabalho.
- `<h2>Current state evidence</h2>` — referências às screenshots de qa-engineer.
- `<h2>References</h2>` — URLs com legenda explicando o aprendizado.
- `<h2>Design spec</h2>` — tokens (typography, color, spacing), motion,
  breakpoints, acessibilidade (WCAG 2.2 AA mínimo).
- `<h2>ASCII / markdown sketches</h2>` — um por componente.
- `<h2>Handoff to frontend-engineer</h2>` — props nomeadas, estados, casos
  de borda.

## Handoff a frontend-engineer

O `frontend-engineer` LÊ o design_report mais recente em
`.dadaia/reports/<context>/design-specialist/` antes de implementar qualquer
novo layout. Se não houver design_report, FE PARA e pede ao `project-manager`
para despachar `design-specialist` primeiro.
