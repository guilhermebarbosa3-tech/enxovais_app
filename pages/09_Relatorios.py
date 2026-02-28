import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core.db import get_conn, exec_query, init_db, get_active_clients_query, from_json
from core.models import OrderStatus

# Garantir que o banco está inicializado
init_db()

st.set_page_config(layout="wide")
st.title("📊 Relatórios")
conn = get_conn()

# ============================================================================
# HELPERS
# ============================================================================
STATUS_LABELS = {
    OrderStatus.CRIADO: "📝 Criado",
    OrderStatus.ENVIADO_FORNECEDOR: "📦 Enviado Fornecedor",
    OrderStatus.AGUARDANDO_CONF: "⏳ Aguardando Confecção",
    OrderStatus.RECEBIDO_CONF: "✅ Recebido Conforme",
    OrderStatus.RECEBIDO_NC: "❌ Não Conforme",
    OrderStatus.EM_ESTOQUE: "📦 Em Estoque",
    OrderStatus.ENTREGUE: "🚚 Entregue",
    OrderStatus.FINALIZADO_FIN: "💰 Finalizado (Financeiro)",
    OrderStatus.DISPONIVEL_VENDA: "🏷️ Disponível Venda",
    OrderStatus.VENDIDO: "🛒 Vendido",
}

def format_br_date(date_str):
    """Formata data ISO para padrão brasileiro"""
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        elif isinstance(date_str, datetime):
            dt = date_str
        else:
            return str(date_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(date_str)

def safe_value(row, key, default=0):
    """Extrai valor de row de forma segura (dict ou sqlite3.Row)"""
    try:
        return row[key] if row else default
    except (KeyError, IndexError, TypeError):
        return default

# ============================================================================
# FILTROS GLOBAIS
# ============================================================================
st.subheader("🔍 Filtros")

col_d1, col_d2, col_tipo = st.columns([1, 1, 1])

with col_d1:
    data_inicio = st.date_input(
        "📅 Data Inicial",
        value=datetime.now() - timedelta(days=30),
        format="DD/MM/YYYY"
    )

with col_d2:
    data_fim = st.date_input(
        "📅 Data Final",
        value=datetime.now(),
        format="DD/MM/YYYY"
    )

with col_tipo:
    relatorio_tipo = st.selectbox(
        "📋 Tipo de Relatório",
        [
            "📈 Visão Geral",
            "👤 Relatório por Cliente",
            "📦 Pedidos por Status",
            "💰 Financeiro Detalhado",
            "🛒 Vendas do Estoque",
            "❌ Não Conformidades",
            "📋 Histórico Completo",
        ]
    )

start_iso = data_inicio.isoformat()
end_iso = data_fim.isoformat()

st.divider()

# ============================================================================
# 1) VISÃO GERAL
# ============================================================================
if relatorio_tipo == "📈 Visão Geral":
    st.header("📈 Visão Geral do Negócio")
    st.caption(f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")

    # ---- KPIs principais ----
    r_total = exec_query(
        "SELECT COUNT(*) AS c FROM orders WHERE date(created_at) BETWEEN ? AND ?",
        (start_iso, end_iso)
    ).fetchone()
    total_pedidos = safe_value(r_total, 'c')

    r_vendidos = exec_query(
        "SELECT COUNT(*) AS c FROM orders WHERE status IN (?,?,?) AND date(created_at) BETWEEN ? AND ?",
        (OrderStatus.FINALIZADO_FIN, OrderStatus.VENDIDO, OrderStatus.ENTREGUE, start_iso, end_iso)
    ).fetchone()
    total_finalizados = safe_value(r_vendidos, 'c')

    r_nc = exec_query(
        "SELECT COUNT(*) AS c FROM nonconformities WHERE date(created_at) BETWEEN ? AND ?",
        (start_iso, end_iso)
    ).fetchone()
    total_nc = safe_value(r_nc, 'c')

    r_clientes = exec_query(get_active_clients_query()).fetchall()
    total_clientes = len(r_clientes)

    r_receita = exec_query(
        "SELECT COALESCE(SUM(sale),0) AS total_venda, COALESCE(SUM(cost),0) AS total_custo, COALESCE(SUM(margin),0) AS total_margem FROM finance_entries WHERE date(created_at) BETWEEN ? AND ?",
        (start_iso, end_iso)
    ).fetchone()
    receita_total = safe_value(r_receita, 'total_venda')
    custo_total = safe_value(r_receita, 'total_custo')
    lucro_total = safe_value(r_receita, 'total_margem')

    # Cards de KPI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Pedidos no Período", total_pedidos)
    with col2:
        st.metric("✅ Finalizados/Vendidos", total_finalizados)
    with col3:
        st.metric("❌ Não Conformidades", total_nc)
    with col4:
        st.metric("👤 Clientes Ativos", total_clientes)

    st.divider()

    col_fin1, col_fin2, col_fin3 = st.columns(3)
    with col_fin1:
        st.metric("💰 Receita (Venda)", f"R$ {receita_total:.2f}")
    with col_fin2:
        st.metric("📉 Custo (Fornecedor)", f"R$ {custo_total:.2f}")
    with col_fin3:
        delta_pct = f"{(lucro_total / receita_total * 100):.1f}%" if receita_total > 0 else "0%"
        st.metric("📊 Lucro Líquido", f"R$ {lucro_total:.2f}", delta=delta_pct)

    st.divider()

    # ---- Pedidos por status (tabela resumo) ----
    st.subheader("📊 Distribuição por Status")
    status_rows = exec_query(
        "SELECT status, COUNT(*) AS qtd FROM orders WHERE date(created_at) BETWEEN ? AND ? GROUP BY status ORDER BY qtd DESC",
        (start_iso, end_iso)
    ).fetchall()

    if status_rows:
        status_data = []
        for sr in status_rows:
            label = STATUS_LABELS.get(sr['status'], sr['status'])
            status_data.append({"Status": label, "Quantidade": sr['qtd']})
        df_status = pd.DataFrame(status_data)
        
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            st.bar_chart(df_status.set_index("Status"))
        with col_table:
            st.dataframe(df_status, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum pedido no período selecionado.")

    # ---- Pedidos por categoria ----
    st.subheader("📂 Pedidos por Categoria")
    cat_rows = exec_query(
        "SELECT category, COUNT(*) AS qtd, SUM(price_sale) AS total_venda FROM orders WHERE date(created_at) BETWEEN ? AND ? GROUP BY category ORDER BY qtd DESC",
        (start_iso, end_iso)
    ).fetchall()

    if cat_rows:
        cat_data = [{"Categoria": r['category'], "Qtd": r['qtd'], "Venda Total": f"R$ {r['total_venda']:.2f}"} for r in cat_rows]
        st.dataframe(pd.DataFrame(cat_data), use_container_width=True, hide_index=True)

    # ---- Top 5 clientes ----
    st.subheader("🏆 Top 5 Clientes (por valor de pedidos)")
    top_clients = exec_query(
        """SELECT c.name, COUNT(o.id) AS qtd_pedidos, SUM(o.price_sale) AS total_venda 
           FROM orders o JOIN clients c ON c.id = o.client_id 
           WHERE date(o.created_at) BETWEEN ? AND ?
           GROUP BY c.name ORDER BY total_venda DESC LIMIT 5""",
        (start_iso, end_iso)
    ).fetchall()

    if top_clients:
        top_data = [{"Cliente": r['name'], "Pedidos": r['qtd_pedidos'], "Total Vendas": f"R$ {r['total_venda']:.2f}"} for r in top_clients]
        st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)


# ============================================================================
# 2) RELATÓRIO POR CLIENTE
# ============================================================================
elif relatorio_tipo == "👤 Relatório por Cliente":
    st.header("👤 Relatório por Cliente")

    clientes = exec_query(get_active_clients_query()).fetchall()
    if not clientes:
        st.info("Nenhum cliente cadastrado.")
        st.stop()

    client_options = {f"{c['name']} (#{c['id']})": c['id'] for c in clientes}
    cliente_sel = st.selectbox("Selecione o cliente", list(client_options.keys()), index=None, placeholder="Selecione...")

    if cliente_sel:
        cid = client_options[cliente_sel]

        # Info do cliente
        cli = exec_query("SELECT * FROM clients WHERE id = ?", (cid,)).fetchone()
        if cli:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**Nome:** {cli['name']}")
            with col2:
                st.write(f"**Telefone:** {cli['phone'] or '—'}")
            with col3:
                st.write(f"**CPF:** {cli['cpf'] or '—'}")
            with col4:
                st.write(f"**Status:** {cli['status']}")

        st.divider()

        # Pedidos do cliente
        pedidos_cli = exec_query(
            "SELECT * FROM orders WHERE client_id = ? AND date(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",
            (cid, start_iso, end_iso)
        ).fetchall()

        st.subheader(f"📦 Pedidos ({len(pedidos_cli)})")

        if pedidos_cli:
            data_ped = []
            for p in pedidos_cli:
                data_ped.append({
                    "Pedido": f"#{p['id']}",
                    "Categoria": p['category'],
                    "Tipo": p['type'],
                    "Produto": p['product'],
                    "Custo": f"R$ {p['price_cost']:.2f}",
                    "Venda": f"R$ {p['price_sale']:.2f}",
                    "Status": STATUS_LABELS.get(p['status'], p['status']),
                    "Data": format_br_date(p['created_at']),
                })
            st.dataframe(pd.DataFrame(data_ped), use_container_width=True, hide_index=True)

            # Resumo financeiro do cliente
            st.subheader("💰 Resumo Financeiro do Cliente")
            total_custo_cli = sum(p['price_cost'] for p in pedidos_cli)
            total_venda_cli = sum(p['price_sale'] for p in pedidos_cli)
            margem_cli = total_venda_cli - total_custo_cli

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Custo Total", f"R$ {total_custo_cli:.2f}")
            with col2:
                st.metric("Venda Total", f"R$ {total_venda_cli:.2f}")
            with col3:
                st.metric("Margem Total", f"R$ {margem_cli:.2f}")

            # NCs do cliente
            nc_cli = exec_query(
                """SELECT n.*, o.product FROM nonconformities n 
                   JOIN orders o ON o.id = n.order_id 
                   WHERE o.client_id = ? AND date(n.created_at) BETWEEN ? AND ?
                   ORDER BY n.created_at DESC""",
                (cid, start_iso, end_iso)
            ).fetchall()

            if nc_cli:
                st.subheader(f"❌ Não Conformidades ({len(nc_cli)})")
                for nc in nc_cli:
                    st.write(f"- Pedido #{nc['order_id']} ({nc['product']}): **{nc['kind']}** — {nc['description'] or 'Sem descrição'}")
        else:
            st.info("Nenhum pedido para este cliente no período.")


# ============================================================================
# 3) PEDIDOS POR STATUS
# ============================================================================
elif relatorio_tipo == "📦 Pedidos por Status":
    st.header("📦 Pedidos por Status")

    status_options = list(STATUS_LABELS.keys())
    status_labels_list = [STATUS_LABELS[s] for s in status_options]

    status_sel = st.selectbox("Filtrar por Status", status_labels_list, index=None, placeholder="Todos os status...")

    # Montar query
    if status_sel:
        status_key = status_options[status_labels_list.index(status_sel)]
        rows = exec_query(
            "SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id = o.client_id WHERE o.status = ? AND date(o.created_at) BETWEEN ? AND ? ORDER BY o.created_at DESC",
            (status_key, start_iso, end_iso)
        ).fetchall()
    else:
        rows = exec_query(
            "SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id = o.client_id WHERE date(o.created_at) BETWEEN ? AND ? ORDER BY o.created_at DESC",
            (start_iso, end_iso)
        ).fetchall()

    st.caption(f"📋 {len(rows)} pedidos encontrados")

    if rows:
        data_rows = []
        for r in rows:
            data_rows.append({
                "Pedido": f"#{r['id']}",
                "Cliente": r['client_name'],
                "Categoria": r['category'],
                "Tipo": r['type'],
                "Produto": r['product'],
                "Custo": f"R$ {r['price_cost']:.2f}",
                "Venda": f"R$ {r['price_sale']:.2f}",
                "Status": STATUS_LABELS.get(r['status'], r['status']),
                "Criado em": format_br_date(r['created_at']),
            })
        
        df = pd.DataFrame(data_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Totais
        total_c = sum(r['price_cost'] for r in rows)
        total_v = sum(r['price_sale'] for r in rows)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Custo", f"R$ {total_c:.2f}")
        with col2:
            st.metric("Total Venda", f"R$ {total_v:.2f}")
        with col3:
            st.metric("Margem", f"R$ {total_v - total_c:.2f}")
    else:
        st.info("Nenhum pedido encontrado com os filtros selecionados.")


# ============================================================================
# 4) FINANCEIRO DETALHADO
# ============================================================================
elif relatorio_tipo == "💰 Financeiro Detalhado":
    st.header("💰 Relatório Financeiro Detalhado")

    # Resumo geral
    fin_rows = exec_query(
        """SELECT f.*, o.category, o.type, o.product, o.status AS order_status, c.name AS client_name
           FROM finance_entries f
           JOIN orders o ON o.id = f.order_id
           JOIN clients c ON c.id = o.client_id
           WHERE date(f.created_at) BETWEEN ? AND ?
           ORDER BY f.created_at DESC""",
        (start_iso, end_iso)
    ).fetchall()

    if not fin_rows:
        st.info("Nenhum lançamento financeiro no período.")
        st.stop()

    total_custo = sum(r['cost'] for r in fin_rows)
    total_venda = sum(r['sale'] for r in fin_rows)
    total_margem = sum(r['margin'] for r in fin_rows)
    total_pago = sum(r['cost'] for r in fin_rows if r['settled'] == 1)
    total_pendente = sum(r['cost'] for r in fin_rows if r['settled'] == 0)

    # Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📦 Lançamentos", len(fin_rows))
    with col2:
        st.metric("💰 Receita", f"R$ {total_venda:.2f}")
    with col3:
        st.metric("📉 Custo", f"R$ {total_custo:.2f}")
    with col4:
        st.metric("📊 Lucro", f"R$ {total_margem:.2f}")
    with col5:
        pct = f"{(total_margem / total_venda * 100):.1f}%" if total_venda > 0 else "0%"
        st.metric("📈 Margem %", pct)

    st.divider()

    # Pagamentos
    col_pago, col_pend = st.columns(2)
    with col_pago:
        st.metric("✅ Pago ao Fornecedor", f"R$ {total_pago:.2f}", delta=f"{len([r for r in fin_rows if r['settled']==1])} lançamentos")
    with col_pend:
        st.metric("⏳ Pendente Fornecedor", f"R$ {total_pendente:.2f}", delta=f"{len([r for r in fin_rows if r['settled']==0])} lançamentos")

    st.divider()

    # Lançamentos por categoria
    st.subheader("📂 Receita por Categoria")
    cat_fin = {}
    for r in fin_rows:
        cat = r['category']
        if cat not in cat_fin:
            cat_fin[cat] = {"custo": 0, "venda": 0, "margem": 0, "qtd": 0}
        cat_fin[cat]["custo"] += r['cost']
        cat_fin[cat]["venda"] += r['sale']
        cat_fin[cat]["margem"] += r['margin']
        cat_fin[cat]["qtd"] += 1

    cat_data = [{
        "Categoria": cat,
        "Qtd": v["qtd"],
        "Custo": f"R$ {v['custo']:.2f}",
        "Venda": f"R$ {v['venda']:.2f}",
        "Lucro": f"R$ {v['margem']:.2f}",
        "Margem %": f"{(v['margem']/v['venda']*100):.1f}%" if v['venda'] > 0 else "0%"
    } for cat, v in sorted(cat_fin.items(), key=lambda x: x[1]['venda'], reverse=True)]

    st.dataframe(pd.DataFrame(cat_data), use_container_width=True, hide_index=True)

    st.divider()

    # Tabela completa
    st.subheader("📋 Todos os Lançamentos")
    fin_data = []
    for r in fin_rows:
        fin_data.append({
            "Pedido": f"#{r['order_id']}",
            "Cliente": r['client_name'],
            "Produto": f"{r['category']}/{r['type']}/{r['product']}",
            "Custo": f"R$ {r['cost']:.2f}",
            "Venda": f"R$ {r['sale']:.2f}",
            "Margem": f"R$ {r['margin']:.2f}",
            "Pago": "✅" if r['settled'] == 1 else "⏳",
            "Data": format_br_date(r['created_at']),
        })
    st.dataframe(pd.DataFrame(fin_data), use_container_width=True, hide_index=True)


# ============================================================================
# 5) VENDAS DO ESTOQUE
# ============================================================================
elif relatorio_tipo == "🛒 Vendas do Estoque":
    st.header("🛒 Relatório de Vendas (Estoque Pronto)")

    vendas = exec_query(
        """SELECT o.*, c.name AS client_name 
           FROM orders o JOIN clients c ON c.id = o.client_id 
           WHERE o.status = ? AND date(o.created_at) BETWEEN ? AND ?
           ORDER BY o.created_at DESC""",
        (OrderStatus.VENDIDO, start_iso, end_iso)
    ).fetchall()

    if not vendas:
        st.info("Nenhuma venda de estoque no período.")
        st.stop()

    total_receita_vendas = sum(v['price_sale'] for v in vendas)
    total_custo_vendas = sum(v['price_cost'] for v in vendas)
    lucro_vendas = total_receita_vendas - total_custo_vendas

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🛒 Total de Vendas", len(vendas))
    with col2:
        st.metric("💰 Receita", f"R$ {total_receita_vendas:.2f}")
    with col3:
        st.metric("📉 Custo", f"R$ {total_custo_vendas:.2f}")
    with col4:
        st.metric("📊 Lucro", f"R$ {lucro_vendas:.2f}")

    st.divider()

    # Vendas por cliente
    st.subheader("👤 Vendas por Cliente")
    cli_vendas = {}
    for v in vendas:
        cn = v['client_name']
        if cn not in cli_vendas:
            cli_vendas[cn] = {"qtd": 0, "total": 0}
        cli_vendas[cn]["qtd"] += 1
        cli_vendas[cn]["total"] += v['price_sale']

    cli_data = [{"Cliente": c, "Qtd Vendas": d["qtd"], "Total": f"R$ {d['total']:.2f}"}
                for c, d in sorted(cli_vendas.items(), key=lambda x: x[1]['total'], reverse=True)]
    st.dataframe(pd.DataFrame(cli_data), use_container_width=True, hide_index=True)

    st.divider()

    # Tabela detalhada
    st.subheader("📋 Detalhamento das Vendas")
    vendas_data = []
    for v in vendas:
        vendas_data.append({
            "Pedido": f"#{v['id']}",
            "Cliente": v['client_name'],
            "Produto": f"{v['category']}/{v['type']}/{v['product']}",
            "Custo": f"R$ {v['price_cost']:.2f}",
            "Venda": f"R$ {v['price_sale']:.2f}",
            "Margem": f"R$ {v['price_sale'] - v['price_cost']:.2f}",
            "Data": format_br_date(v['created_at']),
        })
    st.dataframe(pd.DataFrame(vendas_data), use_container_width=True, hide_index=True)

    # Estoque atual
    st.divider()
    st.subheader("📦 Estoque Atual (Itens Disponíveis)")
    estoque = exec_query("SELECT * FROM stock_items WHERE quantity > 0 ORDER BY created_at DESC").fetchall()
    if estoque:
        est_data = [{"Produto": f"{r['category']}/{r['type']}/{r['product']}", "Qtd": r['quantity'],
                      "Preço Venda": f"R$ {r['price_sale']:.2f}", "Valor em Estoque": f"R$ {r['price_sale'] * r['quantity']:.2f}"}
                     for r in estoque]
        df_est = pd.DataFrame(est_data)
        st.dataframe(df_est, use_container_width=True, hide_index=True)
        total_estoque = sum(r['price_sale'] * r['quantity'] for r in estoque)
        st.metric("💰 Valor Total em Estoque", f"R$ {total_estoque:.2f}")
    else:
        st.info("Nenhum item em estoque.")


# ============================================================================
# 6) NÃO CONFORMIDADES
# ============================================================================
elif relatorio_tipo == "❌ Não Conformidades":
    st.header("❌ Relatório de Não Conformidades")

    ncs = exec_query(
        """SELECT n.*, o.category, o.type, o.product, o.price_cost, o.price_sale, c.name AS client_name
           FROM nonconformities n
           JOIN orders o ON o.id = n.order_id
           JOIN clients c ON c.id = o.client_id
           WHERE date(n.created_at) BETWEEN ? AND ?
           ORDER BY n.created_at DESC""",
        (start_iso, end_iso)
    ).fetchall()

    if not ncs:
        st.info("Nenhuma não conformidade no período. Ótimo! 🎉")
        st.stop()

    # KPIs
    total_ncs = len(ncs)
    total_pedidos_periodo = exec_query(
        "SELECT COUNT(*) AS c FROM orders WHERE date(created_at) BETWEEN ? AND ?",
        (start_iso, end_iso)
    ).fetchone()
    qtd_pedidos = safe_value(total_pedidos_periodo, 'c', 1)
    taxa_nc = (total_ncs / qtd_pedidos * 100) if qtd_pedidos > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("❌ Total de NCs", total_ncs)
    with col2:
        st.metric("📦 Pedidos no Período", qtd_pedidos)
    with col3:
        st.metric("📊 Taxa de NC", f"{taxa_nc:.1f}%")

    st.divider()

    # NCs por tipo
    st.subheader("📂 NCs por Tipo")
    tipo_nc = {}
    for nc in ncs:
        k = nc['kind']
        tipo_nc[k] = tipo_nc.get(k, 0) + 1

    tipo_data = [{"Tipo": k, "Quantidade": v} for k, v in sorted(tipo_nc.items(), key=lambda x: x[1], reverse=True)]
    df_tipo = pd.DataFrame(tipo_data)

    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.bar_chart(df_tipo.set_index("Tipo"))
    with col_table:
        st.dataframe(df_tipo, use_container_width=True, hide_index=True)

    st.divider()

    # NCs por categoria
    st.subheader("📦 NCs por Categoria de Produto")
    cat_nc = {}
    for nc in ncs:
        cat = nc['category']
        cat_nc[cat] = cat_nc.get(cat, 0) + 1
    cat_nc_data = [{"Categoria": c, "NCs": q} for c, q in sorted(cat_nc.items(), key=lambda x: x[1], reverse=True)]
    st.dataframe(pd.DataFrame(cat_nc_data), use_container_width=True, hide_index=True)

    st.divider()

    # Lista detalhada
    st.subheader("📋 Detalhamento das NCs")
    nc_data = []
    for nc in ncs:
        nc_data.append({
            "NC #": nc['id'],
            "Pedido": f"#{nc['order_id']}",
            "Cliente": nc['client_name'],
            "Produto": f"{nc['category']}/{nc['type']}/{nc['product']}",
            "Tipo NC": nc['kind'],
            "Descrição": nc['description'] or "—",
            "Qtd": nc['count'],
            "Data": format_br_date(nc['created_at']),
        })
    st.dataframe(pd.DataFrame(nc_data), use_container_width=True, hide_index=True)


# ============================================================================
# 7) HISTÓRICO COMPLETO
# ============================================================================
elif relatorio_tipo == "📋 Histórico Completo":
    st.header("📋 Histórico Completo de Pedidos")

    # Filtros adicionais
    col_cli, col_cat, col_status = st.columns(3)

    with col_cli:
        clientes = exec_query(get_active_clients_query()).fetchall()
        cli_opts = ["Todos"] + [f"{c['name']} (#{c['id']})" for c in clientes]
        cli_filtro = st.selectbox("Filtrar por Cliente", cli_opts)

    with col_cat:
        cats = exec_query("SELECT DISTINCT category FROM orders ORDER BY category").fetchall()
        cat_opts = ["Todas"] + [c['category'] for c in cats]
        cat_filtro = st.selectbox("Filtrar por Categoria", cat_opts)

    with col_status:
        st_opts = ["Todos"] + list(STATUS_LABELS.values())
        status_filtro = st.selectbox("Filtrar por Status", st_opts)

    # Montar query dinâmica
    query = """SELECT o.*, c.name AS client_name 
               FROM orders o JOIN clients c ON c.id = o.client_id
               WHERE date(o.created_at) BETWEEN ? AND ?"""
    params = [start_iso, end_iso]

    if cli_filtro != "Todos":
        # Extrair ID do cliente
        cid = int(cli_filtro.split("#")[1].rstrip(")"))
        query += " AND o.client_id = ?"
        params.append(cid)

    if cat_filtro != "Todas":
        query += " AND o.category = ?"
        params.append(cat_filtro)

    if status_filtro != "Todos":
        # Converter label de volta para status key
        status_key = [k for k, v in STATUS_LABELS.items() if v == status_filtro]
        if status_key:
            query += " AND o.status = ?"
            params.append(status_key[0])

    query += " ORDER BY o.created_at DESC"

    rows = exec_query(query, tuple(params)).fetchall()

    st.caption(f"📋 {len(rows)} pedidos encontrados")

    if rows:
        hist_data = []
        for r in rows:
            hist_data.append({
                "Pedido": f"#{r['id']}",
                "Cliente": r['client_name'],
                "Categoria": r['category'],
                "Tipo": r['type'],
                "Produto": r['product'],
                "Custo": f"R$ {r['price_cost']:.2f}",
                "Venda": f"R$ {r['price_sale']:.2f}",
                "Margem": f"R$ {r['price_sale'] - r['price_cost']:.2f}",
                "Status": STATUS_LABELS.get(r['status'], r['status']),
                "Criado": format_br_date(r['created_at']),
                "Atualizado": format_br_date(r['updated_at']),
            })

        df = pd.DataFrame(hist_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Totais
        st.divider()
        total_c = sum(r['price_cost'] for r in rows)
        total_v = sum(r['price_sale'] for r in rows)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📦 Total Pedidos", len(rows))
        with col2:
            st.metric("💰 Total Custo", f"R$ {total_c:.2f}")
        with col3:
            st.metric("💵 Total Venda", f"R$ {total_v:.2f}")
        with col4:
            st.metric("📊 Margem Total", f"R$ {total_v - total_c:.2f}")

        # Exportar CSV
        st.divider()
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar para CSV",
            data=csv_data,
            file_name=f"relatorio_pedidos_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Nenhum pedido encontrado com os filtros selecionados.")
