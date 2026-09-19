from flask import Flask, render_template, jsonify, request
import random
from datetime import datetime

app = Flask(__name__)

EVENT_CONFIG = {
    "soccer": {
        "label": "Soccer",
        "teams": [
            {"name": "Lions", "attack": 1.18, "defense": 0.98, "momentum": 0.82},
            {"name": "Rockets", "attack": 1.10, "defense": 1.04, "momentum": 0.73},
            {"name": "Falcons", "attack": 1.25, "defense": 0.90, "momentum": 0.88},
            {"name": "Sharks", "attack": 0.96, "defense": 1.12, "momentum": 0.71},
            {"name": "Titans", "attack": 1.06, "defense": 1.06, "momentum": 0.76},
            {"name": "Bears", "attack": 0.99, "defense": 1.16, "momentum": 0.70},
        ],
    },
    "basketball": {
        "label": "Basketball",
        "teams": [
            {"name": "Storm", "attack": 1.28, "defense": 0.95, "momentum": 0.86},
            {"name": "Hawks", "attack": 1.17, "defense": 1.03, "momentum": 0.79},
            {"name": "Knights", "attack": 1.22, "defense": 0.99, "momentum": 0.81},
            {"name": "Wave", "attack": 1.09, "defense": 1.12, "momentum": 0.74},
            {"name": "Blazers", "attack": 1.14, "defense": 1.05, "momentum": 0.77},
            {"name": "Celtics", "attack": 1.20, "defense": 1.00, "momentum": 0.80},
        ],
    },
    "tennis": {
        "label": "Tennis",
        "teams": [
            {"name": "A. Wright", "attack": 1.30, "defense": 1.05, "momentum": 0.87},
            {"name": "M. Ross", "attack": 1.24, "defense": 1.08, "momentum": 0.83},
            {"name": "D. Patel", "attack": 1.18, "defense": 1.12, "momentum": 0.78},
            {"name": "N. Silva", "attack": 1.16, "defense": 1.11, "momentum": 0.75},
            {"name": "C. Nguyen", "attack": 1.21, "defense": 1.09, "momentum": 0.81},
            {"name": "L. Brooks", "attack": 1.14, "defense": 1.15, "momentum": 0.74},
        ],
    },
}


def select_teams(event_name):
    event = EVENT_CONFIG.get(event_name, EVENT_CONFIG["soccer"])
    teams = event["teams"]
    home_team = random.choice(teams)
    away_team = random.choice([t for t in teams if t["name"] != home_team["name"]])
    return home_team, away_team


def compute_prediction(home_team, away_team):
    home_advantage = 0.18
    home_attack = home_team["attack"] * (1 + home_team["momentum"] * 0.25)
    away_attack = away_team["attack"] * (1 + away_team["momentum"] * 0.25)
    home_defense = home_team["defense"]
    away_defense = away_team["defense"]

    home_expected = max(0.4, (home_attack * 1.2) + home_advantage - (away_defense * 0.8))
    away_expected = max(0.3, (away_attack * 1.1) - (home_defense * 0.7))

    home_win = max(0.05, min(0.75, (home_expected / (home_expected + away_expected + 0.5))))
    away_win = max(0.05, min(0.75, (away_expected / (home_expected + away_expected + 0.5))))
    draw = max(0.08, 1 - home_win - away_win)

    home_win = round(home_win, 3)
    draw = round(draw, 3)
    away_win = round(away_win, 3)

    home_score = max(0, round(home_expected + random.uniform(-0.8, 1.2)))
    away_score = max(0, round(away_expected + random.uniform(-0.8, 1.2)))

    if home_score == away_score:
        outcome = "Draw"
    elif home_score > away_score:
        outcome = home_team["name"]
    else:
        outcome = away_team["name"]

    return {
        "home_team": home_team["name"],
        "away_team": away_team["name"],
        "home_win_probability": home_win,
        "draw_probability": draw,
        "away_win_probability": away_win,
        "projected_score": {"home": home_score, "away": away_score},
        "confidence": round(max(home_win, draw, away_win) * 100, 1),
        "outcome": outcome,
        "updated_at": datetime.utcnow().strftime("%H:%M:%S UTC"),
        "factors": {
            "home_attack": round(home_attack, 2),
            "away_attack": round(away_attack, 2),
            "home_defense": round(home_defense, 2),
            "away_defense": round(away_defense, 2),
            "momentum": round((home_team["momentum"] + away_team["momentum"]) / 2, 2),
        },
    }


@app.route("/")
def index():
    return render_template("index.html", event_types=sorted(EVENT_CONFIG.keys()))


@app.route("/api/predict")
def predict():
    event_name = request.args.get("event", "soccer")
    home_team, away_team = select_teams(event_name)
    result = compute_prediction(home_team, away_team)
    result["event"] = EVENT_CONFIG.get(event_name, EVENT_CONFIG["soccer"])["label"]
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
