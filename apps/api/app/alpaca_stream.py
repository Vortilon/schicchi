from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from alpaca.trading.stream import TradingStream
from sqlmodel import Session, select

from .db import engine
from .models import Fill, Order
from .settings import settings


class AlpacaTradeUpdatesStreamer:
    """
    Listens for Alpaca trade_updates and writes status/fills into DB.
    This is what makes us "real-time" for orders that fill later (e.g., limit orders).
    """

    def __init__(self) -> None:
        if not settings.alpaca_key or not settings.alpaca_secret:
            raise RuntimeError("Alpaca credentials not set.")
        self.stream = TradingStream(
            settings.alpaca_key,
            settings.alpaca_secret,
            paper="paper" in settings.alpaca_base_url,
        )
        self._task: asyncio.Task | None = None

    async def _on_trade_update(self, data: Any) -> None:
        # alpaca-py sends TradeUpdate objects; pull fields defensively.
        event = str(getattr(data, "event", "") or "")
        order = getattr(data, "order", None)
        if not order:
            return

        alpaca_order_id = str(getattr(order, "id", "") or "")
        client_order_id = getattr(order, "client_order_id", None)
        status = str(getattr(order, "status", "") or "")
        filled_at = getattr(order, "filled_at", None)
        filled_qty = getattr(order, "filled_qty", None)
        filled_avg_price = getattr(order, "filled_avg_price", None)

        raw = {
            "event": event,
            "order": {
                "id": alpaca_order_id,
                "client_order_id": client_order_id,
                "status": status,
                "filled_at": str(filled_at) if filled_at else None,
                "filled_qty": str(filled_qty) if filled_qty else None,
                "filled_avg_price": str(filled_avg_price) if filled_avg_price else None,
            },
        }

        with Session(engine) as s:
            db_order = None
            if client_order_id:
                db_order = s.exec(select(Order).where(Order.trade_id == client_order_id)).first()
            if not db_order and alpaca_order_id:
                db_order = s.exec(select(Order).where(Order.alpaca_order_id == alpaca_order_id)).first()
            if not db_order:
                return

            db_order.alpaca_order_id = alpaca_order_id or db_order.alpaca_order_id
            db_order.status = status or db_order.status
            db_order.raw_response_json = json.dumps(raw, separators=(",", ":"), ensure_ascii=False)

            if filled_at:
                db_order.filled_at = filled_at
            if filled_qty:
                try:
                    db_order.filled_qty = float(filled_qty)
                except Exception:
                    pass
            if filled_avg_price:
                try:
                    db_order.filled_avg_price = float(filled_avg_price)
                except Exception:
                    pass

            # Create a fill row when we get a fill/partial_fill update.
            if event in {"fill", "partial_fill"} and db_order.filled_at and db_order.filled_qty and db_order.filled_avg_price:
                exists = s.exec(
                    select(Fill).where(Fill.alpaca_order_id == db_order.alpaca_order_id).where(Fill.trade_id == db_order.trade_id)
                ).first()
                if not exists:
                    s.add(
                        Fill(
                            trade_id=db_order.trade_id,
                            alpaca_order_id=db_order.alpaca_order_id,
                            side=db_order.side,
                            filled_at=db_order.filled_at,
                            filled_qty=db_order.filled_qty,
                            filled_price=db_order.filled_avg_price,
                            created_at=datetime.utcnow(),
                        )
                    )

            s.add(db_order)
            s.commit()

    async def start(self) -> None:
        self.stream.subscribe_trade_updates(self._on_trade_update)
        self._task = asyncio.create_task(self.stream._run_forever())

    async def stop(self) -> None:
        try:
            await self.stream.stop()
        finally:
            if self._task:
                self._task.cancel()

