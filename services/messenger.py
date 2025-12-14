# Integração com WhatsApp (URL-deeplink)
import urllib.parse
from core.db import from_json

def generate_whatsapp_message(order_row) -> str:
    """Gera mensagem formatada com detalhes do pedido para WhatsApp."""
    notes_struct = from_json(order_row['notes_struct'], {})
    specs = "\n".join([f"• {k}: {v}" for k, v in notes_struct.items()])
    
    message = f"""
🧵 *NOVO PEDIDO #{order_row['id']}*

*Cliente:* {order_row['client_name']}
*Categoria:* {order_row['category']}
*Tipo:* {order_row['type']}
*Produto:* {order_row['product']}

*Especificações:*
{specs}

*Preços:*
• Custo: R$ {order_row['price_cost']:.2f}
• Venda: R$ {order_row['price_sale']:.2f}

*Observações:*
{order_row['notes_free']}

Acesse o sistema para mais detalhes.
"""
    return message.strip()


def get_whatsapp_link(phone: str, message: str) -> str:
    """Retorna link WhatsApp com mensagem codificada.
    phone: número com código de país (ex: 5511999999999)
    """
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_msg}"


def share_via_whatsapp(phone: str, message: str) -> str:
    """Retorna URL para compartilhar via WhatsApp."""
    return get_whatsapp_link(phone, message)

