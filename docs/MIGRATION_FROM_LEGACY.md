# Migração do legado

## O que foi preservado

Todos os arquivos recebidos permanecem em `legacy/original/` para referência.

## Mapeamento conceitual

| Baseline | Versão 2.0 |
|---|---|
| `app.py` / Flask | `src/robia_ops/main.py` + `api/` |
| `models.py` Django + `models_sqlalchemy.py` | `src/robia_ops/models.py` |
| `views.py` | rotas API + `services/` |
| `config.json` | `config.py` + ambiente |
| `create_db.py` | Alembic + `robia init-db` |
| `run.py` | `robia serve` |
| chamadas Santander/iFood | contrato `PaymentProvider` + sandbox |
| TensorFlow/PyTorch em `Celpe.py` | `services/analytics.py` + ML opcional |
| HTML/CSS/JS soltos | `web/templates` + `web/static` |
| workflows genéricos | CI/CodeQL/Dependabot específicos |

## Compatibilidade

Os arquivos raiz `run.py` e `create_db.py` foram mantidos como launchers de compatibilidade. O restante do legado não é importado automaticamente.
