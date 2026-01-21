from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..db import engine
from ..models import Order, Signal, Strategy

router = APIRouter()


def _to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


@router.get("/trades")
def list_trades(
    strategy_id: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with Session(engine) as s:
        sig_q = select(Signal)
        ord_q = select(Order)
        if strategy_id:
            sig_q = sig_q.where(Signal.strategy_id == strategy_id)
            ord_q = ord_q.where(Order.strategy_id == strategy_id)
        if symbol:
            sig_q = sig_q.where(Signal.symbol == symbol)
            ord_q = ord_q.where(Order.symbol == symbol)

        signals = list(s.exec(sig_q))
        orders = list(s.exec(ord_q))
        strategies = {st.id: st for st in s.exec(select(Strategy))}

    # Pair by trade_id (as designed)
    by_trade: dict[str, dict[str, Any]] = {}

    for sig in signals:
        t = by_trade.setdefault(
            sig.trade_id,
            {
                "trade_id": sig.trade_id,
                "strategy_id": sig.strategy_id,
                "strategy_name": strategies.get(sig.strategy_id).name if strategies.get(sig.strategy_id) else sig.strategy_id,
                "symbol": sig.symbol,
                "side": sig.side,
                "event": sig.event,
                "signal_time": _to_iso(sig.signal_time),
                "signal_price": sig.signal_price,
                "order": None,
            },
        )
        # Keep earliest signal_time if multiple
        if t.get("signal_time") is None or (sig.signal_time and sig.signal_time.isoformat() < t["signal_time"]):
            t["signal_time"] = _to_iso(sig.signal_time)
            t["signal_price"] = sig.signal_price
            t["side"] = sig.side
            t["event"] = sig.event

    for o in orders:
        t = by_trade.setdefault(
            o.trade_id,
            {
                "trade_id": o.trade_id,
                "strategy_id": o.strategy_id,
                "strategy_name": strategies.get(o.strategy_id).name if strategies.get(o.strategy_id) else o.strategy_id,
                "symbol": o.symbol,
                "side": o.side,
                "event": None,
                "signal_time": None,
                "signal_price": None,
                "order": None,
            },
        )
        t["order"] = {
            "id": o.id,
            "status": o.status,
            "error": o.error_message,
            "alpaca_order_id": o.alpaca_order_id,
            "submitted_at": _to_iso(o.submitted_at),
            "filled_at": _to_iso(o.filled_at),
            "filled_avg_price": o.filled_avg_price,
            "filled_qty": o.filled_qty,
            "qty": o.qty,
            "notional": o.notional,
        }

    # Return newest first by signal_time then order created id
    def sort_key(x: dict[str, Any]):
        st = x.get("signal_time") or ""
        return st

    out = list(by_trade.values())
    out.sort(key=sort_key, reverse=True)
    return out

