import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API = import.meta.env.VITE_API_URL || ''
const pct = value => `${Math.round((Number(value) || 0) * 100)}%`
const iconFor = (weather, severity) => weather?.icon
  ? <img src={`https:${weather.icon}`} alt="" />
  : <span className={`weather-icon ${severity || 'unknown'}`}>{severity === 'high' ? '⛈' : severity === 'moderate' ? '🌦' : severity === 'low' ? '☀' : '☁'}</span>

function ProviderHealth() {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch(`${API}/api/diagnostics`).then(response => response.json()).then(setData).catch(() => setData(null))
  }, [])
  if (!data) return <span className="provider-health unknown">Provider status unavailable</span>
  return <div className="provider-health">{Object.entries(data.providers || {}).filter(([key]) => key !== 'stats').map(([key, value]) => <span className={value.configured || value.mode === 'fallback' ? 'online' : 'unknown'} key={key}><i />{key}: {value.provider}</span>)}</div>
}

function InjuryCard({ factors, home, away }) {
  const injuries = factors?.injuries || {}
  return <section className="factor-card"><div className="card-title"><span>⚕</span><div><h3>Team availability</h3><small>{factors?.news_source || 'No provider status'}</small></div></div><div className="team-factors">{[home, away].map(team => { const reports = injuries[team] || []; return <div className="team-status" key={team}><div className="team-heading"><strong>{team}</strong><span className={`status-badge ${reports.length ? 'warning' : 'good'}`}>{reports.length ? `${reports.length} report${reports.length > 1 ? 's' : ''}` : 'Clear'}</span></div>{reports.length ? reports.map((item, i) => <a key={i} href={item.url || '#'} target="_blank" rel="noreferrer">{item.headline}</a>) : <p className="muted">No provider-matched availability reports.</p>}</div> })}</div><small className="source">Checked {factors?.news_checked_at || '—'}</small></section>
}

function WeatherCard({ factors }) {
  const weather = factors?.weather
  const severity = factors?.weather_severity || 'unknown'
  return <section className={`factor-card weather-card severity-${severity}`}><div className="card-title"><span>☁</span><div><h3>Match forecast</h3><small>{factors?.weather_source || 'No provider status'}</small></div></div>{weather ? <><div className="forecast-main">{iconFor(weather, severity)}<div><b>{weather.temperature ?? '—'}°</b><strong>{weather.condition || 'Current conditions'}</strong><small>{weather.location || 'Venue area'}</small></div><span className={`severity-badge ${severity}`}>{severity}</span></div><div className="weather-grid"><div><b>{weather.feels_like ?? '—'}°</b><small>Feels like</small></div><div><b>{weather.wind_speed ?? '—'}</b><small>Wind km/h</small></div><div><b>{weather.precipitation ?? '—'}</b><small>Rain mm</small></div></div><div className="impact"><span>Model impact</span><strong>{factors.weather_penalty ? `-${Math.round(factors.weather_penalty * 100)}% scoring environment` : 'Neutral conditions'}</strong></div></> : <p className="muted">Weather unavailable or not applicable.</p>}<small className="source">Checked {factors?.weather_checked_at || '—'}</small></section>
}

function EnginePrediction({ prediction }) {
  if (!prediction) return null
  const factors = prediction.factors || {}
  const cells = [
    ['Home win', pct(prediction.home_win_probability)],
    ['Draw', pct(prediction.draw_probability)],
    ['Away win', pct(prediction.away_win_probability)],
    ['Confidence', `${prediction.confidence ?? 0}%`],
  ]
  return <section className="engine-prediction card" style={{ gridColumn: '1 / -1', marginTop: '1rem', border: '1px solid rgba(104, 226, 190, .35)', background: 'linear-gradient(135deg, rgba(28, 55, 75, .95), rgba(14, 24, 42, .98))' }}><div className="card-title"><span>⚙</span><div><h3>Engine prediction</h3><small>{prediction.model || 'Elo + Poisson + live factors'}</small></div></div><div className="engine-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '.75rem', margin: '1rem 0' }}>{cells.map(([label, value]) => <div className="engine-metric" key={label}><small>{label}</small><strong>{value}</strong></div>)}</div><div className="engine-result"><span>Estimated result</span><strong>{prediction.outcome || '—'}</strong><span className="engine-score">Projected score: {prediction.projected_score?.home ?? '—'} – {prediction.projected_score?.away ?? '—'}</span></div><div className="engine-details"><span>Home ELO {factors.home_elo ?? '—'}</span><span>Away ELO {factors.away_elo ?? '—'}</span><span>Updated {prediction.updated_at || '—'}</span></div></section>
}

function App() {
  const [sport, setSport] = useState('soccer')
  const [fixtures, setFixtures] = useState([])
  const [selected, setSelected] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  async function loadFixtures() {
    const data = await fetch(`${API}/api/fixtures?event=${sport}`).then(response => response.json())
    setFixtures(data.fixtures || [])
    if (!selected || !data.fixtures.some(item => item.id === selected)) setSelected(data.fixtures?.[0]?.id || null)
  }

  async function loadPrediction(id = selected) {
    if (!id) return
    setLoading(true)
    try {
      const data = await fetch(`${API}/api/predict?event=${sport}&fixture_id=${encodeURIComponent(id)}`).then(response => response.json())
      setPrediction(data)
      const recent = await fetch(`${API}/api/history?event=${sport}`).then(response => response.json())
      setHistory(recent.history || [])
    } finally { setLoading(false) }
  }

  useEffect(() => { loadFixtures() }, [sport])
  useEffect(() => { loadPrediction() }, [selected, sport])
  useEffect(() => { const timer = setInterval(() => { loadFixtures(); loadPrediction() }, 30000); return () => clearInterval(timer) }, [selected, sport])

  const home = prediction?.home_team || fixtures.find(item => item.id === selected)?.home || 'Home'
  const away = prediction?.away_team || fixtures.find(item => item.id === selected)?.away || 'Away'

  return <div className="shell"><header className="topbar"><div><span className="kicker">LIVE ANALYTICS</span><h1>Pulse<span>Play</span></h1><ProviderHealth /></div><div className="controls"><select value={sport} onChange={event => { setSport(event.target.value); setPrediction(null) }}><option value="soccer">Soccer</option><option value="basketball">Basketball</option></select></div></header><main className="dashboard"><aside className="sidebar"><h2>Fixtures</h2>{fixtures.map(item => <button className={`fixture ${item.id === selected ? 'active' : ''}`} key={item.id} onClick={() => setSelected(item.id)}><b>{item.home}</b><span>vs</span><b>{item.away}</b><small>{item.league}</small></button>)}</aside><section className="content">{prediction && <><section className="hero-card"><span className="kicker">{prediction.league || sport}</span><h2>{home} <span>vs</span> {away}</h2><div className="hero-score"><strong>{prediction.projected_score?.home ?? '—'}</strong><span>–</span><strong>{prediction.projected_score?.away ?? '—'}</strong></div><p>{loading ? 'Refreshing…' : `${prediction.outcome || '—'} · ${prediction.confidence ?? 0}% confidence`}</p></section><section className="factor-grid"><InjuryCard factors={prediction.live_factors} home={home} away={away} /><WeatherCard factors={prediction.live_factors} /></section><section className="probability-card card"><h3>Win probabilities</h3><div className="probability-grid"><div><span>{home}</span><strong>{pct(prediction.home_win_probability)}</strong></div><div><span>Draw</span><strong>{pct(prediction.draw_probability)}</strong></div><div><span>{away}</span><strong>{pct(prediction.away_win_probability)}</strong></div></div></section></>}{history.length > 0 && <section className="history card"><h3>Recent predictions</h3>{history.map((item, index) => <div className="history-item" key={`${item.fixture_id || item.created_at}-${index}`}><strong>{item.home_team} vs {item.away_team}</strong><span>{item.outcome} · {item.confidence}% confidence</span></div>)}</section>}<EnginePrediction prediction={prediction} /></section></main></div>
}

createRoot(document.getElementById('root')).render(<App />)
