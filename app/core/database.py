import os

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings


Base = declarative_base()

engine = create_async_engine(settings.database_url, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


def run_migrations() -> None:
    alembic_ini_path = os.path.join(os.getcwd(), "alembic.ini")
    cfg = Config(alembic_ini_path)
    cfg.set_main_option("sqlalchemy.url", settings.database_url_sync)
    command.upgrade(cfg, "head")
