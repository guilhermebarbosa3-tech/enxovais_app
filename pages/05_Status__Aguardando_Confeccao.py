import streamlit as st
from core.db import get_conn, now_iso
from core.models import OrderStatus

st.title("Status • Aguardando Confecção")
conn = get_conn()
rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.AGUARDANDO_CONF,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        c1, c2 = st.columns(2)
        if c1.button("Chegou conforme", key=f"ok_{r['id']}"):
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.EM_ESTOQUE, now_iso(), r['id']))
            conn.commit()
            st.success("Movido para 'Pedidos em Estoque'")
        if c2.button("Chegou não conforme", key=f"nc_{r['id']}"):
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.RECEBIDO_NC, now_iso(), r['id']))
            conn.commit()
            st.warning("Movido para 'Não Conformes'")
