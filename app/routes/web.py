"""
Web routes for HTML pages
"""
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Render dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/")
async def index(request: Request):
    """Redirect to dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})