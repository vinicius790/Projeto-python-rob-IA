# API v1

Base: `/api/v1`.

## Autorização

Credencial em `X-API-Key`.

| Escopo | Capacidades |
|---|---|
| `read` | consultas de domínio, analytics, métricas |
| `write` | tudo de read + mutações e processamento |
| `admin` | tudo de write + audit/outbox |

`ROBIA_API_KEY` legado equivale a admin. Sem qualquer chave configurada, o modo local permite acesso para reduzir atrito de desenvolvimento. Produção exige uma chave administrativa.

## Infraestrutura

- `GET /live` — processo vivo; não consulta DB
- `GET /health` — health com consulta DB
- `GET /ready` — readiness com consulta DB
- `GET /meta` — metadados não sensíveis do serviço
- `GET /metrics` — Prometheus, sujeito a read scope

## Colaboradores

- `GET /employees`
- `POST /employees`
- `GET /employees/{id}`
- `PATCH /employees/{id}`
- `DELETE /employees/{id}` — desativação lógica

Filtros: `search`, `active`, `limit`, `offset`.

`search` consulta somente nome. CPF é validado na entrada, fingerprinted e exibido mascarado.

## Pagamentos

- `GET /payments`
- `POST /payments`
- `GET /payments/{id}`
- `GET /payments/{id}/attempts`
- `POST /payments/{id}/process`
- `POST /payments/{id}/cancel`
- `POST /payments/generate-payroll` — compatibilidade com v2

### Idempotência

Envie `Idempotency-Key` no `POST /payments`. A chave é vinculada ao payload efetivo. Reuso com payload diferente retorna 409.

### Processamento

```json
{"dry_run": true}
```

Dry-run registra uma tentativa, mas não muda o estado do pagamento. `dry_run=false` usa o provider configurado; na v3, apenas sandbox é habilitado.

## Payroll runs

- `GET /payroll-runs`
- `POST /payroll-runs`
- `GET /payroll-runs/{id}`

`POST` é idempotente por `reference_date`.

## Analytics

- `GET /analytics/summary`
- `GET /analytics/monthly-payroll?months=12`
- `GET /analytics/payment-anomalies`

## Auditoria

Admin only:

- `GET /audit?action=...&entity_type=...`

## Outbox

Admin only:

- `GET /operations/outbox`
- `POST /operations/outbox/{id}/ack`

`ack` representa confirmação de publicação externa. Não publique um evento antes de o transporte real confirmar entrega.

## Erros de domínio

Erros tratados preservam `detail` por compatibilidade e acrescentam metadados:

```json
{
  "detail": "Pagamento não encontrado",
  "error": {
    "code": "not_found",
    "request_id": "..."
  }
}
```

Códigos principais: `not_found`, `conflict`, `invalid_state`, `internal_error`.
