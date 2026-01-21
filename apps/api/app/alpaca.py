from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import re
from typing import Any
from datetime import date, datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

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

def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    # Fallback to string for SDK types
    return str(v)


def _extract_error_dict_from_exception(exc: Exception) -> dict[str, Any] | None:
    """
    Best-effort extraction of Alpaca API error payloads.

    alpaca-py exceptions often include a JSON/dict-like blob in their string
    representation; we extract it so we can display a user-friendly message.
    """
    # Some exceptions expose a structured payload directly.
    for attr in ("error", "payload", "body", "data"):
        v = getattr(exc, attr, None)
        if isinstance(v, dict):
            return v  # type: ignore[return-value]

    text = str(exc) or ""
    # Try to grab the last {...} block (most likely the API error body).
    m = re.search(r"(\{[\s\S]*\})", text)
    if not m:
        return None

    blob = m.group(1).strip()
    # First try strict JSON.
    try:
        parsed = json.loads(blob)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception:
        pass

    # Fallback: Python dict literal (single quotes, etc).
    try:
        parsed = ast.literal_eval(blob)
        if isinstance(parsed, dict):
            return parsed  # type: ignore[return-value]
        return None
    except Exception:
        return None


def _fmt_2(v: Any) -> str:
    """
    Best-effort formatting for quantities/prices to 2 decimals.
    Accepts strings or numbers; returns original string if not parseable.
    """
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return f"{float(v):.2f}"
    if isinstance(v, str):
        try:
            return f"{float(v):.2f}"
        except Exception:
            return v
    return str(v)


def format_alpaca_error_dict(
    err: dict[str, Any],
    *,
    symbol: str | None = None,
    side: str | None = None,
    qty: float | None = None,
    notional: float | None = None,
) -> str:
    code = err.get("code")
    msg = err.get("message") or "order rejected"
    err_symbol = err.get("symbol") or symbol

    bits: list[str] = []
    if side:
        bits.append(str(side).upper())
    if err_symbol:
        bits.append(str(err_symbol))
    prefix = " ".join(bits).strip()
    prefix = (prefix + ": ") if prefix else ""

    requested = err.get("requested")
    available = err.get("available")
    existing_qty = err.get("existing_qty")
    held_for_orders = err.get("held_for_orders")

    requested_fallback: Any | None = None
    if qty is not None:
        requested_fallback = _fmt_2(qty)
    elif notional is not None:
        requested_fallback = f"${float(notional):.2f}"

    details: list[str] = []
    if requested is not None or requested_fallback is not None:
        details.append(f"requested {_fmt_2(requested) if requested is not None else requested_fallback}")
    if available is not None:
        details.append(f"available {_fmt_2(available)}")
    if existing_qty is not None:
        details.append(f"held {_fmt_2(existing_qty)}")
    if held_for_orders is not None:
        details.append(f"held_for_orders {_fmt_2(held_for_orders)}")
    if code is not None:
        details.append(f"code {code}")

    suffix = f" ({', '.join(details)})" if details else ""
    return f"{prefix}{msg}{suffix}"


def format_alpaca_error_message(
    error_message: str | None,
    *,
    symbol: str | None = None,
    side: str | None = None,
) -> str | None:
    """
    If error_message contains a JSON/dict error payload, return a concise formatted message.
    Otherwise return it unchanged.
    """
    if not error_message:
        return error_message

    text = error_message.strip()
    # Fast path: looks like JSON/dict
    if not (text.startswith("{") and text.endswith("}")):
        return error_message
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return format_alpaca_error_dict(parsed, symbol=symbol, side=side)
    except Exception:
        pass
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return format_alpaca_error_dict(parsed, symbol=symbol, side=side)
    except Exception:
        pass
    return error_message


def format_alpaca_error(
    exc: Exception,
    *,
    symbol: str | None = None,
    side: str | None = None,
    qty: float | None = None,
    notional: float | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """
    Returns a concise, user-facing message + the raw parsed error dict (if found).
    """
    err = _extract_error_dict_from_exception(exc)
    if not err:
        # Keep it short; the dashboard is a table cell.
        return (str(exc) or exc.__class__.__name__), None

    return format_alpaca_error_dict(err, symbol=symbol, side=side, qty=qty, notional=notional), err


def submit_order(
    *,
    symbol: str,
    side: str,
    client_order_id: str,
    qty: float | None,
    notional: float | None,
    order_type: str = "market",
    limit_price: float | None = None,
    time_in_force: str = "day",
) -> dict[str, Any]:
    client = trading_client()
    order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

    tif = TimeInForce.GTC if time_in_force.lower() == "gtc" else TimeInForce.DAY

    if order_type.lower() == "limit":
        if limit_price is None:
            raise ValueError("limit_price is required for limit orders")
        req = LimitOrderRequest(
            symbol=symbol,
            side=order_side,
            time_in_force=tif,
            client_order_id=client_order_id,
            qty=qty,
            limit_price=limit_price,
        )
    else:
        req = MarketOrderRequest(
            symbol=symbol,
            side=order_side,
            time_in_force=tif,
            client_order_id=client_order_id,
            qty=qty,
            notional=notional,
        )
    order = client.submit_order(order_data=req)
    # Return a plain dict so we can JSON-store it easily
    return {
        "id": str(order.id),
        "status": str(order.status),
        "order_type": _jsonable(getattr(order, "order_type", None)),
        "time_in_force": _jsonable(getattr(order, "time_in_force", None)),
        "limit_price": _jsonable(getattr(order, "limit_price", None)),
        "submitted_at": _jsonable(getattr(order, "submitted_at", None)),
        "filled_at": _jsonable(getattr(order, "filled_at", None)),
        "filled_avg_price": _jsonable(getattr(order, "filled_avg_price", None)),
        "filled_qty": _jsonable(getattr(order, "filled_qty", None)),
        "client_order_id": _jsonable(getattr(order, "client_order_id", None)),
        "symbol": _jsonable(getattr(order, "symbol", None)),
        "side": _jsonable(getattr(order, "side", None)),
    }

