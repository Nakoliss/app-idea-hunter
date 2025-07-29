"""
Unit tests for database connection management
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import DatabaseManager, get_db


@pytest.fixture
def db_manager():
    """Create a fresh database manager instance for testing"""
    return DatabaseManager()


@pytest.mark.asyncio
async def test_database_initialization(db_manager):
    """Test database manager initialization"""
    with patch('app.database.create_async_engine') as mock_engine, \
         patch('app.database.async_sessionmaker') as mock_session_maker, \
         patch('app.database.create_client') as mock_supabase:
        
        # Mock the engine
        mock_engine_instance = AsyncMock()
        mock_engine.return_value = mock_engine_instance
        
        # Mock the session maker
        mock_session_maker.return_value = AsyncMock()
        
        # Initialize database
        await db_manager.initialize()
        
        assert db_manager._initialized is True
        assert db_manager.engine is not None
        assert db_manager.async_session_maker is not None
        
        # Test that initialization is idempotent
        await db_manager.initialize()
        mock_engine.assert_called_once()  # Should not be called again


@pytest.mark.asyncio
async def test_database_close(db_manager):
    """Test closing database connections"""
    with patch('app.database.create_async_engine') as mock_engine:
        mock_engine_instance = AsyncMock()
        mock_engine.return_value = mock_engine_instance
        
        # Initialize and then close
        await db_manager.initialize()
        await db_manager.close()
        
        assert db_manager._initialized is False
        mock_engine_instance.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_get_session(db_manager):
    """Test getting a database session"""
    with patch('app.database.create_async_engine'), \
         patch('app.database.async_sessionmaker') as mock_session_maker:
        
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None
        
        mock_session_maker_instance = Mock()
        mock_session_maker_instance.return_value = mock_session_context
        mock_session_maker.return_value = mock_session_maker_instance
        
        # Get session
        async with db_manager.get_session() as session:
            assert session == mock_session
            
        # Verify session lifecycle
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_rollback_on_error(db_manager):
    """Test that session rolls back on error"""
    with patch('app.database.create_async_engine'), \
         patch('app.database.async_sessionmaker') as mock_session_maker:
        
        # Mock session that raises an error
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None
        
        mock_session_maker_instance = Mock()
        mock_session_maker_instance.return_value = mock_session_context
        mock_session_maker.return_value = mock_session_maker_instance
        
        # Test rollback on error
        with pytest.raises(ValueError):
            async with db_manager.get_session() as session:
                raise ValueError("Test error")
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_success(db_manager):
    """Test successful health check"""
    with patch.object(db_manager, 'get_session') as mock_get_session:
        # Mock successful query execution
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = None
        mock_get_session.return_value = mock_context
        
        result = await db_manager.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(db_manager):
    """Test failed health check"""
    with patch.object(db_manager, 'get_session') as mock_get_session:
        # Mock query execution failure
        mock_get_session.side_effect = Exception("Database connection failed")
        
        result = await db_manager.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_get_db_dependency():
    """Test the get_db dependency function"""
    with patch('app.database.db_manager') as mock_db_manager:
        # Mock the get_session context manager
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = None
        
        mock_db_manager.get_session.return_value = mock_context
        
        # Test the dependency
        async for session in get_db():
            assert session == mock_session