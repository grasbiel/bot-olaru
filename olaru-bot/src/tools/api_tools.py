import requests
from typing import Optional
from src.config import JAVA_API_URL, logger
from src.services.chatwoot import iniciar_handoff_humano, adicionar_etiqueta_chatwoot

def classificar_lead(id_conversa: int, telefone: str, status: str, resumo: Optional[str] = None) -> str:
    """
    Atualiza a classificação estratégica do lead no sistema.
    :param id_conversa: ID da conversa no Chatwoot para aplicar etiquetas.
    :param telefone: Telefone do cliente.
    :param status: Novo status (lead_quente, lead_morno, lead_frio, qualificado).
    :param resumo: Opcional - resumo executivo da conversa gerado pela IA.
    """
    logger.info("tool_call", tool="classificar_lead", telefone=telefone, status=status)
    try:
        # Atualiza etiqueta visual no Chatwoot
        adicionar_etiqueta_chatwoot(id_conversa, [f"lead_{status}"])
        
        # Sincroniza com a API Java
        payload = {"statusLead": status}
        if resumo:
            payload["resumoConversa"] = resumo
            
        url = f"{JAVA_API_URL}/clientes/telefone/{telefone}"
        response = requests.patch(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return f"Sucesso: Lead classificado como {status}."
        return f"Aviso: Status atualizado no Chatwoot mas erro na API Java ({response.status_code})."
    except Exception as e:
        logger.error("tool_error", tool="classificar_lead", error=str(e))
        return "Erro técnico ao tentar classificar o lead."

def acionar_handoff_humano(id_conversa: int, motivo: str) -> str:
    """Aciona um atendente humano e pausa o bot."""
    logger.info("tool_call", tool="acionar_handoff_humano", id_conversa=id_conversa)
    try:
        iniciar_handoff_humano(id_conversa, motivo)
        return "Atendimento transferido para humano. O robô foi pausado com sucesso."
    except Exception as e:
        logger.error("tool_error", tool="handoff", error=str(e))
        return "Erro ao tentar realizar a transferência para um humano."

def buscar_dados_cliente(telefone: str) -> str:
    """Busca dados cadastrais do cliente."""
    try:
        response = requests.get(f"{JAVA_API_URL}/clientes/telefone/{telefone}", timeout=10)
        if response.status_code == 200:
            d = response.json()
            return f"DADOS DO CLIENTE: Nome={d.get('nome')}, Status={d.get('statusLead')}, Resumo Anterior={d.get('resumoConversa')}"
        return "Cliente não possui cadastro prévio no sistema."
    except Exception as e:
        logger.error("tool_error", tool="buscar_cliente", error=str(e))
        return "Erro ao consultar banco de dados de clientes."

def verificar_estoque(maquina_nome: str) -> str:
    """Verifica disponibilidade de máquinas para locação."""
    try:
        url = f"{JAVA_API_URL}/maquinas/estoque/{maquina_nome}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            d = response.json()
            return f"ESTOQUE: {d.get('nome')} | Disponível: {d.get('quantidadeDisponivel')} unidades."
        return f"Não encontramos máquinas com o nome '{maquina_nome}' em nosso catálogo."
    except Exception as e:
        logger.error("tool_error", tool="estoque", error=str(e))
        return "Erro técnico ao consultar estoque de máquinas."

def consultar_disponibilidade_agenda(data: str, turno: str) -> str:
    """Consulta se há horários vagos para visitas técnicas."""
    try:
        params = {"data": data, "turno": turno}
        response = requests.get(f"{JAVA_API_URL}/visitas/disponibilidade", params=params, timeout=10)
        if response.status_code == 200:
            d = response.json()
            if d.get("disponivel"):
                return f"AGENDA: Há horários disponíveis para {data} no turno {turno}."
            return f"AGENDA: Infelizmente não há horários para {data} no turno {turno}."
        return "Erro ao validar disponibilidade de agenda."
    except Exception as e:
        logger.error("tool_error", tool="agenda", error=str(e))
        return "Erro ao conectar com o serviço de agenda."

def registrar_visita_tecnica(telefone: str, descricao: str, endereco: str, data: str, turno: str) -> str:
    """Finaliza o agendamento de uma visita técnica no sistema."""
    try:
        payload = {
            "telefone": telefone, "descricaoServico": descricao,
            "endereco": endereco, "dataVisita": data, "turno": turno
        }
        response = requests.post(f"{JAVA_API_URL}/visitas", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            vid = response.json().get("id")
            return f"AGENDAMENTO CONCLUÍDO: Visita criada com ID {vid}."
        return f"Erro ao registrar visita: {response.text}"
    except Exception as e:
        logger.error("tool_error", tool="registrar_visita", error=str(e))
        return "Erro ao salvar agendamento técnico."

def salvar_cliente_no_banco(nome: str, telefone: str) -> Optional[str]:
    """Cria um registro inicial de lead no banco de dados."""
    try:
        payload = {"nome": nome, "telefone": telefone, "origem": "WhatsApp (Auto)"}
        response = requests.post(f"{JAVA_API_URL}/clientes", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        return None
    except Exception as e:
        logger.error("api_error", tool="save_client", error=str(e))
        return None
