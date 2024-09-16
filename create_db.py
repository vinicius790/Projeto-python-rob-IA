import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Colaborador, Pagamento, Base, get_engine
from logging.handlers import RotatingFileHandler

# Configuração de logging com rotação de arquivos
handler = RotatingFileHandler('create_db.log', maxBytes=10000000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logging.getLogger().addHandler(handler)

# Configuração do logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config(config_file='config.json'):
    """Carregar configurações do arquivo JSON."""
    try:
        with open(config_file) as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuração não encontrada: {config_file}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar o arquivo JSON: {e}")
        raise

def setup_database():
    """Configurar o banco de dados e criar tabelas."""
    config = load_config()
    DATABASE_URI = config['database']['sqlite']['database_uri']

    try:
        # Configuração do banco de dados
        engine = create_engine(DATABASE_URI)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()

        # Adicionar alguns colaboradores para teste
        if session.query(Colaborador).count() == 0:
            colaboradores = [
                Colaborador(nome='João Silva', cpf='12345678900', salario=3000.00, vale_refeicao=500.00),
                Colaborador(nome='Maria Oliveira', cpf='98765432100', salario=3200.00, vale_refeicao=550.00),
                Colaborador(nome='Carlos Souza', cpf='11122233344', salario=3100.00, vale_refeicao=520.00)
            ]
            session.add_all(colaboradores)
            session.commit()
            logging.info("Dados de teste adicionados com sucesso.")
        else:
            logging.info("Dados já existentes na base de dados. Nenhum dado de teste adicionado.")
    except Exception as e:
        logging.error(f"Erro ao configurar o banco de dados: {e}")
        raise

if __name__ == '__main__':
    setup_database()
