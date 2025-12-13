import streamlit as st
from core.db import init_db, get_conn
from core.models import OrderStatus

st.set_page_config(
    page_title="Estoque Exonvais", 
    page_icon="🧵", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Carrega CSS customizado para mobile
import os
css_path = os.path.join(os.path.dirname(__file__), "assets", "mobile.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

st.title("🧵 Estoque Exonvais — Dashboard")

# KPIs simples (stub)
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.CRIADO,))
criadas = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.AGUARDANDO_CONF,))
aguard = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.EM_ESTOQUE,))
estoque = cur.fetchone()[0]

col1, col2, col3 = st.columns(3)
col1.metric("Pedidos Criados", criadas)
col2.metric("Aguardando Confecção", aguard)
col3.metric("Em Estoque", estoque)

st.info("Use o menu 'pages' à esquerda para navegar pelas fases.")
