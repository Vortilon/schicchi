import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from ..alpaca import submit_market_order
from ..db import engine
from ..models import Order, Signal, Strategy, WebhookRequestLog
from ..settings import settings


limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class TradingViewWebhookPayload(BaseModel):
    model_config = {"extra": "allow"}  # accept provider-specific placeholders/fields

    token: str
    strategy_id: str
    strategy_name: str | None = None

    symbol: str
    exchange: str | None = None

    # Allow DAVIDDTech naming and/or our canonical events.
    side: str
    event: str

    intent_qty_type: str
    intent_qty_value: Any = Field(default=None)

    signal_price: Any = Field(default=None)
    signal_time: str
    bar_time: str

    trade_id: str


def _parse_dt(s: str) -> datetime:
    # TradingView placeholders often arrive as strings; keep forgiving.
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()

def _to_float(v: Any) -> float | None:
    # Accept numbers or numeric strings; ignore placeholders like "#close#".
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except Exception:
            return None
    return None


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
            signal_price=_to_float(payload.signal_price),
            payload_json=raw_payload_json,
        )
        s.add(sig)

        # Store order and attempt Alpaca submission (paper).
        order = Order(
            trade_id=payload.trade_id,
            strategy_id=payload.strategy_id,
            symbol=payload.symbol,
            side=payload.side,
            notional=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "notional_usd" else None,
            qty=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "shares" else None,
            status="received_signal",
        )
        s.add(order)
        s.commit()

        # Submit to Alpaca for real execution (paper now).
        try:
            alpaca_resp = submit_market_order(
                symbol=payload.symbol,
                side=payload.side,
                client_order_id=payload.trade_id,
                qty=order.qty,
                notional=order.notional,
            )
            order.alpaca_order_id = alpaca_resp.get("id")
            order.status = alpaca_resp.get("status") or "submitted"
            order.raw_response_json = json.dumps(alpaca_resp, separators=(",", ":"), ensure_ascii=False)
        except Exception as e:
            order.status = "alpaca_error"
            order.error_message = str(e)

        log.ok = True
        log.reason = "ok"
        s.add(log)

        s.add(order)
        s.commit()

        return {
            "ok": True,
            "trade_id": payload.trade_id,
            "strategy_id": payload.strategy_id,
            "stored": {"signal_id": sig.id, "order_id": order.id},
            "alpaca": {
                "alpaca_order_id": order.alpaca_order_id,
                "status": order.status,
                "error": order.error_message,
            },
        }

