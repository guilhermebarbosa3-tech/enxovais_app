import streamlit as st

def section(title: str):
    st.subheader(title)
    st.divider()

def confirm_dialog(label: str) -> bool:
    return st.checkbox(label, value=False, key=f"confirm_{label}")


def photo_uploader(label: str, accept_multiple=True, key=None):
    # key é opcional; repassa para file_uploader para permitir reset dinâmico
    params = dict(label=label, type=["jpg", "jpeg", "png"], accept_multiple_files=accept_multiple)
    if key is not None:
        params['key'] = key
    return st.file_uploader(**params)
