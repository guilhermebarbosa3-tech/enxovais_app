import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core.db import get_conn, exec_query, now_iso, init_db
from core.audit import log_change
from core.models import OrderStatus
from services.payments import create_payment_batch

# Garantir que o banco está inicializado
init_db()

st.title("💰 Financeiro")
conn = get_conn()

# Helper para formatar data no padrão brasileiro
def format_br_date(date_obj):
    if not date_obj:
        return ""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj)
        except Exception:
            return str(date_obj)
    return date_obj.strftime("%d/%m/%Y %H:%M")

# Filtro por período
st.subheader("Filtros")
col1, col2, col3, col4 = st.columns(4)
with col1:
    start_date = st.date_input("Data inicial", value=datetime.now() - timedelta(days=30), format="DD/MM/YYYY")
with col2:
    end_date = st.date_input("Data final", value=datetime.now(), format="DD/MM/YYYY")
with col3:
    status_filter = st.radio(
        "Status",
        options=["📋 Todos", "⏳ Pendentes", "✅ Pagos"],
        horizontal=True,
        index=0
    )
with col4:
    show_cancelled = st.checkbox("Exibir cancelados", value=False)

# Converter para ISO format para comparação
start_iso = start_date.isoformat()
end_iso = end_date.isoformat()

# Buscar TUDO no período
rows = exec_query("""
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
    # Montar lista de dicts com campo is_cancelled (compatível com bancos sem a coluna ainda)
    data = []
    for r in rows:
        r_dict = dict(r)
        is_cancelled = int(r_dict.get('is_cancelled') or 0)
        cancelled_at = r_dict.get('cancelled_at')
        data.append({
            'Selecionar': False,
            'ID': f"#{r_dict['order_id']}",
            'Cliente': r_dict['client_name'],
            'Produto': f"{r_dict['category']}/{r_dict['type']}/{r_dict['product']}",
            'Custo': f"R$ {r_dict['cost']:.2f}",
            'Venda': f"R$ {r_dict['sale']:.2f}",
            'Margem': f"R$ {r_dict['margin']:.2f}",
            'Criado em': format_br_date(r_dict['created_at']),
            'Status': '❌ CANCELADO' if is_cancelled else ('✅ PAGO' if r_dict['settled'] == 1 else '⏳ Pendente'),
            '_order_id': r_dict['order_id'],
            '_finance_id': r_dict['id'],
            '_cost': r_dict['cost'],
            '_sale': r_dict['sale'],
            '_margin': r_dict['margin'],
            '_settled': r_dict['settled'],
            '_batch_id': r_dict['batch_id'],
            '_is_cancelled': is_cancelled,
        })

    # ============================================================================
    # APLICAR FILTROS
    # ============================================================================
    if not show_cancelled:
        data = [r for r in data if not r['_is_cancelled']]

    data_filtrado = data
    if status_filter == "⏳ Pendentes":
        data_filtrado = [r for r in data if r['_settled'] == 0 and not r['_is_cancelled']]
    elif status_filter == "✅ Pagos":
        data_filtrado = [r for r in data if r['_settled'] == 1 and not r['_is_cancelled']]
    else:
        data_filtrado = data

    # ============================================================================
    # RESUMO DO PERÍODO — exclui cancelados dos totais
    # ============================================================================
    st.subheader("📋 Resumo do Período")

    data_ativos = [r for r in data if not r['_is_cancelled']]
    total_pedidos = len(data_ativos)
    total_custo_geral = sum(r['_cost'] for r in data_ativos)
    total_venda_geral = sum(r['_sale'] for r in data_ativos)
    total_lucro_geral = total_venda_geral - total_custo_geral

    pedidos_pagos = len([r for r in data_ativos if r['_settled'] == 1])
    pedidos_pendentes = len([r for r in data_ativos if r['_settled'] == 0])
    pedidos_cancelados = len([r for r in data if r['_is_cancelled']])

    valor_custo_pago = sum(r['_cost'] for r in data_ativos if r['_settled'] == 1)
    valor_custo_pendente = sum(r['_cost'] for r in data_ativos if r['_settled'] == 0)
    valor_venda_pago = sum(r['_sale'] for r in data_ativos if r['_settled'] == 1)
    valor_venda_pendente = sum(r['_sale'] for r in data_ativos if r['_settled'] == 0)
    lucro_pago = valor_venda_pago - valor_custo_pago
    lucro_pendente = valor_venda_pendente - valor_custo_pendente

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total de Pedidos", total_pedidos,
                  f"✅ {pedidos_pagos} | ⏳ {pedidos_pendentes} | ❌ {pedidos_cancelados}")
    with col2:
        st.metric("💰 Custo Total (Fornecedor)", f"R$ {total_custo_geral:.2f}",
                  f"Pago: R$ {valor_custo_pago:.2f}")
    with col3:
        st.metric("💵 Venda Total (Clientes)", f"R$ {total_venda_geral:.2f}",
                  f"Pago: R$ {valor_venda_pago:.2f}")
    with col4:
        st.metric("📊 SEU LUCRO LÍQUIDO", f"R$ {total_lucro_geral:.2f}",
                  delta=f"Pago: R$ {lucro_pago:.2f}")

    st.subheader("🎯 Detalhamento de Pagamentos")
    col_detalhe1, col_detalhe2 = st.columns(2)
    with col_detalhe1:
        st.write("**Pedidos Pagos** ✅")
        st.write(f"- Quantidade: **{pedidos_pagos}** pedidos")
        st.write(f"- Custo ao Fornecedor: **R$ {valor_custo_pago:.2f}**")
        st.write(f"- Venda ao Cliente: **R$ {valor_venda_pago:.2f}**")
        st.write(f"- Seu Lucro: **R$ {lucro_pago:.2f}**")

    with col_detalhe2:
        st.write("**Pedidos Pendentes** ⏳")
        st.write(f"- Quantidade: **{pedidos_pendentes}** pedidos")
        st.write(f"- Custo ao Fornecedor: **R$ {valor_custo_pendente:.2f}**")
        st.write(f"- Venda ao Cliente: **R$ {valor_venda_pendente:.2f}**")
        st.write(f"- Seu Lucro: **R$ {lucro_pendente:.2f}**")

    st.divider()

    # Filtro de status duplicado — próximo da tabela para acesso rápido
    col_filt1, col_filt2 = st.columns([2, 1])
    with col_filt1:
        status_filter_tabela = st.radio(
            "🔎 Filtrar tabela",
            options=["📋 Todos", "⏳ Pendentes", "✅ Pagos"],
            horizontal=True,
            index=["📋 Todos", "⏳ Pendentes", "✅ Pagos"].index(status_filter),
            key="status_filter_tabela"
        )
    with col_filt2:
        show_cancelled_tabela = st.checkbox("Exibir cancelados", value=show_cancelled, key="show_cancelled_tabela")

    # Reaplicar filtro local (pode diferir do filtro do topo)
    data_tabela = data if show_cancelled_tabela else [r for r in data if not r['_is_cancelled']]
    if status_filter_tabela == "⏳ Pendentes":
        data_tabela = [r for r in data_tabela if r['_settled'] == 0 and not r['_is_cancelled']]
    elif status_filter_tabela == "✅ Pagos":
        data_tabela = [r for r in data_tabela if r['_settled'] == 1 and not r['_is_cancelled']]

    df = pd.DataFrame(data_tabela)

    if 'table_state' not in st.session_state:
        st.session_state['table_state'] = df.copy()

    st.subheader(f"📋 Lista Completa de Pedidos ({len(df)} total)")

    with st.expander("ℹ️ Como ler a tabela"):
        col_leg1, col_leg2, col_leg3 = st.columns(3)
        with col_leg1:
            st.write("**Status:**")
            st.write("- ✅ PAGO: Fornecedor já recebeu")
            st.write("- ⏳ Pendente: Aguardando pagamento ao fornecedor")
            st.write("- ❌ CANCELADO: Venda anulada")
        with col_leg2:
            st.write("**Valores:**")
            st.write("- **Custo**: Você paga ao fornecedor")
            st.write("- **Venda**: Você recebe do cliente")
        with col_leg3:
            st.write("**Margem:**")
            st.write("- **Margem**: Seu lucro (Venda - Custo)")
            st.write("- Selecione linhas para agrupar pagamento")

    st.write("")

    if len(df) == 0:
        st.info("ℹ️ Nenhum pedido encontrado com o filtro selecionado")
    else:
        edited_df = st.data_editor(
            df,
            column_config={
                'Selecionar': st.column_config.CheckboxColumn("Sel.", width="small"),
                'ID': st.column_config.TextColumn(width="small"),
                'Cliente': st.column_config.TextColumn(width="medium"),
                'Produto': st.column_config.TextColumn(width="large"),
                'Custo': st.column_config.TextColumn(width="small"),
                'Venda': st.column_config.TextColumn(width="small"),
                'Margem': st.column_config.TextColumn(width="small"),
                'Criado em': st.column_config.TextColumn(width="medium"),
                'Status': st.column_config.TextColumn(width="small"),
                '_order_id': None,
                '_finance_id': None,
                '_cost': None,
                '_sale': None,
                '_margin': None,
                '_settled': None,
                '_batch_id': None,
                '_is_cancelled': None,
            },
            hide_index=True,
            use_container_width=True,
            disabled=['ID', 'Cliente', 'Produto', 'Custo', 'Venda', 'Margem', 'Criado em', 'Status']
        )

        # Desabilitar checkbox para pedidos já pagos ou cancelados
        if len(df) > 0 and '_settled' in df.columns:
            for idx in df[(df['_settled'] == 1) | (df['_is_cancelled'] == 1)].index:
                if idx < len(edited_df):
                    edited_df.loc[idx, 'Selecionar'] = False

        st.session_state['table_state'] = edited_df

        # ====================================================================
        # CANCELAR PEDIDO (SOFT DELETE)
        # ====================================================================
        st.divider()
        with st.expander("🚫 Cancelar / Anular um Pedido", expanded=False):
            st.warning("⚠️ **Atenção:** O cancelamento é reversível, mas o pedido ficará marcado como ❌ CANCELADO e **não** será contabilizado nos totais.")

            opcoes_cancelar = [
                f"#{r['_order_id']} — {r['Cliente']} — {r['Produto']} ({r['Status']})"
                for r in data
                if not r['_is_cancelled']
            ]

            if not opcoes_cancelar:
                st.info("Não há pedidos ativos para cancelar no período/filtro atual.")
            else:
                cancel_choice = st.selectbox(
                    "Selecione o pedido a cancelar",
                    options=opcoes_cancelar,
                    index=None,
                    placeholder="Selecione um pedido...",
                    key="cancel_choice_select"
                )

                if cancel_choice:
                    # Extrair order_id da opção selecionada
                    order_id_str = cancel_choice.split("—")[0].strip().lstrip("#")
                    order_id_cancel = int(order_id_str)
                    row_cancel = next((r for r in data if r['_order_id'] == order_id_cancel), None)

                    if row_cancel:
                        st.write(f"**Pedido:** {row_cancel['Produto']}")
                        st.write(f"**Cliente:** {row_cancel['Cliente']}")
                        st.write(f"**Valor da Venda:** {row_cancel['Venda']}")
                        st.write(f"**Status atual:** {row_cancel['Status']}")

                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            if st.button("✅ Confirmar Cancelamento", key="btn_confirm_cancel",
                                         use_container_width=True, type="primary"):
                                exec_query(
                                    "UPDATE finance_entries SET is_cancelled=?, cancelled_at=? WHERE id=?",
                                    (1, now_iso(), row_cancel['_finance_id']),
                                    commit=True
                                )
                                exec_query(
                                    "UPDATE orders SET status=?, updated_at=? WHERE id=?",
                                    (OrderStatus.CANCELADO, now_iso(), order_id_cancel),
                                    commit=True
                                )
                                log_change("finance_entry", row_cancel['_finance_id'], "CANCELADO",
                                           "is_cancelled", 0, 1)
                                st.success(f"✅ Pedido #{order_id_cancel} cancelado com sucesso!")
                                st.rerun()
                        with col_c2:
                            if st.button("❌ Voltar", key="btn_back_cancel", use_container_width=True):
                                st.rerun()

        st.divider()

        # ====================================================================
        # SIMULAÇÃO / LOTE DE PAGAMENTO
        # ====================================================================
        selected_rows = edited_df[edited_df['Selecionar'] == True]

        if len(selected_rows) > 0:
            st.subheader("📈 Simulação do Pagamento (Automática)")

            selected_indices = selected_rows.index
            total_cost = sum(df.loc[selected_indices, '_cost']) if '_cost' in df.columns else 0
            total_sale = sum(df.loc[selected_indices, '_sale']) if '_sale' in df.columns else 0
            total_margin = sum(df.loc[selected_indices, '_margin']) if '_margin' in df.columns else 0
            margin_percent = (total_margin / total_sale * 100) if total_sale > 0 else 0

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

            st.warning(f"⚠️ Você está prestes a **registrar pagamento de R$ {payment_value:.2f}** referente a **{len(selected_rows)} pedidos**")

            col_confirm1, col_confirm2 = st.columns(2)
            with col_confirm1:
                if st.button("✅ Confirmar e Criar Lote", key="confirm_batch", use_container_width=True):
                    order_ids = df.loc[selected_indices, '_order_id'].tolist() if '_order_id' in df.columns else []
                    if order_ids:
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
                    else:
                        st.error("Erro: não foi possível obter os IDs dos pedidos")
            with col_confirm2:
                if st.button("❌ Cancelar", key="cancel_batch", use_container_width=True):
                    st.session_state['table_state'] = df.copy()
                    st.rerun()
        else:
            st.info("👆 Selecione pelo menos um pedido pendente para simular o pagamento")
