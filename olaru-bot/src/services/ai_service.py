import random
import asyncio
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.google import Gemini
from src.config import CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger, DB_URL_AGNO
from src.database import storage, r
from src.services.chatwoot import enviar_mensagem_chatwoot, adicionar_etiqueta_chatwoot
from src.services.utils import verificar_limite_mensagens, incrementar_contador_mensagens
from src.tools.api_tools import (
    buscar_dados_cliente, verificar_estoque, 
    consultar_disponibilidade_agenda, registrar_visita_tecnica, 
    iniciar_handoff_humano
)

def obter_modelo():
    """Retorna o modelo de IA configurado no ambiente."""
    if LLM_PROVIDER == "gemini":
        logger.info("inicializando_llm", provider="gemini", model="gemini-1.5-flash")
        return Gemini(id="gemini-1.5-flash", api_key=GEMINI_API_KEY)
    else:
        logger.info("inicializando_llm", provider="groq", model="llama-3.3-70b-versatile")
        return Groq(id="llama-3.3-70b-versatile", api_key=CHAVE_GROQ)

def criar_agente():
    # Roteiro Estratégico de Qualificação de Leads (SDR)
    script_atendimento = """
    Você é a assistente virtual da OLARU, especializada em construção civil.
    Sua missão é QUALIFICAR o lead através destas fases:
    FASE 1: CONEXÃO (Saudação e Nome/Empresa)
    FASE 2: DESCOBERTA (Obra nova? Reforma? Manutenção urgente?)
    FASE 3: QUALIFICAÇÃO TÉCNICA (Endereço e Cronograma)
    FASE 4: COMPROMETIMENTO (Verificar agenda e Registrar Visita Técnica)
    FASE 5: FECHAMENTO (Handoff para o comercial)
    """

    

    return Agent(
        model=obter_modelo(), 
        description="Especialista em Qualificação de Leads para Construção Civil.",
        instructions=[
            script_atendimento,
            "REGRAS DE OURO:",
            "- Analise o histórico e a memória para saber quem é o cliente e em qual FASE você está.",
            "- Fale como um ESPECIALISTA: use termos como 'canteiro', 'fundação', 'cronograma'.",
            "- Faça apenas UMA pergunta por vez.",
            "- NUNCA informe preços. O consultor enviará o orçamento personalizado.",
        ],
        tools=[buscar_dados_cliente, verificar_estoque, consultar_disponibilidade_agenda, registrar_visita_tecnica, iniciar_handoff_humano],
        db=storage,
        update_memory_on_run=True,
        add_history_to_context=True,
        num_history_messages=12,
        markdown=False
    )

agente_construtora = criar_agente()

async def pensar_e_responder(mensagem_cliente: str, id_conversa: int, telefone: str):
    if not verificar_limite_mensagens():
        logger.warning("limite_atingido", telefone=telefone)
        return

    try:
        # Passamos o telefone como user_id para que o Agno vincule a memória a este cliente específico
        resposta = agente_construtora.run(
            mensagem_cliente, 
            session_id=f"conv_{id_conversa}", 
            user_id=telefone
        )
        conteudo_resposta = resposta.content

        if not conteudo_resposta or "error" in conteudo_resposta.lower():
            conteudo_resposta = "Desculpe, tive um probleminha técnico. Um atendente falará com você em breve!"
            adicionar_etiqueta_chatwoot(id_conversa, "erro_ia")
        
        tempo = random.randint(5, 12)
        await asyncio.sleep(tempo)
        
        enviar_mensagem_chatwoot(id_conversa, conteudo_resposta)
        incrementar_contador_mensagens()

    except Exception as e:
        logger.error("erro_critico_ia", erro=str(e))
        fallback_msg = "Olá! No momento estou passando por uma manutenção rápida. Um de nossos atendentes já vai te dar atenção."
        enviar_mensagem_chatwoot(id_conversa, fallback_msg)
        adicionar_etiqueta_chatwoot(id_conversa, "pausar_robo")
