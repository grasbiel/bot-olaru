import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from src.services.ai_service import pensar_e_responder

@pytest.mark.asyncio
async def test_antiban_behavior():
    """
    Testa se o comportamento anti-ban está funcionando:
    1. Chamada de 'digitando...' (presence) ativa.
    2. Delay mínimo respeitado.
    3. Chamada de envio de mensagem.
    4. Chamada de 'digitando...' desativada.
    """
    
    id_conversa = 123
    telefone = "5511999999999"
    mensagem = "Olá, gostaria de alugar uma máquina."
    
    # Mock do Agent do Agno
    with patch("src.services.ai_service.agente_construtora") as mock_agente:
        mock_agente.run.return_value = MagicMock(content="Claro! Temos várias máquinas disponíveis.")
        
        # Mocks dos serviços externos
        with patch("src.services.ai_service.simular_digitacao") as mock_digitacao, \
             patch("src.services.ai_service.enviar_mensagem_chatwoot") as mock_enviar, \
             patch("src.services.ai_service.verificar_limite_mensagens", return_value=True), \
             patch("src.services.ai_service.incrementar_contador_mensagens"):
            
            start_time = time.time()
            
            # Executa a função
            await pensar_e_responder(mensagem, id_conversa, telefone)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verificações
            
            # 1. Deve ter começado a digitar
            mock_digitacao.assert_any_call(telefone, True)
            
            # 2. O delay deve ser de pelo menos 5 segundos (conforme lógica no código)
            assert duration >= 5, f"O delay anti-ban foi muito curto: {duration}s"
            
            # 3. Deve ter enviado a mensagem
            mock_enviar.assert_called_once_with(id_conversa, "Claro! Temos várias máquinas disponíveis.")
            
            # 4. Deve ter parado de digitar
            mock_digitacao.assert_any_call(telefone, False)
            
            print(f"\n✅ Teste anti-ban concluído com sucesso. Duração: {duration:.2f}s")

@pytest.mark.asyncio
async def test_handoff_on_error():
    """
    Testa se o handoff é acionado em caso de erro crítico na IA.
    """
    id_conversa = 456
    telefone = "5511888888888"
    
    with patch("src.services.ai_service.agente_construtora") as mock_agente:
        # Simula erro na execução do agente
        mock_agente.run.side_effect = Exception("Erro de conexão com o LLM")
        
        with patch("src.services.ai_service.enviar_mensagem_chatwoot") as mock_enviar, \
             patch("src.services.ai_service.iniciar_handoff_humano") as mock_handoff, \
             patch("src.services.ai_service.verificar_limite_mensagens", return_value=True):
            
            await pensar_e_responder("Oi", id_conversa, telefone)
            
            # Deve enviar mensagem de fallback e acionar handoff
            mock_enviar.assert_called_once()
            mock_handoff.assert_called_once_with(id_conversa, "erro_excecao_bot")
            
            print("\n✅ Teste de handoff em erro concluído com sucesso.")

if __name__ == "__main__":
    import sys
    # Simulação básica para rodar sem pytest se necessário
    asyncio.run(test_antiban_behavior())
    asyncio.run(test_handoff_on_error())
