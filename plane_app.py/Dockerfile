FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV FLASK_APP=lilhelper.py
ENV DATA_PROVIDER=opensky

CMD ["gunicorn", "-c", "gunicorn_config.py", "lilhelper:app"]
