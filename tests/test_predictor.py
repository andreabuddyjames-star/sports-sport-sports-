import pytest
from predictor import expected_scores, predict_match
from providers import injuries_for, provider_status


def test_injury_penalty_reduces_only_affected_team_rate():
    baseline = expected_scores("soccer", 1550, 1500)
    injured = expected_scores("soccer", 1550, 1500, adjustments={"home_injury_penalty": 0.20})
    assert injured[0] < baseline[0] and injured[1] == pytest.approx(baseline[1])


def test_weather_penalty_reduces_both_soccer_rates():
    baseline = expected_scores("soccer", 1550, 1500)
    storm = expected_scores("soccer", 1550, 1500, adjustments={"weather_penalty": 0.15})
    assert storm[0] < baseline[0] and storm[1] < baseline[1]


def test_weather_is_ignored_for_basketball():
    assert expected_scores("basketball", 1550, 1500, adjustments={"weather_penalty": 0.20}) == pytest.approx(expected_scores("basketball", 1550, 1500))


def test_provider_status_never_contains_secret_values(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "secret")
    status = provider_status()
    assert "secret" not in repr(status)
    assert status["injuries"]["configured"] is True


def test_injury_provider_failure_is_neutral(monkeypatch):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.setenv("ESPN_SOCCER_NEWS_URL", "http://127.0.0.1:1/unavailable")
    result = injuries_for("soccer", "Home", "Away")
    assert result["home_injury_penalty"] == 0
    assert result["away_injury_penalty"] == 0


def test_prediction_exposes_live_factor_inputs():
    result = predict_match("soccer", "Home", "Away", live_factors={"weather_source": "test", "home_injury_penalty": 0.1})
    assert result["factors"]["live_factor_inputs"]["weather_source"] == "test"
