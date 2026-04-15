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
- `RECOMMENDATION_SERVICE_URL`: upstream URL used by the book service for related-book lookups, defaults to `http://recommendation-service:8000`
- `RECOMMENDATION_TIMEOUT_SECONDS`: timeout for recommendation lookups, defaults to `3.0`
- `CIRCUIT_BREAKER_STATE_PATH`: file used by the book service to persist related-book circuit breaker state, defaults to `./circuit_breaker_state.json`
- `CIRCUIT_BREAKER_RESET_TIMEOUT_SECONDS`: how long the related-book circuit remains open after a timeout, defaults to `60.0`
- `BOOK_SERVICE_URL`: upstream URL used by the BFFs, defaults to `http://book-service:8001`
- `CUSTOMER_SERVICE_URL`: upstream URL used by the BFFs, defaults to `http://customer-service:8002`
- `KAFKA_BROKERS`: Kafka broker list used by the customer and CRM services, defaults to `98.88.99.206:9092`
- `KAFKA_TOPIC`: topic used for customer registered events, should be `<your-andrew-id>.customer.evt`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SENDER_EMAIL`: SMTP settings used by the CRM service
- `ANDREW_ID`: your Andrew ID, used by the CRM email body and Kafka consumer group naming

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

### CRM service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m services.crm_service.app.main
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

```bash
docker build -f services/crm_service/Dockerfile -t crm-service .
docker run --rm \
  -e KAFKA_BROKERS='98.88.99.206:9092' \
  -e KAFKA_TOPIC='<your-andrew-id>.customer.evt' \
  -e SMTP_HOST='smtp.example.com' \
  -e SMTP_PORT='587' \
  -e SMTP_USERNAME='your-user' \
  -e SMTP_PASSWORD='your-password' \
  -e SENDER_EMAIL='you@example.com' \
  -e ANDREW_ID='<your-andrew-id>' \
  crm-service
```

## Notes

- Database tables are created automatically at startup.
- Book backend endpoints exist on port `8001`.
- Customer backend endpoints exist on port `8002`.
- The customer service publishes a JSON customer-registered event to Kafka after a successful `POST /customers`.
- The CRM service consumes `<your-andrew-id>.customer.evt` and sends the activation email through SMTP.
- Mobile BFF endpoints exist on port `9001`.
- Web BFF endpoints exist on port `9002`.
- Every BFF request requires an `Authorization: Bearer <jwt>` header.
- A BFF token is accepted only when the decoded payload contains `sub` in `starlord|gamora|drax|rocket|groot`, `iss` equal to `cmu.edu`, and a future `exp` value.
- Both BFFs proxy book and customer endpoints and both authenticate every request.
- Only the mobile BFF rewrites responses.
- `GET /books/{isbn}` and `GET /books/isbn/{isbn}` on the mobile BFF replace `"genre": "non-fiction"` with `"genre": 3`.
- `GET /books/{isbn}/related-books` returns related titles from the external recommendation service.
- A successful related-book lookup returns `200` with a list, `204` when no related titles are found, `504` on the first upstream timeout, and `503` while the circuit breaker is open or when the first retry after 60 seconds times out again.
- `GET /customers/{id}` and `GET /customers?userId=...` on the mobile BFF remove `address`, `address2`, `city`, `state`, and `zipcode`.
- The `summary` field is returned only from the `GET /books/...` endpoints.
