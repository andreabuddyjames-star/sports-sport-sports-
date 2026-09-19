import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API = import.meta.env.VITE_API_URL || ''

function App() {
  const [sport, setSport] = useState('soccer')
  const [fixtures, setFixtures] = useState([])
  const [selected, setSelected] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  async function loadFixtures() {
    const data = await fetch(`${API}/api/fixtures?event=${sport}`).then(r => r.json())
    setFixtures(data.fixtures || [])
    if (!selected || !data.fixtures.some(item => item.id === selected)) setSelected(data.fixtures?.[0]?.id || null)
  }

  async function loadPrediction(id = selected) {
    if (!id) return
    setLoading(true)
    const data = await fetch(`${API}/api/predict?event=${sport}&fixture_id=${encodeURIComponent(id)}`).then(r => r.json())
    setPrediction(data)
    const recent = await fetch(`${API}/api/history?event=${sport}`).then(r => r.json())
    setHistory(recent.history || [])
    setLoading(false)
  }

  useEffect(() => { loadFixtures() }, [sport])
  useEffect(() => { loadPrediction() }, [selected, sport])
  useEffect(() => { const timer = setInterval(() => { loadFixtures(); loadPrediction() }, 30000); return () => clearInterval(timer) }, [selected, sport])

  return <div className="shell">
    <header className="topbar"><div><span className="kicker">LIVE ANALYTICS</span><h1>Pulse<span>Play</span></h1></div><div className="controls"><select value={sport} onChange={e => { setSport(e.target.value); setSelected(null) }}><option value="soccer">Soccer</option><option value="basketball">Basketball</option></select><button onClick={() => loadPrediction()}>{loading ? 'Updating…' : 'Refresh'}</button></div></header>
    <main className="dashboard">
      <aside className="sidebar"><h2>Fixtures</h2>{fixtures.map(item => <button className={`fixture ${item.id === selected ? 'active' : ''}`} key={item.id} onClick={() => setSelected(item.id)}><b>{item.home}</b><span>vs</span><b>{item.away}</b><small>{item.league} · {item.source}</small></button>)}</aside>
      <section className="content">{prediction && <><div className="hero"><div className="badge">{prediction.event} · {prediction.source}</div><p className="league">{prediction.league}</p><div className="teams"><div><small>HOME</small><strong>{prediction.home_team}</strong></div><em>VS</em><div className="away"><small>AWAY</small><strong>{prediction.away_team}</strong></div></div><div className="score">{prediction.projected_score.home}<i>:</i>{prediction.projected_score.away}</div><p className="winner">{prediction.outcome} projected to lead <b>{prediction.confidence}% confidence</b></p></div><div className="cards"><article><small>HOME WIN</small><strong>{(prediction.home_win_probability * 100).toFixed(1)}%</strong></article><article><small>DRAW</small><strong>{(prediction.draw_probability * 100).toFixed(1)}%</strong></article><article><small>AWAY WIN</small><strong>{(prediction.away_win_probability * 100).toFixed(1)}%</strong></article></div><div className="panel"><h2>Model factors</h2><div className="factors">{Object.entries(prediction.factors).map(([key, value]) => <div key={key}><span>{key.replace('_', ' ')}</span><b>{value}</b></div>)}</div><p className="muted">{prediction.model} · Updated {prediction.updated_at}</p></div></>}
      <div className="panel"><h2>Recent predictions</h2>{history.length === 0 ? <p className="muted">No predictions saved yet.</p> : history.slice(0, 6).map(item => <div className="history" key={item.id}><span><b>{item.home_team}</b> vs <b>{item.away_team}</b><small>{item.created_at}</small></span><strong>{item.outcome}<small>{item.confidence}% confidence</small></strong></div>)}</div></section>
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
