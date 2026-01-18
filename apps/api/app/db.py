import time

from sqlmodel import SQLModel, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from .settings import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)

def _ensure_schema() -> None:
    # Minimal "migration" for early-stage deployments without Alembic.
    # Safe on Postgres due to IF NOT EXISTS.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE IF EXISTS orders ADD COLUMN IF NOT EXISTS error_message TEXT"))
        conn.execute(text("ALTER TABLE IF EXISTS orders ADD COLUMN IF NOT EXISTS raw_response_json TEXT"))
        conn.execute(text("ALTER TABLE IF EXISTS fills ADD COLUMN IF NOT EXISTS side TEXT"))


def init_db() -> None:
    # Postgres may not be ready when the container starts. Retry briefly.
    last_err: Exception | None = None
    for _ in range(30):  # ~30s max
        try:
            SQLModel.metadata.create_all(engine)
            _ensure_schema()
            return
        except OperationalError as e:
            last_err = e
            time.sleep(1)
    if last_err:
        raise last_err

