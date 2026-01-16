from sqlmodel import SQLModel, create_engine

from .settings import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)

