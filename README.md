# Plane Tracker App

A starter app for tracking aircraft using secure sources such as OpenSky Network.

## What this project includes

- `lilhelper.py` — Flask app with a simple web UI and JSON API
- `requirements.txt` — required Python dependencies
- `.env.example` — environment variables for secure API credentials
- `.gitignore` — ignores local secrets and Python cache files

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file from `.env.example` and add your commercial API credentials.

3. Start the app:

```bash
python lilhelper.py
```

4. Open `http://localhost:5000` in a browser.

## Usage

- `/` — simple web form to query aircraft
- `/api/aircraft` — JSON endpoint for aircraft data

Query parameters:
- `icao24` — filter by ICAO address
- `lamin`, `lamax`, `lomin`, `lomax` — search by latitude/longitude bounding box

## Secure / Commercial sources

This starter app is designed to work with an API provider that supports secure credentials.

- OpenSky Network is a good development source.
- For commercial use, obtain a licensed data source or paid API contract.
- Store credentials in environment variables instead of committing them to Git.

## Example `.env`

```bash
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
```

## Notes

- If you need a higher-grade commercial feed, swap the `fetch_aircraft` implementation in `lilhelper.py` for a paid provider.
- Always verify the data provider license for your commercial use case.

## Map visualization & Providers

- The web UI now includes a live map (Leaflet + OpenStreetMap) at `/` which displays aircraft returned by the API.
- Switch data sources using the `DATA_PROVIDER` environment variable (default: `opensky`).
- To use a commercial provider, set `DATA_PROVIDER=paid` and provide `PAID_API_URL` and `PAID_API_KEY` in your `.env`.

Example `.env` additions:

```bash
PAID_API_URL=https://api.your-paid-provider.example/aircraft
PAID_API_KEY=your_api_key_here
DATA_PROVIDER=paid
```

## Deployment (Docker + Gunicorn)

This project includes a `Dockerfile` and `docker-compose.yml` for running the app in production using `gunicorn`.

Build and run locally with Docker Compose:

```bash
docker compose build
docker compose up
```

The app will be available at `http://localhost:5000` (docker-compose maps container port 8000 to host port 5000).

Environment variables (in `.env`) are forwarded into the container by docker-compose; set `DATA_PROVIDER`, `OPENSKY_USERNAME`/`OPENSKY_PASSWORD`, or `PAID_API_URL`/`PAID_API_KEY` as needed.

Gunicorn config is in `gunicorn_config.py`.
