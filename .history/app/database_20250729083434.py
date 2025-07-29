import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from supabase import create_client, Client
from app.config import settings
from app.logging_config import logger


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.supabase_client: Optional[Client] = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection and create tables if needed"""
        if self._initialized:
            return

        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                poolclass=NullPool,  # Use NullPool for serverless environments
                pool_pre_ping=True,  # Test connections before using
            )

            # Create session factory
            self.async_session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Initialize Supabase client if URL and key are provided
            if settings.supabase_url and settings.supabase_service_key:
                self.supabase_client = create_client(
                    settings.supabase_url, settings.supabase_service_key
                )

            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)

            self._initialized = True
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        if not self._initialized:
            await self.initialize()

        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check if database is accessible"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with db_manager.get_session() as session:
        yield session
