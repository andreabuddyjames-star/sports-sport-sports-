const refreshBtn = document.getElementById('refreshBtn');
const eventTypeSelect = document.getElementById('eventType');
const eventTagEl = document.getElementById('eventTag');
const homeTeamEl = document.getElementById('homeTeam');
const awayTeamEl = document.getElementById('awayTeam');
const homeScoreEl = document.getElementById('homeScore');
const awayScoreEl = document.getElementById('awayScore');
const confidenceEl = document.getElementById('confidence');
const homeWinEl = document.getElementById('homeWin');
const drawProbEl = document.getElementById('drawProb');
const awayWinEl = document.getElementById('awayWin');
const outcomeEl = document.getElementById('outcome');
const updatedAtEl = document.getElementById('updatedAt');
const homeAttackEl = document.getElementById('homeAttack');
const awayAttackEl = document.getElementById('awayAttack');
const homeDefenseEl = document.getElementById('homeDefense');
const awayDefenseEl = document.getElementById('awayDefense');
const momentumEl = document.getElementById('momentum');

async function fetchPrediction() {
  const selectedEvent = eventTypeSelect.value || 'soccer';
  const response = await fetch(`/api/predict?event=${selectedEvent}`);
  const data = await response.json();

  eventTagEl.textContent = data.event;
  homeTeamEl.textContent = data.home_team;
  awayTeamEl.textContent = data.away_team;
  homeScoreEl.textContent = data.projected_score.home;
  awayScoreEl.textContent = data.projected_score.away;
  confidenceEl.textContent = `${data.confidence}%`;
  homeWinEl.textContent = `${(data.home_win_probability * 100).toFixed(1)}%`;
  drawProbEl.textContent = `${(data.draw_probability * 100).toFixed(1)}%`;
  awayWinEl.textContent = `${(data.away_win_probability * 100).toFixed(1)}%`;
  outcomeEl.textContent = `${data.outcome} expected to win`;
  updatedAtEl.textContent = `Updated: ${data.updated_at}`;
  homeAttackEl.textContent = data.factors.home_attack;
  awayAttackEl.textContent = data.factors.away_attack;
  homeDefenseEl.textContent = data.factors.home_defense;
  awayDefenseEl.textContent = data.factors.away_defense;
  momentumEl.textContent = data.factors.momentum;
}

refreshBtn.addEventListener('click', fetchPrediction);
eventTypeSelect.addEventListener('change', fetchPrediction);

fetchPrediction();
setInterval(fetchPrediction, 5000);
