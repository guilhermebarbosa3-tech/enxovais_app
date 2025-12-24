import streamlit as st
import os
from core.db import get_conn, now_iso, to_json, from_json
from core.models import OrderStatus
from core.storage import save_and_resize
from services.motores.nc_pdf_generator import generate_nc_pdf

st.title("Pedidos Não Conformes")
conn = get_conn()
rows = conn.execute("SELECT o.*, c.name AS client_name FROM orders o JOIN clients c ON c.id=o.client_id WHERE o.status=? ORDER BY o.id DESC", (OrderStatus.RECEBIDO_NC,)).fetchall()

for r in rows:
    with st.expander(f"#{r['id']} — {r['client_name']} • {r['category']}/{r['type']}/{r['product']}"):
        # Informações do pedido
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"**Categoria:** {r['category']}")
        with col2:
            st.caption(f"**Tipo:** {r['type']}")
        with col3:
            st.caption(f"**Produto:** {r['product']}")
        
        st.divider()
        
        # Fotos Originais do Pedido
        original_photos = from_json(r['photos'], [])
        if original_photos:
            st.caption("📷 Fotos Originais do Pedido")
            photo_cols = st.columns(3)
            for idx, photo_path in enumerate(original_photos):
                if os.path.exists(photo_path):
                    with photo_cols[idx % 3]:
                        st.image(photo_path, use_container_width=True, caption=f"Original {idx + 1}")
                else:
                    with photo_cols[idx % 3]:
                        st.warning(f"📷 Foto {idx + 1} não disponível (arquivo não encontrado)")
            st.divider()
        
        # Tipo e descrição da NC
        kind = st.selectbox("Tipo de NC", ["medida","tecido","cor","acabamento","outro"], key=f"kind_{r['id']}")
        desc = st.text_area("Descrição do problema", key=f"desc_{r['id']}", height=100, placeholder="Descreva detalhadamente o problema encontrado...")
        
        st.caption("📸 Fotos do Problema (evidência)")
        problem_photos = st.file_uploader(
            "Carregue as fotos do problema",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"photos_{r['id']}"
        )
        
        # Visualizar fotos carregadas
        if problem_photos:
            st.caption(f"📷 {len(problem_photos)} foto(s) selecionada(s)")
            photo_cols = st.columns(3)
            for idx, photo in enumerate(problem_photos):
                with photo_cols[idx % 3]:
                    st.image(photo, use_container_width=True)
        
        st.divider()
        
        # Botões de ação
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("📄 Gerar PDF para Fornecedor", key=f"pdf_{r['id']}"):
                if not kind or not desc:
                    st.error("Preencha o tipo de NC e a descrição antes de gerar o PDF")
                else:
                    # Salvar fotos do problema
                    saved_photos = []
                    if problem_photos:
                        for idx, photo in enumerate(problem_photos):
                            photo_path = save_and_resize(photo, filename_base=f"nc_pedido_{r['id']}_{idx}")
                            saved_photos.append(photo_path)
                    
                    # Gerar PDF
                    pdf_path = generate_nc_pdf(r, kind, desc, saved_photos)
                    
                    # Preparar para download
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="⬇️ Baixar PDF",
                            data=pdf_file.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            key=f"download_{r['id']}"
                        )
                    
                    st.success("✅ PDF gerado com sucesso!")
        
        with btn_col2:
            if st.button("✅ Informar e reenviar ao fornecedor", key=f"send_{r['id']}"):
                if not kind or not desc:
                    st.error("Preencha o tipo de NC e a descrição")
                else:
                    # Salvar fotos do problema
                    saved_photos = []
                    if problem_photos:
                        for idx, photo in enumerate(problem_photos):
                            photo_path = save_and_resize(photo, filename_base=f"nc_pedido_{r['id']}_{idx}")
                            saved_photos.append(photo_path)
                    
                    # Registrar NC
                    conn.execute(
                        "INSERT INTO nonconformities(order_id, kind, description, photos, created_at) VALUES (?,?,?,?, datetime('now'))",
                        (r['id'], kind, desc, to_json(saved_photos))
                    )
                    
                    # Mover para Aguardando Confecção
                    conn.execute(
                        "UPDATE orders SET status=?, updated_at=? WHERE id=?",
                        (OrderStatus.AGUARDANDO_CONF, now_iso(), r['id'])
                    )
                    
                    # Registrar auditoria
                    conn.execute(
                        "INSERT INTO audit_log(entity, entity_id, action, field, before, after, username, ts) VALUES (?,?,?,?,?,?,?, datetime('now'))",
                        ('orders', r['id'], 'status_changed', 'status', OrderStatus.RECEBIDO_NC, OrderStatus.AGUARDANDO_CONF, 'system')
                    )
                    
                    conn.commit()
                    st.success("✅ NC registrada! Pedido retornou para 'Aguardando Confecção'")
