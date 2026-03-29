from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from src.config import WEBHOOK_SECRET, NUMERO_TESTE, logger, r
from src.services.ai_service import pensar_e_responder
from src.services.chatwoot import adicionar_etiqueta_chatwoot
from src.services.utils import transcrever_audio, obter_endereco_por_coordenadas
from src.tools.api_tools import salvar_cliente_no_banco

router = APIRouter()

@router.post("/webhook")
async def receber_mensagem(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Webhook-Secret")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET: 
        logger.warning("webhook_auth_failed")
        raise HTTPException(status_code=403, detail="Webhook Secret Inválido")

    try:
        dados = await request.json()
    except:
        return {"status": "erro_json"}
    
    msg_id = dados.get("id")
    if msg_id:
        if r.exists(f"msg_processada:{msg_id}"):
            return {"status": "duplicado"}
        r.setex(f"msg_processada:{msg_id}", 600, "1")

    if dados.get("event") == "message_created" and dados.get("message_type") == "incoming":
        
        mensagem_cliente = dados.get("content") or ""
        id_conversa = dados.get("conversation", {}).get("id")
        nome_contato = dados.get("sender", {}).get("name", "").upper()
        telefone_contato = dados.get("sender", {}).get("phone_number", "").replace("+", "")
        etiquetas = dados.get("conversation", {}).get("labels", [])
        
        if NUMERO_TESTE and telefone_contato != NUMERO_TESTE:
            return {"status": "ignorado_teste"}

        attachments = dados.get("attachments", [])
        for anexo in attachments:
            tipo = anexo.get("file_type")
            if tipo == "audio":
                transcricao = transcrever_audio(anexo.get("data_url"))
                mensagem_cliente = f"[ÁUDIO]: {transcricao}" if transcricao else "[ERRO]: Falha ao transcrever áudio."
            elif tipo == "location":
                lat, lon = anexo.get("coordinates_lat"), anexo.get("coordinates_long")
                if lat and lon:
                    endereco = obter_endereco_por_coordenadas(lat, lon)
                    mensagem_cliente = f"[LOCALIZAÇÃO]: {endereco}"
            elif tipo in ["image", "file"]:
                mensagem_cliente = f"[{tipo.upper()} RECEBIDA]: O cliente enviou um arquivo."

        if "GROUP" in nome_contato or "pausar_robo" in etiquetas: 
            return {"status": "ignorado"}

        if not mensagem_cliente:
            return {"status": "sem_conteudo"}

        msg_min = mensagem_cliente.lower()
        if "robo_ativo" in etiquetas or "anúncio" in msg_min or "anuncio" in msg_min:
            if "robo_ativo" not in etiquetas:
                salvar_cliente_no_banco(nome_contato, telefone_contato)
                adicionar_etiqueta_chatwoot(id_conversa, "robo_ativo")
            
            logger.info("nova_mensagem", id_conversa=id_conversa, telefone=telefone_contato)
            background_tasks.add_task(pensar_e_responder, mensagem_cliente, id_conversa, telefone_contato)

    return {"status": "recebido"}
