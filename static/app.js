<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sports Event Predictor</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
  </head>
  <body>
    <div class="container">
      <header>
        <div>
          <p class="eyebrow">Realtime prediction dashboard</p>
          <h1>Sports Event Predictor</h1>
        </div>
        <div class="actions">
          <select id="eventType">
            {% for event in event_types %}
            <option value="{{ event }}">{{ event.title() }}</option>
            {% endfor %}
          </select>
          <button id="refreshBtn">Refresh</button>
        </div>
      </header>

      <main class="layout">
        <section class="panel fixtures-panel">
          <h3>Live fixtures</h3>
          <div id="fixtureList" class="fixture-list"></div>
        </section>

        <section class="panel main-panel">
          <div class="card spotlight">
            <div class="event-tag" id="eventTag">Soccer</div>
            <div class="matchup">
              <div>
                <span class="label">Home</span>
                <h2 id="homeTeam">--</h2>
              </div>
              <div class="versus">VS</div>
              <div>
                <span class="label">Away</span>
                <h2 id="awayTeam">--</h2>
              </div>
            </div>
            <div class="score-box">
              <strong id="homeScore">0</strong>
              <span>:</span>
              <strong id="awayScore">0</strong>
            </div>
            <div class="confidence-wrap">
              <span>Confidence</span>
              <strong id="confidence">0%</strong>
            </div>
          </div>

          <div class="card">
            <h3>Probability</h3>
            <div class="probability-item">
              <span>Home win</span>
              <strong id="homeWin">0%</strong>
            </div>
            <div class="probability-item">
              <span>Draw</span>
              <strong id="drawProb">0%</strong>
            </div>
            <div class="probability-item">
              <span>Away win</span>
              <strong id="awayWin">0%</strong>
            </div>
          </div>

          <div class="card">
            <h3>Prediction</h3>
            <p id="outcome" class="outcome">Waiting for update...</p>
            <p class="timestamp" id="updatedAt">--</p>
            <p class="league" id="leagueLabel">--</p>
          </div>
        </section>
      </main>

      <section class="card insights">
        <h3>Live insights</h3>
        <div class="insight-grid">
          <div>
            <span class="mini-label">Home attack</span>
            <strong id="homeAttack">--</strong>
          </div>
          <div>
            <span class="mini-label">Away attack</span>
            <strong id="awayAttack">--</strong>
          </div>
          <div>
            <span class="mini-label">Home defense</span>
            <strong id="homeDefense">--</strong>
          </div>
          <div>
            <span class="mini-label">Away defense</span>
            <strong id="awayDefense">--</strong>
          </div>
          <div>
            <span class="mini-label">Momentum</span>
            <strong id="momentum">--</strong>
          </div>
        </div>
      </section>
    </div>

    <script src="{{ url_for('static', filename='app.js') }}"></script>
  </body>
</html>
