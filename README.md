# Sports Predictor

A real-time sports prediction MVP with a Flask API, optional live ESPN scoreboard integration, a React/Vite frontend, SQLite history, and a transparent feature-weighted prediction model.

## Run the API

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

The API runs at `http://localhost:5000`.

## Run the React frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite proxy sends `/api` requests to the Flask API. For another API host, set `VITE_API_URL` before building.

## Real data

`/api/fixtures` uses ESPN's public scoreboard endpoints for soccer and basketball when available. If the provider is unavailable or returns no games, the app uses clearly labeled demo fixtures. This avoids hiding outages and means no API key is required for the starter integration. Add a licensed provider before production use.

## Deployment

### Render API

The included `render.yaml` deploys the Flask API with `gunicorn app:app`. Set `FRONTEND_ORIGIN` to the deployed frontend URL. SQLite is suitable for a demo only; use Postgres or another persistent database for production.

### React hosting

Build the frontend with `npm run build` inside `frontend`, then deploy the `frontend/dist` directory to Vercel or Netlify. Set `VITE_API_URL` to the Render API URL at build time.

### Heroku

The included `Procfile` runs the API. Configure `FRONTEND_ORIGIN`, then deploy the repository with the Heroku Python buildpack. A separate static frontend deployment is recommended.

## Prediction model

The starter model uses deterministic team feature vectors and logistic probability weighting so results are reproducible by team while score projections retain small simulation noise. Replace the generated features in `predictor.py` with historical match data, then validate calibration and accuracy before making real-world decisions. Predictions are informational, not betting advice.
