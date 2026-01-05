from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import DATABASE_URL
from src.logger import logger

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def init_db():
    """Initializes the database by creating all tables."""
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # For dev only
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")

async def get_session() -> AsyncSession:
    """Dependency to get a DB session."""
    async with async_session() as session:
        yield session
