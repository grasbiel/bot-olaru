import redis
from agno.db.postgres import PostgresDb
from agno.memory.db.postgres import PostgresMemoryDb
from src.config import (
    REDIS_HOST, REDIS_PORT, REDIS_PASS,
    DB_URL_AGNO
)

# Conexão Global Redis
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True
)

# Armazenamento Persistente de Sessões (histórico de conversa por session_id)
storage = PostgresDb(
    session_table="agent_sessions",
    db_url=DB_URL_AGNO
)

# Memória de Longo Prazo (fatos extraídos pelo agente, vinculados ao user_id/telefone)
memory_db = PostgresMemoryDb(
    table_name="agent_memory",
    db_url=DB_URL_AGNO
)
