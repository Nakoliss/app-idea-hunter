# Technology Stack

## Backend
- **Framework**: FastAPI with Python 3.12
- **Server**: Uvicorn ASGI server
- **Database**: Supabase Postgres (Free tier for MVP)
- **HTTP Client**: httpx for async scraping
- **AI Integration**: OpenAI GPT-3.5 for idea generation

## Frontend
- **Styling**: Tailwind CSS
- **Interactivity**: HTMX + Alpine.js
- **Templates**: HTML served directly by FastAPI

## Infrastructure
- **Hosting**: Fly.io with scale-to-zero capability
- **Secrets Management**: Fly secrets store
- **Scheduling**: Fly cron for automated scraping
- **Containerization**: Docker

## Key Libraries
```
fastapi
uvicorn[standard]
httpx
sqlmodel
python-dotenv
vaderSentiment
python-json-logger
openai
supabase
```

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Run tests
pytest tests/
```

### Deployment
```bash
# Deploy to Fly.io
fly deploy

# Set secrets
fly secrets set OPENAI_API_KEY=your_key
fly secrets set SUPABASE_SERVICE_KEY=your_key
fly secrets set SUPABASE_URL=your_url
```

### Database
- Use Supabase dashboard for schema management
- Fallback to SQLite for offline development: `DB_URL=sqlite:///offline.db`

## Cost Monitoring
- GitHub Action fails if mean tokens per complaint > 600
- Target cost: ~$0.002 per complaint processed