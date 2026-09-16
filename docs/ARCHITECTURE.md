# Arquitetura da RobIA Ops v3

## Objetivos

A arquitetura v3 prioriza: consistência de domínio, rastreabilidade, privacidade, extensibilidade de integrações, testabilidade e operação previsível. Ela evita introduzir broker, cache distribuído ou IAM corporativo sem necessidade real, mas cria pontos de extensão claros para esses componentes.

## Visão em camadas

```text
HTTP / Dashboard / CLI
        │
        ▼
Pydantic schemas + scoped authorization
        │
        ▼
Application services
        │
        ├── domain/payment_state.py
        ├── audit
        ├── outbox
        ├── analytics
        └── provider contract
        │
        ▼
SQLAlchemy 2 Session / ORM
        │
        ▼
SQLite (local) | PostgreSQL (deployment)
```

## Responsabilidades

### `api/`
Transforma HTTP em chamadas de aplicação. Rotas validam paginação, scopes e contratos de transporte, sem duplicar regra financeira.

### `domain/`
Contém invariantes independentes do transporte. A máquina de estados de pagamentos reside aqui para que API, CLI ou worker futuro obedeçam às mesmas transições.

### `services/`
Coordena casos de uso e fronteiras transacionais: colaboradores, pagamentos, payroll runs, auditoria, analytics e outbox.

### `integrations/`
Define `PaymentProvider`. A implementação `SandboxPaymentProvider` é determinística e não usa rede. Um provider real deve entrar por essa interface, nunca diretamente em rota/ORM.

### `observability/`
Centraliza contexto de request e métricas. `X-Request-ID` é propagado para log e auditoria.

### `security/`
CPF, PII fingerprint e autorização por escopo. A aplicação v3 não persiste CPF completo.

### `models.py`
Persistência e invariantes de banco: constraints monetárias, identificadores públicos, versioning otimista e relacionamentos.

### `schemas.py`
Contratos Pydantic de entrada/saída. Valores monetários usam `Decimal`.

## Transações

Cada request recebe uma `Session` própria. Serviços fazem commit em fronteiras de caso de uso. `get_db` executa rollback se uma exceção escapar da operação.

O processamento externo de pagamento é deliberadamente dividido em etapas:

1. pagamento passa para `queued` e essa intenção é persistida;
2. uma `PaymentAttempt` é criada;
3. o provider é invocado;
4. tentativa é encerrada;
5. pagamento passa para `processed` ou `failed`;
6. audit event + outbox event são persistidos junto da atualização final.

Esse desenho deixa histórico suficiente para diagnosticar falhas e abre espaço para worker assíncrono futuro sem fingir que ele já existe.

## Idempotência

`Payment.idempotency_key` é único. A v3 também salva um SHA-256 canônico do payload efetivo (`request_fingerprint`). Reuso da mesma chave:

- mesmo fingerprint → retorna o pagamento existente;
- fingerprint diferente → `409 Conflict`.

Isso evita um erro comum em APIs idempotentes: aceitar silenciosamente uma chave repetida para uma operação diferente.

## Concorrência

`Employee` e `Payment` possuem coluna `version` configurada como `version_id_col` do SQLAlchemy. Updates concorrentes obsoletos podem ser detectados pelo ORM em vez de sobrescrever dados sem sinalização.

## Payroll runs

A competência da folha é representada por `PayrollRun`, única por `reference_date`. A geração de folha é repetível: uma segunda execução reutiliza o run concluído e não duplica pagamentos.

## Outbox transacional

Eventos relevantes são persistidos em `outbox_events` na mesma transação da mudança de estado. A v3 não inclui broker fictício. Um worker futuro pode:

1. buscar eventos `published_at IS NULL`;
2. publicar no transporte real;
3. marcar `published_at` apenas após confirmação;
4. usar `event_id` como chave de deduplicação externa.

## Extensão de provider

Um provider real precisa:

1. implementar `PaymentProvider`;
2. retornar `ProviderResult` com `retryable` coerente;
3. ter sandbox oficial/documentado;
4. definir idempotência do fornecedor;
5. nunca registrar secrets ou payloads sensíveis;
6. possuir testes de contrato;
7. documentar timeouts, retry, rate limits e reconciliação;
8. ser habilitado explicitamente por configuração.

## Decisões deliberadamente não implementadas

- microserviços: não há escala/limites de domínio que justifiquem fragmentação;
- Redis/cache: o perfil atual não possui gargalo comprovado;
- broker: outbox foi preparado, mas entrega externa ainda não é necessária para a demo;
- OIDC: requer provedor real/IAM; API keys scoped são suficientes para o escopo atual;
- event sourcing: auditoria + outbox resolvem o problema atual com complexidade muito menor.
