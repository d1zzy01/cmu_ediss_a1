# Assignment 1 Bookstore Microservices

FastAPI services split into backend book and customer services, plus two BFF services for mobile and web clients.

## Requirements

- Python 3.11+
- A MySQL database for submission or grading
- Optional Gemini API key for book summaries

## Configuration

Use environment variables per service:

- `DATABASE_URL`: SQLAlchemy connection string. Example:
  - `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME`
- `GEMINI_API_KEY`: optional Google AI Studio API key for the book service
- `GEMINI_MODEL`: optional, defaults to `gemini-3-flash-preview`
- `BOOK_SERVICE_URL`: upstream URL used by the BFFs, defaults to `http://book-service:8001`
- `CUSTOMER_SERVICE_URL`: upstream URL used by the BFFs, defaults to `http://customer-service:8002`

If `DATABASE_URL` is omitted, each service falls back to its own local SQLite database for development only.

## Run Locally

### Book service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn services.book_service.app.main:app --reload --port 8001
```

### Customer service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn services.customer_service.app.main:app --reload --port 8002
```

### Mobile BFF

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn services.mobile_bff.app.main:app --reload --port 9001
```

### Web BFF

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn services.web_bff.app.main:app --reload --port 9002
```

## Docker

### Start both services

```bash
docker compose up --build
```

### Build one service manually

```bash
docker build -f services/book_service/Dockerfile -t book-service .
docker run --rm -p 8001:8001 \
  -e DATABASE_URL='mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME' \
  -e GEMINI_API_KEY='your-key' \
  book-service
```

```bash
docker build -f services/customer_service/Dockerfile -t customer-service .
docker run --rm -p 8002:8002 \
  -e DATABASE_URL='mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME' \
  customer-service
```

## Notes

- Database tables are created automatically at startup.
- Book backend endpoints exist on port `8001`.
- Customer backend endpoints exist on port `8002`.
- Mobile BFF endpoints exist on port `9001`.
- Web BFF endpoints exist on port `9002`.
- Every BFF request requires an `Authorization: Bearer <jwt>` header.
- A BFF token is accepted only when the decoded payload contains `sub` in `starlord|gamora|drax|rocket|groot`, `iss` equal to `cmu.edu`, and a future `exp` value.
- Both BFFs proxy book and customer endpoints and both authenticate every request.
- Only the mobile BFF rewrites responses.
- `GET /books/{isbn}` and `GET /books/isbn/{isbn}` on the mobile BFF replace `"genre": "non-fiction"` with `"genre": 3`.
- `GET /customers/{id}` and `GET /customers?userId=...` on the mobile BFF remove `address`, `address2`, `city`, `state`, and `zipcode`.
- The `summary` field is returned only from the `GET /books/...` endpoints.
