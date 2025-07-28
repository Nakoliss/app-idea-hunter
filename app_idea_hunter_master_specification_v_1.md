# App Idea Hunter – Master Specification (v1.4 · 2025‑07‑28)

> **One‑liner:** *Automatically mine complaints from Reddit and Google Play reviews, filter pain points, and let AI draft and score startup ideas—so you can pick your next build fast.*

---

## Table of Contents

1. Scope Levels (Solo Cloud MVP → SaaS Roadmap)
2. Project Overview & Objectives
3. Cloud‑ready Solo MVP Feature Set
4. Phase‑Backlog Features (reminders)
5. Technical Architecture
6. Data Flow & AI Prompting
7. Database Strategy (Supabase first)
8. Cost & Profitability Snapshot
9. Risks & Mitigations
10. Phased Timeline
11. Deliverables Checklist
12. Appendix Y – Starter Files

---

## 1 · Scope Levels

| Level                | Who                | Purpose                                           |
| -------------------- | ------------------ | ------------------------------------------------- |
| **Solo MVP (cloud)** | You alone          | Run from any PC; cost ≈ \$4/mo; zero manual sync. |
| **Alpha SaaS**       | Invite‑only circle | Add auth, usage caps, \$19/mo plan.               |
| **Public SaaS**      | Makers/indie devs  | Tiered plans, Stripe billing, email digests.      |

---

## 2 · Project Overview & Objectives

- **Goal:** In 2 days deploy a FastAPI web app to **Fly.io** that scrapes Reddit + Google Play, stores data in **Supabase Free** Postgres, and displays GPT‑3.5‑scored idea cards.
- **Success criteria (Solo):** ≥ 50 new pain‑point ideas/week; review time < 15 min; cost < \$5/mo.
- **Long‑term:** Upgrade to \$19/mo SaaS with >80 % gross margin.

---

## 3 · Cloud‑ready Solo MVP Feature Set (Phase 0)

| # | Feature                      | Details                                                                                                                                               |
| - | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Scrapers**                 | **Reddit** + **Google Play** 1‑‑3★ reviews. Async `httpx`; trigger via Fly cron (`0 2 * * *`) or “Run now” UI. *Apple App Store deferred to Phase 1.* |
| 2 | **Supabase Postgres (Free)** | Tables: `complaints`, `ideas`, `sources`; automatic backups. Only service‑role key stored in Fly secrets.                                             |
| 3 | **Sentiment & dedup**        | VADER sentiment < −0.3; SHA‑1 of first 120 tokens to drop duplicates.                                                                                 |
| 4 | **GPT‑3.5 idea generator**   | Prompt file `prompts/idea_prompt.txt`; returns idea + six scores; store raw JSON and parsed numeric fields.                                           |
| 5 | **Web UI**                   | Tailwind + HTMX + Alpine. Table & card views; **100‑row pagination**; favorites toggle.                                                               |
| 6 | **PDF / CSV export**         | Export filtered idea list.                                                                                                                            |
| 7 | **Fly.io scale‑to‑zero**     | Dockerised FastAPI; public HTTPS; sleeps when idle → \$0 hosting.                                                                                     |
| 8 | **Logging & retries**        | `logging.json` JSON logs; scraper retries with back‑off; failed URLs to `errors` table.                                                               |
| 9 | **Cost guard CI**            | GitHub Action fails if **mean tokens/complaint > 600**.                                                                                               |

---

## 4 · Phase‑Backlog Features

| Phase | Future feature                              | Rationale                     |
| ----- | ------------------------------------------- | ----------------------------- |
| 1     | Apple App Store & YouTube scrapers          | Broaden complaint sources.    |
| 2     | Embedding clustering; GPT‑4 deep dives      | Better themes & richer ideas. |
| 3     | Supabase Auth, Stripe billing, email digest | Monetise & retain.            |
| 4     | Zapier/Webhook export; self‑hosted Llama 3  | Power‑user & cost control.    |

---

## 5 · Technical Architecture

### 5.1 Solo MVP (Cloud)

- **Hosting:** Fly.io Machines (scale 0).
- **Backend:** FastAPI 3.12, Uvicorn.
- **DB:** Supabase Postgres Free.
- **Frontend:** HTML served by FastAPI (Tailwind/HTMX).
- **Scrapers:** asyncio `httpx`; scheduled via Fly cron.
- **Secrets:** Managed via Fly secrets store.

### 5.2 SaaS Upgrades

- Enable Supabase Auth + RLS.
- Separate Celery worker; UI to Vercel.

---

## 6 · Data Flow & AI Prompting

1. Scraper → `complaints`.
2. Filter → GPT‑3.5 with structured prompt.
3. Store JSON & scores in `ideas`.
4. UI displays joined data.\
   *Cost ≈ \$0.002 per complaint.*

---

## 7 · Database Strategy – Supabase First

Supabase Free covers Solo usage; fallback to SQLite offline (`DB_URL=sqlite:///offline.db`).

---

## 8 · Cost & Profit Snapshot

| Scenario     | Monthly cost | Notes                                                 |
| ------------ | ------------ | ----------------------------------------------------- |
| Solo cloud   | **≈ \$4**    | OpenAI only; Supabase + Fly free.                     |
| 50‑user SaaS | **≈ \$70**   | Supabase Pro + Fly + OpenAI; \$950 MRR ⇒ 93 % margin. |

---

## 9 · Risks & Mitigations

- Scraper blocks → rate‑limit, rotate UA.
- GPT cost creep → cost guard.
- Data loss → Supabase backups + CSV export.

---

## 10 · Phased Timeline (Solo Cloud)

| Step | Goal                                     | Est. Time |
| ---- | ---------------------------------------- | --------- |
| 0    | Create Supabase project; set secrets.    | 30 m      |
| 0.5  | Scaffold FastAPI + Dockerfile + logging. | 2 h       |
| 1    | Reddit & Play scrapers with retries.     | 3 h       |
| 1.25 | Integrate GPT & cost guard.              | 1 h       |
| 1.5  | Build UI + export.                       | 1 h       |
| 2    | Deploy to Fly; set cron.                 | 2 h       |

---

## 11 · Deliverables Checklist

- README with Fly deploy steps
- Dockerfile & `fly.toml`
- Scraper modules
- Prompt file
- FastAPI routes
- UI templates
- `.env.example`
- CI workflow
- Backlog list

---

## Appendix Y – Starter Files for Coding Agents

> These starter files live in the repository so AI coding agents can bootstrap without guessing.

### Y.1 `prompts/idea_prompt.txt`

```txt
Given this user complaint: "{{complaint}}"
Return JSON **exactly** in this format:
{
  "idea": <concise app idea>,
  "score_market": <1-10>,
  "score_tech": <1-10>,
  "score_competition": <1-10>,
  "score_monetisation": <1-10>,
  "score_feasibility": <1-10>,
  "score_overall": <1-10>
}
Constraints:
- Keep idea under 35 words.
- Use plain numbers only.
```

### Y.2 `.env.example`

```
OPENAI_API_KEY=
SUPABASE_SERVICE_KEY=
SUPABASE_URL=
FLY_APP_NAME=app-idea
```

### Y.3 `Dockerfile`

```Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

### Y.4 `logging.json`

```json
{
  "version": 1,
  "formatters": {
    "json": {"()": "python_json_logger.jsonlogger.JsonFormatter"}
  },
  "handlers": {
    "console": {"class": "logging.StreamHandler", "formatter": "json"}
  },
  "root": {"level": "INFO", "handlers": ["console"] }
}
```

### Y.5 `requirements.txt`

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

### Y.6 `tests/test_cost_guard.py`

```python
import json, statistics

def test_cost_guard():
    with open('sample_tokens.json') as f:
        tokens = json.load(f)
    assert statistics.mean(tokens) < 600
```

---

### End of App Idea Hunter Master Specification v1.5
