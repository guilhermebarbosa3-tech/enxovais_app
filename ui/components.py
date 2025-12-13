import streamlit as st

def section(title: str):
    st.subheader(title)
    st.divider()

def confirm_dialog(label: str) -> bool:
    return st.checkbox(label, value=False, key=f"confirm_{label}")


def photo_uploader(label: str, accept_multiple=True):
    return st.file_uploader(label, type=["jpg","jpeg","png"], accept_multiple_files=accept_multiple)
