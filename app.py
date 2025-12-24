import streamlit as st
from core.db import init_db, get_conn
from core.models import OrderStatus

st.set_page_config(
    page_title="Estoque Exonvais", 
    page_icon="🧵", 
    layout="wide"
)

init_db()

st.title("🧵 Estoque Exonvais — Dashboard")

# KPIs simples (stub)
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.CRIADO,))
result = cur.fetchone()
criadas = result[0] if result else 0
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.AGUARDANDO_CONF,))
result = cur.fetchone()
aguard = result[0] if result else 0
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.EM_ESTOQUE,))
result = cur.fetchone()
estoque = result[0] if result else 0

col1, col2, col3 = st.columns(3)
col1.metric("Pedidos Criados", criadas)
col2.metric("Aguardando Confecção", aguard)
col3.metric("Em Estoque", estoque)

st.info("Use o menu 'pages' à esquerda para navegar pelas fases.")
