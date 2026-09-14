"""
Core text-to-SQL agent.
Two LLM calls:
  1. question + schema -> SQL query
  2. question + result table -> plain-English insight
Uses Groq's free API tier (Llama 3.1) — no credit card required, generous
free rate limits, fast inference. OpenAI-compatible chat interface under
the hood, so swapping providers later is a small change if you ever want to.
"""
import os
import sqlite3
import pandas as pd
from groq import Groq
from agent.schema import get_schema_description
from agent.sql_guard import validate_and_sanitize, UnsafeQueryError

# llama-3.1-8b-instant: fast, generous free-tier limits, good enough for
# schema-grounded SQL generation with a well-specified prompt.
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

SQL_SYSTEM_PROMPT = """You are a senior data analyst who writes precise SQLite queries.
Given a database schema and a business question, output ONLY a single valid
SQLite SELECT query that answers the question. Rules:
- Output raw SQL only. No markdown fences, no explanation, no comments.
- Use only tables/columns that exist in the schema provided.
- Prefer explicit JOINs with clear ON conditions.
- Never write anything other than a SELECT statement.
- If the question is ambiguous, make the most reasonable analytical assumption.
"""

INSIGHT_SYSTEM_PROMPT = """You are a data analyst summarizing a query result for
a business stakeholder. Given the original question and the resulting data
(as a small table), write a 2-3 sentence plain-English insight. Be specific
with numbers. No preamble, no "Based on the data" filler — just the insight.
"""


class SQLAgent:
    def __init__(self, db_path: str, api_key: str | None = None):
        self.db_path = db_path
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        self.schema_desc = get_schema_description(db_path)

    def generate_sql(self, question: str) -> str:
        resp = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=400,
            temperature=0,
            messages=[
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"SCHEMA:\n{self.schema_desc}\n\nQUESTION: {question}\n\nSQL:",
                },
            ],
        )
        raw_sql = resp.choices[0].message.content.strip()
        # Strip accidental markdown fences if the model adds them anyway
        raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
        return raw_sql

    def execute_sql(self, sql: str) -> pd.DataFrame:
        safe_sql = validate_and_sanitize(sql)
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query(safe_sql, conn)
        finally:
            conn.close()
        return df, safe_sql

    def summarize(self, question: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "The query returned no results for this question."
        table_preview = df.head(20).to_string(index=False)
        resp = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=200,
            temperature=0.3,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"QUESTION: {question}\n\nRESULT:\n{table_preview}",
                },
            ],
        )
        return resp.choices[0].message.content.strip()

    def ask(self, question: str) -> dict:
        sql = self.generate_sql(question)
        try:
            df, safe_sql = self.execute_sql(sql)
        except UnsafeQueryError as e:
            return {
                "question": question,
                "sql": sql,
                "error": str(e),
                "data": None,
                "insight": None,
            }
        except Exception as e:
            return {
                "question": question,
                "sql": sql,
                "error": f"Query execution failed: {e}",
                "data": None,
                "insight": None,
            }

        insight = self.summarize(question, df)
        return {
            "question": question,
            "sql": safe_sql,
            "error": None,
            "data": df,
            "insight": insight,
        }
