import streamlit as st
from core.db import get_conn, now_iso
from core.models import OrderStatus

st.title("Pedidos Não Conformes")
conn = get_conn()
rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.RECEBIDO_NC,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        kind = st.selectbox("Tipo de NC", ["medida","tecido","cor","acabamento","outro"], key=f"kind_{r['id']}")
        desc = st.text_area("Descrição", key=f"desc_{r['id']}")
        if st.button("Informar e reenviar ao fornecedor", key=f"send_{r['id']}"):
            conn.execute("INSERT INTO nonconformities(order_id, kind, description, photos, created_at) VALUES (?,?,?,?, datetime('now'))", (r['id'], kind, desc, "[]"))
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id']))
            conn.commit()
            st.success("NC registrada e pedido retornou para 'Aguardando Confecção'")
