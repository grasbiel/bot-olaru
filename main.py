import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
import requests
import psycopg2
import random
import asyncio
from agno.agent import Agent
from agno.models.groq import Groq
from groq import Groq as GroqClient

# Carregar variáveis do arquivo .env
load_dotenv()

app = FastAPI()

# Configurações
CHATWOOT_URL = os.getenv("CHATWOOT_URL")
CHATWOOT_BOT_TOKEN = os.getenv("CHATWOOT_BOT_TOKEN")
ID_DA_CONTA = os.getenv("ID_DA_CONTA")
CHAVE_GROQ = os.getenv("CHAVE_GROQ")
WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT")

groq_client = GroqClient(api_key=CHAVE_GROQ)

# --- FUNÇÕES DE APOIO ---

def obter_endereco_por_coordenadas(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "OlaruBot/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get("display_name", f"{lat}, {lon}")
    except:
        return f"Lat: {lat}, Lon: {lon}"

def transcrever_audio(url_audio):
    try:
        response = requests.get(url_audio)
        nome_arquivo = f"temp_{random.randint(1000, 9999)}.ogg"
        with open(nome_arquivo, "wb") as f: f.write(response.content)
        with open(nome_arquivo, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(nome_arquivo, audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="pt"
            )
        os.remove(nome_arquivo)
        return transcription
    except:
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
    except:
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
    except:
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
    except:
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
    except:
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
    except:
        return "Erro registro."

def iniciar_handoff_humano(id_conversa: int, motivo: str) -> str:
    adicionar_etiqueta_chatwoot(id_conversa, "pausar_robo")
    adicionar_etiqueta_chatwoot(id_conversa, f"handoff_{motivo}")
    return "Handoff iniciado. Robô pausado."

# --- AGENTE ---

agente_construtora = Agent(
    model=Groq(id="llama-3.3-70b-versatile", api_key=CHAVE_GROQ), 
    description="Assistente da Construtora OLARU.",
    instructions=[
        "Faça apenas UMA pergunta por vez.",
        "NUNCA invente disponibilidade.",
        "Se o cliente enviar IMAGEM ou DOCUMENTO: Informe que um atendente humano analisará o arquivo e use a ferramenta de handoff.",
        "Se o cliente enviar localização, confirme o endereço.",
        "Se o cliente enviar áudio, use a transcrição recebida."
    ],
    tools=[buscar_dados_cliente, verificar_estoque, consultar_disponibilidade_agenda, registrar_visita_tecnica, iniciar_handoff_humano],
    markdown=True
)

def adicionar_etiqueta_chatwoot(id_conversa, etiqueta):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/labels"
    requests.post(url, json={"labels": [etiqueta]}, headers={"api_access_token": CHATWOOT_BOT_TOKEN})

async def pensar_e_responder(mensagem_cliente: str, id_conversa: int, telefone: str):
    contexto = f"[SISTEMA: Tel={telefone}, ID={id_conversa}]\nCliente: {mensagem_cliente}"
    resposta = agente_construtora.run(contexto)
    tempo = random.randint(10, 20)
    print(f"Aguardando {tempo}s...")
    await asyncio.sleep(tempo)
    enviar_mensagem_chatwoot(id_conversa, resposta.content)

@app.post("/webhook")
async def receber_mensagem(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Webhook-Secret")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET: raise HTTPException(status_code=403)

    dados = await request.json()
    if dados.get("event") == "message_created" and dados.get("message_type") == "incoming":
        
        mensagem_cliente = dados.get("content", "")
        id_conversa = dados.get("conversation", {}).get("id")
        nome_contato = dados.get("sender", {}).get("name", "").upper()
        telefone_contato = dados.get("sender", {}).get("phone_number", "")
        etiquetas = dados.get("conversation", {}).get("labels", [])
        attachments = dados.get("attachments", [])

        # Processar Anexos
        for anexo in attachments:
            tipo = anexo.get("file_type")
            if tipo == "audio":
                transcricao = transcrever_audio(anexo.get("data_url"))
                if transcricao: mensagem_cliente = f"[ÁUDIO]: {transcricao}"
            elif tipo == "location":
                lat, lon = anexo.get("coordinates_lat"), anexo.get("coordinates_long")
                if lat and lon:
                    endereco = obter_endereco_por_coordenadas(lat, lon)
                    mensagem_cliente = f"[LOCALIZAÇÃO]: {endereco}"
            elif tipo in ["image", "file"]:
                mensagem_cliente = f"[{tipo.upper()} RECEBIDA]: O cliente enviou um arquivo para análise técnica."

        if "GROUP" in nome_contato or "pausar_robo" in etiquetas: return {"status": "ignorado"}

        msg_min = mensagem_cliente.lower()
        if "robo_ativo" in etiquetas or "anúncio" in msg_min or "anuncio" in msg_min:
            if "robo_ativo" not in etiquetas:
                salvar_cliente_no_banco(nome_contato, telefone_contato)
                adicionar_etiqueta_chatwoot(id_conversa, "robo_ativo")
            background_tasks.add_task(pensar_e_responder, mensagem_cliente, id_conversa, telefone_contato)

    return {"status": "recebido"}

def enviar_mensagem_chatwoot(id_conversa, texto):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/messages"
    requests.post(url, json={"content": texto, "message_type": "outgoing"}, headers={"api_access_token": CHATWOOT_BOT_TOKEN})
