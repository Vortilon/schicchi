from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..alpaca import trading_client
from ..db import engine
from ..models import Position, Strategy

router = APIRouter()


@router.get("/positions")
def list_positions(strategy_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    # Best-effort enrichment with Alpaca live position fields (current_price, unrealized P&L).
    alpaca_by_symbol: dict[str, dict[str, Any]] = {}
    try:
        c = trading_client()
        for p in c.get_all_positions():
            sym = getattr(p, "symbol", None)
            if not sym:
                continue
            intraday_pl = getattr(p, "unrealized_intraday_pl", None)
            intraday_plpc = getattr(p, "unrealized_intraday_plpc", None)
            alpaca_by_symbol[str(sym)] = {
                "qty": float(getattr(p, "qty", 0.0)) if getattr(p, "qty", None) is not None else None,
                "avg_entry_price": float(getattr(p, "avg_entry_price", 0.0)) if getattr(p, "avg_entry_price", None) else None,
                "current_price": float(getattr(p, "current_price", 0.0)) if getattr(p, "current_price", None) else None,
                "unrealized_pl_usd": float(getattr(p, "unrealized_pl", 0.0)) if getattr(p, "unrealized_pl", None) else None,
                "unrealized_pl_pct": float(getattr(p, "unrealized_plpc", 0.0)) if getattr(p, "unrealized_plpc", None) else None,
                "intraday_pl_usd": float(intraday_pl) if intraday_pl is not None else None,
                "intraday_pl_pct": float(intraday_plpc) if intraday_plpc is not None else None,
                "market_value": float(getattr(p, "market_value", 0.0)) if getattr(p, "market_value", None) else None,
            }
    except Exception:
        # If credentials aren't set or Alpaca is unreachable, we still return DB positions.
        alpaca_by_symbol = {}

    with Session(engine) as s:
        q = select(Position)
        if strategy_id:
            q = q.where(Position.strategy_id == strategy_id)
        positions = list(s.exec(q))

        strategies = {st.id: st for st in s.exec(select(Strategy))}

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for p in positions:
        st = strategies.get(p.strategy_id)
        a = alpaca_by_symbol.get(p.symbol) if p.strategy_id == "ALPACA" else None
        # IMPORTANT:
        # - "ALPACA" rows are *account-level* and must reflect live Alpaca truth.
        # - DB rows can be stale if a sync hasn't run; do not show phantom positions.
        if p.strategy_id == "ALPACA":
            if a is None:
                eff_qty = 0.0
                eff_avg = None
            else:
                eff_qty = a.get("qty") if a.get("qty") is not None else 0.0
                eff_avg = a.get("avg_entry_price")
        else:
            eff_qty = p.qty
            eff_avg = p.avg_entry_price
        side = "long" if (eff_qty or 0) > 0 else "short"
        seen.add((p.strategy_id, p.symbol))
        out.append(
            {
                "id": p.id,
                "strategy_id": p.strategy_id,
                "strategy_name": ("Alpaca account" if p.strategy_id == "ALPACA" else (st.name if st else p.strategy_id)),
                "symbol": p.symbol,
                "side": side,
                "qty": eff_qty,
                "avg_entry_price": eff_avg,
                "open_time": p.open_time,
                "last_sync_time": p.last_sync_time,
                "current_price": a.get("current_price") if a else None,
                "unrealized_pl_usd": a.get("unrealized_pl_usd") if a else None,
                "unrealized_pl_pct": a.get("unrealized_pl_pct") if a else None,
                "intraday_pl_usd": a.get("intraday_pl_usd") if a else None,
                "intraday_pl_pct": a.get("intraday_pl_pct") if a else None,
                "realized_pl_usd": None,
                "status": "open" if (eff_qty or 0) != 0 else "flat",
            }
        )

    # If ALPACA positions exist but aren't yet in DB (or DB is empty), still show them.
    if (strategy_id is None or strategy_id == "ALPACA") and alpaca_by_symbol:
        synthetic_id = -1
        for sym, a in sorted(alpaca_by_symbol.items(), key=lambda x: x[0]):
            key = ("ALPACA", sym)
            if key in seen:
                continue
            q = a.get("qty") or 0.0
            out.append(
                {
                    "id": synthetic_id,
                    "strategy_id": "ALPACA",
                    "strategy_name": "Alpaca account",
                    "symbol": sym,
                    "side": "long" if q > 0 else "short",
                    "qty": a.get("qty"),
                    "avg_entry_price": a.get("avg_entry_price"),
                    "open_time": None,
                    "last_sync_time": None,
                    "current_price": a.get("current_price"),
                    "unrealized_pl_usd": a.get("unrealized_pl_usd"),
                    "unrealized_pl_pct": a.get("unrealized_pl_pct"),
                    "intraday_pl_usd": a.get("intraday_pl_usd"),
                    "intraday_pl_pct": a.get("intraday_pl_pct"),
                    "realized_pl_usd": None,
                    "status": "open",
                }
            )
            synthetic_id -= 1
    return out

