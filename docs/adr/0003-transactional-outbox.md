# ADR 0003 — Transactional outbox antes de broker

**Status:** accepted

## Contexto
Eventos de pagamento poderão precisar de integração externa, mas nenhum broker real faz parte do baseline.

## Decisão
Persistir eventos em outbox na mesma transação do domínio. Não adicionar Kafka/RabbitMQ fictício.

## Consequência
A aplicação fica pronta para entrega confiável futura sem assumir infraestrutura inexistente. Um worker deverá publicar e reconhecer eventos posteriormente.
