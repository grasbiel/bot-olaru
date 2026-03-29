import psycopg2

DB_HOST = "92.113.39.140"
DB_NAME = "db_construtora"
DB_USER = "postgres"
DB_PASS = "72d889c22343e475218d"
DB_PORT = "5432"

# SQL para apagar e recriar tudo conforme a especificação exata
SQL_CLEAN_SETUP = """
DROP TABLE IF EXISTS locacoes CASCADE;
DROP TABLE IF EXISTS visitas_tecnicas CASCADE;
DROP TABLE IF EXISTS maquinas CASCADE;
DROP TABLE IF EXISTS equipes CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;
DROP TABLE IF EXISTS configuracoes_agenda CASCADE;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE clientes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255),
    telefone        VARCHAR(20) UNIQUE NOT NULL,
    origem          VARCHAR(100),
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE maquinas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                    VARCHAR(255) NOT NULL,
    descricao               TEXT,
    quantidade_total        INT NOT NULL CHECK (quantidade_total >= 0),
    quantidade_disponivel   INT NOT NULL CHECK (quantidade_disponivel >= 0),
    valor_diaria            NUMERIC(10, 2),
    ativo                   BOOLEAN DEFAULT TRUE,
    criado_em               TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE equipes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                VARCHAR(255) NOT NULL,
    telefone_whatsapp   VARCHAR(20),
    especialidade       VARCHAR(255),
    ativo               BOOLEAN DEFAULT TRUE,
    criado_em           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE visitas_tecnicas (
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
);

CREATE TABLE locacoes (
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
);

CREATE TABLE configuracoes_agenda (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chave           VARCHAR(100) UNIQUE NOT NULL,
    valor           TEXT NOT NULL,
    descricao       TEXT,
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clientes_telefone ON clientes(telefone);
CREATE INDEX idx_visitas_data ON visitas_tecnicas(data_visita, status);
CREATE INDEX idx_visitas_equipe ON visitas_tecnicas(equipe_id, data_visita);
CREATE INDEX idx_locacoes_maquina ON locacoes(maquina_id, status);

INSERT INTO configuracoes_agenda (chave, valor, descricao) VALUES ('limite_visitas_por_turno', '3', 'Máximo de visitas técnicas por turno');
INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Escavadeira Hidráulica', 'Escavadeira 20 toneladas para terraplanagem', 2, 2, 1500.00);
INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Betoneira 400L', 'Betoneira monofásica', 5, 5, 150.00);
"""

def resetar_banco():
    try:
        print("Conectando para RESET TOTAL do banco...")
        conexao = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
        cursor = conexao.cursor()
        cursor.execute(SQL_CLEAN_SETUP)
        conexao.commit()
        print("✅ SUCESSO! Banco de dados limpo e recriado com a especificação correta.")
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"❌ ERRO Fatal: {e}")

if __name__ == "__main__":
    resetar_banco()
