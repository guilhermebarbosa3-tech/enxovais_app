import streamlit as st
from core.db import get_conn, now_iso
from core.models import OrderStatus

st.title("Pedidos em Estoque")
conn = get_conn()
rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.EM_ESTOQUE,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        st.write(f"Custo atual: R$ {r['price_cost']:.2f} — Venda atual: R$ {r['price_sale']:.2f}")
        edit = st.checkbox("Alterar valores antes de concluir?", key=f"edit_{r['id']}")
        new_cost, new_sale = r['price_cost'], r['price_sale']
        if edit:
            new_cost = st.number_input("Novo custo", value=float(r['price_cost']), key=f"ncost_{r['id']}")
            new_sale = st.number_input("Nova venda", value=float(r['price_sale']), key=f"nsale_{r['id']}")
        if st.button("Concluir Entrega", key=f"done_{r['id']}"):
            if edit:
                conn.execute("UPDATE orders SET price_cost=?, price_sale=?, updated_at=? WHERE id=?", (new_cost, new_sale, now_iso(), r['id']))
            # cria lançamento financeiro
            margin = (new_sale or 0.0) - (new_cost or 0.0)
            conn.execute("INSERT INTO finance_entries(order_id, cost, sale, margin, settled, created_at) VALUES (?,?,?,?,0, datetime('now'))", (r['id'], new_cost, new_sale, margin))
            conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.ENTREGUE, now_iso(), r['id']))
            conn.commit()
            st.success("Entrega concluída e lançamento financeiro criado")
