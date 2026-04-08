import redis
from agno.db.postgres import PostgresDb
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

# PostgresDb unificado — sessões (session_table) + memória de longo prazo (memory_table)
storage = PostgresDb(
    session_table="agent_sessions",
    memory_table="agent_memory",
    db_url=DB_URL_AGNO
)
