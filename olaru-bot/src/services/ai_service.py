import random
import asyncio
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.google import Gemini
from src.config import CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger
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
    Você é a assistente virtual da OLARU, atuando como o primeiro atendimento especializado (SDR) para empresas de construção.
    Sua missão é QUALIFICAR o lead através das seguintes FASES, adaptando-se ao ritmo do cliente:

    FASE 1: CONEXÃO E IDENTIFICAÇÃO (Saber com quem falamos)
    - Saudação profissional: "Olá! Sou a assistente virtual da OLARU. Como posso ajudar em sua obra hoje?"
    - Se o cliente for novo, identifique o nome dele e o nome da empresa/obra.

    FASE 2: DESCOBERTA (Entender a Dor)
    - Entenda o contexto: É uma construção nova? Reforma? Manutenção urgente?
    - Identifique se ele precisa de SERVIÇO TÉCNICO ou LOCAÇÃO DE EQUIPAMENTO.
    - Se o problema for URGENTE (ex: máquina parada), use 'iniciar_handoff_humano' com motivo 'urgencia_tecnica'.

    FASE 3: QUALIFICAÇÃO TÉCNICA (Análise da Oportunidade)
    - Pergunte o local da obra (endereço completo) para logística.
    - Entenda o cronograma: Quando o serviço ou máquina deve começar?
    - Se for locação, use 'verificar_estoque' para validar a disponibilidade.

    FASE 4: COMPROMETIMENTO (Próximo Passo)
    - Proponha uma Visita Técnica como a solução ideal para um diagnóstico preciso.
    - Verifique a agenda usando 'consultar_disponibilidade_agenda'.
    - Registre o agendamento usando 'registrar_visita_tecnica'.

    FASE 5: FECHAMENTO E HANDOFF
    - Confirme os dados e diga que um consultor entrará em contato para formalizar o orçamento final.
    - Se houver perguntas de PREÇO ou contrato, use 'iniciar_handoff_humano'.
    """

    return Agent(
        model=obter_modelo(), 
        description="Especialista em Atendimento e Qualificação de Leads para Construção Civil.",
        instructions=[
            script_atendimento,
            "REGRAS DE OURO:",
            "- Analise o histórico para saber em qual FASE do funil você está.",
            "- Fale como um ESPECIALISTA: use termos técnicos como 'canteiro', 'fundação', 'cronograma'.",
            "- Faça apenas UMA pergunta por vez para manter o engajamento.",
            "- NUNCA informe preços. Diga que o consultor enviará o orçamento personalizado.",
            "- Se o cliente enviar áudio, a transcrição virá no formato [ÁUDIO]: texto."
        ],
        tools=[buscar_dados_cliente, verificar_estoque, consultar_disponibilidade_agenda, registrar_visita_tecnica, iniciar_handoff_humano],
        db=storage, 
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
        resposta = agente_construtora.run(mensagem_cliente, session_id=f"conv_{id_conversa}")
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
