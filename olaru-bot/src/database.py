import redis
from agno.db.postgres import PostgresDb
from src.config import REDIS_HOST, REDIS_PORT, REDIS_PASS, DB_URL

# Conexão Redis
r = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASS, 
    decode_responses=True
)

# Armazenamento de Histórico no Postgres (Agno)
storage = PostgresDb(session_table="agent_sessions", db_url=DB_URL)
