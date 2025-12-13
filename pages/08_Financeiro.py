import streamlit as st
from core.db import get_conn
from services.payments import create_payment_batch
from core.models import OrderStatus

st.title("Financeiro")
conn = get_conn()
rows = conn.execute("SELECT f.*, o.id AS order_id, o.category, o.type, o.product, c.name AS client_name FROM finance_entries f JOIN orders o ON o.id=f.order_id JOIN clients c ON c.id=o.client_id WHERE f.settled=0 ORDER BY f.id DESC").fetchall()

sel = []
for r in rows:
    with st.expander(f"Pedido #{r['order_id']} — {r['client_name']} | {r['category']}/{r['type']}/{r['product']}"):
        st.write(f"Custo: R$ {r['cost']:.2f} | Venda: R$ {r['sale']:.2f} | Margem: R$ {r['margin']:.2f}")
        if st.checkbox("Incluir no pagamento", key=f"pick_{r['id']}"):
            sel.append(r['order_id'])

if st.button("Pagar fornecedor (criar lote)") and sel:
    batch_id = create_payment_batch(sel)
    st.success(f"Lote #{batch_id} criado. Valores quitados.")
