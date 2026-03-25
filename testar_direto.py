from fastapi.testclient import TestClient
from main import app
import time

client = TestClient(app)

# 1. Simulação de um NOVO CLIENTE vindo de um anúncio
payload_novo_cliente = {
    "event": "message_created",
    "message_type": "incoming",
    "content": "Olá, vi seu anúncio no Instagram e gostaria de alugar uma Escavadeira Hidráulica.",
    "conversation": {
        "id": 12345,
        "labels": []
    },
    "sender": {
        "id": 1,
        "name": "João Silva Teste",
        "phone_number": "+5511999999999"
    }
}

def rodar_teste():
    print("\n--- TESTANDO: Primeiro contato via Anúncio ---")
    response = client.post("/webhook", json=payload_novo_cliente)
    print(f"Status do Webhook: {response.status_code}")
    print(f"Resposta: {response.json()}")
    
    # Como o processamento é BackgroundTask, precisamos dar um tempo para os prints aparecerem
    print("\nAguardando processamento da BackgroundTask (IA pensando)...")
    time.sleep(15) 

    print("\n--- TESTANDO: Continuação do atendimento ---")
    payload_continuidade = payload_novo_cliente.copy()
    payload_continuidade["content"] = "Preciso dela para uma obra em Barueri por 5 dias."
    payload_continuidade["conversation"]["labels"] = ["robo_ativo"]
    
    response = client.post("/webhook", json=payload_continuidade)
    print(f"Status do Webhook: {response.status_code}")
    print(f"Resposta: {response.json()}")
    
    time.sleep(15)

if __name__ == "__main__":
    rodar_teste()
