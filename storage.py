from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from flask import current_app, g

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    icon TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_: Exception | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    connection = get_db()
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create the database tables."""
        init_db()
        print("Initialized the database.")


def insert_message(title: str, message: str, icon: str | None) -> tuple[int, str]:
    connection = get_db()
    # store empty string when icon is not provided
    stored_icon = icon if isinstance(icon, str) and icon is not None else ""
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor = connection.execute(
        """
        INSERT INTO messages (title, message, icon, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (title, message, stored_icon, created_at),
    )
    connection.commit()
    return int(cursor.lastrowid), created_at


def list_messages(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[sqlite3.Row]:
    connection = get_db()
    query = [
        "SELECT id, title, message, icon, created_at",
        "FROM messages",
        "WHERE 1 = 1",
    ]
    parameters: list[str] = []

    if start_date is not None:
        query.append("AND date(created_at) >= date(?)")
        parameters.append(start_date.isoformat())

    if end_date is not None:
        query.append("AND date(created_at) <= date(?)")
        parameters.append(end_date.isoformat())

    valid_sort_by = ["created_at", "title", "id"]
    valid_sort_order = ["asc", "desc"]
    
    sort_by = sort_by.lower() if sort_by in valid_sort_by else "created_at"
    sort_order = sort_order.upper() if sort_order.lower() in valid_sort_order else "DESC"
    
    if sort_by == "created_at":
        query.append(f"ORDER BY datetime(created_at) {sort_order}, id DESC")
    else:
        query.append(f"ORDER BY {sort_by} {sort_order}, id DESC")

    if limit is not None:
        query.append("LIMIT ?")
        parameters.append(str(limit))
        if offset is not None:
            query.append("OFFSET ?")
            parameters.append(str(offset))

    return connection.execute("\n".join(query), parameters).fetchall()


def count_messages(start_date: date | None = None, end_date: date | None = None) -> int:
    connection = get_db()
    query = [
        "SELECT COUNT(1) as cnt",
        "FROM messages",
        "WHERE 1 = 1",
    ]
    parameters: list[str] = []

    if start_date is not None:
        query.append("AND date(created_at) >= date(?)")
        parameters.append(start_date.isoformat())

    if end_date is not None:
        query.append("AND date(created_at) <= date(?)")
        parameters.append(end_date.isoformat())

    row = connection.execute("\n".join(query), parameters).fetchone()
    return int(row["cnt"]) if row is not None else 0


def delete_message(message_id: int) -> int:
    connection = get_db()
    cursor = connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    connection.commit()
    return cursor.rowcount


def delete_messages(message_ids: list[int]) -> int:
    if not message_ids:
        return 0

    connection = get_db()
    placeholders = ", ".join("?" for _ in message_ids)
    cursor = connection.execute(
        f"DELETE FROM messages WHERE id IN ({placeholders})",
        message_ids,
    )
    connection.commit()
    return cursor.rowcount
