import streamlit as st
from core.db import init_db, get_conn, HAS_PSYCOPG, exec_query
from core.models import OrderStatus

st.set_page_config(
    page_title="Estoque Exonvais", 
    page_icon="🧵", 
    layout="wide"
)

init_db()

# Verificar se estamos no Streamlit Cloud sem PostgreSQL
import os
is_streamlit_cloud = os.environ.get('STREAMLIT_SERVER_HEADLESS') == 'true'
if is_streamlit_cloud and not HAS_PSYCOPG:
    st.warning("""
    ⚠️ **ATENÇÃO: Dados não serão persistidos!**
    
    Você está usando SQLite no Streamlit Cloud, mas os dados serão perdidos a cada deploy.
    
    Para persistência real, configure PostgreSQL:
    1. Crie conta gratuita no [Supabase](https://supabase.com) ou [Neon](https://neon.tech)
    2. Vá em Settings > Secrets do seu app
    3. Adicione: `DATABASE_URL = "postgresql://..."`
    4. Faça novo deploy
    
    Dados atuais serão mantidos até o próximo deploy.
    """)

st.title("🧵 Estoque Exonvais — Dashboard")

# KPIs simples (stub)
criadas = exec_query("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.CRIADO,)).fetchone()
criadas = (criadas['c'] if isinstance(criadas, dict) or hasattr(criadas, 'keys') else (criadas[0] if criadas else 0))

aguard = exec_query("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.AGUARDANDO_CONF,)).fetchone()
aguard = (aguard['c'] if isinstance(aguard, dict) or hasattr(aguard, 'keys') else (aguard[0] if aguard else 0))

estoque = exec_query("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.EM_ESTOQUE,)).fetchone()
estoque = (estoque['c'] if isinstance(estoque, dict) or hasattr(estoque, 'keys') else (estoque[0] if estoque else 0))

col1, col2, col3 = st.columns(3)
col1.metric("Pedidos Criados", criadas)
col2.metric("Aguardando Confecção", aguard)
col3.metric("Em Estoque", estoque)

st.info("Use o menu 'pages' à esquerda para navegar pelas fases.")
