"""
API routes for scraping operations
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.scrapers import RedditScraper, GooglePlayScraper
from app.services import ComplaintProcessor, AIService, CostMonitor
from app.models import Complaint, Idea, Error
from app.logging_config import logger

router = APIRouter(prefix="/scraping", tags=["scraping"])


class ScrapingService:
    """Service to orchestrate scraping, processing, and idea generation"""
    
    def __init__(self):
        self.reddit_scraper = RedditScraper()
        self.google_play_scraper = GooglePlayScraper()
        self.complaint_processor = ComplaintProcessor()
        self.ai_service = None
        self.cost_monitor = CostMonitor()
    
    async def initialize_ai_service(self):
        """Initialize AI service if API key is available"""
        try:
            self.ai_service = AIService()
            await self.ai_service.test_connection()
            logger.info("AI service initialized successfully")
        except Exception as e:
            logger.warning(f"AI service not available: {str(e)}")
            self.ai_service = None
    
    async def run_full_pipeline(self, db: AsyncSession) -> dict:
        """Run the complete scraping and processing pipeline"""
        stats = {
            "complaints_scraped": 0,
            "complaints_processed": 0,
            "ideas_generated": 0,
            "errors": 0
        }
        
        try:
            # Check cost limits
            if not self.cost_monitor.should_continue_processing():
                raise Exception("Cost limits exceeded, stopping processing")
            
            # Initialize AI service
            await self.initialize_ai_service()
            
            # Scrape from Reddit
            logger.info("Starting Reddit scraping...")
            reddit_complaints = await self.reddit_scraper.scrape()
            stats["complaints_scraped"] += len(reddit_complaints)
            
            # Scrape from Google Play
            logger.info("Starting Google Play scraping...")
            google_play_complaints = await self.google_play_scraper.scrape()
            stats["complaints_scraped"] += len(google_play_complaints)
            
            # Combine all complaints
            all_complaints = reddit_complaints + google_play_complaints
            
            # Process complaints (sentiment + deduplication)
            logger.info(f"Processing {len(all_complaints)} complaints...")
            processed_complaints, process_stats = await self.complaint_processor.batch_process_complaints(
                all_complaints, db
            )
            stats["complaints_processed"] = process_stats["processed"]
            
            # Save processed complaints to database
            for complaint in processed_complaints:
                db.add(complaint)
            await db.commit()
            
            # Generate ideas if AI service is available
            if self.ai_service and processed_complaints:
                logger.info(f"Generating ideas for {len(processed_complaints)} complaints...")
                
                # Limit to prevent excessive API costs
                complaints_for_ai = processed_complaints[:50]
                
                for complaint in complaints_for_ai:
                    try:
                        idea_data = await self.ai_service.generate_idea(complaint.content)
                        
                        # Record cost monitoring
                        tokens_used = idea_data.get('tokens_used', 0)
                        cost = self.ai_service.get_cost_estimate(tokens_used)
                        self.cost_monitor.record_usage(
                            complaint.content, tokens_used, cost, True
                        )
                        
                        # Create idea record
                        idea = Idea(
                            complaint_id=complaint.id,
                            idea_text=idea_data['idea'],
                            score_market=idea_data['score_market'],
                            score_tech=idea_data['score_tech'],
                            score_competition=idea_data['score_competition'],
                            score_monetisation=idea_data['score_monetisation'],
                            score_feasibility=idea_data['score_feasibility'],
                            score_overall=idea_data['score_overall'],
                            raw_response=idea_data['raw_response'],
                            tokens_used=tokens_used
                        )
                        
                        db.add(idea)
                        stats["ideas_generated"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error generating idea: {str(e)}")
                        stats["errors"] += 1
                
                await db.commit()
            
            # Save scraping errors
            all_errors = (
                self.reddit_scraper.get_failed_urls() + 
                self.google_play_scraper.get_failed_urls()
            )
            
            for error in all_errors:
                db.add(error)
            await db.commit()
            
            logger.info(f"Scraping pipeline completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in scraping pipeline: {str(e)}")
            await db.rollback()
            raise


# Global scraping service instance
scraping_service = ScrapingService()


@router.post("/run")
async def run_scraping(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger scraping process"""
    try:
        background_tasks.add_task(scraping_service.run_full_pipeline, db)
        
        return {
            "message": "Scraping started in background",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error starting scraping: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting scraping process")


@router.get("/status")
async def get_scraping_status(db: AsyncSession = Depends(get_db)):
    """Get current scraping status and statistics"""
    try:
        # Get recent complaints count
        recent_complaints = await db.execute(select(Complaint))
        total_complaints = len(recent_complaints.all())
        
        # Get recent ideas count
        recent_ideas = await db.execute(select(Idea))
        total_ideas = len(recent_ideas.all())
        
        # Get cost monitoring info
        cost_stats = scraping_service.cost_monitor.get_usage_statistics()
        cost_guard = scraping_service.cost_monitor.check_cost_guard()
        
        return {
            "total_complaints": total_complaints,
            "total_ideas": total_ideas,
            "cost_monitoring": {
                "total_cost_7_days": cost_stats["total_cost"],
                "mean_tokens_per_complaint": cost_stats["mean_tokens"],
                "cost_guard_passed": cost_guard["passed"],
                "can_continue_processing": scraping_service.cost_monitor.should_continue_processing()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting scraping status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting status")