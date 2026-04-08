import os
import structlog
import redis
from dotenv import load_dotenv

# Carrega .env do diretório raiz do projeto ou olaru-bot
load_dotenv()

# Configuração de Logging Estruturado (Consistente para toda a aplicação)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# --- Configurações do Chatwoot ---
CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_BOT_TOKEN = os.getenv("CHATWOOT_BOT_TOKEN")
ID_DA_CONTA = os.getenv("ID_DA_CONTA")

# --- Configurações da IA ---
# Opções: "groq", "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
CHAVE_GROQ = os.getenv("CHAVE_GROQ")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Segurança Webhook (Evolution API) ---
WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET")

# --- Evolution API (Anti-Ban / Simulação de Presença) ---
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")

# --- URL da API Java (Painel Administrativo) ---
JAVA_API_URL = os.getenv("JAVA_API_URL", "http://api:8080/api/v1")

# --- Banco de Dados PostgreSQL ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "db_construtora")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "72d889c22343e475218d")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- Redis (Dedup, Cache e Rate Limit) ---
REDIS_HOST = os.getenv("REDIS_HOST", "db-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASS = os.getenv("REDIS_PASS")

# URLs de conexão formatadas
DB_URL_AGNO = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
