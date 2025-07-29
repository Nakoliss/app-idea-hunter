"""
Database initialization and migration utilities
"""
import asyncio
from sqlmodel import SQLModel
from app.database import db_manager
from app.models import Complaint, Idea, Source, Error
from app.logging_config import logger


async def init_database():
    """Initialize database and create all tables"""
    try:
        logger.info("Initializing database...")
        
        # Initialize database manager
        await db_manager.initialize()
        
        # The tables are created automatically by SQLModel when we import the models
        # and call create_all in the database manager
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        # Close connections
        await db_manager.close()


async def check_database_health():
    """Check database connectivity and table existence"""
    try:
        logger.info("Checking database health...")
        
        # Initialize if not already done
        await db_manager.initialize()
        
        # Perform health check
        is_healthy = await db_manager.health_check()
        
        if is_healthy:
            logger.info("Database health check passed")
        else:
            logger.error("Database health check failed")
            
        return is_healthy
        
    except Exception as e:
        logger.error(f"Database health check error: {str(e)}")
        return False
    finally:
        await db_manager.close()


if __name__ == "__main__":
    # Run database initialization when script is executed directly
    asyncio.run(init_database())