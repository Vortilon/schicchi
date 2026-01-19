import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from ..alpaca import submit_order
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

    # Optional order params (useful for testing when market is closed)
    order_type: str | None = None  # "market" | "limit"
    limit_price: Any = Field(default=None)
    time_in_force: str | None = None  # "day" | "gtc"


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

def _looks_like_unrendered_placeholder(s: str) -> bool:
    # TradingView placeholders ({{ticker}}) or DaviddTech placeholders (#close#) should never reach the server.
    return ("{{" in s) or ("}}" in s) or ("#" in s)


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

        # Idempotency: if we already have an order for this trade_id, do not re-submit to Alpaca.
        existing_order = s.exec(select(Order).where(Order.trade_id == payload.trade_id)).first()
        if existing_order:
            log.ok = True
            log.reason = "ok_duplicate_trade_id_no_resubmit"
            s.add(log)
            s.commit()
            return {
                "ok": True,
                "trade_id": payload.trade_id,
                "strategy_id": payload.strategy_id,
                "stored": {"signal_id": sig.id, "order_id": existing_order.id},
                "alpaca": {
                    "alpaca_order_id": existing_order.alpaca_order_id,
                    "status": existing_order.status,
                    "error": existing_order.error_message,
                },
                "note": "Duplicate trade_id: stored signal but did not re-submit order to Alpaca.",
            }

        # If this is a limit order and the limit_price did not resolve to a number (often because it is a placeholder),
        # store an order row but skip Alpaca execution (so it shows clearly in the UI).
        if (payload.order_type or "").lower() == "limit" and _to_float(payload.limit_price) is None:
            order = Order(
                trade_id=payload.trade_id,
                strategy_id=payload.strategy_id,
                symbol=payload.symbol,
                side=payload.side,
                notional=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "notional_usd" else None,
                qty=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "shares" else None,
                status="skipped_placeholders",
                error_message=f"Limit order requested but limit_price did not resolve to a number (got {payload.limit_price!r}). If using DaviddTech, ensure placeholders like #ShortTP1# are rendered before webhook send.",
            )
            log.ok = False
            log.reason = "skipped_limit_price_unresolved"
            s.add(log)
            s.add(order)
            s.commit()
            return {
                "ok": True,
                "trade_id": payload.trade_id,
                "strategy_id": payload.strategy_id,
                "stored": {"signal_id": sig.id, "order_id": order.id},
                "alpaca": {"alpaca_order_id": None, "status": order.status, "error": order.error_message},
            }

        # If placeholders weren't rendered, store an order row but skip Alpaca execution (so it shows in UI).
        if (
            _looks_like_unrendered_placeholder(payload.symbol)
            or _looks_like_unrendered_placeholder(payload.trade_id)
            or _looks_like_unrendered_placeholder(payload.signal_time)
            or _looks_like_unrendered_placeholder(payload.bar_time)
        ):
            order = Order(
                trade_id=payload.trade_id,
                strategy_id=payload.strategy_id,
                symbol=payload.symbol,
                side=payload.side,
                notional=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "notional_usd" else None,
                qty=_to_float(payload.intent_qty_value) if payload.intent_qty_type == "shares" else None,
                status="skipped_placeholders",
                error_message="Unrendered placeholders in payload (TradingView {{...}} or DaviddTech #...#). If using 'Any alert() function call', the Pine script must build the JSON with real values.",
            )
            log.ok = False
            log.reason = "skipped_placeholders"
            s.add(log)
            s.add(order)
            s.commit()
            return {
                "ok": True,
                "trade_id": payload.trade_id,
                "strategy_id": payload.strategy_id,
                "stored": {"signal_id": sig.id, "order_id": order.id},
                "alpaca": {"alpaca_order_id": None, "status": order.status, "error": order.error_message},
            }

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
            alpaca_resp = submit_order(
                symbol=payload.symbol,
                side=payload.side,
                client_order_id=payload.trade_id,
                qty=order.qty,
                notional=order.notional,
                order_type=(payload.order_type or "market"),
                limit_price=_to_float(payload.limit_price),
                time_in_force=(payload.time_in_force or "day"),
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

