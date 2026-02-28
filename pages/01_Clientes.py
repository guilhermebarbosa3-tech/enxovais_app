import streamlit as st
from core.db import get_conn, exec_query, now_iso, init_db, is_postgres_conn
from core.audit import log_change
from ui.components import section

# Garantir que o banco está inicializado (inclui migrações)
init_db()

st.title("👥 Clientes")
conn = get_conn()

# ============================================================================
# VERIFICAR SE COLUNA is_active EXISTE (para compatibilidade com banco antigo)
# ============================================================================
def _has_is_active_column():
    """Verifica se a coluna is_active existe na tabela clients"""
    try:
        if is_postgres_conn(conn):
            result = exec_query("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clients' AND column_name = 'is_active'
            """).fetchone()
            return result is not None
        else:
            # SQLite - tentar uma query simples
            try:
                exec_query("SELECT is_active FROM clients LIMIT 1").fetchone()
                return True
            except:
                return False
    except:
        return False

HAS_IS_ACTIVE = _has_is_active_column()

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def normalize_name(name: str) -> str:
    """Normaliza o nome para comparação (lowercase, sem espaços extras)"""
    return name.strip().lower() if name else ""

def check_duplicate_name(name: str, exclude_id: int = None) -> bool:
    """Verifica se já existe cliente ativo com o mesmo nome (case-insensitive)"""
    normalized = normalize_name(name)
    if not normalized:
        return False
    
    if exclude_id:
        # Excluir o próprio cliente na verificação (para edição)
        if HAS_IS_ACTIVE:
            result = exec_query(
                "SELECT id FROM clients WHERE LOWER(name) = ? AND (is_active = 1 OR is_active IS NULL) AND id != ?",
                (normalized, exclude_id)
            ).fetchone()
        else:
            result = exec_query(
                "SELECT id FROM clients WHERE LOWER(name) = ? AND id != ?",
                (normalized, exclude_id)
            ).fetchone()
    else:
        if HAS_IS_ACTIVE:
            result = exec_query(
                "SELECT id FROM clients WHERE LOWER(name) = ? AND (is_active = 1 OR is_active IS NULL)",
                (normalized,)
            ).fetchone()
        else:
            result = exec_query(
                "SELECT id FROM clients WHERE LOWER(name) = ?",
                (normalized,)
            ).fetchone()
    
    return result is not None

# ============================================================================
# INICIALIZAÇÃO DE SESSION STATE
# ============================================================================
if "show_client_details" not in st.session_state:
    st.session_state["show_client_details"] = None
if "edit_client_id" not in st.session_state:
    st.session_state["edit_client_id"] = None
if "delete_client_id" not in st.session_state:
    st.session_state["delete_client_id"] = None
if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0

# ============================================================================
# CADASTRO DE NOVO CLIENTE
# ============================================================================
section("➕ Novo Cliente")

with st.form(f"novo_cliente_{st.session_state['form_version']}"):
    name = st.text_input("Nome *", placeholder="Nome completo do cliente")
    address = st.text_input("Endereço", placeholder="Rua, número, bairro, cidade")
    cpf = st.text_input("CPF", placeholder="000.000.000-00")
    phone = st.text_input("Telefone", placeholder="(00) 00000-0000")
    status = st.selectbox("Status", ["ADIMPLENTE", "INADIMPLENTE"])
    
    if st.form_submit_button("💾 Salvar Cliente", use_container_width=True):
        if not name or not name.strip():
            st.error("❌ O nome do cliente é obrigatório!")
        elif check_duplicate_name(name):
            st.error("❌ Já existe um cliente cadastrado com esse nome.")
        else:
            if HAS_IS_ACTIVE:
                exec_query(
                    "INSERT INTO clients(name, address, cpf, phone, status, is_active) VALUES (?,?,?,?,?,1)",
                    (name.strip(), address, cpf, phone, status),
                    commit=True
                )
            else:
                exec_query(
                    "INSERT INTO clients(name, address, cpf, phone, status) VALUES (?,?,?,?,?)",
                    (name.strip(), address, cpf, phone, status),
                    commit=True
                )
            st.success("✅ Cliente salvo com sucesso!")
            st.session_state["form_version"] += 1
            st.rerun()

st.divider()

# ============================================================================
# PESQUISA DE CLIENTES
# ============================================================================
section("🔍 Pesquisar Clientes")

col_search, col_status = st.columns([3, 1])

with col_search:
    search_term = st.text_input(
        "Buscar por nome ou telefone",
        placeholder="Digite para pesquisar...",
        label_visibility="collapsed"
    )

with col_status:
    show_inactive = st.checkbox("Mostrar excluídos", value=False)

# ============================================================================
# LISTA DE CLIENTES
# ============================================================================
section("📋 Lista de Clientes")

# Construir query de busca
query = "SELECT * FROM clients WHERE 1=1"
params = []

# Filtro de ativos/inativos (apenas se coluna existe)
if HAS_IS_ACTIVE and not show_inactive:
    query += " AND (is_active = 1 OR is_active IS NULL)"

# Filtro de pesquisa
if search_term:
    query += " AND (LOWER(name) LIKE ? OR phone LIKE ?)"
    search_like = f"%{search_term.lower()}%"
    params.extend([search_like, f"%{search_term}%"])

# Order by (condicional)
if HAS_IS_ACTIVE:
    query += " ORDER BY is_active DESC, name ASC"
else:
    query += " ORDER BY name ASC"

rows = exec_query(query, tuple(params) if params else None).fetchall()

if not rows:
    st.info("📭 Nenhum cliente encontrado.")
else:
    st.write(f"**{len(rows)} cliente(s) encontrado(s)**")
    
    for r in rows:
        is_active = r['is_active'] if 'is_active' in r.keys() else 1
        
        # Container do cliente
        with st.container(border=True):
            col_info, col_actions = st.columns([4, 2])
            
            with col_info:
                # Indicador visual de status (ativo/inativo)
                if not is_active:
                    st.write(f"🚫 **{r['name']}** *(excluído)*")
                else:
                    status_icon = "✅" if r['status'] == "ADIMPLENTE" else "⚠️"
                    st.write(f"#{r['id']} — {status_icon} **{r['name']}** ({r['status']})")
                
                # Info resumida
                if r['phone']:
                    st.caption(f"📱 {r['phone']}")
            
            with col_actions:
                if is_active:
                    btn_col1, btn_col2 = st.columns(2)
                    
                    with btn_col1:
                        if st.button("👁️ Detalhes", key=f"view_{r['id']}", use_container_width=True):
                            st.session_state["show_client_details"] = r['id']
                            st.session_state["edit_client_id"] = None
                            st.session_state["delete_client_id"] = None
                    
                    with btn_col2:
                        if st.button("✏️ Editar", key=f"edit_{r['id']}", use_container_width=True):
                            st.session_state["edit_client_id"] = r['id']
                            st.session_state["show_client_details"] = None
                            st.session_state["delete_client_id"] = None
        
        # ============================================================================
        # MODAL DE DETALHES DO CLIENTE
        # ============================================================================
        if st.session_state["show_client_details"] == r['id']:
            with st.container(border=True):
                st.subheader(f"📋 Detalhes do Cliente: {r['name']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nome:** {r['name']}")
                    st.write(f"**CPF:** {r['cpf'] or 'Não informado'}")
                    st.write(f"**Telefone:** {r['phone'] or 'Não informado'}")
                
                with col2:
                    st.write(f"**Endereço:** {r['address'] or 'Não informado'}")
                    st.write(f"**Status:** {r['status']}")
                
                st.divider()
                
                # Histórico de pedidos do cliente
                pedidos = exec_query(
                    "SELECT id, category, type, product, status, created_at FROM orders WHERE client_id = ? ORDER BY created_at DESC LIMIT 5",
                    (r['id'],)
                ).fetchall()
                
                if pedidos:
                    st.write("**📦 Últimos Pedidos:**")
                    for p in pedidos:
                        st.caption(f"#{p['id']} - {p['category']}/{p['type']}/{p['product']} - {p['status']}")
                else:
                    st.caption("Nenhum pedido registrado.")
                
                st.divider()
                
                # Botões de ação nos detalhes
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("✏️ Editar", key=f"detail_edit_{r['id']}", use_container_width=True):
                        st.session_state["edit_client_id"] = r['id']
                        st.session_state["show_client_details"] = None
                        st.rerun()
                
                with action_col2:
                    if st.button("🗑️ Excluir", key=f"detail_delete_{r['id']}", use_container_width=True):
                        st.session_state["delete_client_id"] = r['id']
                        st.session_state["show_client_details"] = None
                        st.rerun()
                
                with action_col3:
                    if st.button("❌ Fechar", key=f"detail_close_{r['id']}", use_container_width=True):
                        st.session_state["show_client_details"] = None
                        st.rerun()
        
        # ============================================================================
        # MODAL DE EDIÇÃO DO CLIENTE
        # ============================================================================
        if st.session_state["edit_client_id"] == r['id']:
            with st.container(border=True):
                st.subheader(f"✏️ Editar Cliente: {r['name']}")
                
                with st.form(f"edit_form_{r['id']}"):
                    edit_name = st.text_input("Nome *", value=r['name'])
                    edit_address = st.text_input("Endereço", value=r['address'] or "")
                    edit_cpf = st.text_input("CPF", value=r['cpf'] or "")
                    edit_phone = st.text_input("Telefone", value=r['phone'] or "")
                    edit_status = st.selectbox(
                        "Status",
                        ["ADIMPLENTE", "INADIMPLENTE"],
                        index=0 if r['status'] == "ADIMPLENTE" else 1
                    )
                    
                    col_save, col_cancel = st.columns(2)
                    
                    with col_save:
                        save_clicked = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                    
                    with col_cancel:
                        cancel_clicked = st.form_submit_button("❌ Cancelar", use_container_width=True)
                    
                    if save_clicked:
                        if not edit_name or not edit_name.strip():
                            st.error("❌ O nome do cliente é obrigatório!")
                        elif check_duplicate_name(edit_name, exclude_id=r['id']):
                            st.error("❌ Já existe um cliente cadastrado com esse nome.")
                        else:
                            # Log das alterações
                            if r['name'] != edit_name.strip():
                                log_change("client", r['id'], "UPDATE", "name", r['name'], edit_name.strip())
                            if r['address'] != edit_address:
                                log_change("client", r['id'], "UPDATE", "address", r['address'], edit_address)
                            if r['cpf'] != edit_cpf:
                                log_change("client", r['id'], "UPDATE", "cpf", r['cpf'], edit_cpf)
                            if r['phone'] != edit_phone:
                                log_change("client", r['id'], "UPDATE", "phone", r['phone'], edit_phone)
                            if r['status'] != edit_status:
                                log_change("client", r['id'], "UPDATE", "status", r['status'], edit_status)
                            
                            exec_query(
                                "UPDATE clients SET name=?, address=?, cpf=?, phone=?, status=? WHERE id=?",
                                (edit_name.strip(), edit_address, edit_cpf, edit_phone, edit_status, r['id']),
                                commit=True
                            )
                            st.success("✅ Cliente atualizado com sucesso!")
                            st.session_state["edit_client_id"] = None
                            st.rerun()
                    
                    if cancel_clicked:
                        st.session_state["edit_client_id"] = None
                        st.rerun()
                
                # Botão de excluir na edição
                st.divider()
                if st.button("🗑️ Excluir este cliente", key=f"edit_delete_{r['id']}", use_container_width=True, type="secondary"):
                    st.session_state["delete_client_id"] = r['id']
                    st.session_state["edit_client_id"] = None
                    st.rerun()
        
        # ============================================================================
        # CONFIRMAÇÃO DE EXCLUSÃO (SOFT DELETE)
        # ============================================================================
        if st.session_state["delete_client_id"] == r['id']:
            with st.container(border=True):
                st.warning(f"⚠️ **Excluir cliente: {r['name']}**")
                st.write("Tem certeza que deseja excluir este cliente?")
                st.info("💡 O histórico de vendas e pedidos será mantido para consulta.")
                
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button("✅ Sim, excluir", key=f"confirm_delete_{r['id']}", use_container_width=True, type="primary"):
                        if HAS_IS_ACTIVE:
                            # Soft delete - apenas marca como inativo
                            exec_query(
                                "UPDATE clients SET is_active = 0 WHERE id = ?",
                                (r['id'],),
                                commit=True
                            )
                            log_change("client", r['id'], "SOFT_DELETE", "is_active", 1, 0)
                        else:
                            # Sem coluna is_active - apenas log (não exclui de verdade para manter histórico)
                            log_change("client", r['id'], "DELETE_ATTEMPTED", "status", r['status'], "INATIVO")
                            st.warning("⚠️ Exclusão registrada no log (funcionalidade completa em breve).")
                        st.success("✅ Cliente excluído com sucesso! O histórico foi mantido.")
                        st.session_state["delete_client_id"] = None
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Cancelar", key=f"cancel_delete_{r['id']}", use_container_width=True):
                        st.session_state["delete_client_id"] = None
                        st.rerun()

