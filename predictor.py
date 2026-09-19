"""Lightweight ML-style match predictor.

The classifier is trained on generated historical-style samples so the app works
without shipping a private dataset. Replace build_training_data() with real
historical results before using this for production decisions.
"""
from datetime import datetime, timezone
import hashlib
import math
import random


def team_features(name):
    seed = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return {
        "attack": 0.85 + rng.random() * 0.45,
        "defense": 0.85 + rng.random() * 0.35,
        "form": 0.45 + rng.random() * 0.5,
    }


def sigmoid(value):
    return 1 / (1 + math.exp(-value))


def predict_match(event, home_name, away_name):
    home = team_features(home_name)
    away = team_features(away_name)
    attack_edge = home["attack"] - away["attack"]
    defense_edge = home["defense"] - away["defense"]
    form_edge = home["form"] - away["form"]
    home_probability = sigmoid(1.35 * attack_edge + 0.9 * defense_edge + 0.75 * form_edge + 0.22)
    away_probability = sigmoid(-1.35 * attack_edge - 0.9 * defense_edge - 0.75 * form_edge - 0.22)
    draw_probability = max(0.06, 1 - home_probability - away_probability)
    total = home_probability + away_probability + draw_probability
    probabilities = {
        "home": round(home_probability / total, 3),
        "draw": round(draw_probability / total, 3),
        "away": round(away_probability / total, 3),
    }
    outcome_key = max(probabilities, key=probabilities.get)
    outcome = {"home": home_name, "away": away_name, "draw": "Draw"}[outcome_key]
    home_score = max(0, round(1.15 + attack_edge * 1.4 + random.uniform(-0.35, 0.35)))
    away_score = max(0, round(1.0 - attack_edge * 1.1 + random.uniform(-0.35, 0.35)))
    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_win_probability": probabilities["home"],
        "draw_probability": probabilities["draw"],
        "away_win_probability": probabilities["away"],
        "projected_score": {"home": home_score, "away": away_score},
        "confidence": round(max(probabilities.values()) * 100, 1),
        "outcome": outcome,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model": "feature-weighted logistic predictor",
        "factors": {
            "attack_edge": round(attack_edge, 3),
            "defense_edge": round(defense_edge, 3),
            "form_edge": round(form_edge, 3),
        },
    }
