import os
import psycopg2
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração do Banco de Dados via Variáveis de Ambiente
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

SQL_COMMANDS = [
    "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";",
    
    # 1. Clientes
    """CREATE TABLE IF NOT EXISTS clientes (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        nome            VARCHAR(255),
        telefone        VARCHAR(20) UNIQUE NOT NULL,
        origem          VARCHAR(100),
        criado_em       TIMESTAMPTZ DEFAULT NOW(),
        atualizado_em   TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 2. Máquinas
    """CREATE TABLE IF NOT EXISTS maquinas (
        id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        nome                    VARCHAR(255) NOT NULL,
        descricao               TEXT,
        quantidade_total        INT NOT NULL CHECK (quantidade_total >= 0),
        quantidade_disponivel   INT NOT NULL CHECK (quantidade_disponivel >= 0),
        valor_diaria            NUMERIC(10, 2),
        ativo                   BOOLEAN DEFAULT TRUE,
        criado_em               TIMESTAMPTZ DEFAULT NOW(),
        atualizado_em           TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 3. Equipes
    """CREATE TABLE IF NOT EXISTS equipes (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        nome                VARCHAR(255) NOT NULL,
        telefone_whatsapp   VARCHAR(20),
        especialidade       VARCHAR(255),
        ativo               BOOLEAN DEFAULT TRUE,
        criado_em           TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 4. Visitas Técnicas
    """CREATE TABLE IF NOT EXISTS visitas_tecnicas (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        equipe_id           UUID REFERENCES equipes(id) ON DELETE SET NULL,
        descricao_servico   TEXT,
        endereco            TEXT,
        data_visita         DATE NOT NULL,
        turno               VARCHAR(20) CHECK (turno IN ('manha', 'tarde', 'integral')),
        status              VARCHAR(30) NOT NULL DEFAULT 'pendente'
                                CHECK (status IN ('pendente', 'confirmada', 'em_andamento', 'concluida', 'cancelada')),
        criado_em           TIMESTAMPTZ DEFAULT NOW(),
        atualizado_em       TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 5. Locações
    """CREATE TABLE IF NOT EXISTS locacoes (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        maquina_id          UUID NOT NULL REFERENCES maquinas(id) ON DELETE RESTRICT,
        endereco_entrega    TEXT,
        data_inicio         DATE NOT NULL,
        data_fim            DATE,
        status              VARCHAR(30) NOT NULL DEFAULT 'solicitada'
                                CHECK (status IN ('solicitada', 'confirmada', 'ativa', 'encerrada', 'cancelada')),
        criado_em           TIMESTAMPTZ DEFAULT NOW(),
        atualizado_em       TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 6. Configurações de Agenda
    """CREATE TABLE IF NOT EXISTS configuracoes_agenda (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chave           VARCHAR(100) UNIQUE NOT NULL,
        valor           TEXT NOT NULL,
        descricao       TEXT,
        atualizado_em   TIMESTAMPTZ DEFAULT NOW()
    );""",
    
    # 7. Índices
    "CREATE INDEX IF NOT EXISTS idx_clientes_telefone ON clientes(telefone);",
    "CREATE INDEX IF NOT EXISTS idx_visitas_data ON visitas_tecnicas(data_visita, status);",
    "CREATE INDEX IF NOT EXISTS idx_visitas_equipe ON visitas_tecnicas(equipe_id, data_visita);",
    "CREATE INDEX IF NOT EXISTS idx_locacoes_maquina ON locacoes(maquina_id, status);",
    
    # 8. Dados Iniciais
    "INSERT INTO configuracoes_agenda (chave, valor, descricao) VALUES ('limite_visitas_por_turno', '3', 'Máximo de visitas técnicas por turno') ON CONFLICT (chave) DO NOTHING;",
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Escavadeira Hidráulica', 'Escavadeira 20 toneladas', 2, 2, 1500.00) ON CONFLICT DO NOTHING;",
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Betoneira 400L', 'Betoneira monofásica', 5, 5, 150.00) ON CONFLICT DO NOTHING;"
]

def executar_migracao():
    try:
        print(f"Conectando ao banco de dados em {DB_HOST}...")
        conexao = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        conexao.autocommit = True
        cursor = conexao.cursor()
        
        for comando in SQL_COMMANDS:
            try:
                print(f"Executando comando: {comando[:50]}...")
                cursor.execute(comando)
            except Exception as e:
                print(f"⚠️ Aviso em comando específico: {e}")
        
        print("✅ SUCESSO! Banco de dados configurado.")
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"❌ ERRO Fatal na migração: {e}")

if __name__ == "__main__":
    executar_migracao()
