# Operação

## Local

```bash
python -m pip install -e ".[dev,ml]"
cp .env.example .env
alembic upgrade head
robia seed-demo
robia serve --reload
```

No Windows, copie `.env.example` manualmente em vez de `cp`.

## Banco

SQLite é o padrão local. PostgreSQL:

```env
ROBIA_DATABASE_URL=postgresql+psycopg://user:password@host:5432/robia
```

Instale `.[postgres]`.

## Migrations

```bash
alembic upgrade head
alembic current
alembic history
```

**Importante:** revision `0002` é one-way porque destrói CPF bruto. Não use `alembic downgrade` para voltar à v2; restaure backup pré-migração.

## Diagnóstico

```bash
robia doctor
robia security-check
```

## Outbox

```bash
robia outbox
robia outbox-ack 1
```

Em uma integração real, `ack` só deve ocorrer após confirmação do broker/consumidor externo.

## Exportação

```bash
robia export-payments exports/payments.csv
```

A escrita é atômica e o arquivo não contém CPF.

## Produção

Checklist mínimo:

- `ROBIA_ENV=production`;
- `ROBIA_ADMIN_API_KEY`/IAM superior;
- `ROBIA_PII_KEY` forte em secret manager;
- hosts/origins explícitos;
- PostgreSQL gerenciado;
- TLS no ingress;
- limites CPU/memória;
- backup + restore testado;
- logs/métricas centralizados;
- alertas;
- política de retenção;
- gateway/rate limit distribuído se público;
- worker de outbox se integrações externas forem habilitadas.
