import streamlit as st
from core.db import get_conn
from ui.components import section

st.title("Clientes")
conn = get_conn()

with st.form("novo_cliente"):
    name = st.text_input("Nome")
    address = st.text_input("Endereço")
    cpf = st.text_input("CPF")
    phone = st.text_input("Telefone")
    status = st.selectbox("Status", ["ADIMPLENTE","INADIMPLENTE"])
    if st.form_submit_button("Salvar"):
        conn.execute("INSERT INTO clients(name,address,cpf,phone,status) VALUES (?,?,?,?,?)", (name,address,cpf,phone,status))
        conn.commit()
        st.success("Cliente salvo")

section("Lista")
rows = conn.execute("SELECT * FROM clients ORDER BY id DESC").fetchall()
for r in rows:
    st.write(f"#{r['id']} — {r['name']} ({r['status']})")
