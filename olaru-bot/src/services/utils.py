import os
import tempfile
import requests
from datetime import datetime
from typing import Optional
from src.config import logger, CHAVE_GROQ
from src.database import r
from groq import Groq

def verificar_limite_mensagens() -> bool:
    """Verifica se o limite diário de mensagens (Anti-Ban) foi atingido."""
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"rate:limit:{hoje}"
        contagem = r.get(chave)
        # Limite de 200 mensagens por dia para segurança do chip
        if contagem and int(contagem) >= 200:
            return False
        return True
    except Exception as e:
        logger.error("redis_rate_limit_error", error=str(e))
        return True 

def incrementar_contador_mensagens() -> None:
    """Incrementa o contador diário de envios."""
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = f"rate:limit:{hoje}"
        r.incr(chave)
        r.expire(chave, 86400) # Expira em 24h
    except Exception as e:
        logger.error("redis_incr_error", error=str(e))

def obter_endereco_por_coordenadas(lat: float, lon: float) -> str:
    """Converte coordenadas em endereço legível via OpenStreetMap."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "OlaruBot/2.0"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get("display_name", f"Localização: {lat}, {lon}")
    except Exception as e:
        logger.error("geocoding_error", error=str(e))
        return f"Coordenadas: {lat}, {lon}"

def transcrever_audio(url_audio: str) -> Optional[str]:
    """Transcreve áudios do WhatsApp usando Whisper via Groq."""
    if not CHAVE_GROQ:
        return None
        
    client = Groq(api_key=CHAVE_GROQ)
    fd, temp_file = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)

    try:
        # Download do áudio
        response = requests.get(url_audio, timeout=20)
        with open(temp_file, "wb") as f:
            f.write(response.content)

        # Transcrição via Groq (Whisper)
        with open(temp_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(temp_file), audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="pt"
            )

        return transcription
    except Exception as e:
        logger.error("transcription_error", error=str(e))
        return None
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
