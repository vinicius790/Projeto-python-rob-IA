# Política de segurança

## Dados sensíveis

Não publique CPFs reais, credenciais, tokens, chaves privadas, dados bancários ou dumps de produção neste repositório. Testes e demonstrações devem usar somente dados sintéticos.

## Controles implementados na v3

- configuração por environment variables e `.env` ignorado;
- produção exige chave administrativa e PII key customizada;
- API keys com escopos read/write/admin e comparação constant-time;
- CPF bruto não é persistido no caminho principal;
- logs JSON com redação de campos sensíveis;
- limite de request body em streaming;
- TrustedHost, CSP, HSTS em produção, no-store para API e demais security headers;
- provider financeiro exclusivamente sandbox;
- validação Pydantic e SQLAlchemy constraints;
- idempotência vinculada ao fingerprint do payload;
- payment attempts + transactional outbox;
- session por request e rollback em erro;
- CodeQL, Dependabot e dependency audit no GitHub Actions.

## PII key

`ROBIA_PII_KEY` é usada para fingerprint HMAC do CPF. A migration 0002 destrói o CPF bruto e é one-way. Faça backup antes da migration e não troque a chave sem um plano de reidentificação autorizado/migração de dados.

## Limites

A solução não afirma conformidade PCI/LGPD, não implementa OIDC/MFA, WAF, rate limit distribuído, KMS/HSM, audit log WORM ou broker real. Esses recursos dependem do ambiente de implantação.

## Relato de vulnerabilidade

Prefira um **GitHub Security Advisory privado** do repositório. Não publique proof-of-concept destrutiva, credenciais ou dados pessoais em issue pública. Inclua impacto, versão afetada, passos mínimos de reprodução e mitigação sugerida quando possível.
