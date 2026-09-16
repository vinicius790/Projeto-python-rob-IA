# Validação da versão 3.0

Resultados observados no ambiente de construção em 2026-09-16. Este documento separa o que foi executado localmente do que permanece delegado ao CI ou a infraestrutura externa.

## [implementado] Testes automatizados

```text
58 passed
coverage: 91.95%
coverage gate: 88%
```

A suíte usa branch coverage e cobre, entre outros pontos: configuração, CPF/PII, banco, colaboradores, pagamentos, idempotência, transições de estado, folha de pagamento, payroll runs, provider sandbox, retries, outbox transacional, API keys e escopos, limites de request, endpoints, dashboard, auditoria, analytics, CLI e migração operacional.

Comando executado:

```bash
PYTHONPATH=src python -m pytest \
  --cov=robia_ops \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=88
```

## [implementado] Validações locais adicionais

Foram executados com sucesso:

- compilação de `src/`, `tests/`, `alembic/` e `scripts/` com `compileall`;
- parse de `pyproject.toml`;
- parse dos YAMLs em `.github/workflows/`;
- construção de `robia_ops-3.0.0-py3-none-any.whl` via backend definido no `pyproject.toml`;
- instalação do wheel em diretório isolado com `--no-deps`;
- `python -m robia_ops --version` a partir do wheel instalado;
- verificação de que `dashboard.html` e `app.css` fazem parte do wheel;
- `alembic upgrade head` sobre banco SQLite vazio;
- migração representativa `0001 -> 0002` sobre banco SQLite com dados legados;
- verificação da migração one-way de CPF para fingerprint + dados mínimos de máscara;
- carregamento e apresentação da CLI v3.

## [pendente] Validações dependentes de ambiente externo

- `ruff` e `mypy` estão configurados como quality gates, porém não estavam instalados no runtime local desta validação; o workflow de CI executa ambos após instalar o extra `dev`.
- Docker/Compose não foram executados localmente neste ambiente. O CI inclui build do container.
- PostgreSQL não foi executado localmente nesta sessão. O CI possui um serviço PostgreSQL 17 e executa migrations + smoke da CLI contra ele.
- `pip-audit`, CodeQL e Dependency Review dependem do ambiente GitHub/instalação das ferramentas e estão configurados nos workflows de segurança.
- nenhum provider financeiro real foi habilitado ou validado. A v3 mantém apenas o provider sandbox por design.

## Critério de release

Uma release é considerada publicável quando os jobs obrigatórios do GitHub Actions ficam verdes em `main`, em especial: quality gate, compatibilidade Python, migração v2→v3, smoke PostgreSQL, build do pacote, build do container e workflows de segurança aplicáveis.
