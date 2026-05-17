# Pushover Web

Pushover Web is a small Flask application that accepts public JSON POST requests, stores them in SQLite, and provides a public browser view with date filtering and deletion tools.

## Features

- Public JSON ingestion endpoint
- SQLite-backed message storage
- HTML viewer with date and date-range filters
- Single-message and bulk delete actions
- Responsive interface with the provided logo

## Requirements

- Python 3.10+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
flask --app app run
```

The app creates the SQLite database automatically in the Flask instance folder on first start.

## Production entrypoint

Use the `wsgi.py` module with a WSGI server such as Waitress or Gunicorn:

```bash
waitress-serve --call wsgi:app
```

## Ingest data

Send a JSON body with `title`, `message`, and `icon` to `POST /api/messages`.

```bash
curl -X POST http://127.0.0.1:5000/api/messages ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Test\",\"message\":\"Hello world\",\"icon\":\"bell\"}"
```

## Viewer

Open `/` in a browser to filter by date and delete entries.

## Pagination and delete protection

- The viewer supports pagination via the `page` and `page_size` query parameters. Example: `/ ?page=2&page_size=20`.
- Delete actions require a server-generated CSRF token included in the page forms to help prevent accidental or forged deletes. The token is generated per-session and automatically added to the page; deleting without the token will return HTTP 403.
