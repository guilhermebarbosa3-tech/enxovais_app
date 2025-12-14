# TODO: gerar PDF/arquivo de pedido para fornecedor
# Recebe pedido + fotos e cria um PDF. Retorna caminho.
import os
from datetime import datetime
from core.db import from_json

def export_order_pdf(order_row) -> str:
    """Gera um arquivo texto/sumário do pedido para enviar ao fornecedor.
    Retorna o caminho do arquivo gerado."""
    
    exports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports"))
    os.makedirs(exports_dir, exist_ok=True)
    
    # Gerar nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pedido_{order_row['id']}_{timestamp}.txt"
    filepath = os.path.join(exports_dir, filename)
    
    # Montar conteúdo
    notes_struct = from_json(order_row['notes_struct'], {})
    content = f"""
╔════════════════════════════════════════════════════════════╗
║                    PEDIDO #{order_row['id']}                   ║
╚════════════════════════════════════════════════════════════╝

Data: {order_row['created_at']}
Status: {order_row['status']}
Cliente: {order_row['client_name']}

─────────────────────────────────────────────────────────────
PRODUTO
─────────────────────────────────────────────────────────────
Categoria: {order_row['category']}
Tipo: {order_row['type']}
Produto: {order_row['product']}

─────────────────────────────────────────────────────────────
PREÇOS
─────────────────────────────────────────────────────────────
Custo: R$ {order_row['price_cost']:.2f}
Venda: R$ {order_row['price_sale']:.2f}
Margem: R$ {(order_row['price_sale'] - order_row['price_cost']):.2f}

─────────────────────────────────────────────────────────────
ESPECIFICAÇÕES
─────────────────────────────────────────────────────────────
{str(notes_struct).replace(', ', chr(10))}

─────────────────────────────────────────────────────────────
OBSERVAÇÕES
─────────────────────────────────────────────────────────────
{order_row['notes_free']}

════════════════════════════════════════════════════════════
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

