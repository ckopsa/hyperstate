# app/infrastructure/database.py

import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Postgres connection string, read from the environment so the same code runs
# against the docker-compose Postgres locally and a managed instance in deploy.
# The default matches the `postgres` service in docker-compose.yml.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://hyperstate:hyperstate@localhost:5432/mealplan",
)

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
