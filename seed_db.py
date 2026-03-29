import os
import psycopg2
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração do Banco de Dados via Variáveis de Ambiente
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "db_construtora")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "72d889c22343e475218d")
DB_PORT = os.getenv("DB_PORT", "5432")

# Senha em Texto Puro para facilitar testes
BCRYPT_PASS = "123456" # Senha real: '123456'

SQL_SEED = [
    # 1. Garantir que a tabela de usuários existe (caso o Spring Boot ainda não tenha rodado)
    """CREATE TABLE IF NOT EXISTS usuarios (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        nome            VARCHAR(255) NOT NULL,
        email           VARCHAR(255) UNIQUE NOT NULL,
        senha_hash      VARCHAR(255) NOT NULL,
        perfil          VARCHAR(30) NOT NULL,
        ativo           BOOLEAN DEFAULT TRUE,
        criado_em       TIMESTAMPTZ DEFAULT NOW()
    );""",

    # 2. Inserir Usuários de Teste (Admin, Gerente, Técnico)
    f"INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES ('Administrador', 'admin@olaru.com', '{BCRYPT_PASS}', 'ADMIN') ON CONFLICT (email) DO UPDATE SET senha_hash = EXCLUDED.senha_hash;",
    f"INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES ('Gerente de Obras', 'gerente@olaru.com', '{BCRYPT_PASS}', 'GERENTE') ON CONFLICT (email) DO UPDATE SET senha_hash = EXCLUDED.senha_hash;",
    f"INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES ('Técnico Carlos', 'carlos@olaru.com', '{BCRYPT_PASS}', 'TECNICO') ON CONFLICT (email) DO UPDATE SET senha_hash = EXCLUDED.senha_hash;",

    # 3. Inserir Máquinas
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Escavadeira Hidráulica 20T', 'Escavadeira para grandes obras', 2, 2, 1200.00) ON CONFLICT DO NOTHING;",
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Betoneira 400L', 'Betoneira monofásica', 10, 8, 150.00) ON CONFLICT DO NOTHING;",
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Andaime Fachadeiro', 'Módulo de 2m x 1m', 50, 45, 10.00) ON CONFLICT DO NOTHING;",
    "INSERT INTO maquinas (nome, descricao, quantidade_total, quantidade_disponivel, valor_diaria) VALUES ('Gerador 50kVA', 'Gerador diesel silenciado', 3, 1, 450.00) ON CONFLICT DO NOTHING;",

    # 4. Inserir Clientes de Exemplo
    "INSERT INTO clientes (nome, telefone, origem) VALUES ('JOÃO SILVA', '55988887777', 'WhatsApp Bot') ON CONFLICT (telefone) DO NOTHING;",
    "INSERT INTO clientes (nome, telefone, origem) VALUES ('MARIA OLIVEIRA', '55911223344', 'Anúncio Facebook') ON CONFLICT (telefone) DO NOTHING;",
    "INSERT INTO clientes (nome, telefone, origem) VALUES ('CONSTRUTORA NORTE', '55944556677', 'Indicação') ON CONFLICT (telefone) DO NOTHING;"
]

def popular_banco():
    try:
        print(f"Conectando ao banco {DB_NAME} em {DB_HOST}...")
        conexao = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        conexao.autocommit = True
        cursor = conexao.cursor()
        
        for comando in SQL_SEED:
            print(f"Executando: {comando[:60]}...")
            cursor.execute(comando)
        
        # 5. Criar algumas visitas para hoje para teste visual
        hoje = "NOW()"
        cursor.execute("SELECT id FROM clientes LIMIT 3;")
        cids = [row[0] for row in cursor.fetchall()]
        
        if cids:
            cursor.execute(f"INSERT INTO visitas_tecnicas (cliente_id, descricao_servico, endereco, data_visita, turno, status) VALUES ('{cids[0]}', 'Manutenção corretiva', 'Rua das Pedras, 123', CURRENT_DATE, 'manha', 'pendente') ON CONFLICT DO NOTHING;")
            cursor.execute(f"INSERT INTO visitas_tecnicas (cliente_id, descricao_servico, endereco, data_visita, turno, status) VALUES ('{cids[1]}', 'Instalação de andaimes', 'Av. Litorânea, S/N', CURRENT_DATE, 'tarde', 'confirmada') ON CONFLICT DO NOTHING;")
            if len(cids) > 2:
                cursor.execute(f"INSERT INTO visitas_tecnicas (cliente_id, descricao_servico, endereco, data_visita, turno, status) VALUES ('{cids[2]}', 'Verificação de gerador', 'Shopping Ilha', CURRENT_DATE, 'integral', 'em_andamento') ON CONFLICT DO NOTHING;")

        print("✅ SUCESSO! Banco de dados populado com dados de teste.")
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"❌ ERRO ao popular banco: {e}")

if __name__ == "__main__":
    popular_banco()
