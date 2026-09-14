"""
Text-to-SQL Analytics Agent — Streamlit Frontend
Run: streamlit run app/streamlit_app.py
"""
import streamlit as st
import requests
import os
import pandas as pd

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="SQL Analytics Agent", page_icon="🗃️", layout="centered")

st.title("🗃️ Ask Your Database")
st.caption(
    "A text-to-SQL agent over a real relational database (digital music "
    "store: customers, invoices, tracks, artists). Ask a business "
    "question in plain English — it writes the SQL, runs it safely, "
    "and summarizes the result."
)

with st.sidebar:
    st.header("How it works")
    st.write(
        "1. LLM generates SQL from your question + live schema\n"
        "2. A guardrail layer blocks anything that isn't a read-only "
        "SELECT (no DROP/DELETE/UPDATE, no chained statements)\n"
        "3. Query runs against SQLite\n"
        "4. LLM summarizes the result table into a plain-English insight"
    )
    st.header("Try asking")
    st.code("Which 5 countries generate the most revenue?")
    st.code("Who are the top 3 best-selling artists by total sales?")
    st.code("What's the average invoice total by year?")
    st.code("Which genre has the most tracks?")

question = st.text_input(
    "Your question",
    placeholder="e.g. Which country's customers spend the most on average?",
)

if st.button("Ask", type="primary", use_container_width=True) and question:
    with st.spinner("Generating SQL, running query, summarizing..."):
        try:
            resp = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            st.markdown("---")

            with st.expander("Generated SQL", expanded=False):
                st.code(result["sql"], language="sql")

            if result["error"]:
                st.error(result["error"])
            else:
                df = pd.DataFrame(result["rows"], columns=result["columns"])
                st.subheader("💡 Insight")
                st.write(result["insight"])

                st.subheader("Data")
                st.dataframe(df, use_container_width=True)

                # Auto-chart if there's one categorical + one numeric column
                if df.shape[1] == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                    st.bar_chart(df.set_index(df.columns[0]))

        except Exception as e:
            st.error(f"Request failed: {e}")
