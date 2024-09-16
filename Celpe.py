import json
import logging
import os
import pandas as pd
import sqlite3
from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton
from PyQt5.QtGui import QFont
from threading import Thread
import requests

# Configuração do logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para carregar configurações do arquivo JSON
def load_config(config_file='config.json'):
    """Carregar configurações do arquivo JSON."""
    if not os.path.exists(config_file):
        logging.error(f"Configuração não encontrada: {config_file}")
        raise FileNotFoundError(f"Configuração não encontrada: {config_file}")
    
    with open(config_file) as f:
        return json.load(f)

# Configuração do banco de dados com SQLAlchemy
Base = declarative_base()

class Colaborador(Base):
    __tablename__ = 'colaboradores'
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    cpf = Column(String, unique=True)
    salario = Column(Float)
    vale_refeicao = Column(Float)

class Pagamento(Base):
    __tablename__ = 'pagamentos'
    id = Column(Integer, primary_key=True)
    colaborador_id = Column(Integer)
    salario = Column(Float)
    vale_refeicao = Column(Float)
    data_pagamento = Column(Date)

def create_app():
    """Criar e configurar a aplicação Flask."""
    config = load_config()
    app = Flask(__name__)
    app.config['DEBUG'] = config['flask'].get('debug', True)

    # Configuração do banco de dados
    DATABASE_URI = config['database']['sqlite']['database_uri']
    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    @app.route('/')
    def index():
        """Renderizar a página inicial."""
        return render_template('index.html')

    @app.route('/api/colaboradores')
    def colaboradores():
        """Retornar a lista de colaboradores em formato JSON."""
        try:
            colaboradores_list = session.query(Colaborador).all()
            result = [{'nome': c.nome, 'cpf': c.cpf} for c in colaboradores_list]
            return jsonify(result)
        except Exception as e:
            logging.error(f"Erro ao buscar colaboradores: {e}")
            return jsonify({'error': 'Erro ao buscar colaboradores'}), 500

    @app.route('/api/pagamentos', methods=['POST'])
    def add_pagamento():
        """Adicionar um pagamento ao banco de dados."""
        data = request.json
        try:
            colaborador = session.query(Colaborador).filter_by(cpf=data['cpf']).first()
            if not colaborador:
                return jsonify({'error': 'Colaborador não encontrado'}), 404
            pagamento = Pagamento(
                colaborador_id=colaborador.id,
                salario=data.get('salario', 0),
                vale_refeicao=data.get('vale_refeicao', 0),
                data_pagamento=data['data_pagamento']
            )
            session.add(pagamento)
            session.commit()
            return jsonify({'message': 'Pagamento adicionado com sucesso!'}), 201
        except Exception as e:
            logging.error(f"Erro ao adicionar pagamento: {e}")
            return jsonify({'error': 'Erro ao adicionar pagamento'}), 500

    return app

def train_tensorflow_model():
    """Treinar um modelo de aprendizado de máquina com TensorFlow."""
    try:
        df = pd.read_csv('dados.csv')
        X = df[['feature1', 'feature2']].values
        y = df['target'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        model = Sequential([
            Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
            Dense(64, activation='relu'),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.2)
        loss = model.evaluate(X_test, y_test)
        logging.info(f'Test loss: {loss}')
        model.save('modelo_tensorflow.h5')
    except Exception as e:
        logging.error(f"Erro ao treinar o modelo TensorFlow: {e}")

def train_pytorch_model():
    """Treinar um modelo de aprendizado de máquina com PyTorch."""
    try:
        df = pd.read_csv('dados.csv')
        X = df[['feature1', 'feature2']].values
        y = df['target'].values

        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.float32).view(-1, 1)

        dataset = TensorDataset(X_tensor, y_tensor)
        train_loader = DataLoader(dataset, batch_size=32, shuffle=True)

        class SimpleNN(nn.Module):
            def __init__(self):
                super(SimpleNN, self).__init__()
                self.fc1 = nn.Linear(2, 64)
                self.fc2 = nn.Linear(64, 64)
                self.fc3 = nn.Linear(64, 1)

            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = torch.relu(self.fc2(x))
                x = self.fc3(x)
                return x

        model = SimpleNN()
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        for epoch in range(10):
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

            logging.info(f'Epoch {epoch+1}, Loss: {loss.item()}')

        torch.save(model.state_dict(), 'modelo_pytorch.pth')
    except Exception as e:
        logging.error(f"Erro ao treinar o modelo PyTorch: {e}")

def enviar_pagamento_ao_banco_santander(pagamentos):
    """Enviar pagamento para o Banco Santander."""
    try:
        config = load_config()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["api_keys"]["santander"]}'
        }
        for _, row in pagamentos.iterrows():
            payload = {
                'cpf': row['cpf'],
                'valor': row['salario'],
                'descricao': 'Salário'
            }
            response = requests.post('https://api.santander.com.br/v1/pagamentos', headers=headers, json=payload)
            if response.status_code == 200:
                logging.info(f'Pagamento realizado com sucesso para {row["nome"]}')
            else:
                logging.error(f'Erro ao realizar pagamento para {row["nome"]}: {response.text}')
    except Exception as e:
        logging.error(f"Erro ao enviar pagamento ao Banco Santander: {e}")

def enviar_vale_refeicao_ao_ifood_beneficios(pagamentos):
    """Enviar vale refeição para o iFood Benefícios."""
    try:
        config = load_config()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["api_keys"]["ifood"]}'
        }
        for _, row in pagamentos.iterrows():
            payload = {
                'cpf': row['cpf'],
                'valor': row['vale_refeicao'],
                'descricao': 'Vale Refeição/Alimentação'
            }
            response = requests.post('https://api.ifood.com.br/v1/beneficios', headers=headers, json=payload)
            if response.status_code == 200:
                logging.info(f'Vale refeição/alimentação realizado com sucesso para {row["nome"]}')
            else:
                logging.error(f'Erro ao realizar vale refeição/alimentação para {row["nome"]}: {response.text}')
    except Exception as e:
        logging.error(f"Erro ao enviar vale refeição ao iFood Benefícios: {e}")

def setup_database():
    """Configurar o banco de dados e inserir dados."""
    try:
        config = load_config()
        DATABASE_URI = config['database']['sqlite']['database_uri']
        engine = create_engine(DATABASE_URI)
        Base.metadata.create_all(engine)

        connection = sqlite3.connect('datacamp_python.db')
        cursor = connection.cursor()

        # Criar tabelas
        cursor.execute('''CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            cpf TEXT UNIQUE,
            salario REAL,
            vale_refeicao REAL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY,
            colaborador_id INTEGER,
            salario REAL,
            vale_refeicao REAL,
            data_pagamento DATE,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores (id)
        )''')
        connection.commit()

        # Inserir dados
        df = pd.read_csv('dados.csv')
        for _, row in df.iterrows():
            cursor.execute("INSERT OR IGNORE INTO colaboradores (nome, cpf, salario, vale_refeicao) VALUES (?, ?, ?, ?)",
                            (row['nome'], row['cpf'], row.get('salario', 0), row.get('vale_refeicao', 0)))
        connection.commit()
        connection.close()
    except Exception as e:
        logging.error(f"Erro ao configurar o banco de dados: {e}")

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('Minha Biblioteca Interativa')

        btn = QPushButton('Executar', self)
        btn.move(100, 80)
        btn.clicked.connect(self.on_click)

        self.show()

    def on_click(self):
        try:
            setup_database()
            train_tensorflow_model()
            train_pytorch_model()
            label = QLabel('Processo concluído!', self)
            label.move(100, 120)
            label.setFont(QFont('Arial', 12))
            label.show()
        except Exception as e:
            logging.error(f"Erro ao executar processo: {e}")
            error_label = QLabel('Erro ao executar processo.', self)
            error_label.move(100, 120)
            error_label.setFont(QFont('Arial', 12))
            error_label.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()

    # Executar o servidor Flask em uma thread separada
    flask_app = create_app()

    def run_flask():
        flask_app.run(host='0.0.0.0', port=5000)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    sys.exit(app.exec_())
