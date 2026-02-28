"""
chat_manager.py — Gerenciador de conversas/chats externos.

Armazena conversas fora do workspace para não sobrecarregar o VS Code.
Padrão: E:/chats_conversas (ou variável de ambiente CHAT_HISTORY_PATH)

Estrutura:
  E:/chats_conversas/
    index.json              ← catálogo de conversas
    conversas/
      YYYYMMDD_HHMMSS__<nome>/
        chat.json           ← conversa completa
        metadata.json       ← metadados (tags, resumo, etc)

Uso:
  >>> manager = ChatManager()
  >>> manager.save_chat("meu-chat", [{"role": "user", "content": "..."}, ...])
  >>> chats = manager.list_chats()
  >>> chat = manager.load_chat(chat_id)
  >>> manager.update_chat(chat_id, new_messages)
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid


class ChatManager:
    """Gerenciador de conversas externas ao workspace."""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa gerenciador de chats.
        
        Args:
            base_path: caminho da pasta de chats. Se None, usa CHAT_HISTORY_PATH 
                      ou padrão E:/chats_conversas
        """
        if base_path is None:
            base_path = os.environ.get(
                "CHAT_HISTORY_PATH",
                "E:/chats_conversas"  # Padrão Windows
            )
        
        self.base_path = Path(base_path)
        self.conversas_dir = self.base_path / "conversas"
        self.index_file = self.base_path / "index.json"
        
        # Criar diretórios se não existirem
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.conversas_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar índice se não existir
        if not self.index_file.exists():
            self._init_index()
    
    def _init_index(self) -> None:
        """Cria arquivo de índice vazio."""
        index = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "chats": {}
        }
        self.index_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _load_index(self) -> Dict[str, Any]:
        """Carrega índice."""
        if not self.index_file.exists():
            self._init_index()
        return json.loads(self.index_file.read_text(encoding="utf-8"))
    
    def _save_index(self, index: Dict[str, Any]) -> None:
        """Salva índice."""
        self.index_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def save_chat(
        self,
        name: str,
        messages: List[Dict[str, str]],
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None
    ) -> str:
        """
        Salva nova conversa.
        
        Args:
            name: nome da conversa (ex: "iso-diffuser-help")
            messages: lista de mensagens {"role": "user|assistant", "content": "..."}
            tags: tags opcionais (ex: ["iso", "diffuser", "help"])
            summary: resumo opcional da conversa
            
        Returns:
            chat_id: ID único da conversa
            
        Exemplo:
            >>> messages = [
            ...     {"role": "user", "content": "Como calcular lambda_min?"},
            ...     {"role": "assistant", "content": "Lambda_min = c/f_min..."}
            ... ]
            >>> chat_id = manager.save_chat("lambda-help", messages, 
            ...                               tags=["iso", "wavelength"],
            ...                               summary="Pergunta sobre wavelength")
        """
        # Gerar ID e pasta
        chat_id = str(uuid.uuid4())[:8]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        folder_name = f"{ts}__{safe_name}"
        chat_folder = self.conversas_dir / folder_name
        chat_folder.mkdir(parents=True, exist_ok=True)
        
        # Salvar chat.json
        chat_data = {
            "chat_id": chat_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "messages": messages
        }
        chat_file = chat_folder / "chat.json"
        chat_file.write_text(
            json.dumps(chat_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Salvar metadata.json
        metadata = {
            "chat_id": chat_id,
            "name": name,
            "folder": str(chat_folder),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "tags": tags or [],
            "summary": summary or ""
        }
        metadata_file = chat_folder / "metadata.json"
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Atualizar índice
        index = self._load_index()
        index["chats"][chat_id] = metadata
        index["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
        self._save_index(index)
        
        print(f"✅ Chat salvo: {chat_id} ({name})")
        return chat_id
    
    def load_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Carrega conversa completa.
        
        Args:
            chat_id: ID da conversa
            
        Returns:
            Dicionário com chat.json ou None se não encontrado
        """
        index = self._load_index()
        
        if chat_id not in index["chats"]:
            print(f"❌ Chat não encontrado: {chat_id}")
            return None
        
        folder_str = index["chats"][chat_id].get("folder")
        if not folder_str:
            print(f"❌ Folder não registrada para chat {chat_id}")
            return None
        
        chat_file = Path(folder_str) / "chat.json"
        if not chat_file.exists():
            print(f"❌ Arquivo chat.json não encontrado: {chat_file}")
            return None
        
        return json.loads(chat_file.read_text(encoding="utf-8"))
    
    def list_chats(self, limit: int = 20, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lista chats, ordenados por data (mais recentes primeiro).
        
        Args:
            limit: número máximo de chats a retornar
            tags: filtrar por tags (ex: ["iso", "diffuser"])
            
        Returns:
            Lista de metadados dos chats
        """
        index = self._load_index()
        chats = list(index["chats"].values())
        
        # Ordenar por created_at (mais recentes primeiro)
        chats.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Filtrar por tags se especificadas
        if tags:
            chats = [
                c for c in chats 
                if any(tag in c.get("tags", []) for tag in tags)
            ]
        
        return chats[:limit]
    
    def find_chat(self, name_or_tag: str) -> Optional[Dict[str, Any]]:
        """
        Busca chat por nome ou tag.
        
        Args:
            name_or_tag: nome ou tag da conversa
            
        Returns:
            Primeiro chat encontrado ou None
        """
        index = self._load_index()
        
        for chat_id, metadata in index["chats"].items():
            if (metadata.get("name") == name_or_tag or 
                name_or_tag in metadata.get("tags", [])):
                return metadata
        
        return None
    
    def update_chat(self, chat_id: str, messages: List[Dict[str, str]]) -> bool:
        """
        Atualiza mensagens de uma conversa existente.
        
        Args:
            chat_id: ID da conversa
            messages: novas mensagens
            
        Returns:
            True se atualizado, False se chat não encontrado
        """
        index = self._load_index()
        
        if chat_id not in index["chats"]:
            print(f"❌ Chat não encontrado: {chat_id}")
            return False
        
        folder_str = index["chats"][chat_id].get("folder")
        chat_file = Path(folder_str) / "chat.json"
        
        # Carregar chat atual
        chat_data = json.loads(chat_file.read_text(encoding="utf-8"))
        
        # Atualizar mensagens
        chat_data["messages"] = messages
        chat_file.write_text(
            json.dumps(chat_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Atualizar metadata
        index["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
        index["chats"][chat_id]["message_count"] = len(messages)
        self._save_index(index)
        
        print(f"✅ Chat atualizado: {chat_id}")
        return True
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        Deleta conversa (arquivo e índice).
        
        Args:
            chat_id: ID da conversa
            
        Returns:
            True se deletado, False se não encontrado
        """
        import shutil
        
        index = self._load_index()
        
        if chat_id not in index["chats"]:
            print(f"❌ Chat não encontrado: {chat_id}")
            return False
        
        folder_str = index["chats"][chat_id].get("folder")
        chat_folder = Path(folder_str)
        
        # Deletar pasta
        if chat_folder.exists():
            shutil.rmtree(chat_folder)
        
        # Remover do índice
        del index["chats"][chat_id]
        self._save_index(index)
        
        print(f"✅ Chat deletado: {chat_id}")
        return True
    
    def export_summary(self, limit: int = 50) -> str:
        """
        Gera resumo em Markdown de todos os chats.
        
        Args:
            limit: número máximo de chats a incluir
            
        Returns:
            String Markdown com sumário
        """
        chats = self.list_chats(limit=limit)
        
        md = "# 📋 Resumo de Conversas\n\n"
        md += f"**Total:** {len(chats)} conversas\n"
        md += f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for chat in chats:
            md += f"## [{chat['name']}](file:///{chat['folder']}/chat.json)\n"
            md += f"- **ID:** `{chat['chat_id']}`\n"
            md += f"- **Data:** {chat['created_at']}\n"
            md += f"- **Mensagens:** {chat['message_count']}\n"
            if chat.get("tags"):
                md += f"- **Tags:** {', '.join(f'`{tag}`' for tag in chat['tags'])}\n"
            if chat.get("summary"):
                md += f"- **Resumo:** {chat['summary']}\n"
            md += "\n"
        
        return md
    
    def get_chat_path(self, chat_id: str) -> Optional[Path]:
        """
        Retorna caminho da pasta de uma conversa.
        
        Útil para acessar arquivos associados.
        """
        index = self._load_index()
        if chat_id in index["chats"]:
            return Path(index["chats"][chat_id]["folder"])
        return None


# Instância global (opcional, para uso rápido)
_default_manager = None

def get_default_manager() -> ChatManager:
    """Retorna instância padrão do ChatManager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ChatManager()
    return _default_manager


# Atalhos de conveniência
def save_chat(name: str, messages: List[Dict[str, str]], tags: Optional[List[str]] = None, summary: Optional[str] = None) -> str:
    """Salva chat usando instância padrão."""
    return get_default_manager().save_chat(name, messages, tags, summary)

def load_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    """Carrega chat usando instância padrão."""
    return get_default_manager().load_chat(chat_id)

def list_chats(limit: int = 20, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Lista chats usando instância padrão."""
    return get_default_manager().list_chats(limit, tags)

def find_chat(name_or_tag: str) -> Optional[Dict[str, Any]]:
    """Busca chat usando instância padrão."""
    return get_default_manager().find_chat(name_or_tag)
