"""
FastAPI application entry point for App Idea Hunter
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("App Idea Hunter starting up")
    
    yield
    
    # Shutdown
    logger.info("App Idea Hunter shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="App Idea Hunter",
    description="Automatically mine complaints and generate startup ideas",
    version="1.0.0",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Mount static files (if needed later)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "App Idea Hunter is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "app-idea-hunter"}