"""
Test basic project structure and imports
"""
import os
import sys
from pathlib import Path

def test_project_structure():
    """Test that all required directories and files exist"""
    
    # Check main directories
    assert os.path.exists("app"), "app directory should exist"
    assert os.path.exists("tests"), "tests directory should exist"
    assert os.path.exists("prompts"), "prompts directory should exist"
    
    # Check app subdirectories
    assert os.path.exists("app/scrapers"), "app/scrapers directory should exist"
    assert os.path.exists("app/models"), "app/models directory should exist"
    assert os.path.exists("app/routes"), "app/routes directory should exist"
    assert os.path.exists("app/services"), "app/services directory should exist"
    
    # Check key files
    assert os.path.exists("app/main.py"), "app/main.py should exist"
    assert os.path.exists("app/config.py"), "app/config.py should exist"
    assert os.path.exists("app/logging_config.py"), "app/logging_config.py should exist"
    assert os.path.exists("requirements.txt"), "requirements.txt should exist"
    assert os.path.exists("Dockerfile"), "Dockerfile should exist"
    assert os.path.exists("fly.toml"), "fly.toml should exist"
    assert os.path.exists(".env.example"), ".env.example should exist"
    assert os.path.exists("prompts/idea_prompt.txt"), "prompts/idea_prompt.txt should exist"


def test_requirements_file():
    """Test that requirements.txt contains expected dependencies"""
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    # Check for key dependencies
    assert "fastapi" in content, "FastAPI should be in requirements"
    assert "uvicorn" in content, "Uvicorn should be in requirements"
    assert "sqlmodel" in content, "SQLModel should be in requirements"
    assert "httpx" in content, "httpx should be in requirements"
    assert "python-dotenv" in content, "python-dotenv should be in requirements"
    assert "vaderSentiment" in content, "vaderSentiment should be in requirements"
    assert "python-json-logger" in content, "python-json-logger should be in requirements"
    assert "openai" in content, "openai should be in requirements"
    assert "supabase" in content, "supabase should be in requirements"


def test_dockerfile():
    """Test that Dockerfile has correct configuration"""
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    assert "FROM python:3.12-slim" in content, "Should use Python 3.12"
    assert "EXPOSE 8000" in content, "Should expose port 8000"
    assert "uvicorn" in content, "Should run with uvicorn"
    assert "HEALTHCHECK" in content, "Should have health check"


def test_fly_toml():
    """Test that fly.toml has correct configuration"""
    with open("fly.toml", "r") as f:
        content = f.read()
    
    assert "app-idea-hunter" in content, "Should have correct app name"
    assert "auto_stop_machines = true" in content, "Should have scale-to-zero"
    assert "min_machines_running = 0" in content, "Should have scale-to-zero"
    assert "0 2 * * *" in content, "Should have daily cron at 2 AM"


def test_prompt_template():
    """Test that prompt template exists and has correct structure"""
    with open("prompts/idea_prompt.txt", "r") as f:
        content = f.read()
    
    assert "startup advisor" in content.lower(), "Should mention startup advisor"
    assert "{complaint_text}" in content, "Should have complaint_text placeholder"
    assert "score_market" in content, "Should have market score"
    assert "score_tech" in content, "Should have tech score"
    assert "score_overall" in content, "Should have overall score"


if __name__ == "__main__":
    test_project_structure()
    test_requirements_file()
    test_dockerfile()
    test_fly_toml()
    test_prompt_template()
    print("All structure tests passed!")