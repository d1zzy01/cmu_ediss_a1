FROM python:3.13-slim

WORKDIR /app

COPY services/crm_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/crm_service/app ./app

CMD ["python", "-m", "app.main"]
