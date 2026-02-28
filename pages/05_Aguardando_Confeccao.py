import streamlit as st
import os
from core.db import get_conn, now_iso, from_json, exec_query, init_db
from core.models import OrderStatus
from core.audit import log_change
from ui.status_badges import badge

# Garantir que o banco está inicializado
init_db()

st.title("Aguardando Confecção")
conn = get_conn()
rows = exec_query("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.AGUARDANDO_CONF,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        # Exibir informações do pedido
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
        
        # Exibir fotos
        photos = from_json(r['photos'], [])
        if photos:
            st.subheader("📸 Fotos do Pedido")
            photo_cols = st.columns(6)
            for idx, photo_path in enumerate(photos):
                col_idx = idx % 6
                with photo_cols[col_idx]:
                    try:
                        if isinstance(photo_path, str) and photo_path.startswith(('http://', 'https://')):
                            st.image(photo_path, width=150, caption=f"Foto {idx + 1}")
                        elif isinstance(photo_path, str) and os.path.exists(photo_path):
                            st.image(photo_path, width=150, caption=f"Foto {idx + 1}")
                        else:
                            st.warning(f"📷 Foto {idx + 1} não disponível")
                    except Exception as e:
                        st.warning(f"Erro ao carregar foto: {e}")
        
        st.divider()
        
        # Ações
        action_cols = st.columns([1,1,1,1])
        
        with action_cols[0]:
            if st.button("✅ Chegou conforme", key=f"ok_{r['id']}", use_container_width=True):
                exec_query("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.EM_ESTOQUE, now_iso(), r['id']), commit=True)
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.AGUARDANDO_CONF, OrderStatus.EM_ESTOQUE)
                st.success("Movido para 'Pedidos em Estoque'")
        
        with action_cols[1]:
            if st.button("❌ Não conforme", key=f"nc_{r['id']}", use_container_width=True):
                exec_query("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.RECEBIDO_NC, now_iso(), r['id']), commit=True)
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.AGUARDANDO_CONF, OrderStatus.RECEBIDO_NC)
                st.warning("Movido para 'Não Conformes'")
        
        with action_cols[2]:
            if st.button("🔙 Retornar para editar", key=f"return_{r['id']}", use_container_width=True):
                exec_query("UPDATE orders SET status=?, updated_at=? WHERE id=?", (OrderStatus.CRIADO, now_iso(), r['id']), commit=True)
                log_change("order", r['id'], "STATUS_UPDATE", "status", OrderStatus.AGUARDANDO_CONF, OrderStatus.CRIADO)
                st.info("Pedido retornado para 'Pedidos' — você pode editá-lo agora")
                st.rerun()
