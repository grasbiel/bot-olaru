import os
import random
import asyncio
import requests
import redis
import structlog
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from agno.agent import Agent
from agno.models.groq import Groq
from agno.db.postgres import PostgresDb
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

# Nova URL da API Java
JAVA_API_URL = os.getenv("JAVA_API_URL", "http://localhost:8080/api/v1")

# Dados do Postgres para o Histórico (Agno ainda usa DB direto para persistência de sessão)
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
storage = PostgresDb(session_table="agent_sessions", db_url=DB_URL)

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
    """Agora via API REST Java."""
    try:
        payload = {"nome": nome, "telefone": telefone, "origem": "Anúncio WhatsApp"}
        response = requests.post(f"{JAVA_API_URL}/clientes", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        return None
    except Exception as e:
        logger.error("erro_api_salvar_cliente", erro=str(e))
        return None

# --- SKILLS DA IA ---

def buscar_dados_cliente(telefone: str) -> str:
    """Busca informações de um cliente pelo número de telefone via API REST.
    
    Args:
        telefone (str): Telefone do cliente (apenas dígitos). Ex: '55988887777'.
    """
    logger.info("tool_call", tool="buscar_dados_cliente", telefone=telefone)
    try:
        response = requests.get(f"{JAVA_API_URL}/clientes/telefone/{telefone}", timeout=10)
        if response.status_code == 200:
            dados = response.json()
            return f"Cliente: {dados.get('nome')} (ID: {dados.get('id')})"
        return "Não cadastrado."
    except Exception as e:
        logger.error("skill_buscar_cliente_api", erro=str(e))
        return "Erro ao buscar dados na API."

def verificar_estoque(maquina_nome: str) -> str:
    """Consulta se temos uma máquina específica em estoque via API REST.
    
    Args:
        maquina_nome (str): O nome curto do equipamento. EX: 'betoneira', 'escavadeira', 'andaime'.
    """
    logger.info("tool_call", tool="verificar_estoque", maquina_nome=maquina_nome)
    try:
        response = requests.get(f"{JAVA_API_URL}/maquinas/estoque/{maquina_nome}", timeout=10)
        if response.status_code == 200:
            dados = response.json()
            return f"Máquina: {dados.get('nome')} | Quantidade Disponível: {dados.get('quantidadeDisponivel')}"
        return "Desculpe, não encontrei nenhuma máquina com esse nome em nosso estoque."
    except Exception as e:
        logger.error("skill_estoque_api", erro=str(e))
        return "Erro ao verificar estoque na API."

def consultar_disponibilidade_agenda(data: str, turno: str) -> str:
    """Verifica se há disponibilidade na agenda via API REST.
    
    Args:
        data (str): Data no formato 'AAAA-MM-DD'.
        turno (str): Turno desejado: 'manha', 'tarde' ou 'integral'.
    """
    logger.info("tool_call", tool="consultar_disponibilidade_agenda", data=data, turno=turno)
    try:
        params = {"data": data, "turno": turno}
        response = requests.get(f"{JAVA_API_URL}/visitas/disponibilidade", params=params, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("disponivel"):
                return "Temos horários disponíveis para este período!"
            return "Infelizmente este turno já está com a agenda lotada."
        return "Erro ao consultar agenda."
    except Exception as e:
        logger.error("skill_agenda_api", erro=str(e))
        return "Erro ao consultar agenda via API."

def registrar_visita_tecnica(telefone: str, descricao: str, endereco: str, data: str, turno: str) -> str:
    """Agenda oficialmente uma visita técnica via API REST.
    
    Args:
        telefone (str): Telefone do cliente.
        descricao (str): Detalhes do serviço.
        endereco (str): Endereço da visita.
        data (str): Data 'AAAA-MM-DD'.
        turno (str): 'manha', 'tarde' ou 'integral'.
    """
    logger.info("tool_call", tool="registrar_visita_tecnica", telefone=telefone)
    try:
        payload = {
            "telefone": telefone,
            "descricaoServico": descricao,
            "endereco": endereco,
            "dataVisita": data,
            "turno": turno
        }
        response = requests.post(f"{JAVA_API_URL}/visitas", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            vid = response.json().get("id")
            return f"Agendamento concluído com sucesso! Protocolo da Visita: {vid}"
        elif response.status_code == 400:
            return f"Erro: {response.text}"
        return "Erro ao salvar agendamento no sistema."
    except Exception as e:
        logger.error("skill_registro_visita_api", erro=str(e))
        return "Erro ao conectar com a API de agendamento."

def iniciar_handoff_humano(id_conversa: int, motivo: str) -> str:
    """Transfere a conversa para um atendente humano e pausa o robô."""
    adicionar_etiqueta_chatwoot(id_conversa, "pausar_robo")
    adicionar_etiqueta_chatwoot(id_conversa, f"handoff_{motivo}")
    return "Handoff iniciado. Robô pausado."

# --- AGENTE ---

def criar_agente():
    return Agent(
        model=Groq(id="llama-3.3-70b-versatile", api_key=CHAVE_GROQ), 
        description="Assistente OLARU",
        instructions=[
            "1. Responda uma coisa por vez.",
            "2. Para máquinas, use 'verificar_estoque'.",
            "3. Para agendar visitas, use 'registrar_visita_tecnica'.",
            "4. Para horários de visita, use 'consultar_disponibilidade_agenda'.",
            "5. Se o cliente enviar foto/arquivo ou se você não souber responder, use 'iniciar_handoff_humano'.",
            "6. Seja breve e profissional."
        ],
        tools=[buscar_dados_cliente, verificar_estoque, consultar_disponibilidade_agenda, registrar_visita_tecnica, iniciar_handoff_humano],
        db=storage, 
        add_history_to_context=True,
        num_history_messages=5,
        markdown=False
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
        # Tenta rodar a IA
        resposta = agente_construtora.run(mensagem_cliente, session_id=f"conv_{id_conversa}")
        conteudo_resposta = resposta.content

        # Verificação extra: se a resposta vier vazia ou com erro técnico, usa fallback
        if not conteudo_resposta or "error" in conteudo_resposta.lower() or "failed to call" in conteudo_resposta.lower():
            logger.error("ia_retornou_erro_em_conteudo", conteudo=conteudo_resposta)
            conteudo_resposta = "Desculpe, tive um probleminha técnico ao processar sua solicitação. Mas não se preocupe, já notifiquei nossa equipe e um atendente humano falará com você em breve!"
            adicionar_etiqueta_chatwoot(id_conversa, "erro_ia")
        
        # Simulação de digitação (Escudo Anti-Ban)
        tempo = random.randint(5, 12) # Tempo um pouco menor para melhorar UX
        logger.info("processando_resposta", id_conversa=id_conversa, delay=tempo)
        await asyncio.sleep(tempo)
        
        enviar_mensagem_chatwoot(id_conversa, conteudo_resposta)
        incrementar_contador_mensagens()

    except Exception as e:
        # FALLBACK CRÍTICO: Nunca envia o log 'e' para o cliente
        logger.error("erro_critico_ia", erro=str(e))
        fallback_msg = "Olá! No momento estou passando por uma manutenção rápida. Poderia aguardar um instante ou descrever o que precisa? Um de nossos atendentes já vai te dar atenção total."
        enviar_mensagem_chatwoot(id_conversa, fallback_msg)
        adicionar_etiqueta_chatwoot(id_conversa, "pausar_robo")

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
