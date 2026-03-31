import os
import structlog
import redis
from dotenv import load_dotenv
from groq import Groq as GroqClient

load_dotenv()

# Configuração de Logging Estruturado
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configurações do Chatwoot
CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_BOT_TOKEN = os.getenv("CHATWOOT_BOT_TOKEN")
ID_DA_CONTA = os.getenv("ID_DA_CONTA")

# Configurações da IA
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") # Opções: "groq", "gemini"
CHAVE_GROQ = os.getenv("CHAVE_GROQ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicialização do Groq (mantida para compatibilidade se necessário)
groq_client = GroqClient(api_key=CHAVE_GROQ) if CHAVE_GROQ else None

# Segurança Webhook
WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET")

# Configuração de Filtro de Teste
NUMERO_TESTE = os.getenv("NUMERO_TESTE") 

# URL da API Java (Spring Boot)
JAVA_API_URL = os.getenv("JAVA_API_URL", "http://api:8080/api/v1")

# Banco de Dados
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "db_construtora")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "72d889c22343e475218d")
DB_PORT = os.getenv("DB_PORT", "5432")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "db-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASS = os.getenv("REDIS_PASS")

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True
)

# URL SQLAlchemy (psycopg2 para scripts) e Agno (psycopg para o framework)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_URL_AGNO = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
