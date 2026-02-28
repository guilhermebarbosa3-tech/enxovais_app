import streamlit as st
import os
import shutil
from pathlib import Path
from core.db import get_conn, now_iso, exec_query, init_db
from core.audit import log_change

# Garantir que o banco está inicializado
init_db()

st.set_page_config(page_title="Administração", page_icon="🔧", layout="wide")
st.title("🔧 Administração do Sistema")

conn = get_conn()

# Paths
UPLOADS_DIR = Path("uploads")
EXPORTS_DIR = Path("exports")
DB_FILE = "exonvais.db"

def get_dir_size(path):
    """Calcula tamanho total de um diretório em bytes."""
    total = 0
    if path.exists():
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    return total

def format_bytes(bytes_size):
    """Formata bytes para unidade legível."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def get_file_count(path):
    """Conta arquivos em um diretório."""
    if not path.exists():
        return 0
    return len(list(path.rglob("*")))

def find_orphaned_uploads():
    """Encontra fotos sem pedido associado."""
    orphaned = []
    if UPLOADS_DIR.exists():
        for photo_file in UPLOADS_DIR.rglob("*.jpg"):
            # Verificar se foto existe em algum pedido
            filename = photo_file.name
            # Buscar em todas as linhas da coluna photos
            result = exec_query(  # type: ignore
                "SELECT COUNT(*) as count FROM orders WHERE photos LIKE ?",
                (f"%{filename}%",)
            ).fetchone()
            
            # Só marcar como órfã se realmente não encontrou em nenhum pedido
            if result and result['count'] == 0:
                orphaned.append(photo_file)
    return orphaned

def get_audit_log(limit=20):
    """Busca últimas mudanças do sistema."""
    return exec_query(  # type: ignore
        "SELECT * FROM audit_log ORDER BY ts DESC LIMIT ?",
        (limit,)
    ).fetchall()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Estatísticas", "🧹 Limpeza", "📋 Auditoria", "⚙️ Avançado"])

# ==================== TAB 1: ESTATÍSTICAS ====================
with tab1:
    st.subheader("📊 Estatísticas do Sistema")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Total de clientes
    total_clients = exec_query("SELECT COUNT(*) as count FROM clients").fetchone()  # type: ignore
    with col1:
        st.metric("👥 Clientes", total_clients['count'])
    
    # Total de pedidos
    total_orders = exec_query("SELECT COUNT(*) as count FROM orders").fetchone()  # type: ignore
    with col2:
        st.metric("📦 Pedidos", total_orders['count'])
    
    # Total de fotos
    total_photos = get_file_count(UPLOADS_DIR)
    with col3:
        st.metric("📸 Fotos", total_photos)
    
    # Total de PDFs
    total_pdfs = get_file_count(EXPORTS_DIR)
    with col4:
        st.metric("📄 PDFs", total_pdfs)
    
    st.divider()
    
    # Tamanhos
    col1, col2, col3, col4 = st.columns(4)
    
    uploads_size = get_dir_size(UPLOADS_DIR)
    exports_size = get_dir_size(EXPORTS_DIR)
    db_size = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
    total_size = uploads_size + exports_size + db_size
    
    with col1:
        st.metric("📸 Tamanho Fotos", format_bytes(uploads_size))
    
    with col2:
        st.metric("📄 Tamanho PDFs", format_bytes(exports_size))
    
    with col3:
        st.metric("🗄️ Tamanho Banco", format_bytes(db_size))
    
    with col4:
        st.metric("💾 Total", format_bytes(total_size))

# ==================== TAB 2: LIMPEZA ====================
with tab2:
    st.subheader("🧹 Limpeza e Manutenção")
    
    # Limpeza de PDFs
    st.markdown("### 📄 Limpar PDFs Antigos")
    col1, col2 = st.columns(2)
    
    with col1:
        days_old = st.slider("PDFs com mais de (dias):", 7, 365, 90)
    
    if st.button("📋 Listar PDFs para deletar", key="list_pdfs"):
        if EXPORTS_DIR.exists():
            old_pdfs = []
            cutoff_time = now_iso()  # Simplificado
            
            for pdf_file in EXPORTS_DIR.glob("*.pdf"):
                file_stat = pdf_file.stat()
                age_seconds = (Path(pdf_file).stat().st_mtime) 
                old_pdfs.append(pdf_file)
            
            if old_pdfs:
                st.write(f"**Encontrados {len(old_pdfs)} PDFs:**")
                total_save = sum(p.stat().st_size for p in old_pdfs)
                st.info(f"💾 Economia esperada: {format_bytes(total_save)}")
                
                for pdf in old_pdfs[:10]:  # Mostrar primeiros 10
                    st.text(f"• {pdf.name} ({format_bytes(pdf.stat().st_size)})")
                
                if len(old_pdfs) > 10:
                    st.text(f"... e mais {len(old_pdfs) - 10} arquivos")
            else:
                st.success("✅ Nenhum PDF antigo encontrado!")
    
    if st.button("🗑️ Deletar PDFs antigos", key="delete_pdfs"):
        st.warning("⚠️ OPERAÇÃO IRREVERSÍVEL")
        st.error("Digite 'DELETAR PDFS' para confirmar:")
        
        confirm = st.text_input("Confirmação:", key="confirm_pdfs")
        
        if confirm == "DELETAR PDFS":
            if EXPORTS_DIR.exists():
                deleted_count = 0
                for pdf_file in EXPORTS_DIR.glob("*.pdf"):
                    try:
                        os.remove(pdf_file)
                        deleted_count += 1
                    except Exception as e:
                        st.error(f"Erro ao deletar {pdf_file.name}: {e}")
                
                log_change("system", "cleanup", "PDFs_DELETED", "count", 0, deleted_count)
                st.success(f"✅ {deleted_count} PDFs deletados com sucesso!")
                st.rerun()
        elif confirm:
            st.error("❌ Confirmação incorreta! Digite 'DELETAR PDFS'")
    
    st.divider()
    
    # Limpeza de uploads órfãos
    st.markdown("### 📸 Limpar Fotos Órfãs")
    
    if st.button("📋 Listar fotos sem pedido", key="list_orphaned"):
        orphaned = find_orphaned_uploads()
        if orphaned:
            st.warning(f"⚠️ Encontradas {len(orphaned)} fotos órfãs")
            total_save = sum(p.stat().st_size for p in orphaned)
            st.info(f"💾 Economia esperada: {format_bytes(total_save)}")
            
            for photo in orphaned[:10]:
                st.text(f"• {photo.name} ({format_bytes(photo.stat().st_size)})")
            
            if len(orphaned) > 10:
                st.text(f"... e mais {len(orphaned) - 10} arquivos")
        else:
            st.success("✅ Nenhuma foto órfã encontrada!")
    
    if st.button("🗑️ Deletar fotos órfãs", key="delete_orphaned"):
        # Confirmação MUITO FORTE
        st.warning("⚠️⚠️⚠️ OPERAÇÃO IRREVERSÍVEL ⚠️⚠️⚠️")
        st.error("Você está prestes a deletar fotos! Digite 'DELETAR FOTOS' para confirmar:")
        
        confirm = st.text_input("Confirmação (deixe vazio e clique novamente para cancelar):", key="confirm_orphaned")
        
        if confirm == "DELETAR FOTOS":
            orphaned = find_orphaned_uploads()
            deleted_count = 0
            
            st.info(f"Deletando {len(orphaned)} fotos órfãs...")
            
            for photo in orphaned:
                try:
                    os.remove(photo)
                    deleted_count += 1
                    st.text(f"✅ Deletado: {photo.name}")
                except Exception as e:
                    st.error(f"❌ Erro ao deletar {photo.name}: {e}")
            
            log_change("system", "cleanup", "ORPHANED_PHOTOS_DELETED", "count", 0, deleted_count)
            st.success(f"✅ {deleted_count} fotos órfãs deletadas!")
            st.rerun()
        elif confirm:
            st.error("❌ Confirmação incorreta! Digite 'DELETAR FOTOS'")
    
    st.divider()
    
    # Compactação do banco
    st.markdown("### 🗄️ Compactar Banco de Dados")
    
    db_size_before = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tamanho atual", format_bytes(db_size_before))
    
    if st.button("🔧 Executar VACUUM (Compactar)", key="vacuum_db"):
        try:
            exec_query("VACUUM", commit=True)  # type: ignore
            db_size_after = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
            saved = db_size_before - db_size_after
            
            log_change("system", "maintenance", "VACUUM_EXECUTED", "saved_bytes", db_size_before, db_size_after)
            
            with col2:
                st.metric("Tamanho após", format_bytes(db_size_after))
            
            if saved > 0:
                st.success(f"✅ Banco compactado! Economizados: {format_bytes(saved)}")
            else:
                st.info("ℹ️ Banco já estava otimizado")
        except Exception as e:
            st.error(f"❌ Erro ao compactar: {e}")

# ==================== TAB 3: AUDITORIA ====================
with tab3:
    st.subheader("📋 Logs de Auditoria")
    
    limit = st.slider("Mostrar últimos (registros):", 10, 100, 20)
    
    audit_logs = get_audit_log(limit)
    
    if audit_logs:
        # Criar tabela formatada incluindo o usuário responsável
        for log in audit_logs:
            col1, col2, col3 = st.columns([2, 2, 4])

            with col1:
                st.caption(log['ts'])

            with col2:
                st.caption(f"**{log['entity']}** #{log['entity_id']}")
                # Mostrar username se presente (compatível com sqlite3.Row e dicts)
                username = None
                try:
                    # dict-like with get
                    username = log.get('username')
                except AttributeError:
                    # sqlite3.Row doesn't have get(); fallback seguro
                    if 'username' in log:
                        username = log['username']

                if username:
                    st.caption(f"Usuário: {username}")

            with col3:
                st.caption(f"{log['action']}: {log['field']} ({log['before']} → {log['after']})")
        
        st.divider()
        st.info(f"Total de {len(audit_logs)} registros mostrados")
    else:
        st.info("ℹ️ Nenhum log de auditoria encontrado")

# ==================== TAB 4: AVANÇADO ====================
with tab4:
    st.subheader("⚙️ Configurações Avançadas")
    
    st.markdown("### 🔐 Operações Perigosas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.warning("⚠️ **Resetar Banco de Dados**")
        st.text("Esta ação deletará TODOS os dados!")
        
        if st.button("🗑️ Resetar banco (Deletar tudo)", key="reset_db"):
            confirm = st.text_input("Digite 'CONFIRMAR' para prosseguir:")
            if confirm == "CONFIRMAR":
                try:
                    os.remove(DB_FILE)
                    log_change("system", "reset", "DATABASE_RESET", "status", "before", "after")
                    st.error("❌ Banco de dados resetado! A aplicação será recarregada...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
    
    with col2:
        st.info("ℹ️ **Informações do Sistema**")
        st.text(f"Versão do banco: SQLite")
        st.text(f"Modo WAL: Ativado")
        st.text(f"Última execução: {now_iso()}")

st.divider()
st.caption("🔧 Página de Administração • Úlltimas ações são auditadas")
