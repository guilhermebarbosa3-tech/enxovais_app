# Registro de Memória e Instruções: Sistema de Chats Externos

**Data de Criação:** 19 de Janeiro de 2026
**Contexto:** Otimização de performance do VS Code e preservação de memória de longo prazo.

---

## 🤖 Para o Agente (Instruções de Auto-Atendimento)

Quando o usuário pedir para **"ler uma conversa antiga"**, **"lembrar do que decidimos"** ou **"consultar o histórico"**, siga este protocolo:

1. **Onde buscar:**
   - O histórico **NÃO** está mais no VS Code (History).
   - O histórico está salvo externamente em: `E:/chats_conversas`.
   - Use o módulo: `utils.chat_manager`.

2. **Como buscar:**
   - Use a função `find_chat(termo)` para buscar por título ou tag.
   - Use `list_chats(tags=['tag'])` para listar assuntos relacionados.
   - Use `load_chat(id)` para ler o conteúdo integral.

   > **Exemplo de pensamento:**
   > *Usuário: "O que decidimos sobre o toolkit membrana?"*
   > *Ação: Executar script python que chama `list_chats` procurando "membrana" no nome ou tags.*

3. **Como atualizar/salvar novos contextos (Conversa Atual):**
   - **Automático:** Execute `python -m utils.update_current_chat` no terminal.
     - Este script busca a sessão ativa no banco de dados interno do VS Code e salva/atualiza no diretório externo.
     - *Nota:* Se a conversa for muito recente, pode ser necessário fechar a aba do chat ou dar um "Reload Window" para que o VS Code grave os dados no disco antes da extração.
   - **Manual (Fallback):** Se o script não encontrar a sessão, use `save_chat()` diretamente via Python com as mensagens textuais, conforme exemplo no `main.py` ou scripts de `scripts/`.
   - **Tagging:** Sempre use tags consistentes (ex: `migration`, `membrana`) para manter a rastreabilidade.

---

## 👤 Para o Usuário (Como funciona)

Este documento serve para lembrarmos como resolvemos o problema de lentidão do VS Code causada pelo excesso de logs de chat.

### O que foi feito?
1. **Extração Cirúrgica:** Acessamos o banco de dados interno oculto do VS Code.
2. **Migração:** Copiamos 34 conversas antigas (incluindo as cruciais sobre "Membrana", "MAM", "Prompt Unificado").
3. **Armazenamento Seguro:** Tudo agora vive em `E:/chats_conversas`, fora da pasta do projeto (para não pesar) e fora do VS Code.

### Como as conversas são atualizadas?
Não "editamos" os arquivos antigos (para não perder o histórico original). O fluxo de atualização é "aditivo":

1. **Você conversa normalmente** comigo aqui.
2. **Ao final**, se a conversa for importante, você pede:
   > *"Salve essa conversa com a tag [ASSUNTO]"*
3. Eu salvo um novo arquivo lá na pasta externa.
4. **No futuro**, quando puxarmos pelo assunto, virão **todos** os arquivos (os de 2025 e os novos de 2026), formando uma memória contínua.

### Estrutura dos Dados (Para referência técnica)
- **Pasta:** `E:/chats_conversas`
- **Índice:** `index.json` (Catálogo rápido)
- **Conversas:** Pastas individuais com `chat.json` (conteúdo) e `metadata.json` (tags).

### Comandos Úteis (Python)
Se precisar gerenciar manualmente:
```python
from utils.chat_manager import list_chats, load_chat

# Ver o que temos sobre Membrana
chats = list_chats(tags=["membrana"])
```

---
**Status:** ✅ Sistema ativo e operante. O histórico do VS Code pode ser limpo com segurança.
