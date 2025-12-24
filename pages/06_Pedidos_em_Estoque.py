import streamlit as st
from core.db import get_conn, now_iso, from_json, exec_query
from core.models import OrderStatus
from ui.status_badges import badge
from core.audit import log_change

st.title("Pedidos em Estoque")
conn = get_conn()
rows = exec_query("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.EM_ESTOQUE,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        # Preços e Status
        cols = st.columns([1,1,1])
        with cols[0]:
            st.write(f"Custo: R$ {r['price_cost']:.2f}")
            st.write(f"Venda: R$ {r['price_sale']:.2f}")
        with cols[1]:
            badge(r['status'])
        
        # Exibir observações
        if r['notes_free']:
            st.subheader("📝 Observações")
            st.write(r['notes_free'])
        
        # Exibir especificações estruturadas
        notes_struct = from_json(r['notes_struct'], {})
        if notes_struct:
            st.subheader("⚙️ Especificações")
            for key, value in notes_struct.items():
                st.write(f"**{key}**: {value}")
        
        # Exibir fotos se existirem
        photos = from_json(r['photos'], [])
        if photos:
            st.subheader("📸 Fotos do Pedido")
            photo_cols = st.columns(6)
            for idx, photo_path in enumerate(photos):
                col_idx = idx % 6
                with photo_cols[col_idx]:
                    if os.path.exists(photo_path):
                        try:
                            st.image(photo_path, width=150, caption=f"Foto {idx + 1}")
                        except Exception as e:
                            st.warning(f"Erro ao carregar foto: {e}")
                    else:
                        st.warning(f"📷 Foto {idx + 1} não disponível")
        
        st.divider()
        
        # Opção de editar antes de concluir
        edit = st.checkbox("✏️ Alterar valores antes de concluir?", key=f"edit_{r['id']}")
        new_cost, new_sale = r['price_cost'], r['price_sale']
        if edit:
            new_cost = st.number_input("Novo custo", value=float(r['price_cost']), key=f"ncost_{r['id']}")
            new_sale = st.number_input("Nova venda", value=float(r['price_sale']), key=f"nsale_{r['id']}")
        
        st.divider()
        
        # Botões de ação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Concluir Entrega", key=f"done_{r['id']}", use_container_width=True):
                if edit:
                    log_change("order", r['id'], "PRICE_UPDATE", "price_cost", r['price_cost'], new_cost)
                    log_change("order", r['id'], "PRICE_UPDATE", "price_sale", r['price_sale'], new_sale)
                    exec_query("UPDATE orders SET price_cost=?, price_sale=?, updated_at=? WHERE id=?", (new_cost, new_sale, now_iso(), r['id']), commit=False)
                
                # Criar lançamento financeiro
                margin = (new_sale or 0.0) - (new_cost or 0.0)
                exec_query("INSERT INTO finance_entries(order_id, cost, sale, margin, settled, created_at) VALUES (?,?,?,?,0, ?)", (r['id'], new_cost, new_sale, margin, now_iso()), commit=False)
                
                # Atualizar status
                exec_query("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.ENTREGUE, now_iso(), r['id']), commit=True)
                
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.EM_ESTOQUE, OrderStatus.ENTREGUE)
                
                st.success("✅ Entrega concluída e lançamento financeiro criado")
                st.rerun()
        
        with col2:
            if st.button("🔙 Retornar para Confecção", key=f"return_{r['id']}", use_container_width=True):
                exec_query("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id']), commit=True)
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.EM_ESTOQUE, OrderStatus.AGUARDANDO_CONF)
                st.warning("↩️ Pedido retornado para Aguardando Confecção")
                st.rerun()
        
        with col3:
            if st.button("🗑️ Excluir", key=f"del_{r['id']}", use_container_width=True):
                st.session_state[f"delete_mode_{r['id']}"] = True
        
        # Modo exclusão com confirmação
        if st.session_state.get(f"delete_mode_{r['id']}", False):
            st.warning("⚠️ Você tem certeza que deseja excluir este pedido? Esta ação é irreversível!")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ Sim, excluir", key=f"confirm_del_{r['id']}", use_container_width=True):
                    log_change("order", r['id'], "DELETE", "all", str(r), None)
                    exec_query("DELETE FROM orders WHERE id=?", (r['id'],), commit=True)
                    st.success("✅ Pedido deletado com sucesso")
                    st.rerun()
            
            with col_cancel:
                if st.button("❌ Cancelar", key=f"cancel_del_{r['id']}", use_container_width=True):
                    st.session_state[f"delete_mode_{r['id']}"] = False
                    st.rerun()
