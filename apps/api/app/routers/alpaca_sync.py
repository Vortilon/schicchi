from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..db import engine
from ..models import Fill, Order, Position, Strategy
from ..settings import settings

router = APIRouter()


def _client() -> TradingClient:
    if not settings.alpaca_key or not settings.alpaca_secret:
        raise RuntimeError("Alpaca credentials not set.")
    return TradingClient(settings.alpaca_key, settings.alpaca_secret, paper="paper" in settings.alpaca_base_url)


@router.get("/alpaca/account")
def alpaca_account() -> dict[str, Any]:
    c = _client()
    acct = c.get_account()
    last_equity = getattr(acct, "last_equity", None)
    try:
        last_equity_f = float(last_equity) if last_equity is not None else None
    except Exception:
        last_equity_f = None
    equity_f = float(acct.equity)
    day_pl_usd = (equity_f - last_equity_f) if last_equity_f else None
    day_pl_pct = (day_pl_usd / last_equity_f) if (day_pl_usd is not None and last_equity_f) else None
    return {
        "account_number": getattr(acct, "account_number", None),
        "id": str(getattr(acct, "id", "")) or None,
        "cash": float(acct.cash),
        "equity": float(acct.equity),
        "last_equity": last_equity_f,
        "day_pl_usd": day_pl_usd,
        "day_pl_pct": day_pl_pct,
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
    }


@router.post("/sync/alpaca")
def sync_alpaca() -> dict[str, Any]:
    """
    Pull latest orders/positions from Alpaca and update DB.
    Fills: for MVP we store filled_qty/avg on Order and create a Fill row when fully filled.
    """
    c = _client()
    since = datetime.now(timezone.utc) - timedelta(days=10)

    orders_req = GetOrdersRequest(status="all", after=since)
    alp_orders = c.get_orders(filter=orders_req)

    updated_orders = 0
    new_fills = 0

    with Session(engine) as s:
        # Map by client_order_id (trade_id) when possible, else by alpaca id.
        db_orders = list(s.exec(select(Order)))
        by_trade = {o.trade_id: o for o in db_orders if o.trade_id}
        by_alpaca = {o.alpaca_order_id: o for o in db_orders if o.alpaca_order_id}

        for ao in alp_orders:
            client_order_id = getattr(ao, "client_order_id", None)
            alp_id = str(getattr(ao, "id", ""))
            o = by_trade.get(client_order_id) if client_order_id else None
            if not o:
                o = by_alpaca.get(alp_id)
            if not o:
                continue

            o.alpaca_order_id = alp_id
            o.status = str(getattr(ao, "status", "") or "")
            o.submitted_at = getattr(ao, "submitted_at", None)
            o.filled_at = getattr(ao, "filled_at", None)
            favg = getattr(ao, "filled_avg_price", None)
            fqty = getattr(ao, "filled_qty", None)
            o.filled_avg_price = float(favg) if favg else None
            o.filled_qty = float(fqty) if fqty else None
            o.raw_response_json = json.dumps(
                {"id": alp_id, "status": o.status, "client_order_id": client_order_id},
                separators=(",", ":"),
                ensure_ascii=False,
            )
            updated_orders += 1

            # Create a fill record when fully filled and not already present (MVP).
            if o.filled_at and o.filled_qty and o.filled_avg_price:
                exists = s.exec(
                    select(Fill).where(Fill.alpaca_order_id == alp_id).where(Fill.trade_id == o.trade_id)
                ).first()
                if not exists:
                    s.add(
                        Fill(
                            trade_id=o.trade_id,
                            alpaca_order_id=alp_id,
                            side=o.side,
                            filled_at=o.filled_at,
                            filled_qty=o.filled_qty,
                            filled_price=o.filled_avg_price,
                        )
                    )
                    new_fills += 1

        # Positions (account-wide). MVP: we store without per-strategy attribution (strategy_id="ALPACA").
        alp_positions = c.get_all_positions()
        now = datetime.utcnow()
        # Upsert by (strategy_id, symbol)
        existing = {(p.strategy_id, p.symbol): p for p in s.exec(select(Position))}
        seen_syms: set[str] = set()
        for ap in alp_positions:
            symbol = ap.symbol
            seen_syms.add(symbol)
            qty = float(ap.qty)
            avg = float(ap.avg_entry_price)
            key = ("ALPACA", symbol)
            if key in existing:
                p = existing[key]
                p.qty = qty
                p.avg_entry_price = avg
                p.last_sync_time = now
            else:
                s.add(
                    Position(
                        strategy_id="ALPACA",
                        symbol=symbol,
                        qty=qty,
                        avg_entry_price=avg,
                        open_time=now,
                        last_sync_time=now,
                    )
                )

        # Mark Alpaca-tracked positions that no longer exist as flat (so the UI matches Alpaca).
        for (sid, sym), p in existing.items():
            if sid != "ALPACA":
                continue
            if sym not in seen_syms:
                p.qty = 0.0
                p.avg_entry_price = p.avg_entry_price
                p.last_sync_time = now

        s.commit()

    return {"ok": True, "updated_orders": updated_orders, "new_fills": new_fills}


def _is_open_status(status: str | None) -> bool:
    if not status:
        return True
    s = str(status).lower()
    return s not in {"filled", "canceled", "cancelled", "rejected", "expired"}


@router.get("/alpaca/orders")
def alpaca_orders(
    status: str = Query(default="all"),  # all|open|closed
    limit: int = Query(default=200, ge=1, le=500),
    after_days: int = Query(default=10, ge=1, le=90),
) -> list[dict[str, Any]]:
    """
    List Alpaca orders, sorted with open/unfilled first.
    Adds strategy info by mapping Alpaca client_order_id -> DB Order/Strategy.
    """
    c = _client()
    since = datetime.now(timezone.utc) - timedelta(days=after_days)
    req = GetOrdersRequest(status=status, after=since, limit=limit)
    orders = c.get_orders(filter=req)

    with Session(engine) as s:
        db_orders = list(s.exec(select(Order)))
        by_trade = {o.trade_id: o for o in db_orders if o.trade_id}
        strategies = {st.id: st for st in s.exec(select(Strategy))}

    out: list[dict[str, Any]] = []
    for o in orders:
        client_order_id = getattr(o, "client_order_id", None)
        db = by_trade.get(client_order_id) if client_order_id else None
        st = strategies.get(db.strategy_id) if db else None

        def f(v: Any) -> float | None:
            try:
                return float(v) if v is not None else None
            except Exception:
                return None

        out.append(
            {
                "alpaca_order_id": str(getattr(o, "id", "")),
                "client_order_id": client_order_id,
                "strategy_id": db.strategy_id if db else None,
                "strategy_name": st.name if st else (db.strategy_id if db else None),
                "symbol": getattr(o, "symbol", None),
                "side": str(getattr(o, "side", "")) if getattr(o, "side", None) is not None else None,
                "order_type": str(getattr(o, "order_type", "")) if getattr(o, "order_type", None) is not None else None,
                "time_in_force": str(getattr(o, "time_in_force", "")) if getattr(o, "time_in_force", None) is not None else None,
                "status": str(getattr(o, "status", "")) if getattr(o, "status", None) is not None else None,
                "qty": f(getattr(o, "qty", None)),
                "notional": f(getattr(o, "notional", None)),
                "limit_price": f(getattr(o, "limit_price", None)),
                "stop_price": f(getattr(o, "stop_price", None)),
                "filled_qty": f(getattr(o, "filled_qty", None)),
                "filled_avg_price": f(getattr(o, "filled_avg_price", None)),
                "submitted_at": getattr(o, "submitted_at", None).isoformat() if getattr(o, "submitted_at", None) else None,
                "filled_at": getattr(o, "filled_at", None).isoformat() if getattr(o, "filled_at", None) else None,
            }
        )

    # Open/unfilled first, then newest first.
    def sort_key(r: dict[str, Any]):
        open_first = 0 if _is_open_status(r.get("status")) else 1
        t = r.get("submitted_at") or ""
        return (open_first, t)

    out.sort(key=sort_key)
    return out

