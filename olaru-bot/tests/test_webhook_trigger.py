import pytest
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

@pytest.fixture
def mock_redis():
    with patch("src.routes.webhook.r") as mock:
        mock.exists.return_value = False
        yield mock

@pytest.fixture
def mock_background_tasks():
    with patch("fastapi.BackgroundTasks.add_task") as mock:
        yield mock

def test_webhook_aciona_com_anuncio(mock_redis, mock_background_tasks):
    # Cenário: Mensagem contém "anúncio"
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "id": "msg_123",
        "content": "Olá, vi seu anúncio no Instagram",
        "sender": {"phone_number": "5511999999999", "name": "Joao"},
        "conversation": {"id": 1, "labels": []}
    }
    
    # Ação
    response = client.post("/api/v1/webhook", json=payload)
    
    # Validação
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    # Verifica se a IA foi acionada (tarefa em background)
    assert mock_background_tasks.called

def test_webhook_ignora_sem_anuncio(mock_redis, mock_background_tasks):
    # Cenário: Mensagem SEM a palavra-chave
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "id": "msg_456",
        "content": "Quero saber o preço",
        "sender": {"phone_number": "5511999999999", "name": "Joao"},
        "conversation": {"id": 1, "labels": []}
    }
    
    # Ação
    response = client.post("/api/v1/webhook", json=payload)
    
    # Validação
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    # Garante que a IA NÃO foi acionada
    assert not mock_background_tasks.called

def test_webhook_bypassa_pausa_com_anuncio(mock_redis, mock_background_tasks):
    # Cenário: Contato está pausado, mas envia "anúncio"
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "id": "msg_789",
        "content": "Vi seu anúncio",
        "sender": {"phone_number": "5511999999999", "name": "Joao"},
        "conversation": {"id": 1, "labels": ["pausar_robo"]}
    }
    
    # Ação
    response = client.post("/api/v1/webhook", json=payload)
    
    # Validação
    assert response.status_code == 200
    # O robô deve acionar mesmo pausado se a palavra chave estiver presente
    assert mock_background_tasks.called
