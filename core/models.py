from dataclasses import dataclass
from typing import Optional

class OrderStatus:
    CRIADO = "CRIADO"
    ENVIADO_FORNECEDOR = "ENVIADO_FORNECEDOR"
    AGUARDANDO_CONF = "AGUARDANDO_CONF"
    RECEBIDO_CONF = "RECEBIDO_CONF"
    RECEBIDO_NC = "RECEBIDO_NC"
    EM_ESTOQUE = "EM_ESTOQUE"
    ENTREGUE = "ENTREGUE"
    FINALIZADO_FIN = "FINALIZADO_FIN"
    # Novos status para módulo de vendas
    DISPONIVEL_VENDA = "DISPONIVEL_VENDA"  # Produto no estoque para venda direta
    VENDIDO = "VENDIDO"                     # Produto vendido no caixa

@dataclass
class Client:
    id: Optional[int]
    name: str
    address: str
    cpf: str
    phone: str
    status: str  # ADIMPLENTE | INADIMPLENTE
