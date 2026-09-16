# Baseline do arquivo recebido

## [confirmado] Propósito observável

O código recebido concentra-se principalmente em **colaboradores e pagamentos**: modelos `Colaborador`/`Pagamento`, cadastro/listagem, API JSON, salários, vale-refeição e tentativas de integração financeira. Há também experimentos de IA/ML e UI desktop em `Celpe.py`, além de um formulário de robótica desconectado do restante.

## [confirmado] Componentes existentes

- Flask em `app.py`, `run.py` e também dentro de `Celpe.py`;
- Django em `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `settings.py` e templates;
- SQLAlchemy duplicado entre `models_sqlalchemy.py`, `app.py` e `Celpe.py`;
- PyQt5 em `Celpe.py`;
- TensorFlow e PyTorch para regressão em `dados.csv` — arquivo ausente no ZIP;
- requests para endpoints de Santander/iFood sem contrato verificável;
- frontend HTML/CSS/JS solto na raiz;
- muitos workflows GitHub genéricos para AWS, Azure, Google, Next.js, Deno, Jekyll, Datadog etc.

## [confirmado] O que estava quebrado ou incompleto

- `forms.py` importa `Robo`, `Sensor` e `Atuador`, que não existem em `models.py`;
- `views.py` importa `PagamentoForm`, inexistente em `forms.py`;
- `views.py` usa `json` sem importá-lo;
- `add_pagamento_api` usa campo `valor`, inexistente no model `Pagamento`;
- templates referenciam rotas de colaborador que não existem em `urls.py`;
- templates usam `{% static %}` sem a estrutura Django completa e sem carregamento explícito de `static`;
- `Celpe.py` usa `sys.argv`/`sys.exit` sem importar `sys`;
- `Celpe.py` exige `dados.csv`, ausente;
- `Pagamento.data_pagamento` em SQLAlchemy espera `Date`, mas a rota atribui string sem validação;
- uma `Session` SQLAlchemy é criada uma vez dentro da factory Flask e reutilizada por requisições;
- há modelos equivalentes com tipos incompatíveis (`Float` vs `Decimal`);
- não existe arquivo de dependências/packaging consistente;
- não existem migrations nem testes;
- `DEBUG` e hosts permissivos aparecem em configuração de desenvolvimento;
- secrets de exemplo ficam misturados à configuração principal;
- integração de pagamentos não implementa retry, idempotência, contrato de provider ou sandbox verificável;
- workflows CI/CD não refletem a tecnologia real do repositório e vários exigiriam secrets/infra não fornecidos.

## [confirmado] Pontos fortes preservados

- intenção clara de separar configuração e banco em alguns arquivos;
- uso de ORM e relacionamentos como direção arquitetural;
- preocupação com logging e rotação em `create_db.py`;
- presença de validação básica de CPF no model Django;
- ideia de API + dashboard;
- ideia de integrar analytics/ML ao domínio operacional;
- tentativa de separar execução (`run.py`) da factory (`app.py`).

## [implementado] Direção escolhida

Em vez de manter dois frameworks web e três definições de modelo, a versão 2.0 consolida o núcleo em FastAPI + Pydantic + SQLAlchemy 2 + Alembic, preservando o material antigo em `legacy/original/`.

A escolha não foi feita apenas por modernização: ela resolve validação, contratos HTTP, documentação OpenAPI e integração com schemas Pydantic em uma base única, eliminando inconsistências do baseline.
