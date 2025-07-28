# App Idea Hunter

Automatically mine complaints from Reddit and Google Play reviews, filter pain points, and use AI to generate and score startup ideas.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run locally**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Run tests**:
   ```bash
   pytest tests/
   ```

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Environment configuration
├── logging_config.py    # JSON structured logging
├── scrapers/            # Reddit and Google Play scrapers
├── models/              # SQLModel database models
├── routes/              # FastAPI route handlers
└── services/            # Business logic and AI integration

prompts/
└── idea_prompt.txt      # GPT-3.5 prompt template

tests/                   # Test files
Dockerfile              # Container configuration
fly.toml               # Fly.io deployment config
requirements.txt       # Python dependencies
```

## Deployment

Deploy to Fly.io:

```bash
# Set secrets
fly secrets set OPENAI_API_KEY=your_key
fly secrets set SUPABASE_SERVICE_KEY=your_key
fly secrets set SUPABASE_URL=your_url

# Deploy
fly deploy
```

## Features

- ✅ FastAPI application structure
- ✅ Environment configuration with python-dotenv
- ✅ JSON structured logging
- ✅ Docker containerization
- ✅ Fly.io deployment configuration with scale-to-zero
- ✅ Automated daily scraping via cron (2 AM UTC)

## Cost Monitoring

- Target cost: ~$0.002 per complaint processed
- Cost guard: CI fails if mean tokens per complaint > 600
- Monthly target: Under $5 for solo usage