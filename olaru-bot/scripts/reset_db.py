import psycopg2
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "db_construtora")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "72d889c22343e475218d")
DB_PORT = os.getenv("DB_PORT", "5432")

# SQL para RESET TOTAL (Apaga o esquema e recria limpo para o Flyway)
SQL_RESET = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

def resetar_banco():
    try:
        print(f"Conectando ao banco {DB_NAME} em {DB_HOST}...")
        conexao = psycopg2.connect(
            host=DB_HOST, 
            database=DB_NAME, 
            user=DB_USER, 
            password=DB_PASS, 
            port=DB_PORT
        )
        conexao.autocommit = True
        cursor = conexao.cursor()
        
        print("Executando DROP SCHEMA public CASCADE...")
        cursor.execute(SQL_RESET)
        
        print("✅ SUCESSO! O banco de dados foi zerado.")
        print("Agora o Flyway (Java) poderá recriar as tabelas corretamente no próximo Deploy.")
        
        cursor.close()
        conexao.close()
    except Exception as e:
        print(f"❌ ERRO Fatal ao resetar banco: {e}")

if __name__ == "__main__":
    resetar_banco()
