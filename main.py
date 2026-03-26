import os
import random
import asyncio
import requests
import psycopg2
import redis
import structlog
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from agno.agent import Agent
from agno.models.groq import Groq
from agno.storage.agent.postgres import PostgresAgentStorage
from groq import Groq as GroqClient

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração de Logging Estruturado
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "online", "message": "Olaru Bot is running!"}

# Configurações
CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_BOT_TOKEN = os.getenv("CHATWOOT_BOT_TOKEN")
ID_DA_CONTA = os.getenv("ID_DA_CONTA")
CHAVE_GROQ = os.getenv("CHAVE_GROQ")
WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET")
NUMERO_TESTE = os.getenv("NUMERO_TESTE") 

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASS = os.getenv("REDIS_PASS")

# URL de Conexão para o Histórico (SQLAlchemy format)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Inicialização de Clientes
groq_client = GroqClient(api_key=CHAVE_GROQ)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)

# Armazenamento de Histórico no Postgres
storage = PostgresAgentStorage(table_name="agent_sessions", db_url=DB_URL)

# --- FUNÇÕES DE APOIO ---

def verificar_limite_mensagens():
    """Verifica se o limite diário de mensagens (Escudo Anti-Ban) foi atingido."""
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"msgs_enviadas:{hoje}"
        contagem = r.get(chave)
        if contagem and int(contagem) >= 200:
            return False
        return True
    except Exception as e:
        logger.error("erro_redis_limite", erro=str(e))
        return True 

def incrementar_contador_mensagens():
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"msgs_enviadas:{hoje}"
        r.incr(chave)
        r.expire(chave, 86400)
    except Exception as e:
        logger.error("erro_redis_incr", erro=str(e))

def obter_endereco_por_coordenadas(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "OlaruBot/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get("display_name", f"{lat}, {lon}")
    except Exception as e:
        logger.error("erro_coordenadas", erro=str(e))
        return f"Lat: {lat}, Lon: {lon}"

def transcrever_audio(url_audio):
    nome_arquivo = f"temp_{random.randint(1000, 9999)}.ogg"
    try:
        response = requests.get(url_audio, timeout=20)
        with open(nome_arquivo, "wb") as f: 
            f.write(response.content)
        
        with open(nome_arquivo, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(nome_arquivo, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="pt"
            )
        
        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)
        return transcription
    except Exception as e:
        logger.error("erro_transcricao_detalhado", erro=str(e), url=url_audio)
        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)
        return None

def salvar_cliente_no_banco(nome, telefone):
    try:
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        sql = "INSERT INTO clientes (nome, telefone, origem) VALUES (%s, %s, 'Anúncio WhatsApp') ON CONFLICT (telefone) DO UPDATE SET nome = EXCLUDED.nome RETURNING id"
        cursor.execute(sql, (nome, telefone))
        cid = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return cid
    except Exception as e:
        logger.error("erro_banco_cliente", erro=str(e))
        return None

# --- SKILLS DA IA ---

def buscar_dados_cliente(telefone: str) -> str:
    try:
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        cursor.execute("SELECT id, nome FROM clientes WHERE telefone = %s", (telefone,))
        res = cursor.fetchone()
        cursor.close()
        conexao.close()
        return f"Cliente: {res[1]} (ID: {res[0]})" if res else "Não cadastrado."
    except Exception as e:
        logger.error("skill_buscar_cliente", erro=str(e))
        return "Erro ao buscar."

def verificar_estoque(maquina_nome: str) -> str:
    try:
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        cursor.execute("SELECT nome, quantidade_disponivel FROM maquinas WHERE nome ILIKE %s", (f"%{maquina_nome}%",))
        res = cursor.fetchone()
        cursor.close()
        conexao.close()
        return f"Máquina: {res[0]} | Qtd: {res[1]}" if res else "Não encontrada."
    except Exception as e:
        logger.error("skill_estoque", erro=str(e))
        return "Erro estoque."

def consultar_disponibilidade_agenda(data: str, turno: str) -> str:
    try:
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        cursor.execute("SELECT COUNT(*) FROM visitas_tecnicas WHERE data_visita = %s AND turno = %s AND status != 'cancelada'", (data, turno))
        agendados = cursor.fetchone()[0]
        cursor.close()
        conexao.close()
        return "Disponível" if agendados < 3 else "Lotado"
    except Exception as e:
        logger.error("skill_agenda", erro=str(e))
        return "Erro agenda."

def registrar_visita_tecnica(telefone: str, descricao: str, endereco: str, data: str, turno: str) -> str:
    try:
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        cursor.execute("SELECT id FROM clientes WHERE telefone = %s", (telefone,))
        cid = cursor.fetchone()[0]
        sql = "INSERT INTO visitas_tecnicas (cliente_id, descricao_servico, endereco, data_visita, turno, status) VALUES (%s, %s, %s, %s, %s, 'pendente') RETURNING id"
        cursor.execute(sql, (cid, descricao, endereco, data, turno))
        vid = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return f"Registrada! Protocolo: {vid}"
    except Exception as e:
        logger.error("skill_registro_visita", erro=str(e))
        return "Erro registro."

def iniciar_handoff_humano(id_conversa: int, motivo: str) -> str:
    adicionar_etiqueta_chatwoot(id_conversa, "pausar_robo")
    adicionar_etiqueta_chatwoot(id_conversa, f"handoff_{motivo}")
    return "Handoff iniciado. Robô pausado."

# --- AGENTE ---

def criar_agente():
    return Agent(
        model=Groq(id="llama-3.3-70b-versatile", api_key=CHAVE_GROQ), 
        description="Assistente da Construtora OLARU.",
        instructions=[
            "Faça apenas UMA pergunta por vez.",
            "NUNCA invente disponibilidade. Use sempre as ferramentas.",
            "Se o cliente enviar IMAGEM ou DOCUMENTO: Informe que um atendente humano analisará o arquivo e use a ferramenta de handoff.",
            "Se o cliente enviar localização, confirme o endereço.",
            "Se o cliente enviar áudio, use a transcrição recebida.",
            "Mantenha o tom profissional e cordial."
        ],
        tools=[buscar_dados_cliente, verificar_estoque, consultar_disponibilidade_agenda, registrar_visita_tecnica, iniciar_handoff_humano],
        storage=storage, # Habilita salvamento de histórico no Postgres
        add_history_to_context=True,
        num_history_messages=8,
        markdown=True
    )

# Agente global 
agente_construtora = criar_agente()

def adicionar_etiqueta_chatwoot(id_conversa, etiqueta):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/labels"
    try:
        requests.post(url, json={"labels": [etiqueta]}, headers={"api_access_token": CHATWOOT_BOT_TOKEN})
    except Exception as e:
        logger.error("erro_etiqueta_chatwoot", erro=str(e))

async def pensar_e_responder(mensagem_cliente: str, id_conversa: int, telefone: str):
    if not verificar_limite_mensagens():
        logger.warning("limite_atingido", telefone=telefone)
        return

    try:
        # O session_id permite que o Agno mantém o histórico específico desta conversa
        resposta = agente_construtora.run(mensagem_cliente, session_id=f"conv_{id_conversa}")
        
        # Simulação de digitação (Escudo Anti-Ban)
        tempo = random.randint(10, 20)
        logger.info("processando_resposta", id_conversa=id_conversa, delay=tempo)
        await asyncio.sleep(tempo)
        
        enviar_mensagem_chatwoot(id_conversa, resposta.content)
        incrementar_contador_mensagens()
    except Exception as e:
        logger.error("erro_ia", erro=str(e))

@app.post("/webhook")
async def receber_mensagem(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Webhook-Secret")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET: 
        logger.warning("webhook_auth_failed", recebido=secret, esperado=WEBHOOK_SECRET)
        raise HTTPException(status_code=403, detail="Webhook Secret Inválido")

    try:
        dados = await request.json()
    except:
        return {"status": "erro_json"}
    
    msg_id = dados.get("id")
    if msg_id:
        try:
            if r.exists(f"msg_processada:{msg_id}"):
                return {"status": "duplicado"}
            r.setex(f"msg_processada:{msg_id}", 600, "1")
        except:
            pass 

    if dados.get("event") == "message_created" and dados.get("message_type") == "incoming":
        
        # Garante que mensagem_cliente nunca seja None
        mensagem_cliente = dados.get("content") or ""
        id_conversa = dados.get("conversation", {}).get("id")
        nome_contato = dados.get("sender", {}).get("name", "").upper()
        telefone_contato = dados.get("sender", {}).get("phone_number", "").replace("+", "")
        etiquetas = dados.get("conversation", {}).get("labels", [])
        
        if NUMERO_TESTE and telefone_contato != NUMERO_TESTE:
            logger.info("ignorado_pelo_filtro_teste", telefone=telefone_contato)
            return {"status": "ignorado_teste"}

        attachments = dados.get("attachments", [])

        for anexo in attachments:
            tipo = anexo.get("file_type")
            if tipo == "audio":
                logger.info("processando_audio", url=anexo.get("data_url"))
                transcricao = transcrever_audio(anexo.get("data_url"))
                if transcricao: 
                    mensagem_cliente = f"[ÁUDIO]: {transcricao}"
                else:
                    logger.error("falha_transcricao_audio")
                    mensagem_cliente = "[ERRO]: Não foi possível transcrever o áudio."
            elif tipo == "location":
                lat, lon = anexo.get("coordinates_lat"), anexo.get("coordinates_long")
                if lat and lon:
                    endereco = obter_endereco_por_coordenadas(lat, lon)
                    mensagem_cliente = f"[LOCALIZAÇÃO]: {endereco}"
            elif tipo in ["image", "file"]:
                mensagem_cliente = f"[{tipo.upper()} RECEBIDA]: O cliente enviou um arquivo para análise técnica."

        if "GROUP" in nome_contato or "pausar_robo" in etiquetas: 
            return {"status": "ignorado"}

        if not mensagem_cliente:
            logger.warning("mensagem_vazia", id_conversa=id_conversa)
            return {"status": "sem_conteudo"}

        msg_min = mensagem_cliente.lower()
        if "robo_ativo" in etiquetas or "anúncio" in msg_min or "anuncio" in msg_min:
            if "robo_ativo" not in etiquetas:
                salvar_cliente_no_banco(nome_contato, telefone_contato)
                adicionar_etiqueta_chatwoot(id_conversa, "robo_ativo")
            
            logger.info("nova_mensagem", id_conversa=id_conversa, telefone=telefone_contato)
            background_tasks.add_task(pensar_e_responder, mensagem_cliente, id_conversa, telefone_contato)

    return {"status": "recebido"}

def enviar_mensagem_chatwoot(id_conversa, texto):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/messages"
    try:
        requests.post(url, json={"content": texto, "message_type": "outgoing"}, headers={"api_access_token": CHATWOOT_BOT_TOKEN})
    except Exception as e:
        logger.error("erro_envio_chatwoot", erro=str(e))
