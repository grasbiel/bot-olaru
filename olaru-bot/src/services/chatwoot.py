import requests
from src.config import CHATWOOT_URL, CHATWOOT_BOT_TOKEN, ID_DA_CONTA, logger

def enviar_mensagem_chatwoot(id_conversa, texto):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/messages"
    try:
        requests.post(
            url, 
            json={"content": texto, "message_type": "outgoing"}, 
            headers={"api_access_token": CHATWOOT_BOT_TOKEN},
            timeout=10
        )
    except Exception as e:
        logger.error("erro_envio_chatwoot", erro=str(e))

def adicionar_etiqueta_chatwoot(id_conversa, etiqueta):
    url = f"{CHATWOOT_URL}/api/v1/accounts/{ID_DA_CONTA}/conversations/{id_conversa}/labels"
    try:
        requests.post(
            url, 
            json={"labels": [etiqueta]}, 
            headers={"api_access_token": CHATWOOT_BOT_TOKEN},
            timeout=10
        )
    except Exception as e:
        logger.error("erro_etiqueta_chatwoot", erro=str(e))
