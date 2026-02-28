import streamlit as st
from core.db import get_conn, to_json, from_json, load_config, save_config, init_db

# Garantir que o banco está inicializado
init_db()

st.title("⚙️ Configurações do Sistema")

conn = get_conn()

# Tabs para organizar
tab1, tab2 = st.tabs(["📦 Hierarquia de Produtos", "🧵 Materiais"])

with tab1:
    st.markdown("### Categoria → Tipo → Produto")
    st.info("💡 Configure a hierarquia: cada categoria tem seus tipos, e cada tipo tem seus produtos.")
    
    # Carrega hierarquia
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
    
    st.divider()
    
    # Seção: Gerenciar Categorias
    st.subheader("1️⃣ Categorias")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_cat = st.text_input("Nova categoria", key="new_cat")
    with col2:
        st.write("")
        st.write("")
        if st.button("Adicionar Categoria"):
            if new_cat and new_cat not in hierarchy:
                hierarchy[new_cat] = {}
                save_config("product_hierarchy", hierarchy)
                st.success(f"Categoria '{new_cat}' adicionada!")
                st.rerun()
    
    if hierarchy:
        for cat in list(hierarchy.keys()):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📁 **{cat}**")
            with col2:
                if st.button("🗑️", key=f"del_cat_{cat}"):
                    del hierarchy[cat]
                    save_config("product_hierarchy", hierarchy)
                    st.rerun()
    
    st.divider()
    
    # Seção: Gerenciar Tipos
    st.subheader("2️⃣ Tipos (por Categoria)")
    if hierarchy:
        sel_cat_tipo = st.selectbox("Selecione a categoria", list(hierarchy.keys()), key="sel_cat_tipo")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_tipo = st.text_input("Novo tipo", key="new_tipo")
        with col2:
            st.write("")
            st.write("")
            if st.button("Adicionar Tipo"):
                if new_tipo and new_tipo not in hierarchy[sel_cat_tipo]:
                    hierarchy[sel_cat_tipo][new_tipo] = []
                    save_config("product_hierarchy", hierarchy)
                    st.success(f"Tipo '{new_tipo}' adicionado em '{sel_cat_tipo}'!")
                    st.rerun()
        
        if hierarchy[sel_cat_tipo]:
            st.write(f"**Tipos em '{sel_cat_tipo}':**")
            for tipo in list(hierarchy[sel_cat_tipo].keys()):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"  └─ {tipo}")
                with col2:
                    if st.button("🗑️", key=f"del_tipo_{sel_cat_tipo}_{tipo}"):
                        del hierarchy[sel_cat_tipo][tipo]
                        save_config("product_hierarchy", hierarchy)
                        st.rerun()
        else:
            st.info("Nenhum tipo cadastrado nesta categoria.")
    else:
        st.warning("Cadastre uma categoria primeiro.")
    
    st.divider()
    
    # Seção: Gerenciar Produtos
    st.subheader("3️⃣ Produtos (por Tipo)")
    if hierarchy:
        sel_cat_prod = st.selectbox("Selecione a categoria", list(hierarchy.keys()), key="sel_cat_prod")
        
        if hierarchy[sel_cat_prod]:
            sel_tipo_prod = st.selectbox("Selecione o tipo", list(hierarchy[sel_cat_prod].keys()), key="sel_tipo_prod")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                new_prod = st.text_input("Novo produto", key="new_prod")
            with col2:
                st.write("")
                st.write("")
                if st.button("Adicionar Produto"):
                    if new_prod and new_prod not in hierarchy[sel_cat_prod][sel_tipo_prod]:
                        hierarchy[sel_cat_prod][sel_tipo_prod].append(new_prod)
                        save_config("product_hierarchy", hierarchy)
                        st.success(f"Produto '{new_prod}' adicionado!")
                        st.rerun()
            
            if hierarchy[sel_cat_prod][sel_tipo_prod]:
                st.write(f"**Produtos em '{sel_cat_prod} > {sel_tipo_prod}':**")
                for idx, prod in enumerate(hierarchy[sel_cat_prod][sel_tipo_prod]):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"    └─ {prod}")
                    with col2:
                        if st.button("🗑️", key=f"del_prod_{sel_cat_prod}_{sel_tipo_prod}_{idx}"):
                            hierarchy[sel_cat_prod][sel_tipo_prod].remove(prod)
                            save_config("product_hierarchy", hierarchy)
                            st.rerun()
            else:
                st.info("Nenhum produto cadastrado neste tipo.")
        else:
            st.warning(f"Cadastre um tipo em '{sel_cat_prod}' primeiro.")
    else:
        st.warning("Cadastre uma categoria primeiro.")

with tab2:
    st.markdown("### Opções Independentes")
    st.info("💡 Estas opções podem ser combinadas livremente com qualquer produto.")
    
    # Gerenciar listas simples
    def manage_simple_list(title: str, key: str, default_items: list):
        st.subheader(title)
        items = load_config(key, default_items)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_item = st.text_input("Novo item", key=f"new_{key}")
        with col2:
            st.write("")
            st.write("")
            if st.button("Adicionar", key=f"add_{key}"):
                if new_item and new_item not in items:
                    items.append(new_item)
                    save_config(key, items)
                    st.success(f"'{new_item}' adicionado!")
                    st.rerun()
        
        if items:
            st.write("**Itens cadastrados:**")
            for idx, item in enumerate(items):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"• {item}")
                with col2:
                    if st.button("🗑️", key=f"del_{key}_{idx}"):
                        items.remove(item)
                        save_config(key, items)
                        st.rerun()
        else:
            st.info("Nenhum item cadastrado.")
        st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        manage_simple_list("🧵 Tecidos", "tecidos", ["Algodão", "Percal", "Cetim", "Microfibra", "Linho"])
    
    with col2:
        manage_simple_list("🎨 Cores", "cores", ["Branco", "Bege", "Azul", "Rosa", "Cinza", "Colorido"])
    
    with col3:
        manage_simple_list("✨ Acabamentos", "acabamentos", ["Bordado", "Renda", "Babado", "Liso", "Estampado"])
