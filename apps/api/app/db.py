import time

from sqlmodel import SQLModel, create_engine
from sqlalchemy.exc import OperationalError

from .settings import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> None:
    # Postgres may not be ready when the container starts. Retry briefly.
    last_err: Exception | None = None
    for _ in range(30):  # ~30s max
        try:
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError as e:
            last_err = e
            time.sleep(1)
    if last_err:
        raise last_err

