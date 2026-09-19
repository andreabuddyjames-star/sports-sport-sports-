"""Deterministic Elo + Poisson match predictor.

This is still a baseline model, not a betting or production forecasting system. Elo
provides a stable estimate of relative team strength while independent Poisson
scoring rates turn that strength into a score distribution. Replace
``team_rating`` with ratings trained from real historical results before using
this for serious decisions.
"""
from datetime import datetime, timezone
import hashlib
import math


ELO_BASE = 1500.0
ELO_SPREAD = 260.0
ELO_K = 400.0

# Approximate scoring environments. These are intentionally conservative defaults
# and can later be replaced with league-specific averages.
SPORT_CONFIG = {
    "soccer": {
        "home_advantage": 55.0,
        "home_average": 1.50,
        "away_average": 1.15,
        "rating_scale": 420.0,
        "draw_rate": 0.26,
        "max_score": 12,
    },
    "basketball": {
        "home_advantage": 65.0,
        "home_average": 112.0,
        "away_average": 108.0,
        "rating_scale": 520.0,
        "draw_rate": 0.005,
        "max_score": 180,
    },
}


def _config(event):
    return SPORT_CONFIG.get(event, SPORT_CONFIG["soccer"])


def team_rating(name):
    """Return a stable stand-in Elo rating until historical ratings are available."""
    digest = hashlib.sha256(name.strip().lower().encode("utf-8")).digest()
    value = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    return ELO_BASE + (value - 0.5) * 2 * ELO_SPREAD


def elo_probability(home_rating, away_rating, home_advantage):
    """Probability that the home team wins, before accounting for draws."""
    rating_difference = home_rating + home_advantage - away_rating
    return 1.0 / (1.0 + 10 ** (-rating_difference / ELO_K))


def poisson_probability(rate, observed):
    """Probability of observing ``observed`` events from a Poisson process."""
    if rate <= 0:
        return 1.0 if observed == 0 else 0.0
    return math.exp(-rate + observed * math.log(rate) - math.lgamma(observed + 1))


def expected_scores(event, home_rating, away_rating):
    """Convert Elo strength into sport-appropriate expected scores."""
    config = _config(event)
    difference = home_rating - away_rating
    scale = config["rating_scale"]
    home_strength = math.exp(difference / scale)
    away_strength = math.exp(-difference / scale)
    denominator = home_strength + away_strength
    home_share = home_strength / denominator
    away_share = away_strength / denominator
    total = config["home_average"] + config["away_average"]
    return total * home_share, total * away_share


def match_probabilities(event, home_rate, away_rate):
    """Calculate home/draw/away probabilities from independent Poisson scores."""
    max_score = _config(event)["max_score"]
    home_distribution = [poisson_probability(home_rate, score) for score in range(max_score + 1)]
    away_distribution = [poisson_probability(away_rate, score) for score in range(max_score + 1)]

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

    # For basketball, ties at the end of regulation are resolved in overtime;
    # keep the tiny tie probability as a draw-like uncertainty in the API.
    total = home_win + draw + away_win
    return {
        "home": home_win / total,
        "draw": draw / total,
        "away": away_win / total,
    }


def predict_match(event, home_name, away_name):
    config = _config(event)
    home_rating = team_rating(home_name)
    away_rating = team_rating(away_name)
    home_rate, away_rate = expected_scores(event, home_rating, away_rating)
    probabilities = match_probabilities(event, home_rate, away_rate)

    outcome_key = max(probabilities, key=probabilities.get)
    outcome = {"home": home_name, "away": away_name, "draw": "Draw"}[outcome_key]
    projected_home = max(0, round(home_rate))
    projected_away = max(0, round(away_rate))

    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_win_probability": round(probabilities["home"], 3),
        "draw_probability": round(probabilities["draw"], 3),
        "away_win_probability": round(probabilities["away"], 3),
        "projected_score": {"home": projected_home, "away": projected_away},
        "confidence": round(max(probabilities.values()) * 100, 1),
        "outcome": outcome,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model": "deterministic Elo + Poisson predictor",
        "factors": {
            "home_elo": round(home_rating, 1),
            "away_elo": round(away_rating, 1),
            "elo_difference": round(home_rating + config["home_advantage"] - away_rating, 1),
            "expected_home_score": round(home_rate, 2),
            "expected_away_score": round(away_rate, 2),
        },
    }
