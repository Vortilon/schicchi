from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .alpaca_stream import AlpacaTradeUpdatesStreamer
from .db import init_db
from .routers.health import router as health_router
from .routers.alpaca_sync import router as alpaca_router
from .routers.positions import router as positions_router
from .routers.strategies import router as strategies_router
from .routers.trades import router as trades_router
from .routers.transactions import router as transactions_router
from .routers.webhook_tradingview import limiter, router as tv_router
from .settings import settings


app = FastAPI(title="Schicchi Forward Testing API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

streamer: AlpacaTradeUpdatesStreamer | None = None

@app.on_event("startup")
async def on_startup():
    init_db()
    global streamer
    try:
        if settings.alpaca_key and settings.alpaca_secret:
            streamer = AlpacaTradeUpdatesStreamer()
            await streamer.start()
    except Exception:
        # Don't prevent API from starting if stream cannot connect.
        streamer = None


@app.on_event("shutdown")
async def on_shutdown():
    global streamer
    if streamer:
        await streamer.stop()
        streamer = None


app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(tv_router, prefix="/api", tags=["webhook"])
app.include_router(alpaca_router, prefix="/api", tags=["alpaca"])
app.include_router(strategies_router, prefix="/api", tags=["strategies"])
app.include_router(positions_router, prefix="/api", tags=["positions"])
app.include_router(trades_router, prefix="/api", tags=["trades"])
app.include_router(transactions_router, prefix="/api", tags=["transactions"])

