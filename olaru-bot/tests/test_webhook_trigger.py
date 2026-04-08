import pytest
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock do Redis para evitar conexão real durante testes."""
    with patch("src.routes.webhook.r") as mock:
        mock.exists.return_value = False
        yield mock


@pytest.fixture
def mock_salvar_cliente():
    """Mock da função de salvar cliente no banco."""
    with patch("src.routes.webhook.salvar_cliente_no_banco") as mock:
        mock.return_value = "fake-uuid"
        yield mock


@pytest.fixture
def mock_etiquetas():
    """Mock da função de adicionar etiquetas no Chatwoot."""
    with patch("src.routes.webhook.adicionar_etiqueta_chatwoot") as mock:
        mock.return_value = True
        yield mock


def make_payload(content, labels=None, phone="5511999999999", name="Joao", msg_id=None):
    """Helper para criar payloads de teste."""
    return {
        "event": "message_created",
        "message_type": "incoming",
        "id": msg_id or f"msg_{hash(content) % 99999}",
        "content": content,
        "sender": {"phone_number": phone, "name": name},
        "conversation": {"id": 1, "labels": labels or []}
    }


# ============================================================
# CENÁRIO 1: Ativação com palavra-chave "anúncio"
# ============================================================

class TestAtivacaoComGatilho:

    def test_anuncio_com_acento_dispara_ia(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Mensagem com 'anúncio' deve ativar o robô e disparar a IA."""
        payload = make_payload("Olá, vi seu anúncio no Instagram")

        with patch("src.routes.webhook.pensar_e_responder") as mock_ia:
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        mock_salvar_cliente.assert_called_once()
        mock_etiquetas.assert_called_once()
        # Verifica que "robo_ativo" foi adicionada
        etiquetas_enviadas = mock_etiquetas.call_args[0][1]
        assert "robo_ativo" in etiquetas_enviadas

    def test_anuncio_sem_acento_dispara_ia(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Mensagem com 'anuncio' (sem acento) também deve ativar."""
        payload = make_payload("Vi o anuncio de vocês")

        with patch("src.routes.webhook.pensar_e_responder"):
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        mock_salvar_cliente.assert_called_once()

    def test_anuncio_adiciona_lead_novo(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Primeiro contato com 'anúncio' deve adicionar etiqueta 'lead_novo'."""
        payload = make_payload("Vi seu anúncio", labels=[])

        with patch("src.routes.webhook.pensar_e_responder"):
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        etiquetas_enviadas = mock_etiquetas.call_args[0][1]
        assert "lead_novo" in etiquetas_enviadas
        assert "robo_ativo" in etiquetas_enviadas

    def test_anuncio_nao_duplica_lead_novo(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Se 'lead_novo' já existe, não deve duplicar."""
        payload = make_payload("Vi outro anúncio", labels=["lead_novo"])

        with patch("src.routes.webhook.pensar_e_responder"):
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        etiquetas_enviadas = mock_etiquetas.call_args[0][1]
        assert "lead_novo" not in etiquetas_enviadas
        assert "robo_ativo" in etiquetas_enviadas


# ============================================================
# CENÁRIO 2: Continuação com etiqueta "robo_ativo"
# ============================================================

class TestContinuacaoComRoboAtivo:

    def test_mensagem_sem_gatilho_com_robo_ativo_dispara_ia(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Mensagem sem 'anúncio' MAS com etiqueta 'robo_ativo' deve continuar o atendimento."""
        payload = make_payload(
            "Quero saber o preço de uma betoneira",
            labels=["robo_ativo", "lead_novo"]
        )

        with patch("src.routes.webhook.pensar_e_responder") as mock_ia:
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        # NÃO deve salvar cliente novamente (não é gatilho)
        mock_salvar_cliente.assert_not_called()
        # NÃO deve adicionar etiquetas novamente
        mock_etiquetas.assert_not_called()

    def test_mensagem_seguinte_sem_robo_ativo_ignora(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Mensagem sem 'anúncio' E sem 'robo_ativo' deve ser ignorada."""
        payload = make_payload(
            "Olá, quero um orçamento",
            labels=[]
        )

        with patch("src.routes.webhook.pensar_e_responder") as mock_ia:
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "no_activation"
        mock_salvar_cliente.assert_not_called()


# ============================================================
# CENÁRIO 3: Bypass de pausa com gatilho
# ============================================================

class TestBypassPausa:

    def test_anuncio_bypassa_pausa(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Gatilho 'anúncio' deve funcionar mesmo com 'pausar_robo' ativo."""
        payload = make_payload(
            "Vi seu anúncio no Google",
            labels=["pausar_robo"]
        )

        with patch("src.routes.webhook.pensar_e_responder"):
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        mock_salvar_cliente.assert_called_once()

    def test_mensagem_normal_bloqueada_por_pausa(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """Mensagem sem gatilho com 'pausar_robo' deve ser bloqueada."""
        payload = make_payload(
            "Quero mais informações",
            labels=["pausar_robo", "robo_ativo"]
        )

        with patch("src.routes.webhook.pensar_e_responder") as mock_ia:
            response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "bot_paused"


# ============================================================
# CENÁRIO 4: Filtros básicos
# ============================================================

class TestFiltrosBasicos:

    def test_ignora_mensagens_de_grupo(self, mock_redis):
        """Mensagens de grupos devem ser ignoradas."""
        payload = make_payload("Oi pessoal", name="GROUP OBRA CENTRO")

        response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "group_ignored"

    def test_ignora_evento_nao_incoming(self, mock_redis):
        """Eventos que não são 'incoming' devem ser ignorados."""
        payload = make_payload("Resposta do bot")
        payload["message_type"] = "outgoing"

        response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "event_ignored"

    def test_ignora_conteudo_vazio(self, mock_redis):
        """Mensagens sem conteúdo de texto devem ser ignoradas."""
        payload = make_payload("", labels=["robo_ativo"])

        response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "no_content"

    def test_deduplicacao_mensagem(self, mock_redis):
        """Mensagem com ID já processado deve ser ignorada."""
        mock_redis.exists.return_value = True
        payload = make_payload("Vi seu anúncio", msg_id="msg_duplicada")

        response = client.post("/api/v1/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "duplicate"


# ============================================================
# CENÁRIO 5: Fluxo completo (simulação de conversa)
# ============================================================

class TestFluxoCompleto:

    def test_fluxo_anuncio_depois_continuacao(self, mock_redis, mock_salvar_cliente, mock_etiquetas):
        """
        Simula o fluxo real:
        1. Cliente envia mensagem com "anúncio" → robô ativa
        2. Cliente envia mensagem de continuação com "robo_ativo" → robô continua
        """
        # Passo 1: Primeiro contato com gatilho
        payload_1 = make_payload("Vi seu anúncio no Instagram", labels=[], msg_id="msg_001")

        with patch("src.routes.webhook.pensar_e_responder"):
            resp_1 = client.post("/api/v1/webhook", json=payload_1)

        assert resp_1.json()["status"] == "processing"
        mock_salvar_cliente.assert_called_once()
        mock_etiquetas.assert_called_once()

        # Reset mocks
        mock_salvar_cliente.reset_mock()
        mock_etiquetas.reset_mock()

        # Passo 2: Continuação (Chatwoot já adicionou "robo_ativo" na conversa)
        payload_2 = make_payload(
            "Preciso de uma escavadeira por 5 dias em Barueri",
            labels=["robo_ativo", "lead_novo"],
            msg_id="msg_002"
        )

        with patch("src.routes.webhook.pensar_e_responder") as mock_ia:
            resp_2 = client.post("/api/v1/webhook", json=payload_2)

        assert resp_2.json()["status"] == "processing"
        # Não deve salvar cliente de novo
        mock_salvar_cliente.assert_not_called()
        # Não deve adicionar etiquetas de novo
        mock_etiquetas.assert_not_called()
