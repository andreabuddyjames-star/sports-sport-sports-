import pytest
from predictor import expected_scores, predict_match


def test_injury_penalty_reduces_only_affected_team_rate():
    baseline = expected_scores("soccer", 1550, 1500)
    injured = expected_scores("soccer", 1550, 1500, adjustments={"home_injury_penalty": 0.20})
    assert injured[0] < baseline[0]
    assert injured[1] == pytest.approx(baseline[1])


def test_weather_penalty_reduces_both_soccer_rates():
    baseline = expected_scores("soccer", 1550, 1500)
    storm = expected_scores("soccer", 1550, 1500, adjustments={"weather_penalty": 0.15})
    assert storm[0] < baseline[0] and storm[1] < baseline[1]


def test_weather_is_ignored_for_basketball():
    assert expected_scores("basketball", 1550, 1500, adjustments={"weather_penalty": 0.20}) == pytest.approx(expected_scores("basketball", 1550, 1500))


def test_provider_values_are_bounded():
    baseline = expected_scores("soccer", 1550, 1500)
    extreme = expected_scores("soccer", 1550, 1500, adjustments={"home_injury_penalty": 99, "away_injury_penalty": 99, "weather_penalty": 99})
    assert extreme[0] >= baseline[0] * 0.385 and extreme[1] >= baseline[1] * 0.385


def test_prediction_exposes_live_factor_inputs():
    result = predict_match("soccer", "Home", "Away", live_factors={"weather_source": "test", "home_injury_penalty": 0.1})
    assert result["factors"]["live_factor_inputs"]["weather_source"] == "test"
