from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

Base = declarative_base()

class Colaborador(Base):
    __tablename__ = 'colaboradores'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(11), unique=True, nullable=False)
    salario = Column(Float, nullable=False)
    vale_refeicao = Column(Float, nullable=False)
    
    pagamentos = relationship('Pagamento', back_populates='colaborador')

    def __repr__(self):
        return f"<Colaborador(id={self.id}, nome={self.nome}, cpf={self.cpf})>"

class Pagamento(Base):
    __tablename__ = 'pagamentos'
    id = Column(Integer, primary_key=True)
    colaborador_id = Column(Integer, ForeignKey('colaboradores.id'), nullable=False)
    salario = Column(Float, nullable=False)
    vale_refeicao = Column(Float, nullable=False)
    data_pagamento = Column(Date, nullable=False)
    
    colaborador = relationship('Colaborador', back_populates='pagamentos')

    def __repr__(self):
        return f"<Pagamento(id={self.id}, colaborador_id={self.colaborador_id}, data_pagamento={self.data_pagamento})>"

def get_engine():
    with open('config.json') as config_file:
        config = json.load(config_file)
    DATABASE_URI = config['database']['sqlite']['database_uri']
    engine = create_engine(DATABASE_URI)
    return engine

def create_all_tables():
    engine = get_engine()
    Base.metadata.create_all(engine)
