"""
Cotação do BTC em tempo real via API pública da Binance.
Não requer chave de API.
"""

import requests
from datetime import datetime


BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
SYMBOL = "BTCUSDT"


def obter_cotacao_btc() -> dict:
    """Busca os dados de cotação do BTC/USDT nas últimas 24h."""
    params = {"symbol": SYMBOL}
    response = requests.get(BINANCE_TICKER_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def formatar_cotacao(dados: dict) -> None:
    """Exibe as informações de cotação formatadas no console."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    preco_atual   = float(dados["lastPrice"])
    abertura      = float(dados["openPrice"])
    maxima        = float(dados["highPrice"])
    minima        = float(dados["lowPrice"])
    variacao_pct  = float(dados["priceChangePercent"])
    volume_btc    = float(dados["volume"])
    volume_usdt   = float(dados["quoteVolume"])

    sinal = "+" if variacao_pct >= 0 else ""

    print("=" * 48)
    print(f"  Cotação BTC/USDT  —  {agora}")
    print("=" * 48)
    print(f"  Preço atual : $ {preco_atual:>14,.2f}")
    print(f"  Abertura    : $ {abertura:>14,.2f}")
    print(f"  Máxima 24h  : $ {maxima:>14,.2f}")
    print(f"  Mínima 24h  : $ {minima:>14,.2f}")
    print(f"  Variação 24h: {sinal}{variacao_pct:.2f} %")
    print(f"  Volume BTC  :   {volume_btc:>14,.4f} BTC")
    print(f"  Volume USDT : $ {volume_usdt:>14,.2f}")
    print("=" * 48)


if __name__ == "__main__":
    try:
        dados = obter_cotacao_btc()
        formatar_cotacao(dados)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API: {e}")
