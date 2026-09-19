from datetime import datetime, timezone
import os
import random
import sqlite3

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from predictor import predict_match

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(app.root_path, "predictions.db"))
API_TIMEOUT = 8

FALLBACK_FIXTURES = {
    "soccer": [
        {"id": "soc-1", "home": "Lions", "away": "Falcons", "league": "Demo Premier League"},
        {"id": "soc-2", "home": "Rockets", "away": "Titans", "league": "Demo Cup"},
        {"id": "soc-3", "home": "Bears", "away": "Sharks", "league": "Demo Championship"},
    ],
    "basketball": [
        {"id": "bb-1", "home": "Storm", "away": "Celtics", "league": "Demo NBA"},
        {"id": "bb-2", "home": "Hawks", "away": "Blazers", "league": "Demo Pacific Cup"},
        {"id": "bb-3", "home": "Knights", "away": "Wave", "league": "Demo Conference"},
    ],
}

ESPN_ENDPOINTS = {
    "soccer": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "basketball": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
}


def db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL, fixture_id TEXT NOT NULL,
                home_team TEXT NOT NULL, away_team TEXT NOT NULL,
                outcome TEXT NOT NULL, confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def normalize_event(event):
    return event if event in {"soccer", "basketball"} else "soccer"


def live_fixtures(event):
    endpoint = ESPN_ENDPOINTS.get(event)
    if endpoint:
        try:
            response = requests.get(endpoint, timeout=API_TIMEOUT)
            response.raise_for_status()
            events = response.json().get("events", [])
            fixtures = []
            for item in events:
                competitions = item.get("competitions", [])
                competition = competitions[0] if competitions else {}
                competitors = competition.get("competitors", [])
                home = next((x for x in competitors if x.get("homeAway") == "home"), {})
                away = next((x for x in competitors if x.get("homeAway") == "away"), {})
                if home.get("team", {}).get("displayName") and away.get("team", {}).get("displayName"):
                    fixtures.append({
                        "id": f"espn-{item.get('id')}",
                        "home": home["team"]["displayName"],
                        "away": away["team"]["displayName"],
                        "league": item.get("leagues", [{}])[0].get("name", "Live league"),
                        "status": item.get("status", {}).get("type", {}).get("description", "Scheduled"),
                        "source": "ESPN",
                    })
            if fixtures:
                return fixtures
        except (requests.RequestException, ValueError, KeyError):
            pass

    return [dict(fixture, source="demo") for fixture in FALLBACK_FIXTURES[event]]


def fixture_by_id(event, fixture_id):
    fixtures = live_fixtures(event)
    return next((fixture for fixture in fixtures if fixture["id"] == fixture_id), None)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.get("/api/fixtures")
def fixtures():
    event = normalize_event(request.args.get("event", "soccer"))
    return jsonify({"event": event, "fixtures": live_fixtures(event)})


@app.get("/api/predict")
def predict():
    event = normalize_event(request.args.get("event", "soccer"))
    fixture_id = request.args.get("fixture_id")
    fixture = fixture_by_id(event, fixture_id) if fixture_id else None
    fixture = fixture or random.choice(live_fixtures(event))
    result = predict_match(event, fixture["home"], fixture["away"])
    result.update({"event": event, "fixture_id": fixture["id"], "league": fixture["league"], "source": fixture["source"]})

    with db_connection() as connection:
        connection.execute(
            "INSERT INTO predictions (event, fixture_id, home_team, away_team, outcome, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event, fixture["id"], result["home_team"], result["away_team"], result["outcome"], result["confidence"], result["updated_at"]),
        )
    return jsonify(result)


@app.get("/api/history")
def history():
    event = normalize_event(request.args.get("event", "soccer"))
    with db_connection() as connection:
        rows = connection.execute("SELECT * FROM predictions WHERE event = ? ORDER BY id DESC LIMIT 20", (event,)).fetchall()
    return jsonify({"event": event, "history": [dict(row) for row in rows]})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
