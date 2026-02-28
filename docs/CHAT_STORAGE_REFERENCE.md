"""
CHAT STORAGE QUICK REFERENCE
============================

Módulo: utils/chat_manager.py
Pasta de armazenamento: E:/chats_conversas (configurável via CHAT_HISTORY_PATH)

ESTRUTURA DE ARMAZENAMENTO
==========================

E:/chats_conversas/
├── index.json              ← catálogo de todas as conversas
└── conversas/
    ├── 20260119_143022__iso-diffuser-help/
    │   ├── chat.json      ← conversa completa (mensagens)
    │   └── metadata.json  ← metadados (tags, resumo, etc)
    └── 20260119_150500__wavelength-calculation/
        ├── chat.json
        └── metadata.json

EXEMPLO DE USO
==============

1. SALVAR NOVA CONVERSA
-----------------------

from utils.chat_manager import ChatManager

manager = ChatManager()

# Salvar com todas as informações
chat_id = manager.save_chat(
    name="iso-diffuser-wavelength",
    messages=[
        {"role": "user", "content": "Como calcular lambda_min para diffusores?"},
        {"role": "assistant", "content": "Lambda_min = 343 / f_min..."},
        {"role": "user", "content": "E para ISO 17497-2?"},
        {"role": "assistant", "content": "ISO 17497-2 é para low frequencies..."}
    ],
    tags=["iso", "diffuser", "wavelength", "iso17497"],
    summary="Discussão sobre cálculo de wavelength mínima para diffusores QRD"
)

print(f"Chat salvo com ID: {chat_id}")


2. CARREGAR CONVERSA EXISTENTE
-------------------------------

# Carregar pelo ID
chat = manager.load_chat("a1b2c3d4")
print(f"Conversa '{chat['name']}' com {len(chat['messages'])} mensagens")

# Listar últimas 10 conversas
recent = manager.list_chats(limit=10)
for c in recent:
    print(f"- {c['name']} ({c['created_at']})")

# Buscar por nome ou tag
chat = manager.find_chat("iso-diffuser")
if chat:
    print(f"Encontrado: {chat['name']}")


3. ATUALIZAR CONVERSA
---------------------

# Adicionar novas mensagens
new_messages = [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]
manager.update_chat(chat_id, new_messages)


4. BUSCAR CONVERSAS POR TAG
---------------------------

# Listar todas as conversas sobre "iso"
iso_chats = manager.list_chats(limit=50, tags=["iso"])

for chat in iso_chats:
    print(f"- {chat['name']}: {chat.get('summary', 'N/A')}")


5. ATALHOS RÁPIDOS
------------------

# Usar funções simplificadas (sem precisar criar manager)
from utils.chat_manager import save_chat, load_chat, list_chats, find_chat

# Salvar
chat_id = save_chat(
    "my-chat",
    [{"role": "user", "content": "..."}],
    tags=["test"]
)

# Carregar
chat = load_chat(chat_id)

# Listar
chats = list_chats(limit=20)

# Buscar
chat = find_chat("my-chat")


ESTRUTURA DO ARQUIVO index.json
================================

{
  "version": "1.0",
  "created_at": "2026-01-19T14:30:00.000000",
  "chats": {
    "a1b2c3d4": {
      "chat_id": "a1b2c3d4",
      "name": "iso-diffuser-help",
      "folder": "E:/chats_conversas/conversas/20260119_143022__iso-diffuser-help",
      "created_at": "2026-01-19T14:30:22.123456",
      "updated_at": "2026-01-19T15:45:30.654321",
      "message_count": 8,
      "tags": ["iso", "diffuser", "wavelength"],
      "summary": "Discussão sobre cálculo de wavelength para diffusores QRD"
    }
  }
}


ESTRUTURA DO ARQUIVO chat.json
================================

{
  "chat_id": "a1b2c3d4",
  "name": "iso-diffuser-help",
  "created_at": "2026-01-19T14:30:22.123456",
  "messages": [
    {
      "role": "user",
      "content": "Como calcular lambda_min para diffusores?"
    },
    {
      "role": "assistant",
      "content": "Lambda_min = 343 / f_min, onde..."
    }
  ]
}


CONFIGURAR PASTA PERSONALIZADA
===============================

# Opção 1: Variável de ambiente
set CHAT_HISTORY_PATH=C:\Users\WIN7\chats_conversas

# Opção 2: No código
from utils.chat_manager import ChatManager
manager = ChatManager(base_path="C:/usuarios/meus_chats")


INTEGRAÇÃO COM PROJETO
======================

Para usar no seu acquisition agent ou em qualquer módulo:

from utils.chat_manager import save_chat, load_chat

# Exemplo: Salvar histórico de wizard
def finish_wizard(wizard_state, results):
    messages = [
        {"role": "system", "content": json.dumps(wizard_state)},
        {"role": "assistant", "content": json.dumps(results)}
    ]
    
    chat_id = save_chat(
        name=f"wizard-{results['measurement_type']}",
        messages=messages,
        tags=["wizard", results['measurement_type']],
        summary=f"Wizard completo de {results['measurement_type']}"
    )


BENEFÍCIOS
==========

✅ Workspace limpo - nenhum arquivo de chat pesa no VS Code
✅ Histórico completo - todas as conversas catalogadas
✅ Pesquisável - tags e nomes para encontrar rápido
✅ Portável - pasta externa, fácil de backup/compartilhar
✅ Acessível - você pode referenciar qualquer conversa
✅ Estruturado - JSON bem organizado para processar depois

"""

# Fim do arquivo de referência
