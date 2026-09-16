# ADR 0001 — Um único core de aplicação

**Status:** accepted

## Contexto
O baseline combinava múltiplos frameworks sem uma aplicação integrada.

## Decisão
FastAPI + SQLAlchemy 2 formam o caminho principal; o legado permanece isolado para rastreabilidade.

## Consequência
Menos duplicação e uma única fronteira de domínio. Novos frameworks só entram se resolverem necessidade concreta.
