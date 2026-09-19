# Sports Predictor

Flask/React sports prediction MVP with ESPN fixtures, structured injury data, weather context, SQLite history, and an explainable Elo + Poisson model.

## Production-safe environment

Copy `.env.example` to `.env` only for local development. Never commit `.env`, provider keys, database files, or deployment secrets. In production, configure the same variables through the hosting provider's secret/environment settings. Keep `FRONTEND_ORIGIN` restricted to the deployed frontend origin; do not use `*` in production.

Provider priority:
- Soccer injuries: API-Football when `API_FOOTBALL_KEY` is set; otherwise ESPN News fallback.
- Weather: WeatherAPI.com when `WEATHER_API_KEY` is set; otherwise Open-Meteo.
- Missing providers produce neutral, explicitly labeled factors.

## Run and validate step-by-step

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Validate the API in this order:

```bash
curl -i http://localhost:5000/api/health
curl -s http://localhost:5000/api/diagnostics
curl -s 'http://localhost:5000/api/fixtures?event=soccer'
curl -s 'http://localhost:5000/api/predict?event=soccer&fixture_id=soc-1'
curl -s 'http://localhost:5000/api/history?event=soccer'
```

Check that health is `200`, diagnostics never exposes secret values, fixtures contain `source` and `refreshed_at`, predictions contain `live_factors` with source/timestamp fields, and history contains the saved prediction. Provider outages should return neutral factors rather than fail the prediction endpoint.

Run tests:

```bash
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Select a fixture and verify the Team availability and Match forecast cards show provider labels, timestamps, team badges, forecast icon/condition, severity, and model impact.
