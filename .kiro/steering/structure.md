# Project Structure

## Core Application Structure
```
app/
├── main.py              # FastAPI application entry point
├── scrapers/            # Reddit and Google Play scrapers
├── models/              # SQLModel database models
├── routes/              # FastAPI route handlers
└── services/            # Business logic and AI integration
```

## Configuration & Deployment
```
prompts/
└── idea_prompt.txt      # GPT-3.5 prompt template

tests/
├── test_cost_guard.py   # Cost monitoring tests
└── ...                  # Other test files

Dockerfile               # Container configuration
fly.toml                # Fly.io deployment config
requirements.txt        # Python dependencies
logging.json            # JSON logging configuration
.env.example            # Environment variables template
```

## Database Schema (Supabase)
- **complaints**: Raw scraped complaint data with sentiment filtering
- **ideas**: AI-generated ideas with scoring metrics
- **sources**: Tracking of scraping sources and metadata
- **errors**: Failed scraping attempts for debugging

## Key Architectural Patterns

### Data Flow
1. Scrapers collect complaints → `complaints` table
2. Filter by sentiment (VADER < -0.3) and deduplicate (SHA-1)
3. GPT-3.5 processes complaints → structured JSON with scores
4. Store in `ideas` table with parsed numeric fields
5. UI displays joined data with pagination (100 rows)

### Async Processing
- Use `asyncio` and `httpx` for concurrent scraping
- Implement retries with exponential backoff
- Schedule via Fly cron: `0 2 * * *` (daily at 2 AM)

### Error Handling
- JSON structured logging for debugging
- Failed URLs stored in `errors` table
- Graceful degradation for API failures

### UI Conventions
- Server-side rendered HTML with FastAPI
- HTMX for dynamic interactions
- Alpine.js for client-side state
- Tailwind for consistent styling
- Support both table and card views
- Include favorites toggle and export functionality