#!/usr/bin/env python3
"""
Script de migração: SQLite → PostgreSQL

Uso:
1. Configure DATABASE_URL no ambiente
2. Execute: python migrate_to_postgres.py
3. O script criará as tabelas e migrará os dados

ATENÇÃO: Isso sobrescreverá dados existentes no PostgreSQL!
"""

import os
import sqlite3
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except ImportError:
    # PostgreSQL não disponível
    print("❌ PostgreSQL não disponível. Instale com: pip install psycopg2-binary")
    exit(1)
from core.db import SCHEMA_SQL_PG, to_json, from_json

# Configurações
SQLITE_DB = os.path.join(os.path.dirname(__file__), "exonvais.db")
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Erro: DATABASE_URL não configurada!")
    print("Configure a variável de ambiente DATABASE_URL primeiro.")
    exit(1)

def migrate_table(table_name, sqlite_conn, pg_conn):
    """Migra uma tabela específica"""
    print(f"📋 Migrando tabela: {table_name}")

    # Buscar dados do SQLite
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()

    if not rows:
        print(f"   ℹ️ Tabela {table_name} vazia, pulando...")
        return

    # Inserir no PostgreSQL
    pg_cur = pg_conn.cursor()

    # Obter nomes das colunas
    columns = [desc[0] for desc in sqlite_cur.description]

    # Criar query de insert
    placeholders = ','.join(['%s'] * len(columns))
    query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

    # Inserir dados
    for row in rows:
        values = []
        for col_name, value in zip(columns, row):
            # Converter tipos se necessário
            if isinstance(value, str) and col_name in ['notes_struct', 'notes_free', 'photos']:
                # Garantir que JSON strings sejam válidas
                try:
                    from_json(value, {})
                    values.append(value)
                except:
                    values.append('{}')
            else:
                values.append(value)

        pg_cur.execute(query, values)

    pg_conn.commit()
    print(f"   ✅ {len(rows)} registros migrados")

def main():
    print("🚀 Iniciando migração SQLite → PostgreSQL")
    print(f"📁 SQLite: {SQLITE_DB}")
    print(f"🗄️ PostgreSQL: {(DATABASE_URL[:50] + '...') if DATABASE_URL else 'NÃO CONFIGURADO'}")

    # Conectar aos bancos
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    pg_conn = psycopg2.connect(DATABASE_URL)

    try:
        # Criar tabelas no PostgreSQL
        print("🏗️ Criando tabelas no PostgreSQL...")
        pg_cur = pg_conn.cursor()
        pg_cur.execute(SCHEMA_SQL_PG)
        pg_conn.commit()

        # Lista de tabelas para migrar (ordem importa por causa das FKs)
        tables = [
            'clients',
            'product_catalog',
            'orders',
            'shipments',
            'nonconformities',
            'finance_entries',
            'payment_batches',
            'audit_log',
            'config',
            'stock_items'
        ]

        # Migrar cada tabela
        for table in tables:
            try:
                migrate_table(table, sqlite_conn, pg_conn)
            except Exception as e:
                print(f"   ❌ Erro na tabela {table}: {e}")
                continue

        print("🎉 Migração concluída!")

    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        pg_conn.rollback()

    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()