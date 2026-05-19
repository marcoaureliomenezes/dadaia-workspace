# Security Spec: dadaia-workspace

> **Status:** [ ] Draft

## Escopo

Segurança da biblioteca Python `dadaia-workspace` e sua CLI — instalação, execução e armazenamento de artefatos.

## Requisitos de Segurança

### Secrets e Credenciais

- **FR-S01**: Nenhuma credencial (tokens, API keys) deve ser commitada ao repositório
- **FR-S02**: Secrets são lidos de variáveis de ambiente ou arquivos `.env` (gitignored)
- **FR-S03**: Templates de configuração são commitados sem valores reais

### Permissões de Arquivo

- **FR-S04**: Arquivos de configuração com credenciais devem ter permissão `600` (owner-only)
- **FR-S05**: A CLI não deve criar arquivos com permissões mais amplas que o necessário

### Dependências

- **FR-S06**: Dependências declaradas com versões pinadas em `pyproject.toml`
- **FR-S07**: Sem dependências com vulnerabilidades conhecidas (OWASP Top 10)

## Verificação

- `grep -r "token\|api_key\|password" . --include="*.py" | grep -v "os.environ\|env\|example"` retorna vazio
- `poetry audit` sem vulnerabilidades críticas
