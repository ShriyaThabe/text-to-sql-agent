"""
Reads the SQLite schema and formats it into a compact, LLM-friendly
description (tables, columns, types, foreign keys) plus a few sample
rows per table so the model understands the actual data, not just names.
"""
import sqlite3


def get_schema_description(db_path: str, sample_rows: int = 2) -> str:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]

    lines = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()  # cid, name, type, notnull, dflt, pk
        col_desc = ", ".join(f"{c[1]} {c[2]}{' PK' if c[5] else ''}" for c in cols)
        lines.append(f"TABLE {table} ({col_desc})")

        cur.execute(f"PRAGMA foreign_key_list({table})")
        fks = cur.fetchall()
        for fk in fks:
            # fk: id, seq, table, from, to, ...
            lines.append(f"  FK: {table}.{fk[3]} -> {fk[2]}.{fk[4]}")

        if sample_rows > 0:
            try:
                cur.execute(f"SELECT * FROM {table} LIMIT {sample_rows}")
                rows = cur.fetchall()
                col_names = [c[1] for c in cols]
                for row in rows:
                    sample = ", ".join(f"{n}={v}" for n, v in zip(col_names, row))
                    lines.append(f"  e.g. {sample}")
            except Exception:
                pass

    conn.close()
    return "\n".join(lines)


def get_table_names(db_path: str) -> list:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables
