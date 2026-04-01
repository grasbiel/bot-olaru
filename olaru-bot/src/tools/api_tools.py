import requests
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from src.config import JAVA_API_URL, logger
from src.services.chatwoot import iniciar_handoff_humano, adicionar_etiqueta_chatwoot

# --- Modelos de Dados (Pydantic) para Validação ---

class LeadStatusUpdate(BaseModel):
    telefone: str = Field(..., description="Telefone do cliente (apenas números).")
    status: str = Field(..., description="Status: 'quente', 'morno', 'frio', 'qualificado'.")
    resumo: Optional[str] = Field(None, description="Resumo executivo da conversa.")

    @validator("status")
    def validate_status(cls, v):
        allowed = ["quente", "morno", "frio", "qualificado"]
        if v.lower() not in allowed:
            raise ValueError(f"Status deve ser um de: {allowed}")
        return v.lower()

class VisitaTecnicaRequest(BaseModel):
    telefone: str = Field(..., description="Telefone do cliente.")
    descricao: str = Field(..., description="O que o cliente precisa (ex: reforma de banheiro).")
    endereco: str = Field(..., description="Endereço completo da obra.")
    data: str = Field(..., description="Data no formato YYYY-MM-DD.")
    turno: str = Field(..., description="Turno: 'MANHA' ou 'TARDE'.")

    @validator("data")
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Data deve estar no formato YYYY-MM-DD.")

    @validator("turno")
    def validate_turno(cls, v):
        if v.upper() not in ["MANHA", "TARDE"]:
            raise ValueError("Turno deve ser 'MANHA' ou 'TARDE'.")
        return v.upper()

# --- Ferramentas Refinadas ---

def classificar_lead(id_conversa: int, telefone: str, status: str, resumo: Optional[str] = None) -> str:
    """
    Atualiza a classificação estratégica do lead no sistema. 
    Use esta ferramenta sempre que identificar o potencial do cliente ou concluir um atendimento.
    """
    try:
        # Validação via Pydantic
        update = LeadStatusUpdate(telefone=telefone, status=status, resumo=resumo)
        
        logger.info("tool_call", tool="classificar_lead", telefone=update.telefone, status=update.status)
        
        # 1. Atualiza Chatwoot
        adicionar_etiqueta_chatwoot(id_conversa, [f"lead_{update.status}"])
        
        # 2. Sincroniza API Java
        payload = {"statusLead": update.status}
        if update.resumo:
            payload["resumoConversa"] = update.resumo
            
        url = f"{JAVA_API_URL}/clientes/telefone/{update.telefone}"
        response = requests.patch(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return f"Sucesso: Lead classificado como '{update.status}' no CRM e Chatwoot."
        return f"Aviso: Lead etiquetado no Chatwoot, mas o CRM retornou status {response.status_code}."
        
    except ValueError as e:
        return f"Erro de validação: {str(e)}"
    except Exception as e:
        logger.error("tool_error", tool="classificar_lead", error=str(e))
        return "Erro técnico ao tentar classificar o lead. Tente novamente em instantes."

def acionar_handoff_humano(id_conversa: int, motivo: str) -> str:
    """
    Transfere o atendimento para um atendente humano e interrompe o robô.
    Use quando o cliente pedir para falar com uma pessoa ou quando houver um problema técnico.
    """
    logger.info("tool_call", tool="handoff", id_conversa=id_conversa, motivo=motivo)
    try:
        iniciar_handoff_humano(id_conversa, motivo)
        return "Atendimento transferido para a equipe humana. Eu (robô) fui pausado."
    except Exception as e:
        logger.error("tool_error", tool="handoff", error=str(e))
        return "Falha ao transferir para humano. Por favor, aguarde um momento."

def buscar_dados_cliente(telefone: str) -> str:
    """
    Consulta o cadastro do cliente para saber o nome e histórico. 
    Chame esta ferramenta sempre que um novo contato for identificado.
    """
    try:
        url = f"{JAVA_API_URL}/clientes/telefone/{telefone.replace('+', '')}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return (f"CLIENTE ENCONTRADO: Nome={data.get('nome')}, "
                    f"Status={data.get('statusLead')}, "
                    f"Histórico={data.get('resumoConversa') or 'Sem histórico'}")
        
        if response.status_code == 404:
            return "CLIENTE NOVO: Não existe cadastro para este número. É necessário coletar o nome."
            
        return "O serviço de consulta de clientes está temporariamente indisponível."
    except Exception as e:
        logger.error("tool_error", tool="buscar_cliente", error=str(e))
        return "Erro ao acessar a base de clientes."

def verificar_estoque(maquina_nome: str) -> str:
    """
    Consulta o estoque real de máquinas para locação. 
    Use quando o cliente demonstrar interesse em alugar equipamentos.
    """
    try:
        # Normalização simples do nome para busca
        nome_busca = maquina_nome.strip().lower()
        url = f"{JAVA_API_URL}/maquinas/estoque/{nome_busca}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            qty = data.get('quantidadeDisponivel', 0)
            if qty > 0:
                return f"ESTOQUE DISPONÍVEL: '{data.get('nome')}' possui {qty} unidades prontas para locação."
            return f"SEM ESTOQUE: '{data.get('nome')}' está esgotado no momento."
            
        if response.status_code == 404:
            return f"NÃO LOCALIZADO: Não trabalhamos com '{maquina_nome}' ou o nome está incorreto."
            
        return "Não foi possível validar o estoque agora."
    except Exception as e:
        logger.error("tool_error", tool="estoque", error=str(e))
        return "Ocorreu um erro ao consultar o catálogo de máquinas."

def consultar_disponibilidade_agenda(data: str, turno: str) -> str:
    """
    Verifica se existe vaga para visita técnica em um dia e turno específico.
    A data deve ser YYYY-MM-DD e o turno deve ser 'MANHA' ou 'TARDE'.
    """
    try:
        # Validação simples de input antes da chamada
        req = VisitaTecnicaRequest(telefone="0", descricao="validação", endereco="validação", data=data, turno=turno)
        
        params = {"data": req.data, "turno": req.turno}
        url = f"{JAVA_API_URL}/visitas/disponibilidade"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            res = response.json()
            if res.get("disponivel"):
                return f"DISPONÍVEL: Temos vaga para o dia {data} ({turno}). Pode prosseguir com o agendamento."
            return f"INDISPONÍVEL: O turno {turno} do dia {data} já está lotado."
            
        return "Erro na API de agendamentos. Tente consultar outro período."
    except ValueError as e:
        return f"Formato inválido: {str(e)}"
    except Exception as e:
        logger.error("tool_error", tool="agenda", error=str(e))
        return "O sistema de agenda está offline. Peça para o cliente aguardar."

def registrar_visita_tecnica(telefone: str, descricao: str, endereco: str, data: str, turno: str) -> str:
    """
    Cria oficialmente o agendamento da visita técnica no banco de dados da empresa.
    SÓ CHAME ESTA FERRAMENTA após confirmar que o cliente aceita a data e turno.
    """
    try:
        # Validação rigorosa via Pydantic
        visita = VisitaTecnicaRequest(
            telefone=telefone, descricao=descricao, 
            endereco=endereco, data=data, turno=turno
        )
        
        logger.info("tool_call", tool="registrar_visita", telefone=visita.telefone)
        
        payload = {
            "telefone": visita.telefone.replace("+", ""),
            "descricaoServico": visita.descricao,
            "endereco": visita.endereco,
            "dataVisita": visita.data,
            "turno": visita.turno
        }
        
        response = requests.post(f"{JAVA_API_URL}/visitas", json=payload, timeout=10)
        
        if response.status_code in [200, 201]:
            result = response.json()
            return f"AGENDAMENTO CONCLUÍDO! Visita confirmada para {visita.data} ({visita.turno}). Protocolo: {result.get('id')}"
            
        return f"Falha no agendamento: O sistema retornou '{response.text}'. Tente novamente."
        
    except ValueError as e:
        return f"Erro nos dados: {str(e)}. Corrija com o cliente."
    except Exception as e:
        logger.error("tool_error", tool="registrar_visita", error=str(e))
        return "Erro técnico catastrófico ao agendar. Notifique o suporte."

def salvar_cliente_no_banco(nome: str, telefone: str) -> Optional[str]:
    """
    Cria um lead novo no CRM.
    Geralmente chamada automaticamente no primeiro contato.
    """
    try:
        payload = {"nome": nome, "telefone": telefone.replace("+", ""), "origem": "WhatsApp (Auto)"}
        response = requests.post(f"{JAVA_API_URL}/clientes", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        return None
    except Exception as e:
        logger.error("api_error", tool="save_client", error=str(e))
        return None
