import streamlit as st
from core.db import init_db, get_conn
from core.models import OrderStatus

st.set_page_config(
    page_title="Estoque Exonvais", 
    page_icon="🧵", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Carrega CSS customizado para mobile
import os
css_path = os.path.join(os.path.dirname(__file__), "assets", "mobile.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Injetar JavaScript para controlar sidebar em mobile
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    
    if (sidebar) {
        // Detectar mudanças no atributo aria-expanded
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'aria-expanded') {
                    const isExpanded = sidebar.getAttribute('aria-expanded') === 'true';
                    const windowWidth = window.innerWidth;
                    
                    // Em mobile (< 768px), controlar overlay
                    if (windowWidth <= 768) {
                        if (isExpanded) {
                            // Mostrar overlay
                            document.body.style.overflow = 'hidden';
                            if (!document.querySelector('.sidebar-overlay')) {
                                const overlay = document.createElement('div');
                                overlay.className = 'sidebar-overlay';
                                overlay.style.cssText = `
                                    position: fixed;
                                    top: 0;
                                    left: 0;
                                    width: 100%;
                                    height: 100%;
                                    background: rgba(0, 0, 0, 0.5);
                                    z-index: 499;
                                    cursor: pointer;
                                `;
                                overlay.onclick = function() {
                                    sidebar.setAttribute('aria-expanded', 'false');
                                };
                                document.body.appendChild(overlay);
                            }
                        } else {
                            // Ocultar overlay
                            document.body.style.overflow = 'auto';
                            const overlay = document.querySelector('.sidebar-overlay');
                            if (overlay) overlay.remove();
                        }
                    }
                }
            });
        });
        
        observer.observe(sidebar, { attributes: true, attributeFilter: ['aria-expanded'] });
    }
});
</script>

<style>
/* Garante que o overlay não afeta desktop */
@media (min-width: 769px) {
    .sidebar-overlay {
        display: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

init_db()

st.title("🧵 Estoque Exonvais — Dashboard")

# KPIs simples (stub)
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.CRIADO,))
criadas = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.AGUARDANDO_CONF,))
aguard = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM orders WHERE status=?", (OrderStatus.EM_ESTOQUE,))
estoque = cur.fetchone()[0]

col1, col2, col3 = st.columns(3)
col1.metric("Pedidos Criados", criadas)
col2.metric("Aguardando Confecção", aguard)
col3.metric("Em Estoque", estoque)

st.info("Use o menu 'pages' à esquerda para navegar pelas fases.")
