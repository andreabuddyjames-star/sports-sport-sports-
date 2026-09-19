from datetime import datetime, timezone
import json
import os
import random
import sqlite3
import threading
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from predictor import predict_match

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(app.root_path, "predictions.db"))
API_TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "8"))
ESPN_ENDPOINTS = {"soccer": os.getenv("ESPN_SOCCER_SCOREBOARD_URL", "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"), "basketball": os.getenv("ESPN_BASKETBALL_SCOREBOARD_URL", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")}
FALLBACK_FIXTURES = {"soccer": [{"id": "soc-1", "home": "Lions", "away": "Falcons", "league": "Demo Premier League"}, {"id": "soc-2", "home": "Rockets", "away": "Titans", "league": "Demo Cup"}], "basketball": [{"id": "bb-1", "home": "Storm", "away": "Celtics", "league": "Demo NBA"}, {"id": "bb-2", "home": "Hawks", "away": "Blazers", "league": "Demo Pacific Cup"}]}
NEWS_ENDPOINTS = {"soccer": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news", "basketball": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news"}


def db_connection():
    connection = sqlite3.connect(DB_PATH); connection.row_factory = sqlite3.Row; return connection


def init_db():
    with db_connection() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, fixture_id TEXT NOT NULL, home_team TEXT NOT NULL, away_team TEXT NOT NULL, outcome TEXT NOT NULL, confidence REAL NOT NULL, created_at TEXT NOT NULL, live_factors TEXT, factors_updated_at TEXT, factors_sources TEXT)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(predictions)")}
        for name in ("live_factors", "factors_updated_at", "factors_sources"):
            if name not in columns: connection.execute(f"ALTER TABLE predictions ADD COLUMN {name} TEXT")


def normalize_event(event): return event if event in {"soccer", "basketball"} else "soccer"


def live_fixtures(event):
    try:
        response = requests.get(ESPN_ENDPOINTS[event], timeout=API_TIMEOUT); response.raise_for_status(); fixtures = []
        for item in response.json().get("events", []):
            competition = (item.get("competitions") or [{}])[0]; competitors = competition.get("competitors", [])
            home = next((x for x in competitors if x.get("homeAway") == "home"), {}); away = next((x for x in competitors if x.get("homeAway") == "away"), {})
            if home.get("team", {}).get("displayName") and away.get("team", {}).get("displayName"):
                fixtures.append({"id": f"espn-{item.get('id')}", "home": home["team"]["displayName"], "away": away["team"]["displayName"], "league": item.get("leagues", [{}])[0].get("name", "Live league"), "status": item.get("status", {}).get("type", {}).get("description", "Scheduled"), "start_time": item.get("date"), "venue": competition.get("venue", {}).get("fullName", ""), "source": "ESPN"})
        if fixtures: return fixtures
    except (requests.RequestException, ValueError, KeyError, TypeError): pass
    return [dict(item, source="demo") for item in FALLBACK_FIXTURES[event]]


def _empty_injuries(home, away, source):
    return {"injuries": {home: [], away: []}, "home_injury_penalty": 0, "away_injury_penalty": 0, "news_checked_at": datetime.now(timezone.utc).isoformat(), "news_source": source}


def _football_injuries(home, away):
    key = os.getenv("API_FOOTBALL_KEY"); base = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io").rstrip("/")
    if not key: return None
    try:
        params = {"league": os.getenv("API_FOOTBALL_LEAGUE_ID", "39"), "season": os.getenv("API_FOOTBALL_SEASON", "2025")}
        response = requests.get(f"{base}/injuries", headers={"x-apisports-key": key}, params=params, timeout=API_TIMEOUT); response.raise_for_status()
        result = response.json().get("response", []); reports = {home: [], away: []}
        for item in result:
            team = item.get("team", {}).get("name", ""); player = item.get("player", {})
            target = next((name for name in reports if name.lower() in team.lower() or team.lower() in name.lower()), None)
            if target:
                reports[target].append({"headline": f"{player.get('name', 'Player')}: {item.get('player', {}).get('reason', 'Unavailable')}", "status": item.get("player", {}).get("reason"), "source": "API-Football", "published": datetime.now(timezone.utc).isoformat()})
        return reports, "API-Football"
    except (requests.RequestException, ValueError, KeyError, TypeError): return None


def _news_factors(event, home, away):
    structured = _football_injuries(home, away) if event == "soccer" else None
    if structured: reports, source = structured
    else:
        reports = {home: [], away: []}; source = "ESPN News fallback"
        try:
            data = requests.get(NEWS_ENDPOINTS[event], timeout=API_TIMEOUT).json(); keywords = ("injur", "out", "sidelined", "doubt", "illness", "surgery", "suspension")
            for article in data.get("articles", []):
                text = (article.get("headline", "") + " " + article.get("description", "")).lower()
                if any(word in text for word in keywords):
                    for team in (home, away):
                        if team.lower() in text: reports[team].append({"headline": article.get("headline", ""), "url": article.get("links", {}).get("web", {}).get("href"), "published": article.get("published"), "source": source})
        except (requests.RequestException, ValueError, AttributeError, TypeError): source = "Injury provider unavailable"
    return {"injuries": reports, "home_injury_penalty": min(0.24, len(reports[home]) * 0.04), "away_injury_penalty": min(0.24, len(reports[away]) * 0.04), "news_checked_at": datetime.now(timezone.utc).isoformat(), "news_source": source}


def _weather_factors(fixture):
    checked = datetime.now(timezone.utc).isoformat(); key = os.getenv("WEATHER_API_KEY"); weather_url = os.getenv("WEATHER_API_URL", "https://api.weatherapi.com/v1/current.json")
    try:
        if key:
            current = requests.get(weather_url, params={"key": key, "q": fixture.get("venue", ""), "aqi": "no"}, timeout=API_TIMEOUT).json()
            location, values = current["location"], current["current"]; source = "WeatherAPI.com"
            weather = {"temperature": values.get("temp_c"), "feels_like": values.get("feelslike_c"), "precipitation": values.get("precip_mm"), "wind_speed": values.get("wind_kph"), "condition": values.get("condition", {}).get("text"), "location": location.get("name")}
        else:
            geo = requests.get(os.getenv("WEATHER_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"), params={"name": fixture.get("venue", ""), "count": 1, "format": "json"}, timeout=API_TIMEOUT).json().get("results", [])
            if not geo: raise ValueError("venue not found")
            location = geo[0]; values = requests.get(os.getenv("WEATHER_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"), params={"latitude": location["latitude"], "longitude": location["longitude"], "current": "temperature_2m,precipitation,wind_speed_10m,weather_code", "timezone": "UTC"}, timeout=API_TIMEOUT).json().get("current", {}); source = "Open-Meteo"
            weather = {"temperature": values.get("temperature_2m"), "feels_like": None, "precipitation": values.get("precipitation"), "wind_speed": values.get("wind_speed_10m"), "condition": f"Code {values.get('weather_code', '—')}", "location": location.get("name")}
        wind, rain = float(weather.get("wind_speed") or 0), float(weather.get("precipitation") or 0); penalty = min(0.16, max(0, (wind - 25) / 180) + min(0.08, rain / 40))
        return {"weather": weather, "weather_penalty": penalty, "weather_checked_at": checked, "weather_source": source}
    except (requests.RequestException, ValueError, KeyError, TypeError): return {"weather": None, "weather_penalty": 0, "weather_checked_at": checked, "weather_source": "Weather provider unavailable"}


def live_factors(event, fixture):
    factors = _news_factors(event, fixture["home"], fixture["away"]); factors.update(_weather_factors(fixture) if event == "soccer" and fixture.get("venue") else {"weather": None, "weather_penalty": 0, "weather_checked_at": datetime.now(timezone.utc).isoformat(), "weather_source": "not applicable"}); return factors


def fixture_by_id(event, fixture_id): return next((fixture for fixture in live_fixtures(event) if fixture["id"] == fixture_id), None)

@app.get("/api/health")
def health(): return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.get("/api/fixtures")
def fixtures():
    event = normalize_event(request.args.get("event", "soccer")); return jsonify({"event": event, "fixtures": live_fixtures(event), "refreshed_at": datetime.now(timezone.utc).isoformat()})

@app.get("/api/predict")
def predict():
    event = normalize_event(request.args.get("event", "soccer")); fixture = fixture_by_id(event, request.args.get("fixture_id")) or random.choice(live_fixtures(event)); factors = live_factors(event, fixture); result = predict_match(event, fixture["home"], fixture["away"], fixture.get("league"), factors); result.update({"event": event, "fixture_id": fixture["id"], "league": fixture["league"], "source": fixture["source"], "live_factors": factors})
    with db_connection() as connection: connection.execute("INSERT INTO predictions (event, fixture_id, home_team, away_team, outcome, confidence, created_at, live_factors, factors_updated_at, factors_sources) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event, fixture["id"], result["home_team"], result["away_team"], result["outcome"], result["confidence"], result["updated_at"], json.dumps(factors), datetime.now(timezone.utc).isoformat(), json.dumps({"news": factors.get("news_source"), "weather": factors.get("weather_source")})))
    return jsonify(result)

@app.get("/api/history")
def history():
    event = normalize_event(request.args.get("event", "soccer"))
    with db_connection() as connection: rows = connection.execute("SELECT * FROM predictions WHERE event = ? ORDER BY id DESC LIMIT 20", (event,)).fetchall()
    return jsonify({"event": event, "history": [dict(row) for row in rows]})


def refresh_cache():
    while True:
        for event in ("soccer", "basketball"): live_fixtures(event)
        time.sleep(max(60, int(os.getenv("FIXTURE_REFRESH_SECONDS", "300"))))

init_db()
if os.getenv("ENABLE_BACKGROUND_REFRESH", "true").lower() == "true": threading.Thread(target=refresh_cache, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
