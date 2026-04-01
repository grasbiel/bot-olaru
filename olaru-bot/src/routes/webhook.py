from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from src.config import WEBHOOK_SECRET, NUMERO_TESTE, logger
from src.database import r
from src.services.ai_service import pensar_e_responder
from src.services.chatwoot import adicionar_etiqueta_chatwoot
from src.services.utils import transcrever_audio, obter_endereco_por_coordenadas
from src.tools.api_tools import salvar_cliente_no_banco

router = APIRouter()

@router.post("/webhook")
async def receber_mensagem(request: Request, background_tasks: BackgroundTasks):
    # 1. Validação de Segurança
    secret = request.headers.get("X-Webhook-Secret")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET: 
        logger.warning("unauthorized_webhook_access")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        dados = await request.json()
    except Exception:
        return {"status": "invalid_json"}
    
    # 2. Deduplicação de Mensagens (Redis)
    msg_id = dados.get("id")
    if msg_id:
        if r.exists(f"msg_proc:{msg_id}"):
            return {"status": "duplicate"}
        r.setex(f"msg_proc:{msg_id}", 600, "1")

    # 3. Filtro de Evento (Apenas mensagens recebidas)
    if dados.get("event") != "message_created" or dados.get("message_type") != "incoming":
        return {"status": "event_ignored"}

    # 4. Extração de Metadados
    id_conversa = dados.get("conversation", {}).get("id")
    nome_contato = dados.get("sender", {}).get("name", "Cliente").upper()
    telefone = dados.get("sender", {}).get("phone_number", "").replace("+", "")
    etiquetas = dados.get("conversation", {}).get("labels", [])
    conteudo_texto = dados.get("content") or ""

    # 5. Validação Sandbox (Número de Teste)
    if NUMERO_TESTE and telefone != NUMERO_TESTE:
        logger.debug("sandbox_ignore", phone=telefone)
        return {"status": "sandbox_active"}

    # 6. Regras de Pausa e Bloqueio
    if "GROUP" in nome_contato or "pausar_robo" in etiquetas:
        return {"status": "bot_paused_or_group"}

    # 7. Processamento de Anexos (Áudio e Localização)
    attachments = dados.get("attachments", [])
    for anexo in attachments:
        tipo = anexo.get("file_type")
        if tipo == "audio":
            transcricao = transcrever_audio(anexo.get("data_url"))
            conteudo_texto = f"[ÁUDIO TRANSCRITO]: {transcricao}" if transcricao else "[ERRO: Falha na transcrição]"
        elif tipo == "location":
            lat, lon = anexo.get("coordinates_lat"), anexo.get("coordinates_long")
            if lat and lon:
                endereco = obter_endereco_por_coordenadas(lat, lon)
                conteudo_texto = f"[LOCALIZAÇÃO RECEBIDA]: {endereco}"

    if not conteudo_texto:
        return {"status": "no_content"}

    # 8. Verificação de Gatilho e Início de Atendimento
    msg_lower = conteudo_texto.lower()
    is_trigger = "anúncio" in msg_lower or "anuncio" in msg_lower
    
    if "robo_ativo" in etiquetas or is_trigger:
        if "robo_ativo" not in etiquetas:
            # Primeiro contato: Cadastra e marca como ativo
            salvar_cliente_no_banco(nome_contato, telefone)
            adicionar_etiqueta_chatwoot(id_conversa, ["robo_ativo", "lead_novo"])
            logger.info("new_lead_activated", phone=telefone)

        # Dispara IA em background
        background_tasks.add_task(pensar_e_responder, conteudo_texto, id_conversa, telefone, etiquetas)

    return {"status": "processing"}
