import streamlit as st
from core.db import get_conn, exec_query

st.title("Relatórios")
conn = get_conn()
# Stubs simples de contagem (compatível com Postgres dict rows e sqlite3.Row)
r = exec_query("SELECT COUNT(*) AS c FROM orders").fetchone()
criadas = r['c'] if (isinstance(r, dict) or hasattr(r, 'keys')) else (r[0] if r else 0)

r = exec_query("SELECT COUNT(*) AS c FROM orders WHERE status='FINALIZADO_FIN'").fetchone()
finalizadas = r['c'] if (isinstance(r, dict) or hasattr(r, 'keys')) else (r[0] if r else 0)

st.write(f"Total de pedidos: {criadas}")
st.write(f"Finalizados (financeiro): {finalizadas}")
