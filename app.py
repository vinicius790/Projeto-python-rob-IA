# app.py
import json
import logging
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

def load_config(config_file='config.json'):
    """Carregar configurações do arquivo JSON."""
    with open(config_file) as f:
        return json.load(f)

def create_app():
    """Criar e configurar a aplicação Flask."""
    config = load_config()
    
    app = Flask(__name__)
    app.config.update(
        DEBUG=config['flask']['debug'],
        SECRET_KEY=config['flask']['secret_key'],
        HOST=config['flask']['host'],
        PORT=config['flask']['port']
    )
    
    # Configuração do banco de dados
    DATABASE_URI = config['database']['sqlite']['database_uri']
    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    
    # Configuração da sessão
    Session = sessionmaker(bind=engine)
    session = Session()

    # Importar e registrar as rotas
    from views import index, colaboradores, add_pagamento
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/api/colaboradores', 'colaboradores', colaboradores)
    app.add_url_rule('/api/pagamentos', 'add_pagamento', add_pagamento, methods=['POST'])
    
    return app
