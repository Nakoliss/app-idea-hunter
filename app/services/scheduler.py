"""
Scheduling service for automated scraping
"""
import asyncio
from datetime import datetime
from typing import Optional
from app.routes.scraping import scraping_service
from app.database import db_manager
from app.logging_config import logger


class SchedulerService:
    """Service for handling scheduled scraping operations"""
    
    def __init__(self):
        self.is_running = False
        self.last_run: Optional[datetime] = None
    
    async def run_scheduled_scraping(self):
        """Run the scheduled scraping process"""
        if self.is_running:
            logger.warning("Scraping already in progress, skipping scheduled run")
            return
        
        self.is_running = True
        self.last_run = datetime.utcnow()
        
        try:
            logger.info("Starting scheduled scraping process")
            
            # Get database session
            async with db_manager.get_session() as db:
                stats = await scraping_service.run_full_pipeline(db)
                logger.info(f"Scheduled scraping completed: {stats}")
                
        except Exception as e:
            logger.error(f"Error in scheduled scraping: {str(e)}")
        finally:
            self.is_running = False
    
    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None
        }


# Global scheduler instance
scheduler = SchedulerService()