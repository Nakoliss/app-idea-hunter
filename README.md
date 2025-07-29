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

- ✅ **Automated Scraping**: Reddit posts/comments and Google Play reviews (1-3 stars)
- ✅ **Sentiment Analysis**: VADER sentiment filtering (< -0.3 threshold)
- ✅ **Deduplication**: SHA-1 hash-based duplicate detection (first 120 tokens)
- ✅ **AI Idea Generation**: OpenAI GPT-3.5 with structured scoring (6 metrics)
- ✅ **Cost Monitoring**: Token usage tracking with CI/CD cost guards
- ✅ **Web Dashboard**: HTMX + Alpine.js interface with pagination and favorites
- ✅ **Export Functions**: PDF and CSV export of filtered ideas
- ✅ **Database Models**: SQLModel with Supabase/PostgreSQL support
- ✅ **Error Handling**: Comprehensive logging and graceful degradation
- ✅ **Deployment Ready**: Fly.io with scale-to-zero and cron scheduling

## API Endpoints

- `GET /`: Dashboard web interface
- `GET /ideas/`: Paginated ideas with filtering (favorites, min score, sorting)
- `PUT /ideas/{id}/favorite`: Toggle favorite status
- `POST /scraping/run`: Manual scraping trigger
- `GET /scraping/status`: Scraping statistics and cost monitoring
- `GET /health`: Health check for monitoring

## Cost Monitoring

- **Target**: ~$0.002 per complaint processed (GPT-3.5 pricing)
- **Cost Guard**: CI fails if mean tokens per complaint > 600
- **Daily Limit**: $100 daily spending cap
- **Monthly Target**: Under $5 for solo usage with scale-to-zero