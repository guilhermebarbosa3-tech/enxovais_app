import streamlit as st
from core.models import OrderStatus

def badge(status: str):
    color = {
        OrderStatus.CRIADO: "gray",
        OrderStatus.ENVIADO_FORNECEDOR: "blue",
        OrderStatus.AGUARDANDO_CONF: "blue",
        OrderStatus.RECEBIDO_CONF: "green",
        OrderStatus.RECEBIDO_NC: "red",
        OrderStatus.EM_ESTOQUE: "purple",
        OrderStatus.ENTREGUE: "green",
        OrderStatus.FINALIZADO_FIN: "green",
    }.get(status, "gray")
    st.markdown(f"<span style='padding:4px 8px;border-radius:999px;background:{color};color:white;font-size:12px'>{status}</span>", unsafe_allow_html=True)
