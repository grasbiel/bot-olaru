-- 1. Trigger Global para atualizado_em
CREATE OR REPLACE FUNCTION fn_atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Tabelas Principais

-- Equipes de campo (necessária para FK em usuários)
CREATE TABLE equipes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                VARCHAR(255) NOT NULL,
    telefone_whatsapp   VARCHAR(20),
    especialidade       VARCHAR(255),
    ativo               BOOLEAN DEFAULT TRUE,
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_equipes_atualizado_em
  BEFORE UPDATE ON equipes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Usuários do painel administrativo (RBAC)
CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    senha_hash      VARCHAR(255) NOT NULL,
    perfil          VARCHAR(30) NOT NULL CHECK (perfil IN ('admin', 'gerente', 'tecnico')),
    equipe_id       UUID REFERENCES equipes(id) ON DELETE SET NULL,
    ativo           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_usuarios_atualizado_em
  BEFORE UPDATE ON usuarios
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Clientes / Leads
CREATE TABLE clientes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255),
    telefone        VARCHAR(20) UNIQUE NOT NULL,
    origem          VARCHAR(100),
    status_lead     VARCHAR(30) DEFAULT 'novo' 
                        CHECK (status_lead IN ('novo', 'quente', 'morno', 'frio', 'qualificado')),
    resumo_conversa TEXT,
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_clientes_atualizado_em
  BEFORE UPDATE ON clientes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Máquinas disponíveis para locação
CREATE TABLE maquinas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                    VARCHAR(255) NOT NULL,
    descricao               TEXT,
    quantidade_total        INT NOT NULL CHECK (quantidade_total >= 0),
    quantidade_disponivel   INT NOT NULL CHECK (quantidade_disponivel >= 0),
    valor_diaria            NUMERIC(10, 2),
    ativo                   BOOLEAN DEFAULT TRUE,
    criado_em               TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_quantidade CHECK (quantidade_disponivel <= quantidade_total)
);

CREATE TRIGGER trg_maquinas_atualizado_em
  BEFORE UPDATE ON maquinas
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Visitas técnicas agendadas
CREATE TABLE visitas_tecnicas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    tecnico_id          UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    descricao_servico   TEXT,
    endereco            TEXT,
    data_visita         DATE NOT NULL,
    turno               VARCHAR(20) CHECK (turno IN ('MANHA', 'TARDE')),
    status              VARCHAR(30) NOT NULL DEFAULT 'pendente'
                            CHECK (status IN ('pendente', 'confirmada', 'em_andamento', 'concluida', 'cancelada')),
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_visitas_atualizado_em
  BEFORE UPDATE ON visitas_tecnicas
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Locações de máquinas
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

CREATE TRIGGER trg_locacoes_atualizado_em
  BEFORE UPDATE ON locacoes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- 3. Tabelas de Suporte

-- Histórico de mensagens por conversa (auditoria)
CREATE TABLE conversas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    conteudo        TEXT NOT NULL,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Tabelas do Framework Agno (Memória da IA)
CREATE TABLE agent_sessions (
    session_id      VARCHAR(255) PRIMARY KEY,
    user_id         VARCHAR(255),
    agent_id        VARCHAR(255),
    memory          JSONB,
    agent_data      JSONB,
    user_data       JSONB,
    session_data    JSONB,
    created_at      BIGINT,
    updated_at      BIGINT
);

CREATE TABLE agent_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     VARCHAR(255) NOT NULL,
    memory      TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Índices de Performance
CREATE INDEX idx_clientes_telefone    ON clientes(telefone);
CREATE INDEX idx_visitas_data         ON visitas_tecnicas(data_visita, status);
CREATE INDEX idx_visitas_tecnico      ON visitas_tecnicas(tecnico_id, data_visita);
CREATE INDEX idx_agent_sessions_user  ON agent_sessions(user_id);
CREATE INDEX idx_agent_memory_user    ON agent_memory(user_id);
