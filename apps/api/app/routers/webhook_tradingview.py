import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from ..db import engine
from ..models import Order, Signal, Strategy, WebhookRequestLog
from ..settings import settings


limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class TradingViewWebhookPayload(BaseModel):
    token: str
    strategy_id: str
    strategy_name: str | None = None

    symbol: str
    exchange: str | None = None

    side: Literal["BUY", "SELL"]
    event: Literal["ENTRY", "EXIT"]

    intent_qty_type: Literal["notional_usd", "shares"]
    intent_qty_value: float = Field(gt=0)

    signal_price: float
    signal_time: str
    bar_time: str

    trade_id: str


def _parse_dt(s: str) -> datetime:
    # TradingView placeholders often arrive as strings; keep forgiving.
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def _require_json_only(req: Request) -> None:
    ct = (req.headers.get("content-type") or "").lower()
    if "application/json" not in ct:
        raise HTTPException(status_code=415, detail="Content-Type must be application/json")


@router.post("/webhook/tradingview")
@limiter.limit("30/minute")
async def tradingview_webhook(request: Request, payload: TradingViewWebhookPayload):
    # NOTE: SlowAPI requires the parameter name to be exactly "request" (or "websocket").
    _require_json_only(request)

    log = WebhookRequestLog(
        remote_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        content_type=request.headers.get("content-type"),
        ok=False,
    )

    if payload.token != settings.webhook_secret:
        log.reason = "invalid_token"
        with Session(engine) as s:
            s.add(log)
            s.commit()
        raise HTTPException(status_code=401, detail="Invalid token")

    raw_payload_json = json.dumps(payload.model_dump(), separators=(",", ":"), ensure_ascii=False)

    with Session(engine) as s:
        # Ensure strategy exists (auto-create for convenience)
        strat = s.get(Strategy, payload.strategy_id)
        if not strat:
            strat = Strategy(
                id=payload.strategy_id,
                name=payload.strategy_name or payload.strategy_id,
                is_active=True,
                sizing_type="fixed_notional_usd" if payload.intent_qty_type == "notional_usd" else "fixed_shares",
                fixed_notional_usd=payload.intent_qty_value if payload.intent_qty_type == "notional_usd" else None,
                fixed_shares=payload.intent_qty_value if payload.intent_qty_type == "shares" else None,
            )
            s.add(strat)
            s.commit()

        sig = Signal(
            trade_id=payload.trade_id,
            strategy_id=payload.strategy_id,
            symbol=payload.symbol,
            side=payload.side,
            event=payload.event,
            signal_time=_parse_dt(payload.signal_time),
            signal_price=float(payload.signal_price),
            payload_json=raw_payload_json,
        )
        s.add(sig)

        # MVP: we store an "intended" order record; Alpaca submission/sync comes next.
        order = Order(
            trade_id=payload.trade_id,
            strategy_id=payload.strategy_id,
            symbol=payload.symbol,
            side=payload.side,
            notional=payload.intent_qty_value if payload.intent_qty_type == "notional_usd" else None,
            qty=payload.intent_qty_value if payload.intent_qty_type == "shares" else None,
            status="received_signal",
        )
        s.add(order)

        log.ok = True
        log.reason = "ok"
        s.add(log)

        s.commit()

        return {
            "ok": True,
            "trade_id": payload.trade_id,
            "strategy_id": payload.strategy_id,
            "stored": {"signal_id": sig.id, "order_id": order.id},
            "note": "Stored signal + intended order. Alpaca execution/sync will populate alpaca_order_id/fills.",
        }

