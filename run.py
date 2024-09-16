import logging
import sys
from app import create_app

def configure_logging():
    """Configura o logging para a aplicação."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

def run_server():
    """Executa o servidor Flask."""
    configure_logging()
    
    # Cria e configura a aplicação Flask
    app = create_app()
    
    # Log de informações sobre a configuração da aplicação
    logging.info(f"Starting Flask app on http://{app.config['HOST']}:{app.config['PORT']}")
    
    try:
        # Executa o servidor Flask
        app.run(host=app.config['HOST'], port=app.config['PORT'])
    except Exception as e:
        logging.error(f"Erro ao iniciar o servidor Flask: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_server()
