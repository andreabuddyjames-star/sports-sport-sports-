"""External live-data providers with normalized, safe application payloads."""
from datetime import datetime, timezone
import os
import requests


def now():
    return datetime.now(timezone.utc).isoformat()


def _get_json(url, **kwargs):
    response = requests.get(url, timeout=float(os.getenv("API_TIMEOUT_SECONDS", "8")), **kwargs)
    response.raise_for_status()
    return response.json()


def provider_status():
    return {
        "injuries": {"provider": "API-Football" if os.getenv("API_FOOTBALL_KEY") else "ESPN News fallback", "configured": bool(os.getenv("API_FOOTBALL_KEY"))},
        "weather": {"provider": "WeatherAPI.com" if os.getenv("WEATHER_API_KEY") else "Open-Meteo", "configured": bool(os.getenv("WEATHER_API_KEY"))},
    }


def injuries_for(event, home, away):
    reports = {home: [], away: []}
    source = "API-Football" if os.getenv("API_FOOTBALL_KEY") and event == "soccer" else "ESPN News fallback"
    try:
        if os.getenv("API_FOOTBALL_KEY") and event == "soccer":
            base = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io").rstrip("/")
            payload = _get_json(f"{base}/injuries", headers={"x-apisports-key": os.environ["API_FOOTBALL_KEY"]}, params={"league": os.getenv("API_FOOTBALL_LEAGUE_ID", "39"), "season": os.getenv("API_FOOTBALL_SEASON", "2025")})
            for item in payload.get("response", []):
                team = item.get("team", {}).get("name", "")
                target = next((name for name in reports if team and (name.lower() in team.lower() or team.lower() in name.lower())), None)
                if target:
                    player = item.get("player", {})
                    reports[target].append({"headline": f"{player.get('name', 'Player')}: {player.get('reason') or 'Unavailable'}", "status": player.get("reason") or "Unavailable", "source": source, "published": now()})
        else:
            endpoint = os.getenv("ESPN_SOCCER_NEWS_URL" if event == "soccer" else "ESPN_BASKETBALL_NEWS_URL", "")
            if endpoint:
                payload = _get_json(endpoint)
                keywords = ("injur", "out", "sidelined", "doubt", "illness", "surgery", "suspension")
                for article in payload.get("articles", []):
                    text = f"{article.get('headline', '')} {article.get('description', '')}".lower()
                    if any(word in text for word in keywords):
                        for team in reports:
                            if team.lower() in text:
                                reports[team].append({"headline": article.get("headline", "Availability report"), "url": article.get("links", {}).get("web", {}).get("href"), "source": source, "published": article.get("published")})
    except (requests.RequestException, ValueError, KeyError, TypeError):
        source = "Injury provider unavailable"
    return {"injuries": reports, "home_injury_penalty": min(0.24, len(reports[home]) * 0.04), "away_injury_penalty": min(0.24, len(reports[away]) * 0.04), "news_checked_at": now(), "news_source": source}


def weather_for(fixture):
    checked = now()
    try:
        venue = fixture.get("venue", "")
        if os.getenv("WEATHER_API_KEY"):
            payload = _get_json(os.getenv("WEATHER_API_URL", "https://api.weatherapi.com/v1/current.json"), params={"key": os.environ["WEATHER_API_KEY"], "q": venue, "aqi": "no"})
            location, current = payload["location"], payload["current"]
            weather = {"temperature": current.get("temp_c"), "feels_like": current.get("feelslike_c"), "precipitation": current.get("precip_mm"), "wind_speed": current.get("wind_kph"), "condition": current.get("condition", {}).get("text"), "location": location.get("name"), "icon": current.get("condition", {}).get("icon")}
            source = "WeatherAPI.com"
        else:
            geo = _get_json(os.getenv("WEATHER_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"), params={"name": venue, "count": 1, "format": "json"}).get("results", [])
            if not geo: raise ValueError("venue not found")
            location = geo[0]
            current = _get_json(os.getenv("WEATHER_FORECAST_URL", "https://api.open-meteo.com/v1/forecast"), params={"latitude": location["latitude"], "longitude": location["longitude"], "current": "temperature_2m,precipitation,wind_speed_10m,weather_code", "timezone": "UTC"}).get("current", {})
            weather = {"temperature": current.get("temperature_2m"), "feels_like": None, "precipitation": current.get("precipitation"), "wind_speed": current.get("wind_speed_10m"), "condition": f"Weather code {current.get('weather_code', '—')}", "location": location.get("name"), "icon": None}
            source = "Open-Meteo"
        wind, rain = float(weather.get("wind_speed") or 0), float(weather.get("precipitation") or 0)
        penalty = min(0.16, max(0, (wind - 25) / 180) + min(0.08, rain / 40))
        severity = "high" if penalty >= 0.10 else "moderate" if penalty >= 0.04 else "low"
        return {"weather": weather, "weather_penalty": penalty, "weather_severity": severity, "weather_checked_at": checked, "weather_source": source}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"weather": None, "weather_penalty": 0, "weather_severity": "unknown", "weather_checked_at": checked, "weather_source": "Weather provider unavailable"}


def live_factors(event, fixture):
    factors = injuries_for(event, fixture["home"], fixture["away"])
    if event == "soccer" and fixture.get("venue"):
        factors.update(weather_for(fixture))
    else:
        factors.update({"weather": None, "weather_penalty": 0, "weather_severity": "not-applicable", "weather_checked_at": now(), "weather_source": "not applicable"})
    return factors
