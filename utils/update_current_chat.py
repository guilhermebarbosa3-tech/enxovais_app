import os
import json
import logging
import sqlite3
import datetime
from pathlib import Path
from utils.chat_manager import ChatManager

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_vscode_workspace_path(target_folder_name="acustica_app"):
    """Encontra o diretório de armazenamento do workspace atual."""
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return None
        
    workspace_storage = os.path.join(appdata, 'Code', 'User', 'workspaceStorage')
    
    if not os.path.exists(workspace_storage):
        logging.error(f"Workspace storage not found at {workspace_storage}")
        return None

    # Ordenar por data de modificação para priorizar ativos recentemente
    folders = sorted(
        [os.path.join(workspace_storage, d) for d in os.listdir(workspace_storage)], 
        key=os.path.getmtime, 
        reverse=True
    )

    for fpath in folders:
        wfile = os.path.join(fpath, 'workspace.json')
        if os.path.exists(wfile):
            try:
                with open(wfile, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    if target_folder_name.lower() in content:
                        logging.info(f"Workspace encontrado: {fpath}")
                        return fpath
            except:
                continue
    return None

def extract_chat_messages(json_path):
    """Lê o arquivo JSON de sessão do VS Code e extrai mensagens."""
    if not os.path.exists(json_path):
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Erro ao ler JSON {json_path}: {e}")
        return []

    requests = data.get('requests', [])
    messages = []
    
    for req in requests:
        # User Message
        user_msg = req.get('message', {}).get('text')
        if user_msg:
            messages.append({
                "role": "user",
                "content": user_msg
            })
            
        # Asisstant Response
        # A resposta pode ser uma lista de partes (markdown, code, etc)
        response_parts = req.get('response', [])
        assistant_text = ""
        
        if response_parts:
            for part in response_parts:
                value = part.get('value')
                # Às vezes value pode ser um objeto complexo, mas geralmente é string markdown
                if isinstance(value, str):
                    assistant_text += value
                elif hasattr(value, '__str__'):
                    assistant_text += str(value)
        
        if assistant_text:
            messages.append({
                "role": "assistant",
                "content": assistant_text
            })
            
    return messages

def main():
    print("=== Atualizador de Contexto do Chat ===")
    
    ws_path = get_vscode_workspace_path("acustica_app")
    if not ws_path:
        print("ERRO: Não foi possível encontrar a pasta de storage deste workspace.")
        return

    chat_sessions_dir = os.path.join(ws_path, "chatSessions")
    if not os.path.exists(chat_sessions_dir):
        print(f"ERRO: Pasta chatSessions não encontrada em {ws_path}")
        return
        
    # Encontrar o arquivo JSON mais recente
    json_files = [
        os.path.join(chat_sessions_dir, f) 
        for f in os.listdir(chat_sessions_dir) 
        if f.endswith('.json')
    ]
    
    if not json_files:
        print("Nenhuma sessão de chat encontrada.")
        return
        
    latest_file = max(json_files, key=os.path.getmtime)
    print(f"Sessão mais recente: {os.path.basename(latest_file)}")
    print(f"Data modificação: {datetime.datetime.fromtimestamp(os.path.getmtime(latest_file))}")
    
    messages = extract_chat_messages(latest_file)
    print(f"Mensagens extraídas: {len(messages)}")
    
    if not messages:
        print("Nenhuma mensagem extraída. Abortando.")
        return

    # 1. Salvar no Banco de Chats (E:/chats_conversas)
    try:
        manager = ChatManager()
        # Usar um ID fixo ou rotativo? O usuário disse "Atualize essa conversa".
        # Vamos salvar como "Current_Active_Session" e sempre sobrescrever ou versionar.
        # Melhor: criar um novo com timestamp para histórico seguro.
        
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        title = f"Resgate_de_Sessao_{timestamp_str}"
        tags = ["auto-recovery", "active-session", "full-dump"]
        
        saved_path = manager.save_chat(
            name=title,
            messages=messages,
            tags=tags
        )
        print(f"Chat salvo no banco externo: {saved_path}")
    except Exception as e:
        print(f"Erro ao salvar no ChatManager: {e}")
        # Mesmo se falhar o manager, tentamos salvar o arquivo local

    # 2. Atualizar 'Relembrar o coilot do contexto.txt'
    # O usuário pediu especificamente "não quero que guarde um resumo".
    # Então vamos salvar o texto COMPLETO.
    
    output_file = "Relembrar o coilot do contexto.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"=== CONTEXTO RECUPERADO EM {datetime.datetime.now()} ===\n\n")
            for msg in messages:
                role = msg['role'].upper()
                content = msg['content']
                f.write(f"--------------------------------------------------\n")
                f.write(f"[{role}]\n")
                f.write(f"--------------------------------------------------\n")
                f.write(content + "\n\n")
        
        print(f"Arquivo '{output_file}' atualizado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao gravar arquivo de texto: {e}")

if __name__ == "__main__":
    main()
