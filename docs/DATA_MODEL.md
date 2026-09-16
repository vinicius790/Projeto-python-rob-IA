# Modelo de dados

## `employees`

- PK interna inteira para joins eficientes;
- `public_id` UUID para exposição externa futura;
- `cpf` contém **fingerprint HMAC**, apesar do nome histórico da coluna;
- `cpf_last2` permite máscara sem recuperar o identificador completo;
- `salary` e `meal_allowance` usam `Numeric(12,2)`;
- `active` implementa desativação lógica;
- `version` suporta locking otimista.

Invariantes: salário > 0; benefício >= 0; fingerprint de CPF único.

## `payroll_runs`

Representa uma execução de folha por competência. `reference_date` é única. Guarda contadores que tornam o resultado operacional observável sem recalcular toda a execução.

Estados: `running`, `completed`, `failed`.

## `payments`

Snapshot monetário do colaborador no momento da criação. Alterar salário do colaborador depois não muda pagamentos históricos.

Campos relevantes:

- `public_id`;
- `payroll_run_id` opcional;
- salário/benefício/currency;
- competência;
- status;
- `idempotency_key`;
- `request_fingerprint`;
- provider reference/failure reason;
- version/timestamps.

## `payment_attempts`

Registra cada interação com provider, inclusive dry-run. O par `(payment_id, attempt_number)` é único.

Não armazena credenciais, request body completo nem CPF.

## `audit_events`

Trilha operacional para ações relevantes. Inclui `request_id` quando originada por HTTP, permitindo correlação com logs.

## `outbox_events`

Envelope persistente para integração futura. `event_id` é UUID único; `payload` deve conter apenas dados estritamente necessários e não deve incluir PII completa ou secret.

## Relações

```text
Employee 1 ─── * Payment * ─── 0..1 PayrollRun
                   │
                   └── 1 ─── * PaymentAttempt

AuditEvent          (independente, referência lógica)
OutboxEvent          (independente, referência lógica)
```
