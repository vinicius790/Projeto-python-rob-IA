# Analytics e IA

O baseline carregava TensorFlow e PyTorch simultaneamente para um CSV ausente. A arquitetura atual usa um problema concreto e uma estratégia proporcional.

## Estratégia

1. fallback estatístico por z-score do total de pagamento;
2. Isolation Forest opcional quando existem ao menos 8 pagamentos válidos e `scikit-learn` está instalado.

Features atuais: salário, benefício e total. Pagamentos cancelados são excluídos da detecção.

A resposta contém `score`, `is_anomaly`, `model` e `reasons`.

## Interpretação

Anomalia é somente um **sinal técnico para revisão**. Não significa fraude, erro, culpa, desempenho de funcionário ou justificativa para decisão trabalhista.

## Qualidade de modelo

Sem labels reais, não existe métrica honesta de precision/recall. Por isso a v3 não publica números inventados de acurácia. Evoluções úteis quando houver dados adequados:

- dataset versionado e governado;
- features sazonais/por função;
- split temporal;
- precision/recall em labels revisados;
- drift de dados/modelo;
- model registry;
- explicabilidade local;
- revisão humana obrigatória para casos sensíveis.
