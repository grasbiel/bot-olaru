import random
import asyncio
import requests
from typing import List, Optional
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.google import Gemini
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.text_reader import TextReader
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.pgvector import PgVector

from src.config import (
    CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger, 
    DB_URL_AGNO, EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE
)
from src.database import storage, r
from src.services.chatwoot import enviar_mensagem_chatwoot, adicionar_etiqueta_chatwoot, iniciar_handoff_humano
from src.services.utils import verificar_limite_mensagens, incrementar_contador_mensagens
from src.tools.api_tools import (
    buscar_dados_cliente, verificar_estoque, 
    consultar_disponibilidade_agenda, registrar_visita_tecnica,
    acionar_handoff_humano, classificar_lead
)

# --- Configuração do Conhecimento (RAG) ---
knowledge_base = Knowledge(
    vector_db=PgVector(
        table_name="conhecimento_empresa",
        db_url=DB_URL_AGNO,
        embedder=FastEmbedEmbedder(),
    ),
)

def carregar_conhecimento():
    """Tenta carregar o conhecimento RAG do diretório knowledge/"""
    try:
        # No Agno, usamos insert com skip_if_exists para carregar arquivos locais
        knowledge_base.insert(path="knowledge/", reader=TextReader(), skip_if_exists=True)
        logger.info("knowledge_base_loaded")
    except Exception as e:
        logger.warning("knowledge_base_load_error", error=str(e))

# Executa carregamento ao iniciar
carregar_conhecimento()

def obter_modelo():
    """Retorna o modelo de IA baseado no provider configurado."""
    if LLM_PROVIDER == "gemini":
        return Gemini(id="gemini-2.0-flash", api_key=GEMINI_API_KEY)
    return Groq(id="llama-3.3-70b-versatile", api_key=CHAVE_GROQ)

def simular_presenca(telefone: str, typing: bool = True):
    """Envia estado de digitação via Evolution API (Anti-Ban)."""
    if not all([EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE]):
        return

    url = f"{EVOLUTION_API_URL}/chat/sendPresence/{EVOLUTION_INSTANCE}"
    presence = "composing" if typing else "available"
    try:
        requests.post(
            url,
            json={"number": telefone, "presence": presence, "delay": 0},
            headers={"apikey": EVOLUTION_API_KEY},
            timeout=5
        )
    except Exception as e:
        logger.error("presence_error", error=str(e))

def criar_agente() -> Agent:
    """Configura o Agente especializado com ferramentas e instruções."""
    
    instrucoes = """
    VOCÊ É A ASSISTENTE VIRTUAL DA CONSTRUTORA OLARU.
    
    DIRETRIZ DE ABORDAGEM (LIDERANÇA DE MERCADO):
    - Se for o primeiro contato ou etiqueta 'lead_novo': Inicie com "Olá! Somos da Construtora OLARU. Estamos há 18 anos no mercado e somos líderes em reformas e construções de todos os tipos. Como podemos ajudar na sua obra hoje?"
    - Use o conhecimento da 'knowledge_base' para detalhes técnicos da empresa.
    
    ESTRATÉGIA SDR (QUALIFICAÇÃO):
    - FASE 1: CONEXÃO (Acolhimento e institucional).
    - FASE 2: DESCOBERTA (O que o cliente precisa? Obra? Reforma? Manutenção? Locação de Máquinas?).
    - FASE 3: TÉCNICA (Endereço e data pretendida).
    - FASE 4: AGENDAMENTO (Usar agenda e registrar visita).
    - FASE 5: HANDOFF (Sinalizar que o comercial assumirá).

    REGRAS DE OURO:
    1. Apenas UMA pergunta por vez.
    2. Linguagem técnica de construção ('canteiro', 'alvenaria', 'cronograma').
    3. NUNCA invente preços.
    4. Atualize o status do lead sempre que houver progresso (ferramenta classificar_lead).
    5. Se o cliente estiver confuso ou pedir humano, use acionar_handoff_humano.
    """

    return Agent(
        model=obter_modelo(),
        description="Especialista em Qualificação de Leads - Construtora OLARU.",
        instructions=[instrucoes],
        tools=[
            buscar_dados_cliente, verificar_estoque, 
            consultar_disponibilidade_agenda, registrar_visita_tecnica,
            acionar_handoff_humano, classificar_lead
        ],
        knowledge=knowledge_base,
        search_knowledge=True,
        db=storage,
        update_memory_on_run=True,
        add_history_to_context=True,
        num_history_messages=10,
        markdown=False
    )

# Singleton do Agente
agente_olara = criar_agente()

async def pensar_e_responder(mensagem_cliente: str, id_conversa: int, telefone: str, etiquetas: List[str] = None):
    """Loop principal de processamento da resposta."""
    if not verificar_limite_mensagens():
        logger.warning("rate_limit_reached", phone=telefone)
        return

    try:
        # 1. Ativa 'Digitando...'
        simular_presenca(telefone, True)

        # 2. Prepara Contexto Adicional
        contexto_etiquetas = f"\nETIQUETAS: {', '.join(etiquetas) if etiquetas else 'nenhuma'}"
        prompt_final = f"{mensagem_cliente}\n\n[CONTEXTO OPERACIONAL: ConversaID={id_conversa}, {contexto_etiquetas}]"

        # 3. Executa a IA
        # Rodar em thread para não bloquear o loop async (agno sync por padrão)
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            None, 
            lambda: agente_olara.run(prompt_final, session_id=f"conv_{id_conversa}", user_id=telefone)
        )
        conteudo = resposta.content

        # 4. Fallback se a IA falhar ou retornar vazio
        if not conteudo:
            raise ValueError("ia_returned_empty")

        # 5. Delay Humano Realista (Anti-Ban)
        # 15 caracteres por segundo + variação aleatória
        typing_time = max(4, min(12, len(conteudo) / 15 + random.uniform(1, 3)))
        await asyncio.sleep(typing_time)

        # 6. Envio e Finalização
        enviar_mensagem_chatwoot(id_conversa, conteudo)
        simular_presenca(telefone, False)
        incrementar_contador_mensagens()

    except Exception as e:
        logger.error("agent_loop_error", error=str(e), conversation_id=id_conversa)
        fallback = "Olá! Tive uma instabilidade momentânea, mas já notifiquei nossa equipe para te atender pessoalmente."
        enviar_mensagem_chatwoot(id_conversa, fallback)
        iniciar_handoff_humano(id_conversa, "critical_bot_error")
