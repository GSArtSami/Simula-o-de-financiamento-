import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

def migrate_sqlite_to_postgres(sqlite_path, postgres_url):
    # conecta no SQLite local
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cur = sqlite_conn.cursor()

    # conecta no Postgres remoto (ou local, se docker-compose)
    pg_conn = psycopg2.connect(postgres_url)
    pg_cur = pg_conn.cursor()

    # cria tabelas no Postgres, se não existirem
    pg_cur.execute("""
    CREATE TABLE IF NOT EXISTS cliente (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        renda REAL NOT NULL,
        contato TEXT NOT NULL
    );
    """)
    pg_cur.execute("""
    CREATE TABLE IF NOT EXISTS simulacao (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES cliente(id),
        valor_imovel REAL NOT NULL,
        prazo INTEGER NOT NULL,
        juros REAL NOT NULL,
        valor_parcela REAL NOT NULL,
        tipo_amortizacao TEXT NOT NULL,
        enquadramento TEXT,
        primeira_parcela REAL,
        ultima_parcela REAL,
        subsídio REAL,
        entrada REAL,
        fgts_utilizado REAL
    );
    """)

    # migra clientes
    sqlite_cur.execute("SELECT id, nome, renda, contato FROM cliente")
    clientes = sqlite_cur.fetchall()
    if clientes:
        execute_values(pg_cur,
            "INSERT INTO cliente (id, nome, renda, contato) VALUES %s ON CONFLICT (id) DO NOTHING",
            clientes
        )

    # migra simulações
    sqlite_cur.execute("""
        SELECT id, cliente_id, valor_imovel, prazo, juros, valor_parcela,
               tipo_amortizacao, enquadramento, primeira_parcela,
               ultima_parcela, subsídio, entrada, fgts_utilizado
        FROM simulacao
    """)
    simulacoes = sqlite_cur.fetchall()
    if simulacoes:
        execute_values(pg_cur, """
            INSERT INTO simulacao (
                id, cliente_id, valor_imovel, prazo, juros, valor_parcela,
                tipo_amortizacao, enquadramento, primeira_parcela,
                ultima_parcela, subsídio, entrada, fgts_utilizado
            )
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """, simulacoes)

    # confirma e fecha
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    sqlite_path = os.getenv("OLD_SQLITE_DB", "simulador.db")
    postgres_url = os.getenv("DATABASE_URL")

    if not postgres_url:
        raise ValueError("Defina a variável de ambiente DATABASE_URL apontando para seu Postgres")

    migrate_sqlite_to_postgres(sqlite_path, postgres_url)
