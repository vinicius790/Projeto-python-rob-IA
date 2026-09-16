# Estratégia de testes

## Pirâmide usada

- regras puras: CPF/PII, state machine, config;
- serviços: colaboradores, pagamentos, payroll, outbox, analytics;
- API: autenticação por escopo, erros, headers, limits, fluxo completo;
- CLI: smoke operacional com banco temporário;
- migration: 0001 populada → 0002, validando destruição do CPF bruto;
- CI PostgreSQL: migrations + seed + payroll + doctor;
- packaging: build e instalação de wheel isolado;
- container: build do Dockerfile.

## Local

```bash
pytest
pytest --cov=robia_ops --cov-report=term-missing --cov-fail-under=88
```

Coverage usa branch coverage. O gate não substitui qualidade de teste: cenários priorizam invariantes, falhas, idempotência, autorização e migração.

## O que não é simulado

- banco gerenciado real;
- provider bancário real;
- broker de eventos;
- IAM corporativo.

Esses pontos exigem ambientes/contratos reais e devem entrar como integration/e2e tests quando existirem.
