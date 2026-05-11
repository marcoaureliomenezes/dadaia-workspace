# 01. Visao Geral do Workspace

## O que o produto realmente faz

O `dadaia-workspace` nao e apenas uma CLI. Ele e um organizador de ambiente para desenvolvimento AI-assisted orientado a SDD.

Na pratica, ele combina cinco camadas de valor:

1. Um runtime local padronizado em `.dadaia/`.
2. Uma interface CLI com contratos estaveis para humanos e agentes.
3. Um modelo de `Spec Context Projects` para focar trabalho multi-repositorio.
4. Um mecanismo de assets de agente instalados em `.claude/`.
5. Uma camada de aprendizagem pratica em `.dadaia/academy/`.

## O problema que ele resolve

Sem um contrato claro, times e agentes acabam decidindo no impulso:

- qual repo e o foco atual;
- onde ficam as specs certas;
- como descobrir contexto ativo;
- onde gravar artefatos de apoio;
- e quais instrucoes do agente ainda valem.

Esse tipo de improviso gera drift estrutural, retrabalho e uma quantidade enorme de ambiguidade escondida.

O `dadaia-workspace` existe para reduzir esse custo de coordenacao.

## O mapa de features do produto

### 1. Bootstrap do workspace

O produto prepara um runtime externo ao repo da biblioteca, incluindo:

- `.dadaia/.venv/`
- `.dadaia/data/`
- `.dadaia/contexts/`
- `.dadaia/tmp/python/`
- `.dadaia/tmp/json/`
- `.dadaia/academy/`
- `.claude/` para assets de agente

### 2. Spec Context Projects

O foco de trabalho do produto nao e um repo isolado, mas um contexto de trabalho com:

- repo principal;
- repos secundarios;
- estado explicito;
- materializacao gerenciada;
- e descoberta estavel por JSON.

### 3. Assets de agente

Rules, skills e commands sao versionados no produto e instalados no runtime do usuario.

Eles existem para impedir que o agente opere no modo "prompt and pray".

### 4. Dadaia Academy

A Academy e a feature de aprendizagem do workspace.

Ela transforma o proprio runtime em um ambiente de estudo aplicado, onde a documentacao deixa de ser um PDF esquecido e passa a ser parte utilizavel do sistema.

## O que o produto nao e

Tambem e importante entender o que ele nao tenta ser:

- nao e um IDE;
- nao e um gerenciador de branches completo;
- nao e um substituto de CI/CD;
- nao e um banco de conhecimento generico sem estrutura.

Ele e uma base operacional para trabalho com agentes e specs.

## Regra de ouro

Se voce precisar resumir o produto em uma frase, use esta:

> O dadaia-workspace organiza runtime, contexto, assets de agente e aprendizagem para que humanos e agentes operem com contratos claros em vez de improviso.