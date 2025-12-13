import streamlit as st
from core.db import get_conn

st.title("Relatórios")
conn = get_conn()
# Stubs simples de contagem
criadas = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
finalizadas = conn.execute("SELECT COUNT(*) FROM orders WHERE status='FINALIZADO_FIN'").fetchone()[0]

st.write(f"Total de pedidos: {criadas}")
st.write(f"Finalizados (financeiro): {finalizadas}")
