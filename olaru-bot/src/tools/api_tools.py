import requests
from src.config import JAVA_API_URL, logger

def buscar_dados_cliente(telefone: str) -> str:
    """Busca informações de um cliente pelo número de telefone via API REST."""
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
    """Consulta se temos uma máquina específica em estoque via API REST."""
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
    """Verifica se há disponibilidade na agenda via API REST."""
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
    """Agenda oficialmente uma visita técnica via API REST."""
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

def salvar_cliente_no_banco(nome, telefone):
    """Via API REST Java."""
    try:
        payload = {"nome": nome, "telefone": telefone, "origem": "Anúncio WhatsApp"}
        response = requests.post(f"{JAVA_API_URL}/clientes", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        return None
    except Exception as e:
        logger.error("erro_api_salvar_cliente", erro=str(e))
        return None
