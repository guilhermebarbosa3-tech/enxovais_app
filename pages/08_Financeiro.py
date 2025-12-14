import streamlit as st
import pandas as pd
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

# Buscar TUDO no período (pendente E pago)
rows = conn.execute("""
    SELECT f.*, o.id AS order_id, o.category, o.type, o.product, c.name AS client_name 
    FROM finance_entries f 
    JOIN orders o ON o.id=f.order_id 
    JOIN clients c ON c.id=o.client_id 
    WHERE date(f.created_at) BETWEEN ? AND ?
    ORDER BY f.settled ASC, f.created_at DESC
""", (start_iso, end_iso)).fetchall()

st.divider()

if not rows:
    st.info("Nenhum lançamento no período selecionado")
else:
    # Converter para DataFrame
    data = []
    for r in rows:
        data.append({
            'Selecionar': False,
            'ID': f"#{r['order_id']}",
            'Cliente': r['client_name'],
            'Produto': f"{r['category']}/{r['type']}/{r['product']}",
            'Custo': f"R$ {r['cost']:.2f}",
            'Venda': f"R$ {r['sale']:.2f}",
            'Margem': f"R$ {r['margin']:.2f}",
            'Criado em': format_br_date(r['created_at']),
            'Status': '✅ PAGO' if r['settled'] == 1 else '⏳ Pendente',
            '_order_id': r['order_id'],
            '_cost': r['cost'],
            '_sale': r['sale'],
            '_margin': r['margin'],
            '_settled': r['settled'],
            '_batch_id': r['batch_id']
        })
    
    df = pd.DataFrame(data)
    
    # Estado para controlar seleções
    if 'table_state' not in st.session_state:
        st.session_state['table_state'] = df.copy()
    
    st.subheader(f"📊 Entradas ({len(df)} total)")
    
    # Exibir tabela com checkboxes
    # Apenas permite selecionar os pendentes (settled=0)
    edited_df = st.data_editor(
        df,
        column_config={
            'Selecionar': st.column_config.CheckboxColumn(
                "Sel.",
                width="small"
            ),
            'ID': st.column_config.TextColumn(width="small"),
            'Cliente': st.column_config.TextColumn(width="medium"),
            'Produto': st.column_config.TextColumn(width="large"),
            'Custo': st.column_config.TextColumn(width="small"),
            'Venda': st.column_config.TextColumn(width="small"),
            'Margem': st.column_config.TextColumn(width="small"),
            'Criado em': st.column_config.TextColumn(width="medium"),
            'Status': st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
        use_container_width=True,
        disabled=['ID', 'Cliente', 'Produto', 'Custo', 'Venda', 'Margem', 'Criado em', 'Status']
    )
    
    # Desabilitar checkbox para pedidos já pagos
    for idx in edited_df[edited_df['_settled'] == 1].index:
        edited_df.loc[idx, 'Selecionar'] = False
    
    # Atualizar session_state
    st.session_state['table_state'] = edited_df
    
    st.divider()
    
    # SIMULAÇÃO AUTOMÁTICA
    selected_rows = edited_df[edited_df['Selecionar'] == True]
    
    if len(selected_rows) > 0:
        st.subheader("📈 Simulação do Pagamento (Automática)")
        
        # Calcular totais
        total_cost = sum(selected_rows['_cost'])
        total_sale = sum(selected_rows['_sale'])
        total_margin = sum(selected_rows['_margin'])
        margin_percent = (total_margin / total_sale * 100) if total_sale > 0 else 0
        
        # Mostrar métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📦 Pedidos", len(selected_rows))
        with col2:
            st.metric("💰 Custo Total", f"R$ {total_cost:.2f}")
        with col3:
            st.metric("💵 Venda Total", f"R$ {total_sale:.2f}")
        with col4:
            st.metric("📊 Margem Total", f"R$ {total_margin:.2f}", delta=f"{margin_percent:.1f}%")
        
        st.divider()
        
        # Input para pagamento parcial
        st.subheader("💳 Registrar Pagamento")
        
        col_input1, col_input2 = st.columns([2, 1])
        with col_input1:
            payment_value = st.number_input(
                "Valor a pagar ao fornecedor",
                min_value=0.0,
                value=total_cost,
                step=0.01,
                format="%.2f"
            )
        
        with col_input2:
            st.metric("Saldo", f"R$ {total_cost - payment_value:.2f}")
        
        st.divider()
        
        # Confirmação
        st.warning(f"⚠️ Você está prestes a **registrar pagamento de R$ {payment_value:.2f}** referente a **{len(selected_rows)} pedidos**")
        
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ Confirmar e Criar Lote", key="confirm_batch", use_container_width=True):
                order_ids = selected_rows['_order_id'].tolist()
                batch_id = create_payment_batch(order_ids)
                st.success(
                    f"✅ **Lote #{batch_id}** criado com sucesso!\n\n"
                    f"**Pedidos:** {len(selected_rows)}\n"
                    f"**Valor Pago:** R$ {payment_value:.2f}\n"
                    f"**Custo Total:** R$ {total_cost:.2f}\n"
                    f"**Saldo Pendente:** R$ {total_cost - payment_value:.2f}"
                )
                st.session_state['table_state'] = df.copy()
                st.rerun()
        
        with col_confirm2:
            if st.button("❌ Cancelar", key="cancel_batch", use_container_width=True):
                st.session_state['table_state'] = df.copy()
                st.rerun()
    else:
        st.info("👆 Selecione pelo menos um pedido pendente para simular o pagamento")
