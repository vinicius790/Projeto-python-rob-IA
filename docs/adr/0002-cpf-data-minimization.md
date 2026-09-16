# ADR 0002 — Minimização de CPF

**Status:** accepted

## Contexto
A API só precisa impedir duplicidade e exibir máscara; não existe caso de uso confirmado que exija recuperar CPF completo.

## Decisão
Persistir HMAC keyed + últimos dois dígitos, eliminando CPF bruto na migration 0002.

## Consequências
Reduz impacto de vazamento de banco. Em contrapartida, a PII key torna-se crítica e sua rotação exige processo de migração coordenado.
