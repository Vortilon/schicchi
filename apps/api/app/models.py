from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"

    id: str = Field(primary_key=True)
    name: str
    description: str | None = None
    is_active: bool = True

    # Order sizing config (minimum viable)
    sizing_type: str = "fixed_notional_usd"  # fixed_notional_usd | fixed_shares | max_cash_pct
    fixed_notional_usd: float | None = 1000.0
    fixed_shares: float | None = None
    max_cash_pct: float | None = None


class Signal(SQLModel, table=True):
    __tablename__ = "signals"

    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: str = Field(index=True)
    strategy_id: str = Field(index=True)
    symbol: str = Field(index=True)
    side: str
    event: str
    signal_time: datetime
    signal_price: float
    payload_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: str = Field(index=True)
    strategy_id: str = Field(index=True)
    symbol: str = Field(index=True)
    side: str

    qty: float | None = None
    notional: float | None = None

    alpaca_order_id: str | None = Field(default=None, index=True)
    status: str | None = None
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    filled_avg_price: float | None = None
    filled_qty: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Fill(SQLModel, table=True):
    __tablename__ = "fills"

    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: str = Field(index=True)
    alpaca_order_id: str = Field(index=True)
    filled_at: datetime
    filled_qty: float
    filled_price: float
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Position(SQLModel, table=True):
    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    symbol: str = Field(index=True)
    qty: float
    avg_entry_price: float
    open_time: datetime
    last_sync_time: datetime | None = None


class EquityPoint(SQLModel, table=True):
    __tablename__ = "equity_points"

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    symbol: str | None = Field(default=None, index=True)
    t: datetime = Field(index=True)
    equity_value: float


class Benchmark(SQLModel, table=True):
    __tablename__ = "benchmarks"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    t: datetime = Field(index=True)
    price: float


class WebhookRequestLog(SQLModel, table=True):
    __tablename__ = "webhook_request_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    remote_ip: str | None = None
    user_agent: str | None = None
    content_type: str | None = None
    ok: bool = False
    reason: str | None = None

