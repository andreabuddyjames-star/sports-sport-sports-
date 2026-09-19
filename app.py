from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)

TEAMS = [
    {"name": "Lions", "attack": 1.10, "defense": 1.00, "momentum": 0.78},
    {"name": "Rockets", "attack": 1.05, "defense": 0.96, "momentum": 0.72},
    {"name": "Falcons", "attack": 1.18, "defense": 0.88, "momentum": 0.85},
    {"name": "Sharks", "attack": 0.94, "defense": 1.08, "momentum": 0.69},
    {"name": "Titans", "attack": 1.02, "defense": 1.04, "momentum": 0.74},
    {"name": "Bears", "attack": 0.97, "defense": 1.12, "momentum": 0.70},
]


def compute_prediction(home_team, away_team):
    home_advantage = 0.18
    home_attack = home_team["attack"] * (1 + home_team["momentum"] * 0.25)
    away_attack = away_team["attack"] * (1 + away_team["momentum"] * 0.25)
    home_defense = home_team["defense"]
    away_defense = away_team["defense"]

    home_expected = max(0.4, (home_attack * 1.2) + home_advantage - (away_defense * 0.8))
    away_expected = max(0.3, (away_attack * 1.1) - (home_defense * 0.7))

    home_win = max(0.05, min(0.8, (home_expected / (home_expected + away_expected + 0.5))))
    away_win = max(0.05, min(0.8, (away_expected / (home_expected + away_expected + 0.5))))
    draw = max(0.08, 1 - home_win - away_win)

    home_win = round(home_win, 3)
    draw = round(draw, 3)
    away_win = round(away_win, 3)

    home_goals = max(0, round(home_expected + random.uniform(-0.8, 1.2)))
    away_goals = max(0, round(away_expected + random.uniform(-0.8, 1.2)))

    if home_goals == away_goals:
        outcome = "Draw"
    elif home_goals > away_goals:
        outcome = home_team["name"]
    else:
        outcome = away_team["name"]

    return {
        "home_team": home_team["name"],
        "away_team": away_team["name"],
        "home_win_probability": home_win,
        "draw_probability": draw,
        "away_win_probability": away_win,
        "projected_score": {"home": home_goals, "away": away_goals},
        "confidence": round(max(home_win, draw, away_win) * 100, 1),
        "outcome": outcome,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/predict")
def predict():
    home_team = random.choice(TEAMS)
    away_team = random.choice([team for team in TEAMS if team["name"] != home_team["name"]])
    result = compute_prediction(home_team, away_team)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
