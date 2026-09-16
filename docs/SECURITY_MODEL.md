# Modelo de segurança

## Escopo

Este documento descreve controles implementados no código. Ele não declara conformidade regulatória.

## Ativos relevantes

- dados de colaboradores;
- valores salariais/benefícios;
- estados e referências de pagamentos;
- API keys;
- PII key usada para fingerprint;
- logs/auditoria;
- banco de dados.

## Ameaças consideradas e controles

### Vazamento de CPF

**Risco:** persistência, resposta ou log do identificador completo.

**Controles:**
- validação na entrada;
- HMAC-SHA256 keyed antes da persistência;
- armazenamento somente dos dois últimos dígitos para máscara;
- logger redacta chaves sensíveis;
- exportação CSV não contém CPF;
- migration 0002 elimina o valor bruto legado.

### Reuso indevido de Idempotency-Key

**Risco:** uma chave usada por payload diferente retornar uma operação antiga como se fosse equivalente.

**Controle:** `request_fingerprint` canônico; divergência gera 409.

### Credencial excessivamente poderosa

**Risco:** uma única chave expor funções administrativas.

**Controle:** scopes `read`, `write`, `admin`; comparação constant-time via `hmac.compare_digest`.

### Requisições abusivamente grandes

**Risco:** consumo de memória/CPU via body grande, inclusive chunked.

**Controle:** middleware ASGI contabiliza bytes em streaming e retorna 413.

### Integração financeira acidental

**Risco:** código de portfólio disparar operação externa real.

**Controle:** provider único `sandbox`, sem request de rede; provider real exige implementação e habilitação explícitas.

### Falha parcial ao integrar

**Risco:** estado local divergir de evento externo.

**Controles:** payment attempts + transactional outbox + idempotência. A entrega externa ainda não está implementada, evitando falsa garantia.

### Host/origin indevidos

**Controles:** TrustedHost; CORS allowlist opcional; CSP; X-Frame-Options; nosniff; Referrer-Policy; HSTS em produção.

### Exposição de tooling de desenvolvimento

Docs e dashboard são desabilitados automaticamente em produção.

## Segredos

Nunca versione `.env`. Produção deve usar secret manager/orchestrator. Rotacione:

- API keys;
- `ROBIA_PII_KEY` com plano de migração coordenado, porque trocar essa chave muda fingerprints.

A PII key é semanticamente parte do esquema de identidade: rotação exige refingerprint a partir de uma fonte autorizada; como v3 não guarda CPF bruto, não há rotação automática possível sem reentrada segura dos dados.

## Limites conhecidos

- API keys não equivalem a OIDC, MFA ou identidade de usuário;
- rate limiting distribuído deve ficar em gateway/ingress ou store compartilhado;
- outbox precisa de worker/broker real para entrega externa;
- audit log local não é WORM/imutável;
- backup, retenção e disaster recovery dependem da infraestrutura;
- nenhum claim de PCI/LGPD é feito.
