import streamlit as st
from core.db import init_db, get_conn, HAS_PSYCOPG, exec_query
from core.models import OrderStatus
from datetime import datetime, timedelta

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

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def get_count(query, params=None):
    """Retorna contagem de uma query"""
    result = exec_query(query, params).fetchone()
    if result is None:
        return 0
    return result['c'] if isinstance(result, dict) or hasattr(result, 'keys') else (result[0] if result else 0)

def get_sum(query, params=None):
    """Retorna soma de uma query"""
    result = exec_query(query, params).fetchone()
    if result is None:
        return 0.0
    val = result['total'] if isinstance(result, dict) or hasattr(result, 'keys') else (result[0] if result else 0)
    return float(val) if val else 0.0

# ============================================================================
# COLETA DE DADOS
# ============================================================================

# Contagens por status
pedidos_criados = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.CRIADO,))
aguardando_conf = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.AGUARDANDO_CONF,))
em_estoque = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.EM_ESTOQUE,))
nao_conformes = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.RECEBIDO_NC,))
entregues = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.ENTREGUE,))
vendidos = get_count("SELECT COUNT(*) as c FROM orders WHERE status=?", (OrderStatus.VENDIDO,))

# Estoque de vendas
estoque_vendas = get_count("SELECT COUNT(*) as c FROM stock_items WHERE quantity > 0")
qtd_total_vendas = get_count("SELECT COALESCE(SUM(quantity), 0) as c FROM stock_items WHERE quantity > 0")

# Clientes
total_clientes = get_count("SELECT COUNT(*) as c FROM clients")

# Financeiro
fin_pendente = get_sum("SELECT COALESCE(SUM(sale), 0) as total FROM finance_entries WHERE settled=0")
fin_pago = get_sum("SELECT COALESCE(SUM(sale), 0) as total FROM finance_entries WHERE settled=1")
lucro_total = get_sum("SELECT COALESCE(SUM(margin), 0) as total FROM finance_entries WHERE settled=1")

# Total de pedidos (todos os status)
total_pedidos = get_count("SELECT COUNT(*) as c FROM orders")

# ============================================================================
# CABEÇALHO COM KPIs PRINCIPAIS
# ============================================================================
st.subheader("📊 Visão Geral")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric(
        "📦 Total Pedidos", 
        total_pedidos,
        help="Todos os pedidos no sistema"
    )

with kpi2:
    st.metric(
        "👥 Clientes", 
        total_clientes,
        help="Total de clientes cadastrados"
    )

with kpi3:
    st.metric(
        "🛒 Estoque Vendas", 
        f"{qtd_total_vendas} un.",
        help="Produtos disponíveis para venda direta"
    )

with kpi4:
    st.metric(
        "💰 A Receber", 
        f"R$ {fin_pendente:.2f}",
        help="Valor pendente de pagamento"
    )

with kpi5:
    st.metric(
        "📈 Lucro Realizado", 
        f"R$ {lucro_total:.2f}",
        delta=f"Pago: R$ {fin_pago:.2f}",
        help="Lucro dos pedidos já pagos"
    )

st.divider()

# ============================================================================
# CARDS DAS FASES - CLICÁVEIS
# ============================================================================
st.subheader("🔄 Fases do Fluxo")

# Linha 1: Entrada → Pedidos → Confecção
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("### 📝 Produtos Comuns")
        st.caption("Cadastrar novos pedidos")
        st.markdown("---")
        st.write("Nova entrada de pedido ou produto para estoque de vendas")
        if st.button("➕ Novo Pedido", key="btn_produtos", use_container_width=True):
            st.switch_page("pages/02_Produtos_Comuns.py")

with col2:
    with st.container(border=True):
        st.markdown("### 📋 Pedidos")
        if pedidos_criados > 0:
            st.markdown(f"<span style='background-color: #ff6b6b; padding: 2px 8px; border-radius: 10px; color: white;'>{pedidos_criados} pendentes</span>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum pendente")
        st.markdown("---")
        st.write("Pedidos aguardando envio para confecção")
        if st.button("📋 Ver Pedidos", key="btn_pedidos", use_container_width=True):
            st.switch_page("pages/04_Pedidos.py")

with col3:
    with st.container(border=True):
        st.markdown("### ⏳ Aguardando Confecção")
        if aguardando_conf > 0:
            st.markdown(f"<span style='background-color: #feca57; padding: 2px 8px; border-radius: 10px; color: black;'>{aguardando_conf} em produção</span>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum em produção")
        st.markdown("---")
        st.write("Pedidos enviados para o fornecedor")
        if st.button("⏳ Ver Confecção", key="btn_confeccao", use_container_width=True):
            st.switch_page("pages/05_Aguardando_Confeccao.py")

with col4:
    with st.container(border=True):
        st.markdown("### 📦 Em Estoque")
        if em_estoque > 0:
            st.markdown(f"<span style='background-color: #48dbfb; padding: 2px 8px; border-radius: 10px; color: black;'>{em_estoque} prontos</span>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum em estoque")
        st.markdown("---")
        st.write("Pedidos prontos para entrega ao cliente")
        if st.button("📦 Ver Estoque", key="btn_estoque", use_container_width=True):
            st.switch_page("pages/06_Pedidos_em_Estoque.py")

# Linha 2: Não Conformes, Vendas, Financeiro
col5, col6, col7, col8 = st.columns(4)

with col5:
    with st.container(border=True):
        st.markdown("### ⚠️ Não Conformes")
        if nao_conformes > 0:
            st.markdown(f"<span style='background-color: #ee5a24; padding: 2px 8px; border-radius: 10px; color: white;'>{nao_conformes} com problema</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='background-color: #2ecc71; padding: 2px 8px; border-radius: 10px; color: white;'>✓ Tudo OK</span>", unsafe_allow_html=True)
        st.markdown("---")
        st.write("Pedidos com problemas de qualidade")
        if st.button("⚠️ Ver NC", key="btn_nc", use_container_width=True):
            st.switch_page("pages/07_Pedidos_Nao_Conformes.py")

with col6:
    with st.container(border=True):
        st.markdown("### 🛒 Vendas")
        if estoque_vendas > 0:
            st.markdown(f"<span style='background-color: #a29bfe; padding: 2px 8px; border-radius: 10px; color: white;'>{estoque_vendas} produtos</span>", unsafe_allow_html=True)
        else:
            st.caption("Estoque vazio")
        st.markdown("---")
        st.write("Venda direta de produtos em estoque")
        if st.button("🛒 Ir para Vendas", key="btn_vendas", use_container_width=True):
            st.switch_page("pages/11_Vendas.py")

with col7:
    with st.container(border=True):
        st.markdown("### 💰 Financeiro")
        pendentes_fin = get_count("SELECT COUNT(*) as c FROM finance_entries WHERE settled=0")
        if pendentes_fin > 0:
            st.markdown(f"<span style='background-color: #f39c12; padding: 2px 8px; border-radius: 10px; color: white;'>{pendentes_fin} a pagar</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='background-color: #2ecc71; padding: 2px 8px; border-radius: 10px; color: white;'>✓ Em dia</span>", unsafe_allow_html=True)
        st.markdown("---")
        st.write("Controle de pagamentos e lucros")
        if st.button("💰 Ver Financeiro", key="btn_financeiro", use_container_width=True):
            st.switch_page("pages/08_Financeiro.py")

with col8:
    with st.container(border=True):
        st.markdown("### 📊 Relatórios")
        st.caption("Análises e exportações")
        st.markdown("---")
        st.write("Relatórios detalhados do sistema")
        if st.button("📊 Ver Relatórios", key="btn_relatorios", use_container_width=True):
            st.switch_page("pages/09_Relatorios.py")

st.divider()

# ============================================================================
# RESUMO RÁPIDO - PIPELINE VISUAL
# ============================================================================
st.subheader("📈 Pipeline de Pedidos")

# Criar visualização do pipeline
pipeline_data = {
    "Criados": pedidos_criados,
    "Em Confecção": aguardando_conf,
    "Em Estoque": em_estoque,
    "Entregues": entregues,
    "Vendidos": vendidos,
    "Não Conformes": nao_conformes
}

# Mostrar como barras horizontais
import pandas as pd

if sum(pipeline_data.values()) > 0:
    df_pipeline = pd.DataFrame({
        "Fase": list(pipeline_data.keys()),
        "Quantidade": list(pipeline_data.values())
    })
    
    st.bar_chart(df_pipeline.set_index("Fase"), horizontal=True, color="#5f27cd")
else:
    st.info("📭 Nenhum pedido no sistema ainda. Comece cadastrando um pedido em 'Produtos Comuns'!")

# ============================================================================
# ATALHOS RÁPIDOS
# ============================================================================
st.divider()
st.subheader("⚡ Ações Rápidas")

atalho1, atalho2, atalho3, atalho4 = st.columns(4)

with atalho1:
    if st.button("👤 Novo Cliente", use_container_width=True, type="secondary"):
        st.switch_page("pages/01_Clientes.py")

with atalho2:
    if st.button("📐 Encomenda Sob Medida", use_container_width=True, type="secondary"):
        st.switch_page("pages/03_Encomendas_Sob_Medida.py")

with atalho3:
    if st.button("⚙️ Configurações", use_container_width=True, type="secondary"):
        st.switch_page("pages/00_Configuracoes.py")

with atalho4:
    if st.button("🔧 Administração", use_container_width=True, type="secondary"):
        st.switch_page("pages/10_Administração.py")

# ============================================================================
# RODAPÉ COM INFO DO SISTEMA
# ============================================================================
st.divider()
col_footer1, col_footer2 = st.columns([3, 1])

with col_footer1:
    db_type = "PostgreSQL" if HAS_PSYCOPG else "SQLite"
    st.caption(f"🗄️ Banco de dados: **{db_type}** | 📅 Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

with col_footer2:
    if st.button("🔄 Atualizar Dashboard", use_container_width=True):
        st.rerun()
