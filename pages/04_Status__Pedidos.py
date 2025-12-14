import streamlit as st
import urllib.parse
from core.db import get_conn, now_iso, from_json, to_json
from core.models import OrderStatus
from core.audit import log_change
from ui.status_badges import badge
from services.motores.pdf_generator import generate_order_pdf
from services.messenger import generate_whatsapp_message

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
        action_cols = st.columns([1,1,1])
        
        with action_cols[0]:
            if st.button("✏️ Editar", key=f"edit_{r['id']}", use_container_width=True):
                st.session_state[f"edit_mode_{r['id']}"] = True
        
        with action_cols[1]:
            if st.button("🔄 Compartilhar", key=f"send_{r['id']}", use_container_width=True):
                st.session_state[f"send_mode_{r['id']}"] = True
        
        with action_cols[2]:
            if st.button("🗑️ Excluir", key=f"del_{r['id']}", use_container_width=True):
                st.session_state[f"delete_mode_{r['id']}"] = True
        
        # Modo compartilhamento
        if st.session_state.get(f"send_mode_{r['id']}", False):
            # Gerar PDF com fotos automaticamente
            pdf_path = generate_order_pdf(r)
            st.success("✅ PDF gerado com sucesso!")
            
            # Botão de download (não muda status)
            with open(pdf_path, 'rb') as pdf_file:
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=pdf_file,
                    file_name=f"pedido_{r['id']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            st.divider()
            
            # Informação e botões de ação
            st.info("📢 Deseja compartilhar e enviar para confecção?")
            
            col_share, col_cancel = st.columns(2)
            
            with col_share:
                if st.button("📱 Compartilhar PDF", key=f"share_native_{r['id']}", use_container_width=True):
                    # Usar Web Share API via JavaScript para compartilhar PDF
                    share_script = f"""
                    <script>
                    if (navigator.share) {{
                        fetch('{pdf_path}')
                        .then(res => res.blob())
                        .then(blob => {{
                            const file = new File([blob], 'pedido_{r['id']}.pdf', {{ type: 'application/pdf' }});
                            navigator.share({{
                                title: 'Pedido #{r['id']}',
                                text: 'Pedido do cliente {r['client_name']}',
                                files: [file]
                            }}).catch(err => console.log('Erro ao compartilhar:', err));
                        }});
                    }} else {{
                        alert('Seu navegador não suporta compartilhamento. Use o botão Baixar PDF.');
                    }}
                    </script>
                    """
                    st.components.v1.html(share_script, height=0)
                    
                    # Atualizar status após compartilhar
                    conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id']))
                    conn.execute("INSERT INTO shipments(order_id, medium, when_ts, document_path) VALUES (?,?,?,?)", 
                        (r['id'], "COMPARTILHADO", now_iso(), pdf_path))
                    conn.commit()
                    log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.CRIADO, OrderStatus.AGUARDANDO_CONF)
                    
                    st.session_state[f"send_mode_{r['id']}"] = False
                    st.success("✅ Pedido compartilhado e movido para 'Aguardando Confecção'")
                    st.rerun()
            
            with col_cancel:
                if st.button("❌ Cancelar", key=f"cancel_share_{r['id']}", use_container_width=True):
                    st.session_state[f"send_mode_{r['id']}"] = False
                    st.rerun()
        
        # Modo exclusão com confirmação
        if st.session_state.get(f"delete_mode_{r['id']}", False):
            st.warning("⚠️ Você tem certeza que deseja excluir este pedido? Esta ação é irreversível!")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ Sim, excluir", key=f"confirm_del_{r['id']}", use_container_width=True):
                    log_change("order", r['id'], "DELETE", "all", str(r), None)
                    conn.execute("DELETE FROM orders WHERE id=?", (r['id'],))
                    conn.commit()
                    st.success("Pedido excluído com sucesso")
                    st.session_state[f"delete_mode_{r['id']}"] = False
                    st.rerun()
            with col_cancel:
                if st.button("❌ Cancelar", key=f"cancel_del_{r['id']}", use_container_width=True):
                    st.session_state[f"delete_mode_{r['id']}"] = False
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
