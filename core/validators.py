from typing import Dict

def validate_prices(cost: float, sale: float) -> None:
    assert cost is not None and sale is not None, "Preços obrigatórios"
    assert cost >= 0 and sale >= 0, "Preços inválidos"
