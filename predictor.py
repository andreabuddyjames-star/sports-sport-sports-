"""Elo + Poisson predictor with live injury and weather adjustments."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os

ELO_BASE = 1500.0
ELO_SPREAD = 260.0
SPORT_CONFIG = {
    "soccer": {"home_advantage": 55.0, "home_average": 1.50, "away_average": 1.15, "rating_scale": 420.0, "draw_rate": 0.26, "draw_blend": 0.20, "max_score": 12},
    "basketball": {"home_advantage": 65.0, "home_average": 112.0, "away_average": 108.0, "rating_scale": 520.0, "draw_rate": 0.005, "draw_blend": 0.0, "max_score": 180},
}
_RATINGS_CACHE = None


def _normalise(value):
    return " ".join(str(value or "").strip().lower().split())


def _load_ratings():
    global _RATINGS_CACHE
    if _RATINGS_CACHE is not None:
        return _RATINGS_CACHE
    _RATINGS_CACHE = {"teams": {}, "leagues": {}}
    path = os.getenv("TEAM_RATINGS_FILE")
    if not path:
        return _RATINGS_CACHE
    try:
        with open(path, encoding="utf-8") as ratings_file:
            payload = json.load(ratings_file)
        _RATINGS_CACHE = {"teams": payload.get("teams", {}), "leagues": payload.get("leagues", {})}
    except (OSError, TypeError, ValueError):
        pass
    return _RATINGS_CACHE


def _config(event, league=None):
    config = dict(SPORT_CONFIG.get(event, SPORT_CONFIG["soccer"]))
    requested = _normalise(league)
    for name, overrides in _load_ratings().get("leagues", {}).items():
        if _normalise(name) == requested and isinstance(overrides, dict):
            config.update({key: value for key, value in overrides.items() if key in config})
    return config


def _fallback_rating(name):
    digest = hashlib.sha256(name.strip().lower().encode("utf-8")).digest()
    return ELO_BASE + (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF - 0.5) * 2 * ELO_SPREAD


def team_rating(name, league=None):
    for team_name, details in _load_ratings().get("teams", {}).items():
        if _normalise(team_name) == _normalise(name):
            if isinstance(details, dict) and isinstance(details.get("rating"), (int, float)):
                return float(details["rating"]), "historical"
            if isinstance(details, (int, float)):
                return float(details), "historical"
    return _fallback_rating(name), "fallback"


def poisson_probability(rate, observed):
    if rate <= 0:
        return 1.0 if observed == 0 else 0.0
    return math.exp(-rate + observed * math.log(rate) - math.lgamma(observed + 1))


def expected_scores(event, home_rating, away_rating, league=None, adjustments=None):
    config = _config(event, league)
    adjustments = adjustments or {}
    strength = math.exp(max(-20.0, min(20.0, (home_rating - away_rating) / config["rating_scale"])))
    home_share = strength / (strength + 1.0)
    total = config["home_average"] + config["away_average"]
    home_rate, away_rate = total * home_share, total * (1.0 - home_share)
    # Injury impact is a percentage of scoring strength; weather is a small
    # scoring dampener, with extreme conditions affecting outdoor soccer most.
    home_rate *= max(0.35, 1.0 - float(adjustments.get("home_injury_penalty", 0)))
    away_rate *= max(0.35, 1.0 - float(adjustments.get("away_injury_penalty", 0)))
    weather_factor = max(0.55, 1.0 - float(adjustments.get("weather_penalty", 0)))
    return home_rate * weather_factor, away_rate * weather_factor


def match_probabilities(event, home_rate, away_rate, league=None):
    config = _config(event, league)
    home_distribution = [poisson_probability(home_rate, score) for score in range(config["max_score"] + 1)]
    away_distribution = [poisson_probability(away_rate, score) for score in range(config["max_score"] + 1)]
    home_win = draw = away_win = 0.0
    for home_score, home_probability in enumerate(home_distribution):
        for away_score, away_probability in enumerate(away_distribution):
            probability = home_probability * away_probability
            if home_score > away_score: home_win += probability
            elif home_score == away_score: draw += probability
            else: away_win += probability
    total = home_win + draw + away_win
    probabilities = {"home": home_win / total, "draw": draw / total, "away": away_win / total}
    if config["draw_blend"] and event == "soccer":
        blended_draw = (1 - config["draw_blend"]) * probabilities["draw"] + config["draw_blend"] * max(0, min(0.8, float(config["draw_rate"])))
        non_draw = probabilities["home"] + probabilities["away"]
        probabilities["home"] = (1 - blended_draw) * probabilities["home"] / non_draw
        probabilities["away"] = (1 - blended_draw) * probabilities["away"] / non_draw
        probabilities["draw"] = blended_draw
    return probabilities


def predict_match(event, home_name, away_name, league=None, live_factors=None):
    live_factors = live_factors or {}
    home_rating, home_source = team_rating(home_name, league)
    away_rating, away_source = team_rating(away_name, league)
    home_rate, away_rate = expected_scores(event, home_rating, away_rating, league, live_factors)
    probabilities = match_probabilities(event, home_rate, away_rate, league)
    outcome_key = max(probabilities, key=probabilities.get)
    return {
        "home_team": home_name, "away_team": away_name,
        "home_win_probability": round(probabilities["home"], 3), "draw_probability": round(probabilities["draw"], 3), "away_win_probability": round(probabilities["away"], 3),
        "projected_score": {"home": max(0, round(home_rate)), "away": max(0, round(away_rate))},
        "confidence": round(max(probabilities.values()) * 100, 1),
        "outcome": {"home": home_name, "away": away_name, "draw": "Draw"}[outcome_key],
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), "model": "Elo + Poisson + live factors",
        "factors": {"home_elo": round(home_rating, 1), "away_elo": round(away_rating, 1), "home_rating_source": home_source, "away_rating_source": away_source, "elo_difference": round(home_rating + _config(event, league)["home_advantage"] - away_rating, 1), "expected_home_score": round(home_rate, 2), "expected_away_score": round(away_rate, 2), "league_prior": league or "sport default", **live_factors},
    }
