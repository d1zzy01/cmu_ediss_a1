FROM python:3.13-slim

WORKDIR /app

COPY services/web_bff/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/web_bff/app ./app

EXPOSE 9002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9002"]
