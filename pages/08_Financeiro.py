import streamlit as st
from datetime import datetime, timedelta
from core.db import get_conn
from services.payments import create_payment_batch

st.title("💰 Financeiro")
conn = get_conn()

# Helper para formatar data no padrão brasileiro
def format_br_date(date_obj):
    if isinstance(date_obj, str):
        date_obj = datetime.fromisoformat(date_obj)
    return date_obj.strftime("%d/%m/%Y %H:%M")

# Filtro por período
st.subheader("Filtros")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data inicial", value=datetime.now() - timedelta(days=30), format="DD/MM/YYYY")
with col2:
    end_date = st.date_input("Data final", value=datetime.now(), format="DD/MM/YYYY")

# Converter para ISO format para comparação
start_iso = start_date.isoformat()
end_iso = end_date.isoformat()

# Buscar lançamentos não quitados no período
rows = conn.execute("""
    SELECT f.*, o.id AS order_id, o.category, o.type, o.product, c.name AS client_name 
    FROM finance_entries f 
    JOIN orders o ON o.id=f.order_id 
    JOIN clients c ON c.id=o.client_id 
    WHERE f.settled=0 AND date(f.created_at) BETWEEN ? AND ?
    ORDER BY f.created_at DESC
""", (start_iso, end_iso)).fetchall()

st.divider()

if not rows:
    st.info("Nenhum lançamento pendente no período selecionado")
else:
    # Estado da seleção
    if 'selected_entries' not in st.session_state:
        st.session_state['selected_entries'] = {}
    
    # Exibir entradas
    st.subheader(f"📊 Entradas Pendentes ({len(rows)} total)")
    
    for r in rows:
        with st.expander(f"#{r['order_id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Custo", f"R$ {r['cost']:.2f}")
            with col2:
                st.metric("Venda", f"R$ {r['sale']:.2f}")
            with col3:
                st.metric("Margem", f"R$ {r['margin']:.2f}", delta=f"{(r['margin']/r['sale']*100 if r['sale'] > 0 else 0):.1f}%")
            
            st.caption(f"Criado em: {format_br_date(r['created_at'])}")
            
            if st.checkbox("Incluir no pagamento", key=f"pick_{r['id']}"):
                st.session_state['selected_entries'][r['id']] = r
            elif r['id'] in st.session_state['selected_entries']:
                del st.session_state['selected_entries'][r['id']]
    
    st.divider()
    
    # Simulação
    if st.session_state['selected_entries']:
        st.subheader("📈 Simulação do Pagamento")
        
        selected_rows = list(st.session_state['selected_entries'].values())
        total_cost = sum(r['cost'] for r in selected_rows)
        total_sale = sum(r['sale'] for r in selected_rows)
        total_margin = sum(r['margin'] for r in selected_rows)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pedidos", len(selected_rows))
        with col2:
            st.metric("Custo Total", f"R$ {total_cost:.2f}")
        with col3:
            st.metric("Venda Total", f"R$ {total_sale:.2f}")
        with col4:
            st.metric("Margem Total", f"R$ {total_margin:.2f}", delta=f"{(total_margin/total_sale*100 if total_sale > 0 else 0):.1f}%")
        
        st.divider()
        
        # Confirmação
        st.warning(f"⚠️ Você está prestes a **criar um lote de pagamento** com **{len(selected_rows)} pedidos**")
        
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ Confirmar e Criar Lote", key="confirm_batch", use_container_width=True):
                order_ids = [r['order_id'] for r in selected_rows]
                batch_id = create_payment_batch(order_ids)
                st.success(f"✅ **Lote #{batch_id}** criado com sucesso!\n\n**Total:** R$ {total_cost:.2f} (custo) → R$ {total_sale:.2f} (venda)\n**Margem:** R$ {total_margin:.2f}")
                st.session_state['selected_entries'] = {}
                st.rerun()
        
        with col_confirm2:
            if st.button("❌ Cancelar", key="cancel_batch", use_container_width=True):
                st.session_state['selected_entries'] = {}
                st.rerun()
    else:
        st.info("Selecione pelo menos um lançamento para prosseguir")
