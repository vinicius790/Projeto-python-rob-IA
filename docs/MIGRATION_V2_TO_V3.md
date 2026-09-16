# Migração v2 → v3

## Mudanças de schema

Revision `0002` adiciona:

- public IDs e optimistic versions;
- `cpf_last2` e conversão do campo histórico `cpf` em HMAC fingerprint;
- `payroll_runs`;
- payment currency/request fingerprint/run linkage;
- `payment_attempts`;
- request ID em audit;
- `outbox_events`;
- constraints monetárias.

## Passo crítico: CPF

A migration lê os CPFs ainda brutos da v2, calcula HMAC com `ROBIA_PII_KEY`, grava os últimos dois dígitos e substitui o valor original. O processo é irreversível.

Antes do upgrade:

1. faça backup testado do banco;
2. defina `ROBIA_PII_KEY` definitiva para o ambiente;
3. confirme que a mesma chave estará disponível para a aplicação após migration;
4. rode em staging primeiro.

```bash
export ROBIA_PII_KEY='...'
alembic upgrade head
```

Trocar a PII key posteriormente impede lookup exato de CPFs criados com a chave antiga. Planeje rotação como migração de dados, não como simples troca de secret.

## Verificação

CI executa uma migration smoke real:

1. cria schema `0001`;
2. insere colaborador/pagamento representativos;
3. aplica `0002`;
4. verifica que CPF bruto desapareceu e novos campos foram preenchidos.
