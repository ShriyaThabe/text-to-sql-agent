"""
Text-to-SQL Agent API
Run locally: uvicorn api.main:app --reload
Requires ANTHROPIC_API_KEY in the environment.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.core import SQLAgent

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "chinook.sqlite")

app = FastAPI(
    title="Text-to-SQL Analytics Agent",
    description="Ask a business question in plain English, get SQL + results + an insight.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent = None


def get_agent() -> SQLAgent:
    global _agent
    if _agent is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY is not set on the server.",
            )
        _agent = SQLAgent(db_path=DB_PATH, api_key=api_key)
    return _agent


class QuestionInput(BaseModel):
    question: str


class AnswerOutput(BaseModel):
    question: str
    sql: str
    error: str | None
    columns: list[str] | None
    rows: list[list] | None
    insight: str | None


@app.get("/")
def root():
    return {"message": "Text-to-SQL Agent API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    agent = get_agent()
    return {"schema": agent.schema_desc}


@app.post("/ask", response_model=AnswerOutput)
def ask(payload: QuestionInput):
    agent = get_agent()
    result = agent.ask(payload.question)

    if result["error"]:
        return AnswerOutput(
            question=result["question"],
            sql=result["sql"],
            error=result["error"],
            columns=None,
            rows=None,
            insight=None,
        )

    df = result["data"]
    return AnswerOutput(
        question=result["question"],
        sql=result["sql"],
        error=None,
        columns=list(df.columns),
        rows=df.values.tolist(),
        insight=result["insight"],
    )
