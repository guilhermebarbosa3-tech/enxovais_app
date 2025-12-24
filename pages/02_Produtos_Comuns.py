import streamlit as st
from core.db import get_conn, now_iso, to_json, from_json, load_config, save_config, exec_query
from core.models import OrderStatus
from core.validators import validate_prices
from core.storage import save_and_resize
from ui.components import section, photo_uploader

st.session_state.setdefault("form_ver", 0)
st.session_state.setdefault("uploader_ver", 0)

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

# Todos os clientes
all_clients = exec_query("SELECT id, name FROM clients ORDER BY name").fetchall()  # type: ignore

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
    button_clicked = st.form_submit_button("Concluir Pedido")

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
if button_clicked:
    # Validar preços
    if price_cost is None or price_sale is None:
        st.error("❌ Preço de custo e preço de venda são obrigatórios!")
        st.stop()
    
    validate_prices(price_cost, price_sale)
    notes_struct = {"tecido":tecido, "cor":cor, "acabamento":acabamento}
    
    # Salvar fotos se existirem (apenas URLs válidas serão persistidas)
    photos_paths = []
    if fotos:
        for idx, foto in enumerate(fotos):
            filename_base = f"order_{now_iso().replace(':', '-')}_{idx}"
            url = save_and_resize(foto, filename_base)
            if url:
                photos_paths.append(url)
            else:
                print("[order] photo upload failed, continuing without this photo")

    exec_query(
        """
        INSERT INTO orders(client_id, category, type, product, price_cost, price_sale, notes_struct, notes_free, photos, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (client_map[client_sel], category, type_, product, price_cost, price_sale, to_json(notes_struct), obs_livre, to_json(photos_paths), OrderStatus.CRIADO, now_iso(), now_iso()),
        commit=True
    )
    st.success("✅ Pedido criado com sucesso! Enviado para Status > Pedidos")
    # Incrementar versões para resetar o form e o uploader de forma limpa
    st.session_state["form_ver"] += 1
    st.session_state["uploader_ver"] += 1

    # Fazer apenas UM rerun seguro para garantir que os widgets sejam recriados limpos
    try:
        st.experimental_rerun()  # type: ignore[attr-defined]
    except Exception:
        try:
            st.rerun()
        except Exception:
            pass
