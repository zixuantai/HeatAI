from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {} if _is_sqlite else {"pool_size": 20, "max_overflow": 10}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
    **_engine_kwargs
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
