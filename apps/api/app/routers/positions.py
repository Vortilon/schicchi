from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..db import engine
from ..models import Position, Strategy

router = APIRouter()


@router.get("/positions")
def list_positions(strategy_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    with Session(engine) as s:
        q = select(Position)
        if strategy_id:
            q = q.where(Position.strategy_id == strategy_id)
        positions = list(s.exec(q))

        strategies = {st.id: st for st in s.exec(select(Strategy))}

    out: list[dict[str, Any]] = []
    for p in positions:
        st = strategies.get(p.strategy_id)
        side = "long" if p.qty > 0 else "short"
        out.append(
            {
                "id": p.id,
                "strategy_id": p.strategy_id,
                "strategy_name": st.name if st else p.strategy_id,
                "symbol": p.symbol,
                "side": side,
                "qty": p.qty,
                "avg_entry_price": p.avg_entry_price,
                "open_time": p.open_time,
                "last_sync_time": p.last_sync_time,
                # TODO: current_price + PnL will come from Alpaca quote sync
                "current_price": None,
                "unrealized_pl_usd": None,
                "unrealized_pl_pct": None,
                "realized_pl_usd": None,
                "status": "open" if p.qty != 0 else "flat",
            }
        )
    return out

