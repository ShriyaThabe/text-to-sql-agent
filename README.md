# 🗃️ Text-to-SQL Analytics Agent

Ask a business question in plain English. The agent writes the SQL, runs it
safely against a real relational database, and returns the result plus a
plain-English insight — no SQL knowledge required from the end user.

**Live demo:** _[add your deployed link here]_
**API docs:** _[add your Render URL]/docs_

> **Cost: $0.** LLM calls run on Groq's free API tier (no credit card
> required), the backend deploys free on Render, and the frontend deploys
> free on Streamlit Community Cloud. No paid trial that expires later.

## Why this project

Most "ML portfolio projects" are a notebook that predicts churn. This is a
small LLM-powered *system* — the difference employers actually care about:

- **Leverages a real skill you already have**: SQL and relational data
  modeling from your analyst background. This isn't a generic ML demo —
  it's your DA experience wrapped in an agentic interface, which is exactly
  the story you want in an interview.
- **On the current hiring radar**: LLM agents / RAG / tool-use are the
  fastest-growing skill area for DS/MLE roles right now, and this
  demonstrates you can build one end-to-end, not just call an API.
- **Has a real safety story**: the model's SQL output is treated as
  untrusted input and validated before execution (read-only, single
  statement, row-capped). This is the kind of guardrail question that comes
  up in MLE system-design interviews.

## Architecture

```
User question (Streamlit UI)
        │
        ▼
FastAPI /ask endpoint
        │
        ├─► agent/schema.py    — introspects live DB schema + sample rows
        │
        ├─► agent/core.py      — Groq (Llama 3.1) call #1: question + schema → SQL
        │
        ├─► agent/sql_guard.py — validates SQL is a single, safe SELECT
        │                        (blocks DROP/DELETE/UPDATE/chained statements)
        │
        ├─► sqlite3            — executes the sanitized query
        │
        └─► agent/core.py      — Groq (Llama 3.1) call #2: result table → insight
        │
        ▼
Results + SQL + insight rendered in Streamlit
```

Dataset: **Chinook** (digital music store — customers, invoices, tracks,
artists, genres, employees). It's a real relational schema with meaningful
joins, so the agent has to do actual multi-table reasoning, not toy
single-table lookups.

## Project structure

```
sql-agent/
├── data/
│   └── chinook.sqlite       # sample database
├── agent/
│   ├── schema.py             # schema introspection for prompting
│   ├── sql_guard.py          # safety layer — validates generated SQL
│   └── core.py                # the agent: NL -> SQL -> execute -> insight
├── api/
│   └── main.py                # FastAPI backend
├── app/
│   └── streamlit_app.py      # Streamlit frontend
├── requirements.txt
├── Dockerfile
└── README.md
```

## Run locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY=your-key-here   # free, no card required — see below

# Terminal 1 — backend
uvicorn api.main:app --reload

# Terminal 2 — frontend
export API_URL=http://localhost:8000
streamlit run app/streamlit_app.py
```

**Get a free Groq API key** (no credit card, no trial-credit expiry):
1. Go to [console.groq.com](https://console.groq.com) and sign up
2. Create an API key under "API Keys"
3. That's it — Groq's free tier gives generous per-minute/per-day request
   limits on models like `llama-3.1-8b-instant`, plenty for a portfolio demo
   or even light real usage.

On Windows PowerShell, set the key with `$env:GROQ_API_KEY="your-key-here"`
instead of `export`.

## Deploy — 100% free hosting

**Backend (FastAPI) → Render free tier**
1. Push this repo to GitHub.
2. On [render.com](https://render.com), create a new **Web Service**, connect
   the repo, choose "Docker" as the environment (it'll pick up the
   `Dockerfile` automatically).
3. Add environment variable `GROQ_API_KEY` in Render's dashboard (Settings →
   Environment).
4. Deploy — you'll get a URL like `https://your-app.onrender.com`.
   (Free tier spins down after inactivity — first request after idle takes
   ~30s to wake up. Worth mentioning you know this trade-off in interviews.)

**Frontend (Streamlit) → Streamlit Community Cloud**
1. On [share.streamlit.io](https://share.streamlit.io), connect the same
   GitHub repo, set the main file to `app/streamlit_app.py`.
2. In the app's "Secrets", add:
   ```
   API_URL = "https://your-app.onrender.com"
   ```
3. Deploy — you get a public `*.streamlit.app` link to put on your resume.

Alternative: deploy both together as a single **Hugging Face Space**
(Docker SDK) if you'd rather have one URL — combine the FastAPI and
Streamlit processes with a small supervisor script, or just run Streamlit
alone and call `agent/core.py` directly instead of going through the API.

## Safety notes (talk about this in interviews)

Generated SQL is never trusted blindly:
- Parsed with `sqlparse` to confirm it's exactly one `SELECT` statement
- Blocklist rejects `DROP`, `DELETE`, `UPDATE`, `ATTACH`, `PRAGMA`, etc.
- A row limit is injected if the model doesn't include one
- Chained statements (`SELECT ...; DROP TABLE ...;`) are rejected outright

This mirrors the real-world guardrail pattern used in production text-to-SQL
tools (e.g. how BI copilots restrict LLM-generated queries to read replicas
with row/column-level permissions).

## Extending it further (good "what would you do next" interview answers)

- Add conversation memory so follow-up questions ("now break that down by
  quarter") work without repeating context
- Cache schema + few-shot examples per table to cut prompt tokens
- Add a feedback loop: if the SQL errors, feed the error back to the model
  for a self-correction retry (one extra LLM call, meaningfully better
  success rate)
- Swap the row-level guardrail for real DB-level read-only credentials
- Add column-level permissioning (e.g. mask `Email`/`Phone` in `Customer`)
