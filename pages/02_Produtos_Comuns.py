import streamlit as st
from core.db import get_conn, now_iso, to_json, from_json, load_config, save_config, exec_query, init_db, get_active_clients_query
from core.models import OrderStatus
from core.validators import validate_prices
from core.storage import save_and_resize
from core.audit import log_change
from ui.components import section, photo_uploader

# Garantir que o banco está inicializado
init_db()

st.session_state.setdefault("form_ver", 0)
st.session_state.setdefault("uploader_ver", 0)
st.session_state.setdefault("confirm_action", None)
st.session_state.setdefault("pending_data", None)

st.title("Produtos Comuns — Novo Pedido")
conn = get_conn()

# Buscar últimos 5 clientes usados (com pedidos recentes) OU recém cadastrados
# PostgreSQL não permite ORDER BY em uma query DISTINCT por coluna não selecionada.
# Selecionamos client_id ordenados por created_at e deduplicamos em Python.
recentes_pedidos = exec_query(
    "SELECT client_id FROM orders ORDER BY created_at DESC LIMIT 5"
).fetchall()
recentes_cadastrados = exec_query(
    "SELECT id as client_id FROM clients ORDER BY id DESC LIMIT 5"
).fetchall()

# Unir e remover duplicatas, mantendo ordem (recentes pedidos + recentes cadastrados)
recentes_ids = set()
for r in recentes_pedidos:
    recentes_ids.add(r['client_id'])
for r in recentes_cadastrados:
    recentes_ids.add(r['client_id'])

# Todos os clientes (apenas ativos)
all_clients = exec_query(get_active_clients_query()).fetchall()  # type: ignore

# Montar lista com recentes no topo
client_list = []
client_map = {}

# Recentes primeiro
for c in all_clients:
    if c['id'] in recentes_ids:
        label = f"🌟 {c['name']} (#{c['id']})"
        client_list.append(label)
        client_map[label] = c['id']

# Depois os outros em ordem alfabética
if client_list:
    client_list.append("─" * 40)  # Divisor visual

for c in all_clients:
    if c['id'] not in recentes_ids:
        label = f"{c['name']} (#{c['id']})"
        client_list.append(label)
        client_map[label] = c['id']

# Carrega configurações
hierarchy = load_config("product_hierarchy", {
    "Lençol": {
        "Solteiro": ["3 peças", "4 peças"],
        "Casal": ["3 peças", "4 peças", "5 peças"],
        "Queen": ["4 peças", "5 peças"],
        "King": ["5 peças", "Jogo completo"]
    },
    "Toalha": {
        "Banho": ["Lisa", "Bordada"],
        "Rosto": ["Lisa", "Bordada"]
    }
})
tecidos = load_config("tecidos", ["Algodão", "Percal", "Cetim", "Microfibra", "Linho"])
cores = load_config("cores", ["Branco", "Bege", "Azul", "Rosa", "Cinza", "Colorido"])
acabamentos = load_config("acabamentos", ["Bordado", "Renda", "Babado", "Liso", "Estampado"])

if not client_list:
    st.warning("⚠️ Cadastre um cliente primeiro na página 'Clientes'.")
    st.stop()

if not hierarchy:
    st.warning("⚠️ Configure a hierarquia de produtos em 'Configurações' primeiro.")
    st.stop()

# Versões dinâmicas para form e uploader (permitem reset sem deletar session_state)
form_key = f"pedido_form_{st.session_state['form_ver']}"
uploader_key = f"uploader_{st.session_state['uploader_ver']}"

# SELETORES EM CASCATA - FORA DO FORM (para atualizar dinamicamente)
st.subheader("📦 Selecione o Produto")

client_sel = st.selectbox("Cliente", client_list)

# Categoria
category = st.selectbox("Categoria", list(hierarchy.keys()) if hierarchy else [])

# Tipos disponíveis baseado na categoria selecionada
tipos_disponiveis = list(hierarchy.get(category, {}).keys()) if category else []
type_ = st.selectbox("Tipo", tipos_disponiveis if tipos_disponiveis else ["Nenhum tipo cadastrado"])

# Produtos disponíveis baseado na categoria E tipo selecionados
produtos_disponiveis = hierarchy.get(category, {}).get(type_, []) if category and type_ else []
product = st.selectbox("Produto", produtos_disponiveis if produtos_disponiveis else ["Nenhum produto cadastrado"])

st.divider()

# FORM - com preços e observações
with st.form(key=form_key):
    st.write(f"**Cliente:** {client_sel}")
    st.write(f"**Produto:** {category} › {type_} › {product}")
    
    price_cost = st.number_input("Preço de custo", value=None, min_value=0.0, step=1.0)
    price_sale = st.number_input("Preço de venda", value=None, min_value=0.0, step=1.0)
    
    # Opções independentes
    tecido = st.selectbox("Tecido", tecidos if tecidos else ["Configure em Configurações"])
    cor = st.selectbox("Cor", cores if cores else ["Configure em Configurações"])
    acabamento = st.selectbox("Acabamento", acabamentos if acabamentos else ["Configure em Configurações"])
    
    obs_livre = st.text_area("Observações livres")
    
    # Quantidade (para estoque de vendas ou venda direta)
    st.divider()
    st.write("**📦 Opções de destino:**")
    quantidade_estoque = st.number_input("Quantidade", value=1, min_value=1, step=1, help="Quantidade de itens (vale para estoque de vendas e venda direta)")
    
    # Botões de ação
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        button_pedido = st.form_submit_button("📤 Enviar Marta", use_container_width=True)
    with col_btn2:
        button_estoque = st.form_submit_button("🛒 Adicionar ao Estoque Vendas", use_container_width=True)
    with col_btn3:
        button_venda_direta = st.form_submit_button("💰 Venda Direta", use_container_width=True)

# Upload de fotos FORA do form para atualizar preview dinamicamente
st.subheader("📸 Fotos do Produto")
fotos_raw = photo_uploader("Fotos (múltiplas)", key=uploader_key)
# Garantir que fotos é sempre uma lista
fotos = fotos_raw if isinstance(fotos_raw, list) else ([fotos_raw] if fotos_raw else None)

# Mostrar preview das fotos carregadas
if fotos:
    st.write("**Preview das fotos:**")
    cols = st.columns(6)
    for idx, foto in enumerate(fotos):
        col_idx = idx % 6
        with cols[col_idx]:
            st.image(foto, width=150, caption=f"Foto {idx + 1}")
    st.write(f"✅ {len(fotos)} foto(s) carregada(s)")

# Processar submissão do formulário
if button_pedido or button_estoque or button_venda_direta:
    # Validar preços
    if price_cost is None or price_sale is None:
        st.error("❌ Preço de custo e preço de venda são obrigatórios!")
        st.stop()
    
    validate_prices(price_cost, price_sale)
    notes_struct = {"tecido":tecido, "cor":cor, "acabamento":acabamento}
    
    # Salvar dados pendentes para confirmação
    st.session_state["pending_data"] = {
        "client_id": client_map[client_sel],
        "client_sel": client_sel,
        "category": category,
        "type_": type_,
        "product": product,
        "price_cost": price_cost,
        "price_sale": price_sale,
        "notes_struct": notes_struct,
        "obs_livre": obs_livre,
        "fotos": fotos,
        "quantidade_estoque": quantidade_estoque
    }
    
    if button_pedido:
        st.session_state["confirm_action"] = "enviar_marta"
    elif button_estoque:
        st.session_state["confirm_action"] = "estoque_vendas"
    elif button_venda_direta:
        st.session_state["confirm_action"] = "venda_direta"
    
    st.rerun()

# ============================================================================
# DIÁLOGOS DE CONFIRMAÇÃO
# ============================================================================

if st.session_state["confirm_action"] and st.session_state["pending_data"]:
    data = st.session_state["pending_data"]
    action = st.session_state["confirm_action"]
    
    st.divider()
    
    # Box de confirmação
    with st.container(border=True):
        
        if action == "enviar_marta":
            st.subheader("📤 Enviar para confecção")
            st.write("Deseja enviar esse pedido para confecção?")
            st.info(f"**Produto:** {data['category']} › {data['type_']} › {data['product']}")
            st.info(f"**Cliente:** {data['client_sel']}")
            
            col_sim, col_nao = st.columns(2)
            
            with col_sim:
                if st.button("✅ Sim", key="confirm_marta", use_container_width=True, type="primary"):
                    # Salvar fotos se existirem
                    photos_paths = []
                    if data["fotos"]:
                        for idx, foto in enumerate(data["fotos"]):
                            filename_base = f"order_{now_iso().replace(':', '-')}_{idx}"
                            url = save_and_resize(foto, filename_base)
                            if url:
                                photos_paths.append(url)
                    
                    exec_query(
                        """
                        INSERT INTO orders(client_id, category, type, product, price_cost, price_sale, notes_struct, notes_free, photos, status, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (data["client_id"], data["category"], data["type_"], data["product"], data["price_cost"], data["price_sale"], to_json(data["notes_struct"]), data["obs_livre"], to_json(photos_paths), OrderStatus.CRIADO, now_iso(), now_iso()),
                        commit=True
                    )
                    st.success("✅ Pedido criado com sucesso! Enviado para Status > Pedidos")
                    
                    # Limpar estados
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.session_state["form_ver"] += 1
                    st.session_state["uploader_ver"] += 1
                    st.rerun()
            
            with col_nao:
                if st.button("❌ Não", key="cancel_marta", use_container_width=True):
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.rerun()
        
        elif action == "estoque_vendas":
            st.subheader("🛒 Adicionar ao Estoque de Vendas")
            st.write("Deseja incluir no seu estoque atual de vendas?")
            st.info(f"**Produto:** {data['category']} › {data['type_']} › {data['product']}")
            st.info(f"**Quantidade:** {data['quantidade_estoque']}")
            
            col_sim, col_nao = st.columns(2)
            
            with col_sim:
                if st.button("✅ Sim", key="confirm_estoque", use_container_width=True, type="primary"):
                    # Salvar fotos se existirem
                    photos_paths = []
                    if data["fotos"]:
                        for idx, foto in enumerate(data["fotos"]):
                            filename_base = f"order_{now_iso().replace(':', '-')}_{idx}"
                            url = save_and_resize(foto, filename_base)
                            if url:
                                photos_paths.append(url)
                    
                    exec_query(
                        """
                        INSERT INTO stock_items(category, type, product, price_cost, price_sale, notes_struct, notes_free, photos, quantity, owner_client_id, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (data["category"], data["type_"], data["product"], data["price_cost"], data["price_sale"], to_json(data["notes_struct"]), data["obs_livre"], to_json(photos_paths), data["quantidade_estoque"], data["client_id"], now_iso(), now_iso()),
                        commit=True
                    )
                    st.success(f"✅ Produto adicionado ao Estoque de Vendas! Quantidade: {data['quantidade_estoque']}")
                    
                    # Limpar estados
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.session_state["form_ver"] += 1
                    st.session_state["uploader_ver"] += 1
                    st.rerun()
            
            with col_nao:
                if st.button("❌ Não", key="cancel_estoque", use_container_width=True):
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.rerun()
        
        elif action == "venda_direta":
            qtd = data.get('quantidade_estoque', 1)
            total_venda = data['price_sale'] * qtd
            total_custo = data['price_cost'] * qtd
            
            st.subheader("💰 Venda Direta")
            st.write("Deseja registrar esta venda diretamente?")
            st.info("O pedido será marcado como **FATURADO** e enviado diretamente para o **Financeiro**.")
            st.info(f"**Produto:** {data['category']} › {data['type_']} › {data['product']}")
            st.info(f"**Cliente:** {data['client_sel']}")
            st.info(f"**Quantidade:** {qtd}")
            st.info(f"**Valor Unitário:** R$ {data['price_sale']:.2f}  |  **Total:** R$ {total_venda:.2f}")
            
            col_sim, col_nao = st.columns(2)
            
            with col_sim:
                if st.button("✅ Sim, Faturar", key="confirm_venda_direta", use_container_width=True, type="primary"):
                    # Salvar fotos se existirem
                    photos_paths = []
                    if data["fotos"]:
                        for idx, foto in enumerate(data["fotos"]):
                            filename_base = f"order_{now_iso().replace(':', '-')}_{idx}"
                            url = save_and_resize(foto, filename_base)
                            if url:
                                photos_paths.append(url)
                    
                    # 1. Criar pedido com status VENDIDO (faturado) — valores totais
                    exec_query(
                        """
                        INSERT INTO orders(client_id, category, type, product, price_cost, price_sale, notes_struct, notes_free, photos, status, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (data["client_id"], data["category"], data["type_"], data["product"], total_custo, total_venda, to_json(data["notes_struct"]), data["obs_livre"], to_json(photos_paths), OrderStatus.VENDIDO, now_iso(), now_iso()),
                        commit=False
                    )
                    
                    # 2. Obter o ID do pedido recém criado
                    last_order = exec_query("SELECT id FROM orders ORDER BY id DESC LIMIT 1").fetchone()
                    order_id = last_order['id']
                    
                    # 3. Criar lançamento no financeiro com valores totais
                    margem = total_venda - total_custo
                    exec_query(
                        """
                        INSERT INTO finance_entries(order_id, cost, sale, margin, settled, created_at)
                        VALUES (?,?,?,?,0,?)
                        """,
                        (order_id, total_custo, total_venda, margem, now_iso()),
                        commit=True
                    )
                    
                    # 4. Log de auditoria
                    log_change("order", order_id, "VENDA_DIRETA", "status", None, OrderStatus.VENDIDO)
                    
                    st.success("✅ Venda realizada com sucesso!")
                    st.info("📊 O lançamento foi enviado para o Financeiro.")
                    
                    # Limpar estados
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.session_state["form_ver"] += 1
                    st.session_state["uploader_ver"] += 1
                    st.rerun()
            
            with col_nao:
                if st.button("❌ Cancelar", key="cancel_venda_direta", use_container_width=True):
                    st.session_state["confirm_action"] = None
                    st.session_state["pending_data"] = None
                    st.rerun()

