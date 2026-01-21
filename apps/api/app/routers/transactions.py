from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..alpaca import format_alpaca_error_message
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

    def _extract_order_fields_from_payload(payload_json: str) -> dict[str, Any]:
        try:
            p = json.loads(payload_json)
            if isinstance(p, dict):
                return {
                    "order_type": p.get("order_type"),
                    "limit_price": p.get("limit_price"),
                    "time_in_force": p.get("time_in_force"),
                }
        except Exception:
            pass
        return {"order_type": None, "limit_price": None, "time_in_force": None}

    out: list[dict[str, Any]] = []
    for sig in sigs:
        if today_only and sig.signal_time.date() != date.today():
            continue
        o = by_trade_order.get(sig.trade_id)
        extra = _extract_order_fields_from_payload(sig.payload_json)
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
                "order_type": extra["order_type"],
                "limit_price": extra["limit_price"],
                "time_in_force": extra["time_in_force"],
                "alpaca_order_id": o.alpaca_order_id if o else None,
                "alpaca_status": o.status if o else None,
                "alpaca_error": format_alpaca_error_message(o.error_message, symbol=sig.symbol, side=sig.side) if o else None,
                "filled_qty": o.filled_qty if o else None,
                "filled_avg_price": o.filled_avg_price if o else None,
            }
        )

    # If today_only and no rows, fall back to last N regardless of date.
    if today_only and not out:
        for sig in sigs:
            o = by_trade_order.get(sig.trade_id)
            extra = _extract_order_fields_from_payload(sig.payload_json)
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
                    "order_type": extra["order_type"],
                    "limit_price": extra["limit_price"],
                    "time_in_force": extra["time_in_force"],
                    "alpaca_order_id": o.alpaca_order_id if o else None,
                    "alpaca_status": o.status if o else None,
                    "alpaca_error": format_alpaca_error_message(o.error_message, symbol=sig.symbol, side=sig.side) if o else None,
                    "filled_qty": o.filled_qty if o else None,
                    "filled_avg_price": o.filled_avg_price if o else None,
                }
            )

    return out[:limit]

