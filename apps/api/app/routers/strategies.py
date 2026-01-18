from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..db import engine
from ..models import Order, Position, Signal, Strategy

router = APIRouter()


@router.get("/strategies")
def list_strategies(active_only: bool = Query(default=False)) -> list[dict[str, Any]]:
    with Session(engine) as s:
        q = select(Strategy)
        if active_only:
            q = q.where(Strategy.is_active == True)  # noqa: E712
        strategies = list(s.exec(q))

        # Preload latest orders/signals for simple summary stats.
        orders = list(s.exec(select(Order)))
        positions = list(s.exec(select(Position)))
        signals = list(s.exec(select(Signal)))

    by_strategy_orders: dict[str, list[Order]] = {}
    for o in orders:
        by_strategy_orders.setdefault(o.strategy_id, []).append(o)

    by_strategy_positions: dict[str, list[Position]] = {}
    for p in positions:
        by_strategy_positions.setdefault(p.strategy_id, []).append(p)

    by_strategy_signals: dict[str, list[Signal]] = {}
    for sig in signals:
        by_strategy_signals.setdefault(sig.strategy_id, []).append(sig)

    out: list[dict[str, Any]] = []
    for strat in strategies:
        open_positions = [p for p in by_strategy_positions.get(strat.id, []) if p.qty != 0]
        sigs = sorted(by_strategy_signals.get(strat.id, []), key=lambda x: x.signal_time)
        first_sig = sigs[0] if sigs else None
        last_sig = sigs[-1] if sigs else None

        # Buy & hold comparison (MVP): use first/last signal price if we don't have live quote yet.
        bh_pct = None
        bh_usd = None
        bh_basis_usd = None
        if first_sig and last_sig and first_sig.signal_price and last_sig.signal_price:
            bh_pct = (last_sig.signal_price / first_sig.signal_price) - 1.0
            # USD basis: use strategy sizing notional if available, else $1,000 default.
            basis = strat.fixed_notional_usd or 1000.0
            bh_basis_usd = basis
            bh_usd = basis * bh_pct

        out.append(
            {
                "id": strat.id,
                "name": strat.name,
                "description": strat.description,
                "is_active": strat.is_active,
                "sizing_type": strat.sizing_type,
                "open_positions_count": len(open_positions),
                "pnl_usd": 0.0,  # TODO: compute from fills
                "pnl_pct": 0.0,  # TODO: compute from fills / equity curve
                "buy_hold_basis_usd": bh_basis_usd,
                "buy_hold_usd": bh_usd,
                "buy_hold_pct": bh_pct,
                "notes": "Buy&Hold uses first/last signal_price until Alpaca quote sync is implemented.",
            }
        )
    return out


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> dict[str, Any]:
    with Session(engine) as s:
        strat = s.get(Strategy, strategy_id)
        if not strat:
            return {"error": "not_found"}
        return strat.model_dump()

