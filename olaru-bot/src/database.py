import redis
from agno.db.postgres import PostgresDb
from src.config import (
    REDIS_HOST, REDIS_PORT, REDIS_PASS, 
    DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
)

# Conexão Redis
r = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASS, 
    decode_responses=True
)

# URL SQLAlchemy utilizando psycopg (recomendado pela documentação Agno)
DB_URL_AGNO = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Armazenamento Persistente no Postgres (Agno)
# Separamos as tabelas de Sessão (Histórico) e Memória (Fatos do usuário)
storage = PostgresDb(
    session_table="agent_sessions",
    db_url=DB_URL_AGNO
)
