import sqlite3
from datetime import datetime

DB = "feedback.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo       TEXT    NOT NULL,
    item_type  TEXT    NOT NULL,
    message    TEXT,
    score      REAL,
    accepted   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
)
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(_SCHEMA)


def save_feedback(
    repo: str,
    item_type: str,
    message: str,
    score: float,
    accepted: int,  
) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO feedback (repo, item_type, message, score, accepted, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                repo,
                item_type,
                message or "",
                round(float(score), 6),
                int(accepted),
                datetime.utcnow().isoformat(),
            ),
        )


def load_feedback(limit: int = 200) -> list[dict]:
    with _conn() as conn:
        cur = conn.execute(
            """
            SELECT id, repo, item_type, message, score, accepted, created_at
            FROM feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def feedback_stats() -> dict:
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)                      AS total,
                SUM(accepted)                 AS correct,
                ROUND(AVG(accepted) * 100, 1) AS accuracy_pct,
                ROUND(AVG(score), 4)          AS avg_score
            FROM feedback
            """
        ).fetchone()

    return {
        "total":        row[0] or 0,
        "correct":      row[1] or 0,
        "accuracy_pct": row[2] or 0.0,
        "avg_score":    row[3] or 0.0,
    }