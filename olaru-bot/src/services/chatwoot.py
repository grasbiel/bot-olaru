import requests
from typing import List, Optional
from src.config import CHATWOOT_URL, CHATWOOT_BOT_TOKEN, ID_DA_CONTA, logger

def enviar_mensagem_chatwoot(id_conversa: int, texto: str, private: bool = False) -> bool:
    """Envia mensagem para o Chatwoot. Permite mensagens públicas ou notas privadas."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/messages"
    payload = {
        "content": texto, 
        "message_type": "outgoing",
        "private": private
    }
    headers = {"api_access_token": CHATWOOT_BOT_TOKEN}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error("chatwoot_send_error", conversation_id=id_conversa, error=str(e))
        return False

def obter_etiquetas_chatwoot(id_conversa: int) -> List[str]:
    """Busca as etiquetas atuais de uma conversa."""
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/labels"
    headers = {"api_access_token": CHATWOOT_BOT_TOKEN}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("payload", [])
    except Exception as e:
        logger.error("chatwoot_get_labels_error", conversation_id=id_conversa, error=str(e))
    return []

def adicionar_etiqueta_chatwoot(id_conversa: int, etiquetas: List[str]) -> bool:
    """Acrescenta etiquetas a uma conversa sem apagar as existentes.

    A API do Chatwoot substitui todas as etiquetas ao usar POST /labels.
    Por isso, buscamos as etiquetas atuais antes de enviar o conjunto completo.
    """
    if isinstance(etiquetas, str):
        etiquetas = [etiquetas]

    etiquetas_atuais = obter_etiquetas_chatwoot(id_conversa)
    etiquetas_finais = list(set(etiquetas_atuais + etiquetas))

    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/labels"
    headers = {"api_access_token": CHATWOOT_BOT_TOKEN}

    try:
        response = requests.post(url, json={"labels": etiquetas_finais}, headers=headers, timeout=10)
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error("chatwoot_label_error", conversation_id=id_conversa, error=str(e))
        return False

def iniciar_handoff_humano(id_conversa: int, motivo: str = "solicitado_pelo_cliente") -> None:
    """Pausa o robô e sinaliza para atendentes humanos assumirem."""
    logger.info("handoff_initiated", conversation_id=id_conversa, reason=motivo)
    
    # 1. Atribui etiquetas de status e pausa
    adicionar_etiqueta_chatwoot(id_conversa, ["pausar_robo", f"handoff_{motivo}"])
    
    # 2. Deixa uma nota interna explicativa para a equipe
    nota = f"🤖 ROBÔ PAUSADO: Handoff acionado devido a: {motivo}."
    enviar_mensagem_chatwoot(id_conversa, nota, private=True)
