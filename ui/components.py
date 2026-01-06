import streamlit as st

def section(title: str):
    st.subheader(title)
    st.divider()

def confirm_dialog(label: str) -> bool:
    return st.checkbox(label, value=False, key=f"confirm_{label}")


def photo_uploader(label: str, accept_multiple=True, key=None):
    """
    Componente de upload de fotos com suporte a câmera em dispositivos móveis.
    Oferece duas opções: upload de arquivo ou captura pela câmera.
    """
    # Gerar chaves únicas baseadas no key fornecido
    base_key = key or "photo"
    tab_key = f"{base_key}_tab"
    upload_key = f"{base_key}_upload"
    camera_key = f"{base_key}_camera"
    
    st.write(f"**{label}**")
    
    # Tabs para escolher método de captura
    tab_upload, tab_camera = st.tabs(["📁 Enviar Arquivo", "📷 Usar Câmera"])
    
    fotos_coletadas = []
    
    with tab_upload:
        # Upload tradicional de arquivos
        params = dict(
            label="Selecione as fotos",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=accept_multiple,
            key=upload_key
        )
        uploaded_files = st.file_uploader(**params)
        
        if uploaded_files:
            if isinstance(uploaded_files, list):
                fotos_coletadas.extend(uploaded_files)
            else:
                fotos_coletadas.append(uploaded_files)
    
    with tab_camera:
        st.info("📱 Use a câmera do seu dispositivo para tirar uma foto")
        # Captura pela câmera (uma foto por vez)
        camera_photo = st.camera_input("Tire uma foto", key=camera_key)
        
        if camera_photo:
            fotos_coletadas.append(camera_photo)
            st.success("✅ Foto capturada!")
    
    # Retornar lista de fotos ou None
    if fotos_coletadas:
        return fotos_coletadas if accept_multiple else fotos_coletadas[0]
    return None


def photo_uploader_simple(label: str, accept_multiple=True, key=None):
    """
    Versão simplificada do uploader (apenas arquivo, sem câmera).
    Mantido para compatibilidade.
    """
    params = dict(label=label, type=["jpg", "jpeg", "png"], accept_multiple_files=accept_multiple)
    if key is not None:
        params['key'] = key
    return st.file_uploader(**params)
