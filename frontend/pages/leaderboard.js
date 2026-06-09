import { useEffect, useState } from 'react'
import Head from 'next/head'
import Nav from '../components/Nav'
import { useLang } from '../contexts/LangContext'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Leaderboard() {
  const { t } = useLang()
  const lb = t.leaderboard

  const [stats,   setStats]   = useState(null)
  const [wallets, setWallets] = useState([])

  useEffect(() => {
    fetch(`${API}/api/stats`).then(r => r.json()).then(setStats)
    fetch(`${API}/api/leaderboard?limit=50`).then(r => r.json()).then(setWallets)
  }, [])

  return (
    <>
      <Head>
        <title>Leaderboard · Agentry</title>
        <link rel="icon" type="image/png" href="/logo.png" />
      </Head>
      <Nav />

      <section style={{ background: 'transparent', padding: '120px 2rem 64px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse at 70% 50%, rgba(37,99,235,0.12) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 4, textTransform: 'uppercase', color: '#60a5fa', marginBottom: 14 }}>
            {lb.badge}
          </div>
          <h1 style={{ fontSize: 'clamp(36px,5vw,60px)', fontWeight: 900, color: '#ffffff', marginBottom: 12 }}>
            {lb.title}
          </h1>
          <p style={{ fontSize: 16, color: '#94a3b8', maxWidth: 480 }}>{lb.sub}</p>
        </div>
      </section>

      <main className="page">
        {stats && (
          <div className="stat-grid">
            {[
              [stats.total_wallets?.toLocaleString(), lb.stats.wallets],
              [`${stats.pct_agentic}%`,               lb.stats.agentic],
              [stats.high_confidence?.toLocaleString(), lb.stats.highConf],
              [stats.roc_auc,                           lb.stats.rocAuc],
            ].map(([num, lbl]) => (
              <div key={lbl} className="stat-card">
                <div className="stat-num">{num}</div>
                <div className="stat-label">{lbl}</div>
              </div>
            ))}
          </div>
        )}

        <div className="hr" />

        <div className="section-label">{lb.tableSection}</div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', marginBottom: 16 }}>{lb.tableTitle}</h2>

        <table className="data-table">
          <thead>
            <tr>
              {Object.values(lb.cols).map(c => <th key={c}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {wallets.map((w, i) => (
              <tr key={w.address}>
                <td style={{ color: '#475569' }}>{i + 1}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{w.address.slice(0,10)}...{w.address.slice(-8)}</td>
                <td>
                  <span style={{
                    padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                    background: w.label?.startsWith('agent') ? 'rgba(37,99,235,0.2)' : 'rgba(255,255,255,0.07)',
                    color: w.label?.startsWith('agent') ? '#60a5fa' : '#64748b',
                  }}>
                    {t.analytics.labelNames[w.label] ?? w.label}
                  </span>
                </td>
                <td style={{ fontWeight: 700, color: '#60a5fa' }}>{w.agent_score?.toFixed(1)}</td>
                <td>{w.transfer_total ?? '—'}</td>
                <td>{w.active_days ?? '—'}</td>
                <td>{w.unique_counterparties ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </>
  )
}
