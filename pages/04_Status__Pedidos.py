import streamlit as st
from core.db import get_conn, now_iso, from_json
from core.models import OrderStatus
from ui.status_badges import badge

st.title("Status • Pedidos")
conn = get_conn()

rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.CRIADO,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        cols = st.columns([1,1,1])
        with cols[0]:
            st.write(f"Custo: R$ {r['price_cost']:.2f}")
            st.write(f"Venda: R$ {r['price_sale']:.2f}")
        with cols[1]:
            badge(r['status'])
        
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
        
        if st.button("Compartilhar p/ fornecedor", key=f"send_{r['id']}"):
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id']))
            conn.commit()
            st.success("Pedido enviado e movido para 'Aguardando Confecção'")
