# Assignment 1 Bookstore Service

FastAPI service implementing the assignment endpoints for books, customers, and health monitoring.

## Requirements

- Python 3.11+
- A MySQL database for submission or grading
- Optional Gemini API key for background book summaries

## Configuration

Use environment variables:

- `DATABASE_URL`: SQLAlchemy connection string. Example:
  - `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME`
- `GEMINI_API_KEY`: optional Google AI Studio API key
- `GEMINI_MODEL`: optional, defaults to `gemini-1.5-flash`

If `DATABASE_URL` is omitted, the app falls back to local SQLite for development only.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t a1-bookstore-service .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL='mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME' \
  -e GEMINI_API_KEY='your-key' \
  a1-bookstore-service
```

## Notes

- Database tables are created automatically at startup.
- `POST /books` stores the book immediately, then generates the summary in a background task to keep request latency low.
- The `summary` field is returned only from the `GET /books/...` endpoints.
