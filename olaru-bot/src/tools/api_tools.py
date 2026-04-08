import requests
from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from src.config import JAVA_API_URL, logger
from src.services.chatwoot import iniciar_handoff_humano, adicionar_etiqueta_chatwoot, substituir_etiqueta_lead_chatwoot


# --- Modelos de Validação ---

class LeadStatusUpdate(BaseModel):
    telefone: str = Field(..., description="Telefone do cliente (apenas números).")
    status: str = Field(..., description="Status: 'quente', 'morno', 'frio', 'qualificado'.")
    resumo: Optional[str] = Field(None, description="Resumo executivo da conversa para salvar no CRM.")

    @validator("status")
    def validate_status(cls, v):
        allowed = ["quente", "morno", "frio", "qualificado"]
        if v.lower() not in allowed:
            raise ValueError(f"Status deve ser um de: {allowed}")
        return v.lower()


# --- Ferramentas do Agente ---

def buscar_dados_cliente(telefone: str) -> str:
    """
    Consulta o CRM para recuperar nome, status atual e histórico resumido do cliente.
    SEMPRE chame esta ferramenta na primeira mensagem de uma conversa para ter contexto completo.
    """
    try:
        url = f"{JAVA_API_URL}/clientes/telefone/{telefone.replace('+', '')}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            resumo = data.get("resumoConversa") or "Sem histórico anterior."
            return (
                f"CLIENTE ENCONTRADO:\n"
                f"  Nome: {data.get('nome')}\n"
                f"  Status no funil: {data.get('statusLead')}\n"
                f"  Histórico resumido: {resumo}"
            )

        if response.status_code == 404:
            return "CLIENTE NOVO: Sem cadastro para este número. Colete o nome do cliente."

        return "Serviço de consulta indisponível no momento."
    except Exception as e:
        logger.error("tool_error", tool="buscar_cliente", error=str(e))
        return "Erro ao acessar a base de clientes."


def verificar_estoque(maquina_nome: str) -> str:
    """
    Consulta o estoque real de máquinas disponíveis para locação.
    Use quando o cliente demonstrar interesse em alugar um equipamento específico.
    """
    try:
        url = f"{JAVA_API_URL}/maquinas/estoque/{maquina_nome.strip()}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            qty = data.get("quantidadeDisponivel", 0)
            if qty > 0:
                return f"DISPONÍVEL: '{data.get('nome')}' tem {qty} unidade(s) pronta(s) para locação."
            return f"SEM ESTOQUE: '{data.get('nome')}' está esgotado no momento."

        if response.status_code == 404:
            return f"NÃO ENCONTRADO: Não trabalhamos com '{maquina_nome}' ou o nome está incorreto. Peça mais detalhes ao cliente."

        return "Não foi possível consultar o catálogo agora."
    except Exception as e:
        logger.error("tool_error", tool="estoque", error=str(e))
        return "Erro ao consultar o catálogo de máquinas."


def consultar_disponibilidade_agenda(data: str, turno: str) -> str:
    """
    Verifica se há vaga para visita técnica em um dia e turno específicos.
    Parâmetros: data no formato YYYY-MM-DD, turno como 'MANHA' ou 'TARDE'.
    Use ANTES de propor qualquer data ao cliente.
    """
    try:
        try:
            datetime.strptime(data, "%Y-%m-%d")
        except ValueError:
            return "Formato de data inválido. Use YYYY-MM-DD (ex: 2026-05-15)."

        turno_upper = turno.upper()
        if turno_upper not in ["MANHA", "TARDE"]:
            return "Turno inválido. Use 'MANHA' ou 'TARDE'."

        params = {"data": data, "turno": turno_upper}
        response = requests.get(f"{JAVA_API_URL}/visitas/disponibilidade", params=params, timeout=10)

        if response.status_code == 200:
            res = response.json()
            if res.get("disponivel"):
                return f"DISPONÍVEL: Temos vaga para {data} ({turno_upper}). Pode confirmar com o cliente."
            return f"INDISPONÍVEL: O turno {turno_upper} do dia {data} está lotado. Sugira outra data ou turno."

        return "Sistema de agenda indisponível. Tente outro período."
    except Exception as e:
        logger.error("tool_error", tool="agenda", error=str(e))
        return "Erro ao consultar a agenda. Informe ao cliente que verificaremos manualmente."


def registrar_visita_tecnica(telefone: str, descricao: str, endereco: str, data: str, turno: str) -> str:
    """
    Registra oficialmente a visita técnica no banco de dados.
    SÓ chame esta ferramenta após o cliente CONFIRMAR EXPLICITAMENTE a data e o turno.
    Após registrar com sucesso, chame `classificar_lead` com status='qualificado'
    e depois `acionar_handoff_humano` com motivo='agendamento_concluido'.
    """
    try:
        try:
            datetime.strptime(data, "%Y-%m-%d")
        except ValueError:
            return "Data inválida. Use YYYY-MM-DD."

        turno_upper = turno.upper()
        if turno_upper not in ["MANHA", "TARDE"]:
            return "Turno inválido. Use 'MANHA' ou 'TARDE'."

        telefone_limpo = telefone.replace("+", "")
        payload = {
            "telefone": telefone_limpo,
            "descricaoServico": descricao,
            "endereco": endereco,
            "dataVisita": data,
            "turno": turno_upper,
        }

        logger.info("tool_call", tool="registrar_visita", telefone=telefone_limpo, data=data, turno=turno_upper)
        response = requests.post(f"{JAVA_API_URL}/visitas", json=payload, timeout=10)

        if response.status_code in [200, 201]:
            result = response.json()
            return (
                f"AGENDAMENTO CONFIRMADO! Visita registrada para {data} ({turno_upper}). "
                f"Protocolo: {result.get('id')}. "
                f"Agora classifique o lead como 'qualificado' e acione o handoff humano."
            )

        return f"Falha no agendamento: {response.text}. Verifique os dados e tente novamente."

    except Exception as e:
        logger.error("tool_error", tool="registrar_visita", error=str(e))
        return "Erro técnico ao registrar a visita. Acione o handoff humano para resolver manualmente."


def classificar_lead(id_conversa: int, telefone: str, status: str, resumo: Optional[str] = None) -> str:
    """
    Atualiza a classificação do lead no CRM e no Chatwoot.
    Use sempre que identificar claramente o potencial ou o estágio do cliente.
    A etiqueta anterior de lead é substituída (nunca acumulada).
    """
    try:
        update = LeadStatusUpdate(telefone=telefone, status=status, resumo=resumo)
        logger.info("tool_call", tool="classificar_lead", telefone=update.telefone, status=update.status)

        # Substitui a etiqueta lead_* anterior pela nova (sem acumular)
        substituir_etiqueta_lead_chatwoot(id_conversa, update.status)

        # Sincroniza com o CRM Java
        payload = {"statusLead": update.status}
        if update.resumo:
            payload["resumoConversa"] = update.resumo

        response = requests.patch(
            f"{JAVA_API_URL}/clientes/telefone/{update.telefone}",
            json=payload,
            timeout=10,
        )

        if response.status_code == 200:
            return f"Lead classificado como '{update.status}' e sincronizado no CRM."
        return f"Lead etiquetado no Chatwoot, mas CRM retornou status {response.status_code}."

    except ValueError as e:
        return f"Erro de validação: {str(e)}"
    except Exception as e:
        logger.error("tool_error", tool="classificar_lead", error=str(e))
        return "Erro ao classificar o lead."


def acionar_handoff_humano(id_conversa: int, motivo: str) -> str:
    """
    Transfere o atendimento para um agente humano e pausa o robô.
    Use nos seguintes casos:
    - Cliente solicitou falar com humano/atendente/gerente
    - Palavras de urgência detectadas (urgente, emergência, quebrou, acidente)
    - Agendamento concluído (motivo='agendamento_concluido')
    - Cliente perguntou sobre preços com insistência
    - Mais de 10 trocas sem progresso no funil
    """
    logger.info("tool_call", tool="handoff", id_conversa=id_conversa, motivo=motivo)
    try:
        iniciar_handoff_humano(id_conversa, motivo)
        return "Atendimento transferido para a equipe humana com sucesso. O robô foi pausado."
    except Exception as e:
        logger.error("tool_error", tool="handoff", error=str(e))
        return "Falha ao transferir. Informe ao cliente que um atendente entrará em contato em breve."


def atualizar_nome_cliente(telefone: str, novo_nome: str) -> str:
    """
    Atualiza o nome do cliente no CRM quando ele se apresentar ou corrigir o nome.
    Chame IMEDIATAMENTE quando o cliente informar o próprio nome.
    Após chamar, use apenas o nome informado pelo cliente.
    """
    try:
        telefone_limpo = telefone.replace("+", "")
        response = requests.patch(
            f"{JAVA_API_URL}/clientes/telefone/{telefone_limpo}",
            json={"nome": novo_nome},
            timeout=10,
        )
        logger.info("tool_call", tool="atualizar_nome", telefone=telefone_limpo, novo_nome=novo_nome)

        if response.status_code == 200:
            return f"Nome atualizado para '{novo_nome}' no sistema."
        return f"Não foi possível salvar o nome agora (status {response.status_code}). Continue usando o nome informado."

    except Exception as e:
        logger.error("tool_error", tool="atualizar_nome", error=str(e))
        return "Erro ao salvar o nome. Continue usando o nome que o cliente informou."


def salvar_cliente_no_banco(nome: str, telefone: str) -> Optional[str]:
    """Registra um novo lead no CRM. Chamada automaticamente no primeiro contato."""
    try:
        payload = {
            "nome": nome,
            "telefone": telefone.replace("+", ""),
            "origem": "whatsapp_robo",
        }
        response = requests.post(f"{JAVA_API_URL}/clientes", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        return None
    except Exception as e:
        logger.error("api_error", tool="salvar_cliente", error=str(e))
        return None
