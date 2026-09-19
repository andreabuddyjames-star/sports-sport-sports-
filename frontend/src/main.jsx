import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API = import.meta.env.VITE_API_URL || ''
const pct = value => `${Math.round((Number(value) || 0) * 100)}%`

function InjuryCard({ factors, home, away }) {
  const injuries = factors?.injuries || {}
  const reports = team => injuries[team] || []
  return <section className="factor-card"><div className="card-title"><span>⚕</span><div><h3>Injuries & news</h3><small>{factors?.news_source || 'No provider status'}</small></div></div><div className="team-factors"><div><strong>{home}</strong>{reports(home).length ? reports(home).map((item, i) => <a key={i} href={item.url || '#'} target="_blank" rel="noreferrer">{item.headline}</a>) : <p className="muted">No matching reports</p>}</div><div><strong>{away}</strong>{reports(away).length ? reports(away).map((item, i) => <a key={i} href={item.url || '#'} target="_blank" rel="noreferrer">{item.headline}</a>) : <p className="muted">No matching reports</p>}</div></div><small className="source">Checked {factors?.news_checked_at || '—'}</small></section>
}

function WeatherCard({ factors }) {
  const weather = factors?.weather
  return <section className="factor-card"><div className="card-title"><span>☁</span><div><h3>Match weather</h3><small>{factors?.weather_source || 'No provider status'}</small></div></div>{weather ? <div className="weather-grid"><div><b>{weather.temperature ?? '—'}°</b><small>Temperature</small></div><div><b>{weather.wind_speed ?? '—'}</b><small>Wind km/h</small></div><div><b>{weather.precipitation ?? '—'}</b><small>Rain mm</small></div></div> : <p className="muted">Weather unavailable or not applicable.</p>}<small className="source">Checked {factors?.weather_checked_at || '—'}</small></section>
}

function App() {
  const [sport, setSport] = useState('soccer'); const [fixtures, setFixtures] = useState([]); const [selected, setSelected] = useState(null); const [prediction, setPrediction] = useState(null); const [history, setHistory] = useState([]); const [loading, setLoading] = useState(false)
  async function loadFixtures() { const data = await fetch(`${API}/api/fixtures?event=${sport}`).then(r => r.json()); setFixtures(data.fixtures || []); if (!selected || !data.fixtures.some(item => item.id === selected)) setSelected(data.fixtures?.[0]?.id || null) }
  async function loadPrediction(id = selected) { if (!id) return; setLoading(true); try { const data = await fetch(`${API}/api/predict?event=${sport}&fixture_id=${encodeURIComponent(id)}`).then(r => r.json()); setPrediction(data); const recent = await fetch(`${API}/api/history?event=${sport}`).then(r => r.json()); setHistory(recent.history || []) } finally { setLoading(false) } }
  useEffect(() => { loadFixtures() }, [sport]); useEffect(() => { loadPrediction() }, [selected, sport]); useEffect(() => { const timer = setInterval(() => { loadFixtures(); loadPrediction() }, 30000); return () => clearInterval(timer) }, [selected, sport])
  return <div className="shell"><header className="topbar"><div><span className="kicker">LIVE ANALYTICS</span><h1>Pulse<span>Play</span></h1></div><div className="controls"><select value={sport} onChange={e => { setSport(e.target.value); setPrediction(null) }}><option value="soccer">Soccer</option><option value="basketball">Basketball</option></select></div></header><main className="dashboard"><aside className="sidebar"><h2>Fixtures</h2>{fixtures.map(item => <button className={`fixture ${item.id === selected ? 'active' : ''}`} key={item.id} onClick={() => setSelected(item.id)}><b>{item.home}</b><span>vs</span><b>{item.away}</b><small>{item.status || item.source}</small></button>)}</aside><section className="content">{loading && <p className="loading">Refreshing live factors…</p>}{prediction && <><div className="hero"><div className="badge">{prediction.event} · {prediction.source}</div><p className="league">{prediction.league}</p><h2>{prediction.home_team} <span>vs</span> {prediction.away_team}</h2><div className="probabilities"><div><b>{pct(prediction.home_win_probability)}</b><small>Home</small></div><div><b>{pct(prediction.draw_probability)}</b><small>Draw</small></div><div><b>{pct(prediction.away_win_probability)}</b><small>Away</small></div></div><p>Projected score: <strong>{prediction.projected_score.home} — {prediction.projected_score.away}</strong> · Confidence {prediction.confidence}%</p></div><div className="factor-grid"><InjuryCard factors={prediction.live_factors} home={prediction.home_team} away={prediction.away_team}/><WeatherCard factors={prediction.live_factors}/></div></>}<div className="panel"><h2>Recent predictions</h2>{history.length === 0 ? <p className="muted">No predictions saved yet.</p> : history.slice(0, 6).map(item => <div className="history" key={item.id}><span>{item.home_team} vs {item.away_team}</span><strong>{item.outcome}</strong><small>{item.created_at}</small></div>)}</div></section></main></div>
}
createRoot(document.getElementById('root')).render(<App />)
