FROM python:3.13-slim

WORKDIR /app

COPY services/mobile_bff/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/mobile_bff/app ./app

EXPOSE 9001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9001"]
