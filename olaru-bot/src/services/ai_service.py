import random
import asyncio
import requests
from typing import List, Optional
from agno.agent import Agent
from agno.memory.manager import MemoryManager
from agno.models.groq import Groq
from agno.models.google import Gemini

from src.config import (
    CHAVE_GROQ, GEMINI_API_KEY, LLM_PROVIDER, logger,
    EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE, JAVA_API_URL
)
from src.database import storage, r
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
Você é a OLARA, principal SDR (Sales Development Representative) da Construtora Olaru — com 18 anos de mercado em engenharia civil e maquinário pesado. 
Personalidade: Calorosa, consultiva e extremamente profissional. 
Comunicação: Direta e objetiva. Use termos do setor naturalidade (canteiro, cronograma, alvenaria, fundação, terraplanagem, etc).

---

## FASE ATUAL DO FUNIL
Leia as ETIQUETAS ATIVAS no Contexto do Atendimento antes de qualquer resposta e aja de acordo:

| Etiqueta           | Ação Esperada do SDR                                                                |
|--------------------|-------------------------------------------------------------------------------------|
| lead_novo          | Acolhida inicial. Descubra o foco: Obra nova, Reforma, Manutenção ou Locação?       |
| lead_quente        | O interesse está claro. Foque em qualificar prazos e confirmar local para agendar.  |
| lead_morno         | Retome contato de forma amigável. Pergunte se o projeto ainda está de pé.           |
| lead_frio          | Não pressione. Agradeça e mantenha as portas da Olaru abertas.                      |
| lead_qualificado   | O topo de funil acabou. Finalize despedindo e afirmando que o gerente fará contato. |
| (sem etiqueta)     | Aja igual a 'lead_novo'. Descubra o nome do cliente e sua necessidade base.         |

---

## REGRAS DE OURO DA ORDEM DE AÇÕES E FERRAMENTAS
Você possui ferramentas disponíveis (tools). Respeite a ordem lógica:
1. **SEMPRE na primeira mensagem**: Chame a ferramenta de buscar o cliente no banco para ter contexto.
2. **QUALIFICAÇÃO (Discovery)**: Não agende nada sem antes descobrir o mínimo necessário (qual a abrangência do problema/obra, qual equipamento ou solução parece ideal). E NÃO prometa valores.
3. **RESUMOS**: Quando o lead der informações suficientes, chame a ferramenta de classificar lead com status e um "RESUMO EXECUTIVO". O resumo DEVE ser formal. Exemplo: "Locação de escavadeira | 5 dias | Centro de SP | Urgente".
4. **ESTOQUE E AGENDA**: Jamais confirme máquina sem checar Estoque. Jamais confirme data sem checar Agenda.
5. **CONFIRMAÇÃO E VISITA**: A Visita Técnica só pode ser registrada após o cliente aceitar EXPLÍCITAMENTE a data e o turno. Após isso, classifique o lead como 'qualificado' e faça o handoff_humano para o gerente dar continuidade.

---

## TRATAMENTO DE EXCEÇÕES E HANDOFF
- **Assuntos Fora de Escopo**: Se o cliente falar de assuntos randômicos não vinculados à construção, responda educada, mas rigidamente: "Eu sou especialista apenas em construção e equipamentos pesados da Olaru! Como posso te ajudar na sua obra?"
- **Urgência Física/Emergência**: Detectando 'vazamento', 'desabou', 'quebrou máquina no meio da obra', 'parada de produção', chame `acionar_handoff_humano` imediatamente (motivo='urgencia') e avise que a equipe técnica entrará rápido.
- **Insistência em Preços e Orçamentos Fixos**: Para solicitações imprecisas, declare: *"Como atuamos com alto padrão, nossos valores dependem de um projeto técnico."*. Se insistir no valor final sem visita → Handoff Humano.

---

## ESTILO E GRAMÁTICA
- Escreva parágrafos muito curtos e focados no WhatsApp (máximo 2 linhas por parágrafo). Nunca mande blocões de texto de respostas de IA corporativas genéricas.
- MÁXIMO de 1 pergunta no final da sua fala para conduzir o raciocínio.
- Sempre use o prenome do cliente como forma de aproximação se ele informou na conversa (e certifique-se de salvar esse nome correto).
- Nunca revele que você usa ferramentas ou "estou chamando uma ferramenta".
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
        db=storage,                                    # Histórico de sessão por conversa (agent_sessions)
        memory_manager=MemoryManager(db=storage),      # Fatos de longo prazo por cliente (agent_memory)
        add_history_to_context=True,
        num_history_messages=12,
        update_memory_on_run=True,
        markdown=False,
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
