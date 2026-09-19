# Sports Predictor

A Flask/React sports prediction MVP with ESPN fixtures, live injury/news context, Open-Meteo weather data for soccer venues, SQLite prediction history, and an explainable Elo + Poisson model.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

The API runs at `http://localhost:5000`. In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Live data and model adjustments

- `/api/fixtures` refreshes ESPN scoreboard fixtures and returns `refreshed_at`, venue, status, and start time.
- `/api/predict` fetches recent ESPN news and flags conservative injury/suspension headlines for either team. It also queries Open-Meteo geocoding and current conditions for soccer venues when ESPN supplies a venue.
- News and weather payloads include provider source labels and UTC timestamps. Unavailable providers produce clearly labeled neutral factors rather than fabricated data.
- Injury headlines apply a capped scoring-strength penalty per team; high wind/precipitation applies a capped scoring dampener. These are transparent heuristics, not medical or betting advice.
- Predictions persist `live_factors`, `factors_updated_at`, and `factors_sources` in SQLite. Existing databases are migrated automatically.
- A background refresh thread refreshes fixtures every five minutes by default. Configure `FIXTURE_REFRESH_SECONDS` and `ENABLE_BACKGROUND_REFRESH`; `/api/fixtures` and `/api/predict` also refresh on demand.

For production, use a persistent database and replace the demo/news heuristic with a licensed structured injury feed. Do not treat missing or unverified reports as confirmed injuries.

## Deployment

`render.yaml` uses `pip install -r requirements.txt` and `gunicorn app:app`. Set `FRONTEND_ORIGIN` and use persistent storage/database for production.
