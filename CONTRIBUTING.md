# Contribuindo

## Ambiente local

```bash
python -m venv .venv
python -m pip install -e ".[dev,ml,postgres]"
pre-commit install
alembic upgrade head
```

Copie `.env.example` para `.env` e use somente dados sintéticos.

## Antes do PR

```bash
make check
```

Se alterar schema, também valide migration em banco limpo e upgrade a partir da revision anterior.

## Regras arquiteturais

- rotas HTTP não devem conter regra de domínio;
- transições de pagamento passam pela state machine;
- valores monetários usam `Decimal`/`Numeric`, nunca float persistido;
- CPF bruto não pode voltar a ser persistido/logado;
- integração externa implementa contrato em `integrations/`;
- provider real exige sandbox oficial, idempotência, timeout/retry e testes de contrato;
- side effects externos futuros devem usar outbox/worker, não request síncrona sem estratégia de recuperação;
- migrations são versionadas e devem documentar irreversibilidade quando aplicável;
- não altere `legacy/original/` salvo correção documental explícita;
- não adicione framework/dependência sem justificar benefício concreto.

## Testes

Priorize invariantes e falhas reais: autenticação, idempotência, concorrência, migration, retries, privacidade e estados. Cobertura é um gate, não um objetivo isolado.

## Pull request

Explique:

1. problema;
2. decisão técnica;
3. alternativas descartadas;
4. risco/impacto de dados;
5. migration, se houver;
6. testes executados;
7. impacto operacional/deploy.
