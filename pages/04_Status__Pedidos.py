import streamlit as st
from core.db import get_conn, now_iso, from_json, to_json
from core.models import OrderStatus
from core.audit import log_change
from ui.status_badges import badge
from services.exporter import export_order_pdf

st.title("Status • Pedidos")
conn = get_conn()

rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.CRIADO,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
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
                    try:
                        st.image(photo_path, width=150, caption=f"Foto {idx + 1}")
                    except Exception as e:
                        st.warning(f"Erro ao carregar foto: {e}")
        
        st.divider()
        
        # Ações
        action_cols = st.columns([1,1,1,1])
        
        with action_cols[0]:
            if st.button("✏️ Editar", key=f"edit_{r['id']}", use_container_width=True):
                st.session_state[f"edit_mode_{r['id']}"] = True
        
        with action_cols[1]:
            if st.button("📄 Exportar", key=f"export_{r['id']}", use_container_width=True):
                pdf_path = export_order_pdf(r)
                st.success(f"Exportado: {pdf_path}")
                # Registrar em shipments
                conn.execute("INSERT INTO shipments(order_id, medium, when_ts, document_path) VALUES (?,?,?,?)", 
                    (r['id'], "EXPORT_PDF", now_iso(), pdf_path))
                conn.commit()
                log_change("order", r['id'], "EXPORT_PDF", "document_path", None, pdf_path)
        
        with action_cols[2]:
            if st.button("🔄 Compartilhar p/ fornecedor", key=f"send_{r['id']}", use_container_width=True):
                conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id']))
                conn.commit()
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.CRIADO, OrderStatus.AGUARDANDO_CONF)
                st.success("Pedido enviado e movido para 'Aguardando Confecção'")
        
        with action_cols[3]:
            if st.button("🗑️ Excluir", key=f"del_{r['id']}", use_container_width=True):
                if st.checkbox("Confirmar exclusão?", key=f"confirm_del_{r['id']}"):
                    log_change("order", r['id'], "DELETE", "all", str(r), None)
                    conn.execute("DELETE FROM orders WHERE id=?", (r['id'],))
                    conn.commit()
                    st.warning("Pedido excluído")
                    st.rerun()
        
        # Modo edição
        if st.session_state.get(f"edit_mode_{r['id']}", False):
            st.subheader("Editar Pedido")
            with st.form(f"edit_form_{r['id']}"):
                new_cost = st.number_input("Preço de custo", value=float(r['price_cost']), key=f"ecost_{r['id']}")
                new_sale = st.number_input("Preço de venda", value=float(r['price_sale']), key=f"esale_{r['id']}")
                new_notes = st.text_area("Observações", value=r['notes_free'], key=f"enotes_{r['id']}")
                
                if st.form_submit_button("Salvar alterações"):
                    if r['price_cost'] != new_cost:
                        log_change("order", r['id'], "UPDATE", "price_cost", r['price_cost'], new_cost)
                    if r['price_sale'] != new_sale:
                        log_change("order", r['id'], "UPDATE", "price_sale", r['price_sale'], new_sale)
                    if r['notes_free'] != new_notes:
                        log_change("order", r['id'], "UPDATE", "notes_free", r['notes_free'], new_notes)
                    
                    conn.execute("UPDATE orders SET price_cost=?, price_sale=?, notes_free=?, updated_at=? WHERE id=?", 
                        (new_cost, new_sale, new_notes, now_iso(), r['id']))
                    conn.commit()
                    st.session_state[f"edit_mode_{r['id']}"] = False
                    st.success("Alterações salvas")
                    st.rerun()
