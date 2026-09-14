"""
Safety layer: the LLM's output is untrusted input. Before executing any
generated SQL against the database, this module enforces:
  - Only a single SELECT statement (no INSERT/UPDATE/DELETE/DROP/ATTACH/etc.)
  - No multiple statements chained with ';'
  - A hard row limit is injected if the query doesn't already have one
This is the difference between a toy demo and something you could
defend in a system-design interview.
"""
import re
import sqlparse

BLOCKED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create",
    "attach", "detach", "pragma", "replace", "truncate", "vacuum",
    "reindex", "grant", "revoke",
}

MAX_ROWS = 500


class UnsafeQueryError(Exception):
    pass


def validate_and_sanitize(sql: str) -> str:
    sql = sql.strip().rstrip(";")

    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        raise UnsafeQueryError("Only a single SQL statement is allowed.")

    statement = parsed[0]
    stmt_type = statement.get_type()
    if stmt_type != "SELECT":
        raise UnsafeQueryError(f"Only SELECT statements are allowed (got {stmt_type}).")

    lowered = sql.lower()
    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            raise UnsafeQueryError(f"Query contains a disallowed keyword: '{kw}'.")

    # Inject a row cap if none present, to prevent runaway result sets
    if not re.search(r"\blimit\s+\d+", lowered):
        sql = f"{sql}\nLIMIT {MAX_ROWS}"

    return sql
