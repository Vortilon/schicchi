from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..db import engine
from ..models import Order, Signal, Strategy

router = APIRouter()


@router.get("/transactions")
def transactions(
    today_only: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[dict[str, Any]]:
    with Session(engine) as s:
        sigs = list(s.exec(select(Signal).order_by(Signal.id.desc()).limit(limit)))
        orders = list(s.exec(select(Order)))
        strategies = {st.id: st for st in s.exec(select(Strategy))}

    by_trade_order = {o.trade_id: o for o in orders}

    out: list[dict[str, Any]] = []
    for sig in sigs:
        if today_only and sig.signal_time.date() != date.today():
            continue
        o = by_trade_order.get(sig.trade_id)
        out.append(
            {
                "trade_id": sig.trade_id,
                "strategy_id": sig.strategy_id,
                "strategy_name": strategies.get(sig.strategy_id).name if strategies.get(sig.strategy_id) else sig.strategy_id,
                "symbol": sig.symbol,
                "event": sig.event,
                "side": sig.side,
                "signal_time": sig.signal_time.isoformat(),
                "signal_price": sig.signal_price,
                "alpaca_order_id": o.alpaca_order_id if o else None,
                "alpaca_status": o.status if o else None,
                "alpaca_error": o.error_message if o else None,
                "filled_qty": o.filled_qty if o else None,
                "filled_avg_price": o.filled_avg_price if o else None,
            }
        )

    # If today_only and no rows, fall back to last N regardless of date.
    if today_only and not out:
        for sig in sigs:
            o = by_trade_order.get(sig.trade_id)
            out.append(
                {
                    "trade_id": sig.trade_id,
                    "strategy_id": sig.strategy_id,
                    "strategy_name": strategies.get(sig.strategy_id).name if strategies.get(sig.strategy_id) else sig.strategy_id,
                    "symbol": sig.symbol,
                    "event": sig.event,
                    "side": sig.side,
                    "signal_time": sig.signal_time.isoformat(),
                    "signal_price": sig.signal_price,
                    "alpaca_order_id": o.alpaca_order_id if o else None,
                    "alpaca_status": o.status if o else None,
                    "alpaca_error": o.error_message if o else None,
                    "filled_qty": o.filled_qty if o else None,
                    "filled_avg_price": o.filled_avg_price if o else None,
                }
            )

    return out[:limit]

