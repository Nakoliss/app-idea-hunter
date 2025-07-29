"""
Complaint processing pipeline that combines sentiment filtering and deduplication
"""
from typing import Optional, Set, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models import Complaint
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.services.deduplication_service import DeduplicationService
from app.logging_config import logger


class ComplaintProcessor:
    """Orchestrates complaint processing with sentiment analysis and deduplication"""
    
    def __init__(self, sentiment_threshold: float = -0.3, token_limit: int = 120):
        """
        Initialize complaint processor
        
        Args:
            sentiment_threshold: Minimum sentiment score for filtering
            token_limit: Number of tokens for deduplication hash
        """
        self.sentiment_analyzer = SentimentAnalyzer(threshold=sentiment_threshold)
        self.deduplication_service = DeduplicationService(token_limit=token_limit)
        logger.info("Complaint processor initialized")
    
    async def load_existing_hashes(self, session: AsyncSession) -> Set[str]:
        """
        Load existing complaint hashes from database
        
        Args:
            session: Database session
            
        Returns:
            Set of existing content hashes
        """
        try:
            result = await session.execute(
                select(Complaint.content_hash).where(Complaint.content_hash.isnot(None))
            )
            hashes = {row[0] for row in result}
            logger.info(f"Loaded {len(hashes)} existing complaint hashes from database")
            return hashes
        except Exception as e:
            logger.error(f"Error loading existing hashes: {str(e)}")
            return set()
    
    async def process_complaint(
        self,
        content: str,
        source: str,
        source_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        existing_hashes: Optional[Set[str]] = None
    ) -> Optional[Complaint]:
        """
        Process a single complaint through sentiment and deduplication pipeline
        
        Args:
            content: Complaint text content
            source: Source of complaint (reddit, google_play)
            source_url: Optional URL of the source
            metadata: Optional metadata dictionary
            existing_hashes: Optional set of existing hashes to check against
            
        Returns:
            Complaint object if it passes filters, None otherwise
        """
        try:
            # Step 1: Sentiment analysis
            sentiment_score = self.sentiment_analyzer.analyze(content)
            
            if not self.sentiment_analyzer.is_negative_complaint(content):
                logger.debug(f"Complaint filtered out - positive sentiment: {sentiment_score}")
                return None
            
            # Step 2: Deduplication
            content_hash = self.deduplication_service.generate_hash(content)
            
            if self.deduplication_service.is_duplicate(content, existing_hashes):
                logger.debug(f"Complaint filtered out - duplicate hash: {content_hash}")
                return None
            
            # Step 3: Create complaint object
            complaint = Complaint(
                source=source,
                source_url=source_url,
                content=content,
                content_hash=content_hash,
                sentiment_score=sentiment_score,
                metadata=metadata,
                scraped_at=datetime.utcnow()
            )
            
            logger.debug(f"Complaint processed successfully - Hash: {content_hash}, Sentiment: {sentiment_score}")
            return complaint
            
        except Exception as e:
            logger.error(f"Error processing complaint: {str(e)}")
            return None
    
    async def batch_process_complaints(
        self,
        complaints_data: List[dict],
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[Complaint], dict]:
        """
        Process multiple complaints in batch
        
        Args:
            complaints_data: List of dicts with keys: content, source, source_url, metadata
            session: Optional database session to load existing hashes
            
        Returns:
            Tuple of (processed complaints list, statistics dict)
        """
        stats = {
            'total': len(complaints_data),
            'processed': 0,
            'filtered_sentiment': 0,
            'filtered_duplicate': 0,
            'errors': 0
        }
        
        # Load existing hashes if session provided
        existing_hashes = set()
        if session:
            existing_hashes = await self.load_existing_hashes(session)
        
        # Track new hashes in this batch
        batch_hashes = existing_hashes.copy()
        processed_complaints = []
        
        for data in complaints_data:
            try:
                # Extract data
                content = data.get('content', '')
                source = data.get('source', '')
                source_url = data.get('source_url')
                metadata = data.get('metadata')
                
                if not content or not source:
                    stats['errors'] += 1
                    continue
                
                # Check sentiment
                sentiment_score = self.sentiment_analyzer.analyze(content)
                if not self.sentiment_analyzer.is_negative_complaint(content):
                    stats['filtered_sentiment'] += 1
                    continue
                
                # Check duplicate
                content_hash = self.deduplication_service.generate_hash(content)
                if content_hash in batch_hashes:
                    stats['filtered_duplicate'] += 1
                    continue
                
                # Create complaint
                complaint = Complaint(
                    source=source,
                    source_url=source_url,
                    content=content,
                    content_hash=content_hash,
                    sentiment_score=sentiment_score,
                    metadata=metadata,
                    scraped_at=datetime.utcnow()
                )
                
                processed_complaints.append(complaint)
                batch_hashes.add(content_hash)
                stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing complaint in batch: {str(e)}")
                stats['errors'] += 1
        
        logger.info(
            f"Batch processing completed - "
            f"Total: {stats['total']}, "
            f"Processed: {stats['processed']}, "
            f"Filtered (sentiment): {stats['filtered_sentiment']}, "
            f"Filtered (duplicate): {stats['filtered_duplicate']}, "
            f"Errors: {stats['errors']}"
        )
        
        return processed_complaints, stats
    
    def reset_cache(self):
        """Reset the deduplication cache"""
        self.deduplication_service.clear_cache()
        logger.info("Complaint processor cache reset")