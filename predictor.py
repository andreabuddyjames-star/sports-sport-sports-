"""Elo + Poisson match predictor with optional historical ratings.

The model accepts an optional JSON ratings file through ``TEAM_RATINGS_FILE``.
The file can contain actual ratings and league-specific scoring priors, for example:

{
  "teams": {"Arsenal": {"rating": 1740}},
  "leagues": {"Premier League": {"home_average": 1.52, "away_average": 1.18}}
}

Without that file the app remains fully runnable and uses deterministic stand-in
ratings. Those fallback ratings are useful for demos only, not for real decisions.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os


ELO_BASE = 1500.0
ELO_SPREAD = 260.0
ELO_K = 400.0

SPORT_CONFIG = {
    "soccer": {
        "home_advantage": 55.0,
        "home_average": 1.50,
        "away_average": 1.15,
        "rating_scale": 420.0,
        "draw_rate": 0.26,
        "draw_blend": 0.20,
        "max_score": 12,
    },
    "basketball": {
        "home_advantage": 65.0,
        "home_average": 112.0,
        "away_average": 108.0,
        "rating_scale": 520.0,
        "draw_rate": 0.005,
        "draw_blend": 0.0,
        "max_score": 180,
    },
}

_RATINGS_CACHE = None


def _normalise(value):
    return " ".join(str(value or "").strip().lower().split())


def _load_ratings():
    global _RATINGS_CACHE
    path = os.getenv("TEAM_RATINGS_FILE")
    if _RATINGS_CACHE is not None:
        return _RATINGS_CACHE
    _RATINGS_CACHE = {"teams": {}, "leagues": {}}
    if not path:
        return _RATINGS_CACHE
    try:
        with open(path, encoding="utf-8") as ratings_file:
            payload = json.load(ratings_file)
        _RATINGS_CACHE = {
            "teams": payload.get("teams", {}),
            "leagues": payload.get("leagues", {}),
        }
    except (OSError, TypeError, ValueError):
        pass
    return _RATINGS_CACHE


def _config(event, league=None):
    config = dict(SPORT_CONFIG.get(event, SPORT_CONFIG["soccer"]))
    leagues = _load_ratings().get("leagues", {})
    requested = _normalise(league)
    for name, overrides in leagues.items():
        if _normalise(name) == requested and isinstance(overrides, dict):
            config.update({key: value for key, value in overrides.items() if key in config})
            break
    return config


def _fallback_rating(name):
    digest = hashlib.sha256(name.strip().lower().encode("utf-8")).digest()
    value = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    return ELO_BASE + (value - 0.5) * 2 * ELO_SPREAD


def team_rating(name, league=None):
    """Return a historical rating when configured, otherwise a stable demo rating."""
    teams = _load_ratings().get("teams", {})
    for team_name, details in teams.items():
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


def expected_scores(event, home_rating, away_rating, league=None):
    config = _config(event, league)
    difference = home_rating - away_rating
    strength = math.exp(max(-20.0, min(20.0, difference / config["rating_scale"])))
    home_share = strength / (strength + 1.0)
    total = config["home_average"] + config["away_average"]
    return total * home_share, total * (1.0 - home_share)


def match_probabilities(event, home_rate, away_rate, league=None):
    config = _config(event, league)
    maximum = config["max_score"]
    home_distribution = [poisson_probability(home_rate, score) for score in range(maximum + 1)]
    away_distribution = [poisson_probability(away_rate, score) for score in range(maximum + 1)]
    home_win = draw = away_win = 0.0
    for home_score, home_probability in enumerate(home_distribution):
        for away_score, away_probability in enumerate(away_distribution):
            probability = home_probability * away_probability
            if home_score > away_score:
                home_win += probability
            elif home_score == away_score:
                draw += probability
            else:
                away_win += probability

    total = home_win + draw + away_win
    probabilities = {
        "home": home_win / total,
        "draw": draw / total,
        "away": away_win / total,
    }
    if config["draw_blend"] and event == "soccer":
        target_draw = max(0.0, min(0.8, float(config["draw_rate"])))
        blended_draw = (1 - config["draw_blend"]) * probabilities["draw"] + config["draw_blend"] * target_draw
        non_draw = probabilities["home"] + probabilities["away"]
        probabilities["home"] = (1 - blended_draw) * probabilities["home"] / non_draw
        probabilities["away"] = (1 - blended_draw) * probabilities["away"] / non_draw
        probabilities["draw"] = blended_draw
    return probabilities


def predict_match(event, home_name, away_name, league=None):
    config = _config(event, league)
    home_rating, home_source = team_rating(home_name, league)
    away_rating, away_source = team_rating(away_name, league)
    home_rate, away_rate = expected_scores(event, home_rating, away_rating, league)
    probabilities = match_probabilities(event, home_rate, away_rate, league)
    outcome_key = max(probabilities, key=probabilities.get)
    outcome = {"home": home_name, "away": away_name, "draw": "Draw"}[outcome_key]

    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_win_probability": round(probabilities["home"], 3),
        "draw_probability": round(probabilities["draw"], 3),
        "away_win_probability": round(probabilities["away"], 3),
        "projected_score": {"home": max(0, round(home_rate)), "away": max(0, round(away_rate))},
        "confidence": round(max(probabilities.values()) * 100, 1),
        "outcome": outcome,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model": "Elo + Poisson predictor",
        "factors": {
            "home_elo": round(home_rating, 1),
            "away_elo": round(away_rating, 1),
            "home_rating_source": home_source,
            "away_rating_source": away_source,
            "elo_difference": round(home_rating + config["home_advantage"] - away_rating, 1),
            "expected_home_score": round(home_rate, 2),
            "expected_away_score": round(away_rate, 2),
            "league_prior": league or "sport default",
        },
    }
