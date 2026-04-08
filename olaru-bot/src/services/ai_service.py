import random
import asyncio
import requests
from typing import List, Optional
from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.google import Gemini

from src.config import (
    CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger,
    EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE, JAVA_API_URL
)
from src.database import storage, memory_db, r
from src.services.chatwoot import enviar_mensagem_chatwoot, adicionar_etiqueta_chatwoot, iniciar_handoff_humano
from src.services.utils import verificar_limite_mensagens, incrementar_contador_mensagens
from src.tools.api_tools import (
    buscar_dados_cliente, verificar_estoque,
    consultar_disponibilidade_agenda, registrar_visita_tecnica,
    acionar_handoff_humano, classificar_lead, atualizar_nome_cliente
)

# ---------------------------------------------------------------------------
# Instruções do Agente — SDR Olara
# Estruturadas como máquina de estados por fase do funil para reduzir
# ambiguidade e forçar uso correto das ferramentas.
# ---------------------------------------------------------------------------
INSTRUCOES_OLARA = """
## IDENTIDADE
Você é a OLARA, SDR especialista da Construtora Olaru — 18 anos de atuação em engenharia civil
e locação de maquinário pesado. Personalidade: técnica, direta e calorosa.
Use termos do setor com naturalidade: canteiro, cronograma, alvenaria, fundação, manutenção corretiva.

---

## FASE ATUAL DO FUNIL
Leia as ETIQUETAS ATIVAS antes de qualquer resposta e aja conforme a fase:

| Etiqueta ativa    | Ação esperada                                                              |
|-------------------|----------------------------------------------------------------------------|
| lead_novo         | Apresente-se brevemente. Descubra: Obra, Reforma, Manutenção ou Locação?  |
| lead_quente       | Cliente tem interesse real. Avance para confirmar endereço e agendar.     |
| lead_morno        | Reaqueça com empatia. Pergunte se a necessidade ainda existe.             |
| lead_frio         | Abordagem leve. Não pressione. Deixe canal aberto.                        |
| lead_qualificado  | Visita já agendada. Confirme detalhes e encerre com handoff.              |
| (sem etiqueta)    | Trate como novo lead. Descubra nome e necessidade.                        |

---

## ORDEM OBRIGATÓRIA DE FERRAMENTAS

1. **SEMPRE na primeira troca** → chame `buscar_dados_cliente` para recuperar histórico e resumo.
2. **Ao entender o interesse** → chame `classificar_lead` com status e resumo executivo.
3. **Se LOCAÇÃO** → chame `verificar_estoque` antes de confirmar disponibilidade de qualquer equipamento.
4. **Se OBRA/REFORMA/MANUTENÇÃO** → chame `consultar_disponibilidade_agenda` antes de propor datas.
5. **Só após confirmação explícita do cliente** → chame `registrar_visita_tecnica`.
6. **Após registrar a visita** → chame `classificar_lead` com status='qualificado' + chame `acionar_handoff_humano` com motivo='agendamento_concluido'.

---

## GATILHOS DE HANDOFF IMEDIATO
Ao detectar qualquer uma das situações abaixo, chame `acionar_handoff_humano` SEM fazer perguntas:

- **Urgência física**: 'urgente', 'emergência', 'acidente', 'vazamento', 'quebrou', 'parou', 'caiu', 'desabou'
- **Pedido de humano**: 'falar com pessoa', 'atendente', 'gerente', 'responsável', 'humano', 'alguém'
- **Insistência em preço**: após responder que valores são personalizados, se o cliente insistir → handoff

Para urgência física, use motivo='urgencia'. Para pedido humano, use motivo='solicitado_pelo_cliente'.

---

## REGRAS DE COMUNICAÇÃO

- Máximo 2-3 frases por mensagem. UMA pergunta por vez.
- Use sempre o nome que o CLIENTE informou — não o nome do perfil do WhatsApp.
  Se o cliente se apresentar, chame `atualizar_nome_cliente` imediatamente.
- Nunca peça o telefone — você já tem.
- Nunca revele operações internas (chamadas de ferramentas, classificações, etc.).
- Nunca invente preços, prazos ou disponibilidade sem consultar as ferramentas.
- Para perguntas de preço: *"Nossos valores são personalizados conforme o escopo e a logística da sua obra.
  O melhor caminho é uma visita técnica gratuita para um orçamento preciso."*
- Ao finalizar o agendamento: agradeça, informe que um consultor entrará em contato e encerre.
"""


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
            timeout=5,
        )
    except Exception as e:
        logger.error("presence_error", error=str(e))


def _buscar_resumo_cliente(telefone: str) -> Optional[str]:
    """Busca o resumo da conversa anterior diretamente no CRM para injetar no contexto.

    Isso garante que o agente tenha contexto de interações anteriores mesmo que
    o histórico do Agno tenha sido limpo ou seja uma nova sessão.
    """
    try:
        url = f"{JAVA_API_URL}/clientes/telefone/{telefone.replace('+', '')}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            resumo = data.get("resumoConversa")
            status = data.get("statusLead", "novo")
            if resumo:
                return f"[Status: {status}] {resumo}"
            return f"[Status: {status}] Sem resumo anterior."
    except Exception:
        pass
    return None


def criar_agente() -> Agent:
    """Cria uma nova instância do agente por requisição.

    Instância por requisição garante isolamento de estado entre conversas
    concorrentes — o Agno mutaciona estado interno durante agent.run(),
    o que tornaria um singleton inseguro sob carga.
    O custo de criação é mínimo (sem chamada de rede; modelo é stateless).
    """
    return Agent(
        model=obter_modelo(),
        description="SDR Especialista — Construtora OLARU",
        instructions=INSTRUCOES_OLARA,
        tools=[
            buscar_dados_cliente,
            verificar_estoque,
            consultar_disponibilidade_agenda,
            registrar_visita_tecnica,
            acionar_handoff_humano,
            classificar_lead,
            atualizar_nome_cliente,
        ],
        storage=storage,       # Histórico de sessão por conversa (agent_sessions)
        memory=memory_db,      # Fatos de longo prazo por cliente (agent_memory)
        add_history_to_context=True,
        num_history_messages=12,
        update_memory_on_run=True,
        markdown=False,
        show_tool_calls=False,
    )


async def pensar_e_responder(
    mensagem_cliente: str,
    id_conversa: int,
    telefone: str,
    nome_contato: str,
    etiquetas: List[str] = None,
):
    """Loop principal de processamento da resposta."""
    if not verificar_limite_mensagens():
        logger.warning("rate_limit_reached", phone=telefone)
        return

    try:
        # 1. Ativa 'Digitando...' imediatamente para feedback visual ao cliente
        simular_presenca(telefone, True)

        # 2. Busca resumo anterior do CRM para garantir continuidade entre sessões
        resumo_anterior = _buscar_resumo_cliente(telefone)

        # 3. Monta prompt com contexto completo e estruturado
        prompt_final = (
            f"Mensagem do cliente: {mensagem_cliente}\n\n"
            f"--- CONTEXTO DO ATENDIMENTO ---\n"
            f"Nome no WhatsApp: {nome_contato}\n"
            f"Telefone: {telefone}\n"
            f"Etiquetas ativas: {', '.join(etiquetas) if etiquetas else 'nenhuma'}\n"
            f"Histórico CRM: {resumo_anterior or 'Primeiro contato.'}\n"
        )

        # 4. Cria instância isolada do agente (thread-safe) e executa em thread pool
        agente = criar_agente()
        loop = asyncio.get_running_loop()
        resposta = await loop.run_in_executor(
            None,
            lambda: agente.run(
                prompt_final,
                session_id=f"conv_{id_conversa}",
                user_id=telefone,
            ),
        )
        conteudo = resposta.content

        # 5. Fallback se a IA retornar resposta vazia
        if not conteudo:
            raise ValueError("ia_returned_empty")

        # 6. Delay proporcional ao tamanho da resposta (Anti-Ban / naturalidade)
        # ~15 chars/segundo + variação aleatória de 1-3s
        typing_time = max(4, min(12, len(conteudo) / 15 + random.uniform(1, 3)))
        await asyncio.sleep(typing_time)

        # 7. Envia mensagem e encerra presença
        enviar_mensagem_chatwoot(id_conversa, conteudo)
        simular_presenca(telefone, False)
        incrementar_contador_mensagens()

        logger.info(
            "agent_response_sent",
            phone=telefone,
            conversation_id=id_conversa,
            response_len=len(conteudo),
        )

    except Exception as e:
        logger.error("agent_loop_error", error=str(e), conversation_id=id_conversa)
        fallback = (
            "Olá! Tive uma instabilidade momentânea, mas já notifiquei nossa equipe. "
            "Um de nossos consultores vai te atender em breve!"
        )
        enviar_mensagem_chatwoot(id_conversa, fallback)
        iniciar_handoff_humano(id_conversa, "critical_bot_error")
