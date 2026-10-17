# Text-to-SQL Analytics Agent

Type a business question in plain English and get back the SQL, the result table, and a short written summary. It runs against a sample music store database (Chinook).

- **Live demo:** https://text-to-sql-agent-bylfkkivfpmt4qccstqmzy.streamlit.app/
- **API docs:** https://text-to-sql-agent-yv2u.onrender.com/docs

> The backend is on a free tier and goes to sleep when idle, so the first request can take up to a minute. After that it's fast.
If you ask a question for example as shown in image below 
![alt text](image-1.png)
It produces insights as shown in image below 
![alt text](image-2.png)
For example you copy paste one of the starter questions it will also show you the SQL logic used to generate the said insights
![alt text](image-3.png)




## Why I built it

I work as a data analyst, so most of my day is writing SQL for other people's questions. I wanted to see how far an LLM could take that over, and what I'd need to put around it to trust the output. The interesting part turned out to be the safety layer, not the prompt.

## How it works

1. The question goes to a FastAPI endpoint (`/ask`).
2. The app reads the live database schema (tables, columns, foreign keys, a couple of sample rows) and sends it with the question to an LLM, which returns a SQL query.
3. A guardrail checks the query before it touches the database (details below).
4. The query runs on SQLite and the result comes back as a table.
5. A second LLM call summarises the result in two or three sentences.
6. Streamlit shows the SQL, the table, a bar chart when the result is a simple two-column breakdown, and the summary.

```
Streamlit  ->  FastAPI /ask  ->  LLM (SQL)  ->  guardrail  ->  SQLite  ->  LLM (summary)
```

## The guardrail

The model's output is treated like user input. Before running anything, `agent/sql_guard.py`:

- parses the query with `sqlparse` and allows exactly one `SELECT`
- rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, `PRAGMA` and similar keywords
- rejects chained statements like `SELECT ...; DROP TABLE ...`
- adds `LIMIT 500` if the query has no limit

I tested it with a handful of destructive and chained queries and all were blocked.

## Stack

- Python, FastAPI, Streamlit, SQLite, pandas, sqlparse
- LLM: `openai/gpt-oss-20b` through Groq's free tier
- Hosting: Render (backend, Docker) and Streamlit Community Cloud (frontend)

Total cost is zero.

## Project layout

```
.
├── agent/
│   ├── schema.py       # reads the schema for the prompt
│   ├── sql_guard.py    # validates generated SQL
│   └── core.py         # question -> SQL -> run -> summary
├── api/main.py         # FastAPI app
├── app/
│   ├── streamlit_app.py
│   └── requirements.txt  # frontend-only dependencies
├── data/chinook.sqlite
├── Dockerfile
└── requirements.txt    # backend dependencies
```

## Run it locally

You need Python 3.10 or newer and a free API key from [console.groq.com](https://console.groq.com) (no card needed).

```bash
pip install -r requirements.txt

# Mac/Linux
export GROQ_API_KEY=your-key
# Windows (cmd)
set GROQ_API_KEY=your-key

# terminal 1
uvicorn api.main:app --reload

# terminal 2
# Mac/Linux: export API_URL=http://localhost:8000
# Windows (cmd): set API_URL=http://localhost:8000
streamlit run app/streamlit_app.py
```

Try: "Which 5 countries generate the most revenue?" or "Who are the top 3 best-selling artists?"

## Deploying

- **Backend:** Render web service using the Dockerfile. Set `GROQ_API_KEY` as an environment variable.
- **Frontend:** Streamlit Community Cloud with main file `app/streamlit_app.py`. Add `API_URL = "https://your-render-url"` under Secrets.

## Problems I ran into

- `groq` and a newer `httpx` don't work together (`unexpected keyword argument 'proxies'`). Fixed by pinning `httpx==0.27.2`.
- Groq moved its Llama models to an enterprise tier in August 2026, so the model I started with returned a 404. I switched to `openai/gpt-oss-20b`.
- Streamlit Cloud defaulted to Python 3.14, where my pinned packages had no prebuilt wheels and the build hung. Choosing an older Python version fixed it. I also gave the frontend its own small `requirements.txt` so it doesn't install the backend packages.

## Limitations

- The model is small, so complex multi-join questions sometimes produce wrong SQL. There is no retry step yet.
- Each question is independent. It doesn't remember earlier ones, so "now break that down by year" won't work.
- The guardrail is a keyword and parse check. In a real deployment I'd also use a read-only database user.
- It only knows the Chinook database.

## What I'd add next

- Feed SQL errors back to the model for one retry
- Conversation memory for follow-up questions
- A small set of test questions with expected results, to measure accuracy
- Masking sensitive columns such as email and phone
