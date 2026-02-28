"""
Migração 001: Adicionar campo is_active na tabela clients
- Adiciona coluna is_active (default 1 = ativo)
- Atualiza clientes existentes para is_active = 1
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_conn, is_postgres_conn, exec_query

def run_migration():
    print("🚀 Executando migração 001: Adicionar is_active aos clientes...")
    
    conn = get_conn()
    is_pg = is_postgres_conn(conn)
    
    try:
        # Verificar se a coluna já existe
        if is_pg:
            # PostgreSQL
            result = exec_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clients' AND column_name = 'is_active'
            """).fetchone()
        else:
            # SQLite
            result = exec_query("PRAGMA table_info(clients)").fetchall()
            has_column = any(col['name'] == 'is_active' for col in result)
            result = {'column_name': 'is_active'} if has_column else None
        
        if result:
            print("✅ Coluna 'is_active' já existe. Migração não necessária.")
            return True
        
        # Adicionar coluna is_active
        print("📝 Adicionando coluna 'is_active'...")
        
        if is_pg:
            exec_query("ALTER TABLE clients ADD COLUMN is_active INTEGER DEFAULT 1", commit=True)
        else:
            exec_query("ALTER TABLE clients ADD COLUMN is_active INTEGER DEFAULT 1", commit=True)
        
        # Atualizar registros existentes
        print("📝 Atualizando clientes existentes para is_active = 1...")
        exec_query("UPDATE clients SET is_active = 1 WHERE is_active IS NULL", commit=True)
        
        print("✅ Migração concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False

if __name__ == "__main__":
    run_migration()
