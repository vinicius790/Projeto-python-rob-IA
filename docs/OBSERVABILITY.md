# Observabilidade

## Logs

Logs são JSON em stdout, adequados para coleta por container runtime ou agente externo.

Campos básicos: timestamp, level, logger, message e `request_id` quando disponível. Contextos conhecidos são submetidos a redação de chaves sensíveis.

## Request ID

- cliente pode enviar `X-Request-ID`;
- se ausente, um UUID é criado;
- o valor retorna na resposta;
- o contexto entra em logs;
- audit events originados pela request recebem o mesmo ID.

## Métricas

`GET /api/v1/metrics` expõe formato Prometheus.

Métricas principais:

- `robia_http_requests_total`;
- `robia_http_request_duration_seconds`;
- `robia_payment_processing_total`.

Labels usam template de rota quando disponível para evitar cardinalidade por ID.

## Probes

- `/live`: verifica apenas que o processo HTTP está respondendo;
- `/ready`: consulta DB e deve ser usado antes de receber tráfego;
- `/health`: compatibilidade/diagnóstico geral.

## Produção

Recomendado: centralizar logs, Prometheus/OpenTelemetry collector, alertas por erro/latência, dashboards por SLO e retenção coerente. Esses componentes não são fingidos dentro do repositório.
