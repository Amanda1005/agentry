import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import Nav from '../components/Nav'
import { useLang } from '../contexts/LangContext'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const COLORS  = { agent_acp: '#2563eb', agent_virtuals: '#60a5fa', eoa_sampled: '#f87171', mev_bot: '#fb923c' }

export default function Analytics() {
  const { t } = useLang()
  const an = t.analytics

  const [dist, setDist] = useState([])

  useEffect(() => {
    fetch(`${API}/api/distribution`).then(r => r.json()).then(raw => {
      const map = {}
      raw.forEach(({ bin, label, count }) => {
        if (!map[bin]) map[bin] = { bin }
        map[bin][label] = count
      })
      setDist(Object.values(map).sort((a, b) => a.bin - b.bin))
    })
  }, [])

  return (
    <>
      <Nav />

      <section style={{ background: 'transparent', padding: '120px 2rem 64px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse at 30% 50%, rgba(37,99,235,0.12) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 4, textTransform: 'uppercase', color: '#60a5fa', marginBottom: 14 }}>
            {an.badge}
          </div>
          <h1 style={{ fontSize: 'clamp(36px,5vw,60px)', fontWeight: 900, color: '#ffffff', marginBottom: 12 }}>{an.title}</h1>
          <p style={{ fontSize: 16, color: '#94a3b8', maxWidth: 480 }}>{an.sub}</p>
        </div>
      </section>

      <main className="page">
        {/* Chart */}
        <div style={{ background: '#0d1829', borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)', padding: '24px 8px 8px' }}>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={dist} margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
              <XAxis dataKey="bin" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: '#0d1829', color: '#f8fafc' }} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
              {Object.entries(COLORS).map(([key, color]) => (
                <Bar key={key} dataKey={key} name={an.labelNames[key]} stackId="a" fill={color} radius={key === 'mev_bot' ? [3,3,0,0] : [0,0,0,0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="hr" />

        {/* How It Works */}
        <div className="section-label">{an.howBadge}</div>
        <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, color: '#f8fafc' }}>{an.howTitle}</h2>
        <p style={{ fontSize: 15, color: '#94a3b8', marginBottom: 32 }}>{an.howSub}</p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20, marginBottom: 40 }}>
          {an.steps.map(([num, title, desc]) => (
            <div key={num} style={{ background: '#0d1829', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 12 }}>STEP {num}</div>
              <div style={{ fontSize: 17, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>{title}</div>
              <div style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>

        {/* Callout */}
        <div style={{ background: 'rgba(37,99,235,0.12)', border: '1px solid rgba(96,165,250,0.2)', borderRadius: 12, padding: '20px 24px', display: 'flex', gap: 40, flexWrap: 'wrap' }}>
          {[
            [an.callout.features, an.callout.featVal],
            [an.callout.truth,    an.callout.truthVal],
            [an.callout.perf,     an.callout.perfVal],
          ].map(([label, val]) => (
            <div key={label}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#60a5fa', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>{val}</div>
            </div>
          ))}
        </div>

      </main>
    </>
  )
}
