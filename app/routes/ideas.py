"""
API routes for ideas management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Idea, Complaint
from app.logging_config import logger

router = APIRouter(prefix="/ideas", tags=["ideas"])


@router.get("/")
async def get_ideas(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("generated_at", regex="^(generated_at|score_overall|score_market)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    favorite_only: bool = Query(False),
    min_score: Optional[int] = Query(None, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated ideas with filtering and sorting"""
    try:
        # Build query
        query = select(Idea, Complaint).join(Complaint)
        
        # Apply filters
        if favorite_only:
            query = query.where(Idea.is_favorite == True)
        
        if min_score:
            query = query.where(Idea.score_overall >= min_score)
        
        # Apply sorting
        if order == "desc":
            query = query.order_by(getattr(Idea, sort_by).desc())
        else:
            query = query.order_by(getattr(Idea, sort_by).asc())
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        ideas_with_complaints = result.all()
        
        # Format response
        ideas = []
        for idea, complaint in ideas_with_complaints:
            idea_dict = idea.model_dump()
            idea_dict['complaint'] = complaint.model_dump()
            ideas.append(idea_dict)
        
        return {
            "ideas": ideas,
            "page": page,
            "limit": limit,
            "total": len(ideas)
        }
        
    except Exception as e:
        logger.error(f"Error fetching ideas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching ideas")


@router.put("/{idea_id}/favorite")
async def toggle_favorite(
    idea_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Toggle favorite status of an idea"""
    try:
        # Find idea
        result = await db.execute(select(Idea).where(Idea.id == idea_id))
        idea = result.scalar_one_or_none()
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        
        # Toggle favorite
        idea.is_favorite = not idea.is_favorite
        db.add(idea)
        await db.commit()
        
        return {
            "id": str(idea.id),
            "is_favorite": idea.is_favorite
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating favorite status")


@router.get("/{idea_id}")
async def get_idea(
    idea_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific idea with its complaint"""
    try:
        result = await db.execute(
            select(Idea, Complaint)
            .join(Complaint)
            .where(Idea.id == idea_id)
        )
        idea_with_complaint = result.first()
        
        if not idea_with_complaint:
            raise HTTPException(status_code=404, detail="Idea not found")
        
        idea, complaint = idea_with_complaint
        idea_dict = idea.model_dump()
        idea_dict['complaint'] = complaint.model_dump()
        
        return idea_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching idea {idea_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching idea")


@router.get("/stats/summary")
async def get_ideas_stats(db: AsyncSession = Depends(get_db)):
    """Get summary statistics for ideas"""
    try:
        # Total ideas count
        total_result = await db.execute(select(Idea))
        total_ideas = len(total_result.all())
        
        # Favorites count
        favorites_result = await db.execute(select(Idea).where(Idea.is_favorite == True))
        total_favorites = len(favorites_result.all())
        
        # Average scores
        if total_ideas > 0:
            ideas_result = await db.execute(select(Idea))
            ideas = ideas_result.scalars().all()
            
            avg_market = sum(idea.score_market for idea in ideas) / total_ideas
            avg_tech = sum(idea.score_tech for idea in ideas) / total_ideas
            avg_overall = sum(idea.score_overall for idea in ideas) / total_ideas
        else:
            avg_market = avg_tech = avg_overall = 0
        
        return {
            "total_ideas": total_ideas,
            "total_favorites": total_favorites,
            "average_scores": {
                "market": round(avg_market, 1),
                "tech": round(avg_tech, 1),
                "overall": round(avg_overall, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching ideas stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")