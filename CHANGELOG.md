# Changelog

## 3.0.0 — 2026-09-16

### Segurança e privacidade
- armazenamento de CPF completo removido do caminho principal: HMAC keyed + dois últimos dígitos
- migration one-way v2→v3 para converter dados legados
- chaves de API com escopos `read`, `write` e `admin`
- limite de request body inclusive em streaming
- CSP, Permissions-Policy, no-store em API e HSTS em produção
- docs e dashboard automaticamente desativados em produção

### Domínio e confiabilidade
- `PayrollRun` como entidade de primeira classe
- máquina de estados explícita para pagamentos
- versionamento otimista de `Employee` e `Payment`
- identificadores públicos UUID
- fingerprint do payload de idempotência para rejeitar reuso inconsistente da chave
- `PaymentAttempt` para rastrear tentativas do provider
- retry exponencial configurável para falhas transitórias
- transactional outbox para eventos de integração

### Observabilidade
- request IDs propagados para logs e auditoria
- métricas Prometheus de HTTP e processamento de pagamentos
- probes separadas de liveness/readiness
- analytics mensal adicional

### Engenharia
- cobertura com branches e gate de 88%
- CI multi-Python, migration smoke populada v2→v3, PostgreSQL smoke, wheel smoke e Docker build
- dependency audit, CodeQL, Dependabot e workflow de release por tag
- Docker multi-stage, usuário não-root, healthcheck e Compose endurecido
- pre-commit e documentação técnica/ADRs expandidos

## 2.0.0 — 2026-09-16

### Adicionado
- aplicação principal FastAPI com API versionada e dashboard
- SQLAlchemy 2, Alembic e suporte SQLite/PostgreSQL
- validação e mascaramento de CPF
- fluxo de pagamentos com idempotência
- provider sandbox sem transferência real
- auditoria operacional
- analytics estatístico e Isolation Forest opcional
- CLI operacional
- logs JSON com redação de campos sensíveis
- Dockerfile, Compose, CI, CodeQL e Dependabot
- suíte de testes e documentação técnica

### Corrigido estruturalmente
- duplicidade de modelos Django/SQLAlchemy sem contrato comum
- sessão SQLAlchemy global usada pelas rotas Flask
- campos incompatíveis entre views e models
- referências a componentes inexistentes
- mistura de templates Django com app Flask sem integração consistente
- configuração insegura no caminho principal
- integração financeira não verificável no código principal
- workflows GitHub desalinhados com o repositório

### Preservado
- código recebido integralmente em `legacy/original/` para rastreabilidade
