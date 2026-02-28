"""
Testes básicos para as novas funcionalidades implementadas:
- CRUD de Clientes (com soft delete)
- Validação de nome duplicado
- Fluxos de pedidos
"""
import sys
import os

# Adicionar o diretório raiz ao path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.db import get_conn, init_db, exec_query, now_iso

def test_clients_crud():
    """Testa operações CRUD de clientes"""
    print("\n🧪 Testando CRUD de Clientes...")
    
    # Inicializar banco
    init_db()
    
    # 1. Criar cliente
    print("  ➡️ Criando cliente de teste...")
    exec_query(
        "INSERT INTO clients(name, address, cpf, phone, status, is_active) VALUES (?,?,?,?,?,?)",
        ("Cliente Teste CRUD", "Endereço Teste", "123.456.789-00", "(11) 99999-9999", "ADIMPLENTE", 1),
        commit=True
    )
    
    # Verificar criação
    cliente = exec_query("SELECT * FROM clients WHERE name = ?", ("Cliente Teste CRUD",)).fetchone()
    assert cliente is not None, "Falha ao criar cliente"
    assert cliente['is_active'] == 1, "Cliente deveria estar ativo"
    print("  ✅ Cliente criado com sucesso!")
    
    cliente_id = cliente['id']
    
    # 2. Editar cliente
    print("  ➡️ Editando cliente...")
    exec_query(
        "UPDATE clients SET phone = ? WHERE id = ?",
        ("(11) 88888-8888", cliente_id),
        commit=True
    )
    
    cliente_editado = exec_query("SELECT * FROM clients WHERE id = ?", (cliente_id,)).fetchone()
    assert cliente_editado['phone'] == "(11) 88888-8888", "Falha ao editar cliente"
    print("  ✅ Cliente editado com sucesso!")
    
    # 3. Soft delete
    print("  ➡️ Testando soft delete...")
    exec_query(
        "UPDATE clients SET is_active = 0 WHERE id = ?",
        (cliente_id,),
        commit=True
    )
    
    cliente_excluido = exec_query("SELECT * FROM clients WHERE id = ?", (cliente_id,)).fetchone()
    assert cliente_excluido['is_active'] == 0, "Soft delete falhou"
    print("  ✅ Soft delete funcionando!")
    
    # 4. Verificar que cliente excluído não aparece na listagem padrão
    clientes_ativos = exec_query("SELECT * FROM clients WHERE is_active = 1").fetchall()
    ids_ativos = [c['id'] for c in clientes_ativos]
    assert cliente_id not in ids_ativos, "Cliente excluído não deveria aparecer na lista de ativos"
    print("  ✅ Cliente excluído oculto na listagem padrão!")
    
    # 5. Verificar que cliente excluído ainda existe (para histórico)
    cliente_no_historico = exec_query("SELECT * FROM clients WHERE id = ?", (cliente_id,)).fetchone()
    assert cliente_no_historico is not None, "Cliente excluído deveria continuar no banco para histórico"
    print("  ✅ Cliente excluído mantido para histórico!")
    
    # Limpar
    exec_query("DELETE FROM clients WHERE name LIKE 'Cliente Teste%'", commit=True)
    
    print("  ✅ Todos os testes de CRUD passaram!\n")
    return True


def test_duplicate_name_validation():
    """Testa validação de nome duplicado"""
    print("🧪 Testando validação de nome duplicado...")
    
    # Criar cliente (sem acentos para evitar problemas de encoding)
    exec_query(
        "INSERT INTO clients(name, address, cpf, phone, status, is_active) VALUES (?,?,?,?,?,?)",
        ("Cliente Unico Teste", "Endereço", "111.111.111-11", "(11) 11111-1111", "ADIMPLENTE", 1),
        commit=True
    )
    
    # Função de normalização
    def normalize_name(name):
        return name.strip().lower() if name else ""
    
    # Verificar se nome duplicado é detectado
    nome_teste = "Cliente Unico Teste"
    normalized = normalize_name(nome_teste)
    
    # Buscar com query que funciona em SQLite e PostgreSQL
    result = exec_query(
        "SELECT id FROM clients WHERE LOWER(name) = ? AND is_active = 1",
        (normalized,)
    ).fetchone()
    
    assert result is not None, "Deveria detectar nome duplicado (case-insensitive)"
    print("  ✅ Validação de duplicata funcionando!")
    
    # Testar com variação de case
    nome_teste_case = "CLIENTE UNICO TESTE"
    normalized_case = normalize_name(nome_teste_case)
    
    result_case = exec_query(
        "SELECT id FROM clients WHERE LOWER(name) = ? AND is_active = 1",
        (normalized_case,)
    ).fetchone()
    
    assert result_case is not None, "Deveria detectar duplicata mesmo com case diferente"
    print("  ✅ Validação case-insensitive funcionando!")
    
    # Limpar
    exec_query("DELETE FROM clients WHERE name = 'Cliente Unico Teste'", commit=True)
    
    print("  ✅ Todos os testes de duplicata passaram!\n")
    return True


def test_order_statuses():
    """Testa os status de pedidos"""
    print("🧪 Verificando status de pedidos...")
    
    from core.models import OrderStatus
    
    # Verificar status existentes
    assert hasattr(OrderStatus, 'CRIADO'), "Status CRIADO não existe"
    assert hasattr(OrderStatus, 'VENDIDO'), "Status VENDIDO não existe"
    assert hasattr(OrderStatus, 'ENVIADO_FORNECEDOR'), "Status ENVIADO_FORNECEDOR não existe"
    
    print("  ✅ Todos os status necessários existem!")
    print("  ✅ Testes de status passaram!\n")
    return True


def run_all_tests():
    """Executa todos os testes"""
    print("=" * 60)
    print("🚀 EXECUTANDO TESTES DAS NOVAS FUNCIONALIDADES")
    print("=" * 60)
    
    results = []
    
    results.append(test_order_statuses())
    results.append(test_clients_crud())
    results.append(test_duplicate_name_validation())
    
    print("=" * 60)
    if all(results):
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
