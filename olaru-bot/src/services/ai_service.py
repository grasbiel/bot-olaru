import random
import asyncio
import requests
from typing import List, Optional
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.google import Gemini

from src.config import (
    CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger, 
    EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE
)
from src.database import storage, memory_db, r
from src.services.chatwoot import enviar_mensagem_chatwoot, adicionar_etiqueta_chatwoot, iniciar_handoff_humano
from src.services.utils import verificar_limite_mensagens, incrementar_contador_mensagens
from src.tools.api_tools import (
    buscar_dados_cliente, verificar_estoque, 
    consultar_disponibilidade_agenda, registrar_visita_tecnica,
    acionar_handoff_humano, classificar_lead, atualizar_nome_cliente
)

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
    """Configura o Agente especializado com ferramentas e instruções aprimoradas."""
    
    instrucoes = [
        "VOCÊ É A 'OLARA', ASSISTENTE VIRTUAL SÊNIOR DA CONSTRUTORA OLARU (18 ANOS DE MERCADO).",
        "SUA PERSONALIDADE: Profissional, técnica, acolhedora e focada em solução. Use termos como 'canteiro', 'cronograma', 'alvenaria'.",
        
        "MISSÃO PRINCIPAL (SDR):",
        "1. QUALIFICAR: Entender se o cliente quer Obra, Reforma, Manutenção ou Locação.",
        "2. LOCALIZAR: Confirmar o endereço da obra e reforma do cliente ou se for máquina, onde ela será utilizada.",
        "3. AGENDAR: Consultar disponibilidade e registrar visita técnica usando as ferramentas.",
        "4. TRANSICIONAR: Informar que um consultor humano assumirá após o agendamento.",

        "DIRETRIZES DE RESPOSTA:",
        "- Seja CONCISO. Máximo 2-3 frases por mensagem.",
        "- APENAS UMA PERGUNTA por vez para não sobrecarregar o cliente.",
        "- Se for o primeiro contato (etiqueta 'lead_novo'), apresente-se com autoridade (18 anos de mercado).",
        "- NUNCA invente preços ou prazos que não venham das ferramentas.",
        "- Se o cliente demonstrar urgência ou irritação, use 'acionar_handoff_humano'.",
        "- Não passe para o cliente que você está fazendo consultas de funções internas como: classificação dele, salvando o número em base de dados, etc.",
        "- Atenção: O atendimento é via Whatsapp, você já tem o telefone do cliente. Nunca peça o número dele",
        "- Olhe os [DADOS DO CLIENTE]. Se o Nome for 'CLIENTE', pergunte educadamente como a pessoa se chama para personalizar o atendimento.",
        "- ATENÇÃO: O 'Nome' nos dados iniciais vem do perfil do WhatsApp. Seja amigável e sempre confirme o nome com o cliente. Se ele disser um nome diferente (ex: 'me chamo Carlos', 'aqui é a Ana'), chame a ferramenta 'atualizar_nome_cliente' na mesma hora para salvar no banco. Depois disso, chame o cliente APENAS pelo nome que ele escolheu.",

        "PROCESSO DE PENSAMENTO (CoT):",
        "Antes de responder, analise as etiquetas e o histórico para saber em qual fase do SDR o cliente está.",
    ]

    return Agent(
        model=obter_modelo(),
        description="SDR Specialist - Construtora OLARU",
        instructions=instrucoes,
        tools=[
            buscar_dados_cliente, verificar_estoque,
            consultar_disponibilidade_agenda, registrar_visita_tecnica,
            acionar_handoff_humano, classificar_lead, atualizar_nome_cliente
        ],
        storage=storage,        # Sessões/histórico por conversa (agent_sessions)
        memory=memory_db,       # Fatos de longo prazo por cliente (agent_memory)
        # Configurações de Memória e Contexto
        add_history_to_context=True,
        num_history_messages=12,
        update_memory_on_run=True,
        markdown=False
    )

# Singleton do Agente
agente_olara = criar_agente()

async def pensar_e_responder(mensagem_cliente: str, id_conversa: int, telefone: str, nome_contato:str, etiquetas: List[str] = None):
    """Loop principal de processamento da resposta."""
    if not verificar_limite_mensagens():
        logger.warning("rate_limit_reached", phone=telefone)
        return

    try:
        # 1. Ativa 'Digitando...'
        simular_presenca(telefone, True)

        # 2. Prepara Contexto Adicional
        contexto_etiquetas = f"\nETIQUETAS: {', '.join(etiquetas) if etiquetas else 'nenhuma'}"
        prompt_final = f"{mensagem_cliente}\n\n[DADOS DO CLIENTE: Nome={nome_contato}, Telefone={telefone}, ETIQUETAS: {', '.join(etiquetas) if etiquetas else 'nenhuma'}]"

        # 3. Executa a IA
        # Rodar em thread para não bloquear o loop async (agno sync por padrão)
        loop = asyncio.get_running_loop()
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
