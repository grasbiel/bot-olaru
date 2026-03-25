import requests
import json
import time

URL_WEBHOOK = "http://localhost:8000/webhook"

# 1. Simulação de um NOVO CLIENTE vindo de um anúncio
payload_novo_cliente = {
    "event": "message_created",
    "message_type": "incoming",
    "content": "Olá, vi seu anúncio no Instagram e gostaria de alugar uma Escavadeira Hidráulica.",
    "conversation": {
        "id": 12345,
        "labels": [] # Sem etiquetas ainda
    },
    "sender": {
        "id": 1,
        "name": "João Silva Teste",
        "phone_number": "+5511999999999"
    }
}

def enviar_teste(payload, descricao):
    print(f"\n--- TESTANDO: {descricao} ---")
    try:
        response = requests.post(URL_WEBHOOK, json=payload)
        print(f"Status do Webhook: {response.status_code}")
        print(f"Resposta: {response.json()}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

if __name__ == "__main__":
    # Teste 1: Novo Cliente
    enviar_teste(payload_novo_cliente, "Primeiro contato via Anúncio")
    
    print("\n⚠️  O robô agora deve estar processando e aguardando o delay (10-20s)...")
    print("Aguardando 25 segundos para simular o tempo de resposta do robô...")
    time.sleep(25)
    
    # Teste 2: Continuando Atendimento (Já com a etiqueta 'robo_ativo')
    payload_continuidade = payload_novo_cliente.copy()
    payload_continuidade["content"] = "Preciso dela para uma obra em Barueri por 5 dias."
    payload_continuidade["conversation"]["labels"] = ["robo_ativo"]
    
    enviar_teste(payload_continuidade, "Continuação do atendimento (Etiqueta robo_ativo)")
