import streamlit as st
from core.db import get_conn, now_iso, from_json
from core.models import OrderStatus
from ui.status_badges import badge
from core.audit import log_change

st.title("Pedidos em Estoque")
conn = get_conn()
rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.EM_ESTOQUE,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        # Preços e Status
        cols = st.columns([1,1,1])
        with cols[0]:
            st.write(f"Custo: R$ {r['price_cost']:.2f}")
            st.write(f"Venda: R$ {r['price_sale']:.2f}")
        with cols[1]:
            badge(r['status'])
        
        # Exibir observações
        if r['notes_free']:
            st.subheader("📝 Observações")
            st.write(r['notes_free'])
        
        # Exibir especificações estruturadas
        notes_struct = from_json(r['notes_struct'], {})
        if notes_struct:
            st.subheader("⚙️ Especificações")
            for key, value in notes_struct.items():
                st.write(f"**{key}**: {value}")
        
        # Exibir fotos se existirem
        photos = from_json(r['photos'], [])
        if photos:
            st.subheader("📸 Fotos do Pedido")
            photo_cols = st.columns(6)
            for idx, photo_path in enumerate(photos):
                col_idx = idx % 6
                with photo_cols[col_idx]:
                    try:
                        st.image(photo_path, width=150, caption=f"Foto {idx + 1}")
                    except Exception as e:
                        st.warning(f"Erro ao carregar foto: {e}")
        
        st.divider()
        
        # Opção de editar antes de concluir
        edit = st.checkbox("✏️ Alterar valores antes de concluir?", key=f"edit_{r['id']}")
        new_cost, new_sale = r['price_cost'], r['price_sale']
        if edit:
            new_cost = st.number_input("Novo custo", value=float(r['price_cost']), key=f"ncost_{r['id']}")
            new_sale = st.number_input("Nova venda", value=float(r['price_sale']), key=f"nsale_{r['id']}")
        
        if st.button("✅ Concluir Entrega", key=f"done_{r['id']}", use_container_width=True):
            if edit:
                log_change("order", r['id'], "PRICE_UPDATE", "price_cost", r['price_cost'], new_cost)
                log_change("order", r['id'], "PRICE_UPDATE", "price_sale", r['price_sale'], new_sale)
                conn.execute("UPDATE orders SET price_cost=?, price_sale=?, updated_at=? WHERE id=?", (new_cost, new_sale, now_iso(), r['id']))
            
            # Criar lançamento financeiro
            margin = (new_sale or 0.0) - (new_cost or 0.0)
            conn.execute("INSERT INTO finance_entries(order_id, cost, sale, margin, settled, created_at) VALUES (?,?,?,?,0, ?)", (r['id'], new_cost, new_sale, margin, now_iso()))
            
            # Atualizar status
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.ENTREGUE, now_iso(), r['id']))
            conn.commit()
            
            log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.EM_ESTOQUE, OrderStatus.ENTREGUE)
            
            st.success("✅ Entrega concluída e lançamento financeiro criado")
            st.rerun()
