from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..alpaca import trading_client
from ..db import engine
from ..models import Order, Position, Signal, Strategy

router = APIRouter()


def _basis_per_symbol_usd(strat: Strategy) -> float:
    # USD basis per symbol for comparisons (MVP)
    return float(strat.fixed_notional_usd or 1000.0)


def _order_ts(o: Order) -> datetime:
    # Prefer fill time (real execution), then submission, then DB created time.
    if o.filled_at:
        return o.filled_at
    if o.submitted_at:
        return o.submitted_at
    return o.created_at or datetime.min


def _compute_bh_from_signals(*, strat: Strategy, sigs: list[Signal]) -> dict[str, Any]:
    """
    Buy & Hold, computed per-symbol first/last signal_price, then rolled up.

    This prevents mixing symbols (which can create absurd % changes in minutes).
    """
    by_symbol: dict[str, list[Signal]] = defaultdict(list)
    for s in sigs:
        by_symbol[s.symbol].append(s)

    basis_per_symbol = _basis_per_symbol_usd(strat)
    per_symbol: dict[str, dict[str, Any]] = {}

    total_basis = 0.0
    total_usd = 0.0
    for sym, sym_sigs in by_symbol.items():
        sym_sigs = sorted(sym_sigs, key=lambda x: x.signal_time)
        first = next((x for x in sym_sigs if x.signal_price is not None), None)
        last = next((x for x in reversed(sym_sigs) if x.signal_price is not None), None)
        if not first or not last:
            continue
        if not first.signal_price or not last.signal_price:
            continue
        if first.signal_price <= 0:
            continue

        pct = (last.signal_price / first.signal_price) - 1.0
        basis = basis_per_symbol
        usd = basis * pct
        per_symbol[sym] = {
            "symbol": sym,
            "start_time": first.signal_time.isoformat(),
            "end_time": last.signal_time.isoformat(),
            "start_price": first.signal_price,
            "end_price": last.signal_price,
            "buy_hold_basis_usd": basis,
            "buy_hold_pct": pct,
            "buy_hold_usd": usd,
        }
        total_basis += basis
        total_usd += usd

    total_pct = (total_usd / total_basis) if total_basis else None
    return {
        "buy_hold_basis_usd": total_basis if total_basis else None,
        "buy_hold_usd": total_usd if total_basis else None,
        "buy_hold_pct": total_pct,
        "buy_hold_by_symbol": sorted(per_symbol.values(), key=lambda x: x["symbol"]),
        "notes": "Buy&Hold uses per-symbol first/last signal_price until live quote sync is implemented.",
    }


def _compute_realized_performance(*, orders: list[Order]) -> dict[str, Any]:
    """
    Minimal realized P&L + trade stats from filled orders.

    We treat a "trade" as a round-trip per symbol: position goes from flat -> non-zero -> flat.
    """
    filled = [
        o
        for o in orders
        if o.filled_qty is not None and o.filled_avg_price is not None and float(o.filled_qty) != 0.0
    ]
    filled.sort(key=_order_ts)

    # State per symbol
    state: dict[str, dict[str, Any]] = {}
    # Chronological realized deltas (for drawdown)
    realized_events: list[tuple[datetime, float]] = []

    def ensure(sym: str) -> dict[str, Any]:
        if sym not in state:
            state[sym] = {
                "qty": 0.0,  # signed
                "avg": 0.0,
                "open_time": None,  # datetime | None
                "realized_since_open": 0.0,
                "trades": [],  # list[float] pnl per round-trip
                "realized_total": 0.0,
                "filled_orders": 0,
            }
        return state[sym]

    for o in filled:
        sym = o.symbol
        side = (o.side or "").upper()
        qty = float(o.filled_qty)  # type: ignore[arg-type]
        price = float(o.filled_avg_price)  # type: ignore[arg-type]
        t = _order_ts(o)

        if side not in ("BUY", "SELL"):
            continue
        delta = qty if side == "BUY" else -qty

        st = ensure(sym)
        st["filled_orders"] += 1
        pos_qty = float(st["qty"])
        pos_avg = float(st["avg"])

        # Opening from flat
        if pos_qty == 0.0:
            st["qty"] = delta
            st["avg"] = price
            st["open_time"] = t
            st["realized_since_open"] = 0.0
            continue

        # Adding to same direction
        if (pos_qty > 0 and delta > 0) or (pos_qty < 0 and delta < 0):
            new_abs = abs(pos_qty) + abs(delta)
            if new_abs > 0:
                st["avg"] = ((abs(pos_qty) * pos_avg) + (abs(delta) * price)) / new_abs
            st["qty"] = pos_qty + delta
            continue

        # Reducing or flipping
        closing_qty = min(abs(pos_qty), abs(delta))
        realized = 0.0
        if pos_qty > 0 and delta < 0:
            # selling long
            realized = closing_qty * (price - pos_avg)
        elif pos_qty < 0 and delta > 0:
            # buying to cover short
            realized = closing_qty * (pos_avg - price)

        if realized != 0.0:
            st["realized_total"] += realized
            st["realized_since_open"] += realized
            realized_events.append((t, realized))

        new_qty = pos_qty + delta

        # If we flipped (closed old + opened opposite without going flat),
        # we treat this as: close trade, then open a new one at this price/time.
        flipped = (pos_qty > 0 and new_qty < 0) or (pos_qty < 0 and new_qty > 0)
        if flipped:
            st["trades"].append(float(st["realized_since_open"]))
            st["realized_since_open"] = 0.0
            st["open_time"] = t
            st["avg"] = price
            st["qty"] = new_qty
            continue

        # Fully flat => close trade
        if new_qty == 0.0:
            st["qty"] = 0.0
            st["avg"] = 0.0
            st["trades"].append(float(st["realized_since_open"]))
            st["realized_since_open"] = 0.0
            st["open_time"] = None
            continue

        # Partial reduce but still same direction
        st["qty"] = new_qty
        # avg stays the same

    # Aggregate + per symbol summary
    per_symbol: list[dict[str, Any]] = []
    all_trades: list[float] = []
    total_realized = 0.0
    open_positions_count = 0
    for sym, st in state.items():
        trades = [float(x) for x in st["trades"]]
        wins = sum(1 for x in trades if x > 0)
        losses = sum(1 for x in trades if x < 0)
        net = float(st["realized_total"])
        total_realized += net
        all_trades.extend(trades)
        if float(st["qty"]) != 0.0:
            open_positions_count += 1

        gross_profit = sum(x for x in trades if x > 0)
        gross_loss = sum(x for x in trades if x < 0)  # negative
        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss else None
        win_rate = (wins / len(trades)) if trades else None
        per_symbol.append(
            {
                "symbol": sym,
                "open_qty": float(st["qty"]),
                "avg_entry_price": float(st["avg"]) if float(st["qty"]) != 0.0 else None,
                "filled_orders": int(st["filled_orders"]),
                "trades_total": len(trades),
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "net_profit_usd": net,
                "gross_profit_usd": gross_profit,
                "gross_loss_usd": gross_loss,
                "profit_factor": profit_factor,
            }
        )

    per_symbol.sort(key=lambda x: x["symbol"])

    # Overall stats across round-trips
    wins_total = sum(1 for x in all_trades if x > 0)
    losses_total = sum(1 for x in all_trades if x < 0)
    gross_profit_total = sum(x for x in all_trades if x > 0)
    gross_loss_total = sum(x for x in all_trades if x < 0)  # negative
    profit_factor_total = (gross_profit_total / abs(gross_loss_total)) if gross_loss_total else None
    win_rate_total = (wins_total / len(all_trades)) if all_trades else None
    avg_trade = (sum(all_trades) / len(all_trades)) if all_trades else None
    largest_win = max([x for x in all_trades if x > 0], default=None)
    largest_loss = min([x for x in all_trades if x < 0], default=None)

    # Max drawdown on realized equity curve (MVP)
    max_dd_pct = None
    if realized_events:
        realized_events.sort(key=lambda x: x[0])
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for _, d in realized_events:
            equity += d
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        # Convert to pct of peak (if peak>0), else leave None
        if peak > 0:
            max_dd_pct = max_dd / peak

    return {
        "open_positions_count": open_positions_count,
        "trades_total": len(all_trades),
        "wins": wins_total,
        "losses": losses_total,
        "win_rate": win_rate_total,
        "pnl_usd": total_realized,
        "gross_profit_usd": gross_profit_total,
        "gross_loss_usd": gross_loss_total,
        "profit_factor": profit_factor_total,
        "avg_trade_usd": avg_trade,
        "largest_win_usd": largest_win,
        "largest_loss_usd": largest_loss,
        "max_drawdown_pct": max_dd_pct,
        "by_symbol": per_symbol,
    }


def _build_roundtrip_trades(*, orders: list[Order]) -> list[dict[str, Any]]:
    """
    Build a TradingView-like trade list (round-trips) from filled orders.

    A trade is closed when a symbol position returns to flat. If a position flips,
    we close the current trade and open a new one at the flip timestamp.
    """
    filled = [
        o
        for o in orders
        if o.filled_qty is not None and o.filled_avg_price is not None and float(o.filled_qty) != 0.0
    ]
    filled.sort(key=_order_ts)

    state: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    trade_no = 0
    cumulative = 0.0

    def ensure(sym: str) -> dict[str, Any]:
        if sym not in state:
            state[sym] = {
                "qty": 0.0,  # signed
                "avg": 0.0,
                "entry_time": None,  # datetime | None
                "basis_usd": 0.0,  # sum of entry legs (abs(qty)*price) while trade open
                "realized_usd": 0.0,
            }
        return state[sym]

    for o in filled:
        sym = o.symbol
        side = (o.side or "").upper()
        qty = float(o.filled_qty)  # type: ignore[arg-type]
        price = float(o.filled_avg_price)  # type: ignore[arg-type]
        t = _order_ts(o)
        if side not in ("BUY", "SELL"):
            continue
        delta = qty if side == "BUY" else -qty

        st = ensure(sym)
        pos_qty = float(st["qty"])
        pos_avg = float(st["avg"])

        # Open from flat
        if pos_qty == 0.0:
            st["qty"] = delta
            st["avg"] = price
            st["entry_time"] = t
            st["basis_usd"] = abs(delta) * price
            st["realized_usd"] = 0.0
            continue

        # Add to same direction (increase basis)
        if (pos_qty > 0 and delta > 0) or (pos_qty < 0 and delta < 0):
            new_abs = abs(pos_qty) + abs(delta)
            if new_abs > 0:
                st["avg"] = ((abs(pos_qty) * pos_avg) + (abs(delta) * price)) / new_abs
            st["qty"] = pos_qty + delta
            st["basis_usd"] = float(st["basis_usd"]) + (abs(delta) * price)
            continue

        # Reduce or flip => realize P&L on the closed portion
        closing_qty = min(abs(pos_qty), abs(delta))
        realized = 0.0
        if pos_qty > 0 and delta < 0:
            realized = closing_qty * (price - pos_avg)
        elif pos_qty < 0 and delta > 0:
            realized = closing_qty * (pos_avg - price)
        st["realized_usd"] = float(st["realized_usd"]) + realized

        new_qty = pos_qty + delta

        # Flip: close trade then open opposite
        flipped = (pos_qty > 0 and new_qty < 0) or (pos_qty < 0 and new_qty > 0)
        if flipped:
            trade_no += 1
            pnl = float(st["realized_usd"])
            cumulative += pnl
            basis = float(st["basis_usd"]) or None
            pnl_pct = (pnl / basis) if basis else None
            out.append(
                {
                    "trade_no": trade_no,
                    "symbol": sym,
                    "direction": "long" if pos_qty > 0 else "short",
                    "entry_time": st["entry_time"].isoformat() if st["entry_time"] else None,
                    "exit_time": t.isoformat(),
                    "entry_avg_price": pos_avg,
                    "exit_price": price,
                    "position_size_usd": basis,
                    "net_pnl_usd": pnl,
                    "net_pnl_pct": pnl_pct,
                    "cumulative_pnl_usd": cumulative,
                }
            )
            # Open new opposite trade at flip timestamp
            st["qty"] = new_qty
            st["avg"] = price
            st["entry_time"] = t
            st["basis_usd"] = abs(new_qty) * price
            st["realized_usd"] = 0.0
            continue

        # Close to flat => finalize trade
        if new_qty == 0.0:
            trade_no += 1
            pnl = float(st["realized_usd"])
            cumulative += pnl
            basis = float(st["basis_usd"]) or None
            pnl_pct = (pnl / basis) if basis else None
            out.append(
                {
                    "trade_no": trade_no,
                    "symbol": sym,
                    "direction": "long" if pos_qty > 0 else "short",
                    "entry_time": st["entry_time"].isoformat() if st["entry_time"] else None,
                    "exit_time": t.isoformat(),
                    "entry_avg_price": pos_avg,
                    "exit_price": price,
                    "position_size_usd": basis,
                    "net_pnl_usd": pnl,
                    "net_pnl_pct": pnl_pct,
                    "cumulative_pnl_usd": cumulative,
                }
            )
            st["qty"] = 0.0
            st["avg"] = 0.0
            st["entry_time"] = None
            st["basis_usd"] = 0.0
            st["realized_usd"] = 0.0
            continue

        # Partial reduce remaining open
        st["qty"] = new_qty
        # avg unchanged for remaining qty

    return out


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
        strat_orders = by_strategy_orders.get(strat.id, [])
        sigs = sorted(by_strategy_signals.get(strat.id, []), key=lambda x: x.signal_time)

        perf = _compute_realized_performance(orders=strat_orders)
        bh = _compute_bh_from_signals(strat=strat, sigs=sigs)
        filled_orders_total = sum(
            1
            for o in strat_orders
            if o.filled_qty is not None and o.filled_avg_price is not None and float(o.filled_qty or 0) != 0.0
        )

        # Fallback: if we have explicit Position rows for this strategy, include them in open positions count
        # (useful if a future position tracker populates the table).
        explicit_open = [p for p in by_strategy_positions.get(strat.id, []) if p.qty != 0]
        open_positions_count = max(int(perf["open_positions_count"]), len(explicit_open))

        out.append(
            {
                "id": strat.id,
                "name": strat.name,
                "description": strat.description,
                "is_active": strat.is_active,
                "sizing_type": strat.sizing_type,
                "open_positions_count": open_positions_count,
                "trades_total": int(perf["trades_total"]),
                "wins": int(perf["wins"]),
                "losses": int(perf["losses"]),
                "pnl_usd": float(perf["pnl_usd"]),
                # pct basis: compare to "basis per symbol * symbols traded"
                "pnl_pct": (
                    (float(perf["pnl_usd"]) / (float(bh["buy_hold_basis_usd"]) or 1.0)) if bh["buy_hold_basis_usd"] else 0.0
                ),
                "buy_hold_basis_usd": bh["buy_hold_basis_usd"],
                "buy_hold_usd": bh["buy_hold_usd"],
                "buy_hold_pct": bh["buy_hold_pct"],
                "symbols_traded": len({s.symbol for s in sigs}) if sigs else 0,
                "signals_total": len(sigs),
                "orders_total": len(strat_orders),
                "filled_orders_total": filled_orders_total,
                "profit_factor": perf["profit_factor"],
                "max_drawdown_pct": perf["max_drawdown_pct"],
                "notes": bh["notes"],
            }
        )
    return out


@router.get("/strategies/{strategy_id}/report")
def strategy_report(
    strategy_id: str,
    initial_capital_usd: float | None = Query(default=None, gt=0),
) -> dict[str, Any]:
    """
    Strategy report with per-symbol breakdown (TradingView-like numbers, no charts).
    """
    with Session(engine) as s:
        strat = s.get(Strategy, strategy_id)
        if not strat:
            return {"error": "not_found"}
        sigs = list(s.exec(select(Signal).where(Signal.strategy_id == strategy_id)))
        ords = list(s.exec(select(Order).where(Order.strategy_id == strategy_id)))

    sigs_sorted = sorted(sigs, key=lambda x: x.signal_time)
    bh = _compute_bh_from_signals(strat=strat, sigs=sigs_sorted)
    perf = _compute_realized_performance(orders=ords)
    trades = _build_roundtrip_trades(orders=ords)

    # Determine an "initial capital" comparable number.
    # For forward testing, a good default is Alpaca last_equity (start-of-day equity) if available.
    acct_last_equity = None
    try:
        acct = trading_client().get_account()
        v = getattr(acct, "last_equity", None)
        acct_last_equity = float(v) if v is not None else None
    except Exception:
        acct_last_equity = None

    basis_total = float(bh["buy_hold_basis_usd"] or 0.0)
    init_cap = float(initial_capital_usd or acct_last_equity or (basis_total or 100000.0))
    init_cap_source = "query" if initial_capital_usd else ("alpaca_last_equity" if acct_last_equity else ("basis_total" if basis_total else "default_100000"))

    # Buy & hold return on initial capital (TV-style)
    bh_pct_total = bh.get("buy_hold_pct")
    bh_return_usd = (init_cap * float(bh_pct_total)) if bh_pct_total is not None else None

    pnl_usd = float(perf["pnl_usd"])
    pnl_pct = (pnl_usd / init_cap) if init_cap else None

    gross_profit = float(perf["gross_profit_usd"])
    gross_loss = float(perf["gross_loss_usd"])

    # Strategy outperformance vs buy&hold on the same initial capital.
    outperf_usd = (pnl_usd - bh_return_usd) if bh_return_usd is not None else None

    # Merge BH + performance per symbol
    bh_by_symbol = {x["symbol"]: x for x in (bh.get("buy_hold_by_symbol") or [])}
    perf_by_symbol = {x["symbol"]: x for x in (perf.get("by_symbol") or [])}
    symbols = sorted(set(bh_by_symbol.keys()) | set(perf_by_symbol.keys()) | {s.symbol for s in sigs_sorted})

    signals_count_by_symbol: dict[str, int] = defaultdict(int)
    for s in sigs_sorted:
        signals_count_by_symbol[s.symbol] += 1

    by_symbol: list[dict[str, Any]] = []
    for sym in symbols:
        row: dict[str, Any] = {"symbol": sym, "signals": int(signals_count_by_symbol.get(sym, 0))}
        if sym in perf_by_symbol:
            row.update(perf_by_symbol[sym])
        else:
            row.update(
                {
                    "open_qty": 0.0,
                    "avg_entry_price": None,
                    "filled_orders": 0,
                    "trades_total": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": None,
                    "net_profit_usd": 0.0,
                    "gross_profit_usd": 0.0,
                    "gross_loss_usd": 0.0,
                    "profit_factor": None,
                }
            )
        if sym in bh_by_symbol:
            row.update(bh_by_symbol[sym])
        else:
            row.update({"buy_hold_basis_usd": None, "buy_hold_pct": None, "buy_hold_usd": None})
        by_symbol.append(row)

    # Open P&L (best-effort): mark strategy open qty/avg to market using latest Alpaca price if available,
    # else fall back to last signal price for that symbol.
    last_signal_price: dict[str, float] = {}
    for s in sigs_sorted:
        if s.signal_price is not None:
            last_signal_price[s.symbol] = float(s.signal_price)
    latest_price: dict[str, float] = {}
    try:
        for p in trading_client().get_all_positions():
            sym = getattr(p, "symbol", None)
            cp = getattr(p, "current_price", None)
            if sym and cp is not None:
                latest_price[str(sym)] = float(cp)
    except Exception:
        latest_price = {}

    open_pnl_usd = 0.0
    open_basis_usd = 0.0
    open_trades = 0
    for sym, st in {x["symbol"]: x for x in (perf.get("by_symbol") or [])}.items():
        q = float(st.get("open_qty") or 0.0)
        avg = st.get("avg_entry_price")
        if q == 0.0 or avg is None:
            continue
        px = latest_price.get(sym) or last_signal_price.get(sym)
        if px is None:
            continue
        open_trades += 1
        open_basis_usd += abs(q) * float(avg)
        if q > 0:
            open_pnl_usd += abs(q) * (float(px) - float(avg))
        else:
            open_pnl_usd += abs(q) * (float(avg) - float(px))
    open_pnl_pct = (open_pnl_usd / open_basis_usd) if open_basis_usd else None

    return {
        "strategy": {
            "id": strat.id,
            "name": strat.name,
            "is_active": strat.is_active,
            "sizing_type": strat.sizing_type,
            "basis_per_symbol_usd": _basis_per_symbol_usd(strat),
        },
        "summary": {
            "initial_capital_usd": init_cap,
            "initial_capital_source": init_cap_source,
            "open_pnl_usd": open_pnl_usd if open_trades else None,
            "open_pnl_pct": open_pnl_pct,
            "net_pnl_usd": pnl_usd,
            "net_pnl_pct": pnl_pct,
            "gross_profit_usd": gross_profit,
            "gross_profit_pct": (gross_profit / init_cap) if init_cap else None,
            "gross_loss_usd": gross_loss,
            "gross_loss_pct": (gross_loss / init_cap) if init_cap else None,
            "profit_factor": perf["profit_factor"],
            "commission_paid_usd": 0.0,
            "expected_payoff_usd": perf["avg_trade_usd"],
            "buy_hold_return_usd": bh_return_usd,
            "buy_hold_return_pct": bh_pct_total,
            "strategy_outperformance_usd": outperf_usd,
            "symbols_traded": len(symbols),
            "signals_total": len(sigs_sorted),
            "total_trades": int(perf["trades_total"]),
            "total_open_trades": int(perf["open_positions_count"]),
            "winning_trades": int(perf["wins"]),
            "losing_trades": int(perf["losses"]),
            "percent_profitable": perf["win_rate"],
            "avg_pnl_usd": perf["avg_trade_usd"],
            "avg_winning_trade_usd": (
                (gross_profit / float(perf["wins"])) if perf["wins"] else None
            ),
            "avg_losing_trade_usd": (
                (abs(gross_loss) / float(perf["losses"])) if perf["losses"] else None
            ),
            "ratio_avg_win_avg_loss": (
                ((gross_profit / float(perf["wins"])) / (abs(gross_loss) / float(perf["losses"])))
                if (perf["wins"] and perf["losses"] and gross_loss)
                else None
            ),
            "largest_winning_trade_usd": perf["largest_win_usd"],
            "largest_losing_trade_usd": perf["largest_loss_usd"],
            "largest_winning_trade_pct": (float(perf["largest_win_usd"]) / init_cap) if (perf["largest_win_usd"] is not None and init_cap) else None,
            "largest_losing_trade_pct": (abs(float(perf["largest_loss_usd"])) / init_cap) if (perf["largest_loss_usd"] is not None and init_cap) else None,
            "largest_winner_pct_gross_profit": (float(perf["largest_win_usd"]) / gross_profit) if (perf["largest_win_usd"] is not None and gross_profit) else None,
            "largest_loser_pct_gross_loss": (abs(float(perf["largest_loss_usd"])) / abs(gross_loss)) if (perf["largest_loss_usd"] is not None and gross_loss) else None,
            "max_drawdown_pct": perf["max_drawdown_pct"],
            "sharpe_ratio": None,
            "sortino_ratio": None,
        },
        "by_symbol": by_symbol,
        "trades": trades,
        "formulas": {
            "open_pnl_usd": "Σ over open symbols: long => qty*(px-avg), short => qty*(avg-px)",
            "open_pnl_pct": "open_pnl_usd / Σ(|qty|*avg)",
            "net_pnl_usd": "Σ realized P&L from filled orders when position reduces/closes",
            "net_pnl_pct": "net_pnl_usd / initial_capital_usd",
            "gross_profit_usd": "Σ(trade_pnl) where trade_pnl > 0",
            "gross_loss_usd": "Σ(trade_pnl) where trade_pnl < 0",
            "profit_factor": "gross_profit_usd / |gross_loss_usd|",
            "expected_payoff_usd": "avg(trade_pnl_usd) across closed trades",
            "percent_profitable": "winning_trades / total_trades",
            "buy_hold_return_pct": "(last_price/first_price) - 1 (per symbol), then capital-weighted rollup",
            "buy_hold_return_usd": "initial_capital_usd * buy_hold_return_pct",
            "strategy_outperformance_usd": "net_pnl_usd - buy_hold_return_usd",
        },
        "notes": [
            "All strategy metrics are computed from THIS strategy_id’s filled orders (strategy-scoped).",
            "Alpaca positions are account-level and may net multiple strategies together; we only use Alpaca for latest prices when possible.",
            "Trade stats are computed from filled orders: a trade is counted when a symbol position returns to flat.",
            bh["notes"],
        ],
    }


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> dict[str, Any]:
    with Session(engine) as s:
        strat = s.get(Strategy, strategy_id)
        if not strat:
            return {"error": "not_found"}
        return strat.model_dump()

