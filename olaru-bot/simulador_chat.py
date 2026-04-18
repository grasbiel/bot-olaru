import sys
import os
from dotenv import load_dotenv

# Adiciona a raiz do projeto ao sys.path para conseguir importar de src.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.ai_service import criar_agente

def iniciar_simulacao():
    print("="*50)
    print("👷 OLARA CONSOLE INTERATIVO 👷")
    print("Digite 'sair' para encerrar a conversa.")
    print("="*50)
    
    # Cria uma instância direta do agente (sem passar por webhooks)
    agente = criar_agente()
    
    sessao_id = "sessao_simulacao_01"
    telefone_falso = "+5511999999999"
    nome = "Grasbiel"
    
    print(f"\n[SISTEMA]: Você está logado como {nome} ({telefone_falso}). O contexto inicial foi injetado.")
    print("Pode mandar um 'Oi, vim pelo anúncio' para começar.\n")
    
    while True:
        try:
            mensagem = input("Você: ")
            if not mensagem.strip():
                continue
                
            if mensagem.lower() in ['sair', 'exit', 'quit']:
                print("Encerrando simulação...")
                break
                
            # Nós simulamos exatamente o mesmo prompt que o webhook injeta:
            prompt_injetado = (
                f"Mensagem do cliente: {mensagem}\n\n"
                f"--- CONTEXTO DO ATENDIMENTO ---\n"
                f"Nome no WhatsApp: {nome}\n"
                f"Telefone: {telefone_falso}\n"
                f"Etiquetas ativas: robo_ativo\n"
                f"Histórico CRM: Sem histórico anterior.\n"
            )
            
            print("OLARA digitando...", end="")
            sys.stdout.flush() # Força o print p/ tela antes de terminar de processar
            
            # Chama a inteligência processando o texto igualzinho em produção
            resposta = agente.run(prompt_injetado, session_id=sessao_id, user_id=telefone_falso)
            
            # Apaga o "digitando..." e imprime a resposta
            print(f"\rOLARA: {resposta.content}\n")
            
        except KeyboardInterrupt:
            print("\nEncerrando simulação...")
            break
        except Exception as e:
            print(f"\r[ERRO NO ROBO]: {e}\n")

if __name__ == "__main__":
    iniciar_simulacao()
