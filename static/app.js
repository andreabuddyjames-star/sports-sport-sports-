const refreshBtn = document.getElementById('refreshBtn');
const homeTeamEl = document.getElementById('homeTeam');
const awayTeamEl = document.getElementById('awayTeam');
const homeScoreEl = document.getElementById('homeScore');
const awayScoreEl = document.getElementById('awayScore');
const confidenceEl = document.getElementById('confidence');
const homeWinEl = document.getElementById('homeWin');
const drawProbEl = document.getElementById('drawProb');
const awayWinEl = document.getElementById('awayWin');
const outcomeEl = document.getElementById('outcome');

async function fetchPrediction() {
  const response = await fetch('/api/predict');
  const data = await response.json();

  homeTeamEl.textContent = data.home_team;
  awayTeamEl.textContent = data.away_team;
  homeScoreEl.textContent = data.projected_score.home;
  awayScoreEl.textContent = data.projected_score.away;
  confidenceEl.textContent = `${data.confidence}%`;
  homeWinEl.textContent = `${(data.home_win_probability * 100).toFixed(1)}%`;
  drawProbEl.textContent = `${(data.draw_probability * 100).toFixed(1)}%`;
  awayWinEl.textContent = `${(data.away_win_probability * 100).toFixed(1)}%`;
  outcomeEl.textContent = `${data.outcome} expected to win`;
}

refreshBtn.addEventListener('click', fetchPrediction);
fetchPrediction();
setInterval(fetchPrediction, 4000);
