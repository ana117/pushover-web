from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for, session
import secrets

import storage


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        DATABASE_PATH=os.environ.get(
            "DATABASE_PATH",
            os.path.join(app.instance_path, "pushover_web.sqlite3"),
        ),
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    storage.init_app(app)

    with app.app_context():
        storage.init_db()

    @app.get("/")
    def index():
        start_date, end_date = parse_date_filters()

        try:
            page = int(request.args.get("page", "1"))
        except ValueError:
            page = 1
        page = max(1, page)
        try:
            page_size = int(request.args.get("page_size", "20"))
        except ValueError:
            page_size = 20
        page_size = max(1, min(100, page_size))

        total = storage.count_messages(start_date=start_date, end_date=end_date)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        messages = storage.list_messages(start_date=start_date, end_date=end_date, limit=page_size, offset=offset)

        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(16)

        window = 4
        start_page = max(1, page - window)
        end_page = min(total_pages, page + window)

        display_messages = [
            {
                **dict(message),
                "created_at": format_created_at_for_wib(message["created_at"]),
            }
            for message in messages
        ]

        return render_template(
            "index.html",
            messages=display_messages,
            date_from=start_date.isoformat() if start_date else "",
            date_to=end_date.isoformat() if end_date else "",
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            start_page=start_page,
            end_page=end_page,
            csrf_token=session.get("csrf_token"),
        )

    @app.get("/api/messages")
    def register_message():
        return jsonify({
            "status": "ok",
        })

    @app.post("/api/messages")
    def create_message():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            print("Invalid JSON payload:", request.data)
            return jsonify({"error": "Request body must be valid JSON."}), 400

        try:
            title = normalize_text(payload.get("title"), "title")
            message = normalize_text(payload.get("message"), "message")
            icon = payload.get("icon")
        except ValueError as error:
            print("Validation error:", str(error))
            return jsonify({"error": str(error)}), 400

        message_id, created_at = storage.insert_message(title=title, message=message, icon=icon)
        return (
            jsonify(
                {
                    "id": message_id,
                    "title": title,
                    "message": message,
                    "icon": icon,
                    "created_at": created_at.replace(" ", "T") + "Z",
                }
            ),
            201,
        )

    @app.post("/messages/<int:message_id>/delete")
    def remove_message(message_id: int):
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            abort(403)

        deleted = storage.delete_message(message_id)
        if deleted == 0:
            abort(404)
        return redirect(url_for("index"))

    @app.post("/messages/delete")
    def remove_selected_messages():
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            abort(403)

        raw_ids = request.form.getlist("message_ids")
        message_ids: list[int] = []
        for raw_id in raw_ids:
            try:
                message_ids.append(int(raw_id))
            except ValueError:
                continue

        if message_ids:
            storage.delete_messages(message_ids)
        return redirect(url_for("index"))

    return app


def normalize_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise_value_error(field_name)
    cleaned = value.strip()
    if not cleaned:
        raise_value_error(field_name)
    return cleaned


def raise_value_error(field_name: str) -> None:
    raise ValueError(f"Field '{field_name}' is required and must be a non-empty string.")


def parse_date_filters() -> tuple[date | None, date | None]:
    raw_from = request.args.get("date_from", "").strip()
    raw_to = request.args.get("date_to", "").strip()

    start_date = parse_optional_date(raw_from, "date_from")
    end_date = parse_optional_date(raw_to, "date_to")

    if start_date and end_date and start_date > end_date:
        abort(400, description="date_from cannot be after date_to.")

    return start_date, end_date


def parse_optional_date(value: str, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        abort(400, description=f"{field_name} must be a valid date in YYYY-MM-DD format.")


def format_created_at_for_wib(created_at: str) -> str:
    try:
        utc_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return created_at

    wib_timezone = timezone(timedelta(hours=7))
    return utc_dt.astimezone(wib_timezone).strftime("%Y-%m-%d %H:%M:%S")


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
