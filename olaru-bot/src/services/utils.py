import os
import random
import requests
from datetime import datetime
from src.config import logger, groq_client, r

def verificar_limite_mensagens():
    """Verifica se o limite diário de mensagens foi atingido."""
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"msgs_enviadas:{hoje}"
        contagem = r.get(chave)
        if contagem and int(contagem) >= 200:
            return False
        return True
    except Exception as e:
        logger.error("erro_redis_limite", erro=str(e))
        return True 

def incrementar_contador_mensagens():
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"msgs_enviadas:{hoje}"
        r.incr(chave)
        r.expire(chave, 86400)
    except Exception as e:
        logger.error("erro_redis_incr", erro=str(e))

def obter_endereco_por_coordenadas(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "OlaruBot/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get("display_name", f"{lat}, {lon}")
    except Exception as e:
        logger.error("erro_coordenadas", erro=str(e))
        return f"Lat: {lat}, Lon: {lon}"

def transcrever_audio(url_audio):
    nome_arquivo = f"temp_{random.randint(1000, 9999)}.ogg"
    try:
        response = requests.get(url_audio, timeout=20)
        with open(nome_arquivo, "wb") as f: 
            f.write(response.content)
        
        with open(nome_arquivo, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(nome_arquivo, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="pt"
            )
        
        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)
        return transcription
    except Exception as e:
        logger.error("erro_transcricao_detalhado", erro=str(e), url=url_audio)
        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)
        return None
