from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .settings import settings


@dataclass(frozen=True)
class AlpacaOrderResult:
    alpaca_order_id: str
    status: str
    submitted_at: Any | None


def trading_client() -> TradingClient:
    if not settings.alpaca_key or not settings.alpaca_secret:
        raise RuntimeError("Alpaca credentials not set (ALPACA_KEY/ALPACA_SECRET).")
    # alpaca-py expects the base host; we normalize "/v2" away in settings.
    return TradingClient(settings.alpaca_key, settings.alpaca_secret, paper="paper" in settings.alpaca_base_url)


def submit_market_order(
    *,
    symbol: str,
    side: str,
    client_order_id: str,
    qty: float | None,
    notional: float | None,
) -> dict[str, Any]:
    client = trading_client()
    order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

    req = MarketOrderRequest(
        symbol=symbol,
        side=order_side,
        time_in_force=TimeInForce.DAY,
        client_order_id=client_order_id,
        qty=qty,
        notional=notional,
    )
    order = client.submit_order(order_data=req)
    # Return a plain dict so we can JSON-store it easily
    return {
        "id": str(order.id),
        "status": str(order.status),
        "submitted_at": getattr(order, "submitted_at", None),
        "filled_at": getattr(order, "filled_at", None),
        "filled_avg_price": getattr(order, "filled_avg_price", None),
        "filled_qty": getattr(order, "filled_qty", None),
        "client_order_id": getattr(order, "client_order_id", None),
        "symbol": getattr(order, "symbol", None),
        "side": getattr(order, "side", None),
    }

