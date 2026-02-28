import streamlit as st
import os
from core.db import get_conn, now_iso, from_json, to_json, exec_query, load_config, init_db
from core.models import OrderStatus
from core.audit import log_change

# Garantir que o banco está inicializado
init_db()

st.set_page_config(layout="wide")
st.title("🛒 Vendas — Estoque Pronto")
conn = get_conn()

# Inicializar carrinho na sessão
if "carrinho" not in st.session_state:
    st.session_state["carrinho"] = []

# Carregar configurações de hierarquia para filtro
hierarchy = load_config("product_hierarchy", {})

# ============================================================================
# FILTROS DE PESQUISA
# ============================================================================
st.subheader("🔍 Pesquisar Produtos")

col_search, col_cat = st.columns([2, 1])

with col_search:
    termo_pesquisa = st.text_input("Buscar por nome/descrição", placeholder="Digite para pesquisar...")

with col_cat:
    categorias_disponiveis = ["Todos"] + list(hierarchy.keys()) if hierarchy else ["Todos"]
    categoria_filtro = st.selectbox("Filtrar por Categoria", categorias_disponiveis)

st.divider()

# ============================================================================
# BUSCAR PRODUTOS DO ESTOQUE
# ============================================================================
query = """
    SELECT s.*, c.name AS owner_name 
    FROM stock_items s 
    LEFT JOIN clients c ON c.id = s.owner_client_id
    WHERE s.quantity > 0
"""
params = []

# Aplicar filtro de categoria
if categoria_filtro != "Todos":
    query += " AND s.category = ?"
    params.append(categoria_filtro)

# Aplicar filtro de pesquisa
if termo_pesquisa:
    query += " AND (s.product LIKE ? OR s.type LIKE ? OR s.notes_free LIKE ?)"
    termo = f"%{termo_pesquisa}%"
    params.extend([termo, termo, termo])

query += " ORDER BY s.created_at DESC"

rows = exec_query(query, tuple(params) if params else None).fetchall()

# ============================================================================
# EXIBIR PRODUTOS EM GRID COM FOTOS
# ============================================================================
if not rows:
    st.info("📦 Nenhum produto no estoque de vendas. Adicione produtos em 'Produtos Comuns' clicando em 'Adicionar ao Estoque Vendas'.")
else:
    st.subheader(f"📦 Produtos Disponíveis ({len(rows)} itens)")
    
    # Exibir em cards de 3 colunas
    cols_per_row = 3
    
    for i in range(0, len(rows), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(rows):
                r = rows[i + j]
                
                with col:
                    # Card do produto
                    with st.container(border=True):
                        # Foto à esquerda, info à direita
                        foto_col, info_col = st.columns([1, 2])
                        
                        with foto_col:
                            photos = from_json(r['photos'], [])
                            if photos and len(photos) > 0:
                                photo_path = photos[0]
                                try:
                                    if isinstance(photo_path, str) and photo_path.startswith(('http://', 'https://')):
                                        st.image(photo_path, width=120)
                                    elif isinstance(photo_path, str) and os.path.exists(photo_path):
                                        st.image(photo_path, width=120)
                                    else:
                                        st.image("https://via.placeholder.com/120x120?text=Sem+Foto", width=120)
                                except Exception:
                                    st.image("https://via.placeholder.com/120x120?text=Erro", width=120)
                            else:
                                st.image("https://via.placeholder.com/120x120?text=Sem+Foto", width=120)
                        
                        with info_col:
                            st.write(f"**{r['category']} › {r['type']}**")
                            st.write(f"📦 {r['product']}")
                            
                            # Especificações
                            notes = from_json(r['notes_struct'], {})
                            if notes:
                                specs = " | ".join([f"{v}" for k, v in notes.items() if v])
                                st.caption(specs)
                            
                            st.write(f"💰 **R$ {r['price_sale']:.2f}**")
                            st.caption(f"Estoque: {r['quantity']} un.")
                        
                        # Seletor de quantidade e botão adicionar
                        add_col1, add_col2 = st.columns([1, 1])
                        
                        with add_col1:
                            qtd_add = st.number_input(
                                "Qtd",
                                min_value=1,
                                max_value=r['quantity'],
                                value=1,
                                key=f"qtd_{r['id']}",
                                label_visibility="collapsed"
                            )
                        
                        with add_col2:
                            if st.button("🛒 Adicionar", key=f"add_{r['id']}", use_container_width=True):
                                # Verificar se já está no carrinho
                                item_existente = next((item for item in st.session_state["carrinho"] if item["id"] == r["id"]), None)
                                
                                if item_existente:
                                    # Atualizar quantidade
                                    nova_qtd = item_existente["qtd_selecionada"] + qtd_add
                                    if nova_qtd <= r['quantity']:
                                        item_existente["qtd_selecionada"] = nova_qtd
                                        st.success(f"✅ Quantidade atualizada!")
                                    else:
                                        st.error(f"❌ Estoque insuficiente!")
                                else:
                                    # Adicionar novo item ao carrinho
                                    st.session_state["carrinho"].append({
                                        "id": r["id"],
                                        "category": r["category"],
                                        "type": r["type"],
                                        "product": r["product"],
                                        "price_cost": r["price_cost"],
                                        "price_sale": r["price_sale"],
                                        "qtd_selecionada": qtd_add,
                                        "qtd_disponivel": r["quantity"],
                                        "notes_struct": r["notes_struct"],
                                        "notes_free": r["notes_free"],
                                        "photos": r["photos"]
                                    })
                                    st.success(f"✅ Adicionado ao carrinho!")
                                st.rerun()

st.divider()

# ============================================================================
# CARRINHO DE VENDAS
# ============================================================================
st.subheader("🛒 Carrinho de Vendas")

carrinho = st.session_state["carrinho"]

if not carrinho:
    st.info("🛒 Carrinho vazio. Selecione produtos acima para adicionar.")
else:
    # Exibir itens do carrinho
    total_venda = 0
    total_custo = 0
    
    for idx, item in enumerate(carrinho):
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{item['category']} › {item['type']} › {item['product']}**")
            
            with col2:
                st.write(f"Qtd: **{item['qtd_selecionada']}**")
            
            with col3:
                subtotal = item['price_sale'] * item['qtd_selecionada']
                st.write(f"**R$ {subtotal:.2f}**")
                total_venda += subtotal
                total_custo += item['price_cost'] * item['qtd_selecionada']
            
            with col4:
                if st.button("🗑️", key=f"remove_{idx}", help="Remover do carrinho"):
                    st.session_state["carrinho"].pop(idx)
                    st.rerun()
    
    # Resumo
    st.divider()
    
    col_resumo1, col_resumo2, col_resumo3 = st.columns(3)
    
    with col_resumo1:
        st.metric("📦 Itens no carrinho", len(carrinho))
    
    with col_resumo2:
        st.metric("💰 Total da Venda", f"R$ {total_venda:.2f}")
    
    with col_resumo3:
        margem = total_venda - total_custo
        st.metric("📊 Margem de Lucro", f"R$ {margem:.2f}")
    
    st.divider()
    
    # ============================================================================
    # SELEÇÃO DO CLIENTE COMPRADOR (OBRIGATÓRIO)
    # ============================================================================
    st.subheader("👤 Cliente Comprador")
    
    # Buscar todos os clientes (apenas ativos)
    all_clients = exec_query("SELECT id, name FROM clients WHERE is_active = 1 OR is_active IS NULL ORDER BY name").fetchall()
    
    if not all_clients:
        st.error("❌ Nenhum cliente cadastrado. Cadastre um cliente primeiro em 'Clientes'.")
        st.stop()
    
    client_options = [f"{c['name']} (#{c['id']})" for c in all_clients]
    client_map = {f"{c['name']} (#{c['id']})": c['id'] for c in all_clients}
    
    cliente_selecionado = st.selectbox(
        "Selecione o cliente que está comprando",
        options=client_options,
        index=None,
        placeholder="Selecione um cliente..."
    )
    
    st.divider()
    
    # ============================================================================
    # FINALIZAR VENDA
    # ============================================================================
    col_finalizar, col_limpar = st.columns(2)
    
    with col_finalizar:
        if st.button("✅ Finalizar Venda", use_container_width=True, type="primary"):
            if not cliente_selecionado:
                st.error("❌ Selecione um cliente para finalizar a venda!")
            else:
                client_id = client_map[cliente_selecionado]
                
                # Processar cada item do carrinho
                for item in carrinho:
                    # 1. Criar pedido com status VENDIDO
                    exec_query(
                        """
                        INSERT INTO orders(client_id, category, type, product, price_cost, price_sale, notes_struct, notes_free, photos, status, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            client_id,
                            item['category'],
                            item['type'],
                            item['product'],
                            item['price_cost'] * item['qtd_selecionada'],
                            item['price_sale'] * item['qtd_selecionada'],
                            item['notes_struct'],
                            item['notes_free'],
                            item['photos'],
                            OrderStatus.VENDIDO,
                            now_iso(),
                            now_iso()
                        ),
                        commit=False
                    )
                    
                    # Obter o ID do pedido recém criado
                    last_order = exec_query("SELECT id FROM orders ORDER BY id DESC LIMIT 1").fetchone()
                    order_id = last_order['id']
                    
                    # 2. Criar lançamento financeiro
                    custo_total = item['price_cost'] * item['qtd_selecionada']
                    venda_total = item['price_sale'] * item['qtd_selecionada']
                    margem_item = venda_total - custo_total
                    
                    exec_query(
                        """
                        INSERT INTO finance_entries(order_id, cost, sale, margin, settled, created_at)
                        VALUES (?,?,?,?,0,?)
                        """,
                        (order_id, custo_total, venda_total, margem_item, now_iso()),
                        commit=False
                    )
                    
                    # 3. Decrementar quantidade no estoque
                    nova_quantidade = item['qtd_disponivel'] - item['qtd_selecionada']
                    
                    if nova_quantidade <= 0:
                        # Remover item do estoque
                        exec_query("DELETE FROM stock_items WHERE id=?", (item['id'],), commit=False)
                    else:
                        # Atualizar quantidade
                        exec_query(
                            "UPDATE stock_items SET quantity=?, updated_at=? WHERE id=?",
                            (nova_quantidade, now_iso(), item['id']),
                            commit=False
                        )
                    
                    # 4. Log de auditoria
                    log_change("stock_item", item['id'], "VENDA", "quantity", item['qtd_disponivel'], nova_quantidade)
                
                # Commit de todas as operações
                conn.commit()
                
                # Limpar carrinho
                st.session_state["carrinho"] = []
                
                st.success(f"✅ Venda finalizada com sucesso! Total: R$ {total_venda:.2f}")
                st.info("📊 Os lançamentos foram enviados para o Financeiro.")
                st.balloons()
                st.rerun()
    
    with col_limpar:
        if st.button("🗑️ Limpar Carrinho", use_container_width=True):
            st.session_state["carrinho"] = []
            st.rerun()

# ============================================================================
# GERENCIAR ESTOQUE (Expandível)
# ============================================================================
with st.expander("⚙️ Gerenciar Estoque de Vendas"):
    st.subheader("📋 Todos os Itens do Estoque")
    
    all_stock = exec_query("""
        SELECT s.*, c.name AS owner_name 
        FROM stock_items s 
        LEFT JOIN clients c ON c.id = s.owner_client_id
        ORDER BY s.created_at DESC
    """).fetchall()
    
    if all_stock:
        for r in all_stock:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**#{r['id']}** - {r['category']} › {r['type']} › {r['product']}")
                    st.caption(f"Cadastrado por: {r['owner_name'] or 'N/A'}")
                
                with col2:
                    st.write(f"Qtd: **{r['quantity']}**")
                
                with col3:
                    st.write(f"R$ {r['price_sale']:.2f}")
                
                with col4:
                    if st.button("🗑️ Excluir", key=f"del_stock_{r['id']}"):
                        exec_query("DELETE FROM stock_items WHERE id=?", (r['id'],), commit=True)
                        log_change("stock_item", r['id'], "DELETE", "all", str(dict(r)), None)
                        st.success("Item removido do estoque!")
                        st.rerun()
    else:
        st.info("Nenhum item no estoque.")
