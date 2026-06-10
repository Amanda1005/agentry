import { useState } from 'react'
import Head from 'next/head'
import dynamic from 'next/dynamic'
import Nav from '../components/Nav'
import { useLang } from '../contexts/LangContext'

const HeroScene = dynamic(() => import('../components/HeroScene'), { ssr: false })

const CHAINS    = ['Base', 'Ethereum', 'Arbitrum', 'Optimism', 'Polygon']
const CHAIN_KEY = { Base: 'base', Ethereum: 'ethereum', Arbitrum: 'arbitrum', Optimism: 'optimism', Polygon: 'polygon' }
const API       = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const { t } = useLang()
  const h = t.home

  const [chain,     setChain]     = useState('Base')
  const [address,   setAddress]   = useState('')
  const [result,    setResult]    = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis,  setAnalysis]  = useState(null)
  const [analysisError, setAnalysisError] = useState('')

  const isBase = chain === 'Base'

  async function handleScore(e) {
    e.preventDefault()
    const addr = address.trim()
    if (!addr || addr.length !== 42) { setError(h.errAddr); return }
    setError(''); setResult(null); setLoading(true)
    try {
      const res = await fetch(`${API}/api/score?address=${addr}&chain=${CHAIN_KEY[chain]}`)
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || h.errNone) }
      setResult(await res.json())
      setAnalysis(null)
      setAnalysisError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAnalyze() {
    const addr = address.trim()
    setAnalysis(null); setAnalysisError(''); setAnalyzing(true)
    try {
      const res = await fetch(`${API}/api/analyze?address=${addr}&chain=${CHAIN_KEY[chain]}`)
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Analysis failed') }
      setAnalysis(await res.json())
    } catch (err) {
      setAnalysisError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const score       = result?.agent_score ?? 0
  const accentColor = score >= 70 ? '#60a5fa' : score >= 40 ? '#fbbf24' : '#f87171'
  const glowColor   = score >= 70 ? 'rgba(96,165,250,0.18)' : score >= 40 ? 'rgba(251,191,36,0.15)' : 'rgba(248,113,113,0.15)'
  const verdict     = score >= 70 ? h.verdict.agent : score >= 40 ? h.verdict.uncertain : h.verdict.human
  const verdictIcon = score >= 70 ? '⬡' : score >= 40 ? '◈' : '◯'

  const features = result ? [
    [h.features.activeDays,      result.active_days           ?? 0],
    [h.features.activeHours,     result.active_hours          ?? 0],
    [h.features.transfers,       result.transfer_total        ?? 0],
    [h.features.nightActivity,   `${((result.night_ratio      ?? 0)*100).toFixed(1)}%`],
    [h.features.weekendActivity, `${((result.weekend_ratio    ?? 0)*100).toFixed(1)}%`],
    [h.features.counterparties,  result.unique_counterparties ?? 0],
    [h.features.tokens,          result.unique_tokens         ?? 0],
    [h.features.topTokenRatio,   `${((result.top_token_ratio  ?? 0)*100).toFixed(1)}%`],
    [h.features.intervalCV,      (result.inter_tx_cv          ?? 0).toFixed(2)],
  ] : []

  return (
    <>
      <Head>
        <title>Agentry — Agentic Wallet Intelligence</title>
        <link rel="icon" type="image/png" href="/logo.png" />
      </Head>
      <Nav />
      <section style={{
        position: 'relative', minHeight: '100vh', background: '#060d1a',
        overflow: 'hidden', paddingTop: 56, display: 'flex', alignItems: 'center',
      }}>
        <HeroScene />
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(105deg, rgba(6,13,26,0.88) 0%, rgba(6,13,26,0.5) 60%, rgba(6,13,26,0.2) 100%)',
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', zIndex: 10, maxWidth: 1200, margin: '0 auto', padding: '4rem 2rem', width: '100%' }}>
          <div style={{ maxWidth: 620 }}>

            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 4, textTransform: 'uppercase', color: '#60a5fa', marginBottom: 16 }}>
              {h.badge}
            </div>
            <h1 style={{ fontSize: 'clamp(38px,5.5vw,68px)', fontWeight: 900, lineHeight: 1.08, color: '#ffffff', margin: '0 0 16px' }}>
              {h.title1}<br /><span style={{ color: '#60a5fa' }}>{h.title2}</span> {h.titleEnd}
            </h1>
            <p style={{ fontSize: 16, color: '#94a3b8', lineHeight: 1.7, marginBottom: 36, maxWidth: 480, whiteSpace: 'pre-line' }}>
              {h.sub}
            </p>

            {/* Chain selector */}
            <div className="chain-tabs" style={{ marginBottom: 12 }}>
              {CHAINS.map(c => (
                <button key={c} className={`chain-tab chain-tab-dark${chain === c ? ' active' : ''}`}
                  onClick={() => { setChain(c); setResult(null); setError('') }}>
                  {c}{c !== 'Base' && <span style={{ fontSize: 9, marginLeft: 5, opacity: 0.65 }}>EXP</span>}
                </button>
              ))}
            </div>

            {/* Input */}
            <form onSubmit={handleScore} style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
              <input className="address-input address-input-dark" placeholder="0x..." value={address} onChange={e => setAddress(e.target.value)} />
              <button type="submit" style={{
                padding: '14px 28px', background: '#2563eb', color: '#fff',
                border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 14,
                cursor: 'pointer', whiteSpace: 'nowrap', fontFamily: 'Inter, sans-serif',
              }}>{h.score}</button>
            </form>

            {loading && <p style={{ color: '#94a3b8', fontSize: 14, marginTop: 12 }}>{h.loading}</p>}
            {error   && <p style={{ color: '#f87171', fontSize: 14, marginTop: 12 }}>{error}</p>}

            {/* Result */}
            {result && (
              <>
              <div className="result-grid" style={{ marginTop: 28 }}>
                <div style={{
                  background: '#0d1829', border: `1px solid ${accentColor}40`,
                  borderTop: `3px solid ${accentColor}`, borderRadius: 16, padding: '28px 24px',
                  boxShadow: `0 0 40px ${glowColor}`, display: 'flex', flexDirection: 'column', gap: 16,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 22, color: accentColor }}>{verdictIcon}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: 3, textTransform: 'uppercase', color: accentColor }}>{verdict}</span>
                  </div>
                  <div>
                    <div style={{ fontSize: 80, fontWeight: 900, lineHeight: 1, color: accentColor, textShadow: `0 0 40px ${accentColor}60` }}>
                      {score.toFixed(0)}
                    </div>
                    <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 2, textTransform: 'uppercase', marginTop: 4 }}>
                      {h.agentScore} · {chain}
                    </div>
                  </div>
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }} />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: `${accentColor}22`, color: accentColor, border: `1px solid ${accentColor}40` }}>
                        {t.analytics.labelNames[result.label] ?? result.label ?? 'unknown'}
                      </span>
                      {!isBase && <span style={{ fontSize: 10, color: '#64748b' }}>{h.experimental}</span>}
                    </div>
                    <div style={{ fontSize: 11, color: '#475569', fontFamily: 'monospace' }}>
                      {address.slice(0,14)}...{address.slice(-8)}
                    </div>
                  </div>
                </div>

                <div className="feat-card">
                  <h3>{h.fingerprint}</h3>
                  <table className="feat-table">
                    <tbody>
                      {features.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v}</td></tr>)}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* AI Analysis — Azure AI Foundry / Foundry IQ */}
              <div style={{ marginTop: 16 }}>
                {!analysis && !analyzing && (
                  <button
                    onClick={handleAnalyze}
                    style={{
                      width: '100%', padding: '13px 20px',
                      background: 'linear-gradient(135deg, #1e3a5f 0%, #1a2f52 100%)',
                      border: '1px solid #2563eb55', borderRadius: 10,
                      color: '#93c5fd', fontWeight: 600, fontSize: 13,
                      cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 15 }}>⬡</span>
                    {h.analyzeBtn}
                    <span style={{
                      fontSize: 10, padding: '2px 7px', borderRadius: 20,
                      background: '#2563eb33', color: '#60a5fa', fontWeight: 700,
                    }}>Azure AI Foundry</span>
                  </button>
                )}

                {analyzing && (
                  <div style={{
                    background: '#0a1628', border: '1px solid #2563eb40', borderRadius: 12,
                    padding: '20px 20px', color: '#60a5fa', fontSize: 13,
                    display: 'flex', alignItems: 'center', gap: 10,
                  }}>
                    <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⬡</span>
                    {h.analyzing}
                  </div>
                )}

                {analysisError && (
                  <p style={{ color: '#f87171', fontSize: 13, marginTop: 8 }}>{analysisError}</p>
                )}

                {analysis && (
                  <div style={{
                    background: '#080f1e', border: '1px solid #2563eb50',
                    borderTop: '2px solid #3b82f6', borderRadius: 12, padding: '20px 22px',
                    marginTop: 4,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                      <span style={{ color: '#60a5fa', fontSize: 16 }}>⬡</span>
                      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#60a5fa' }}>
                        {h.aiAnalysis}
                      </span>
                      <span style={{
                        marginLeft: 'auto', fontSize: 10, padding: '2px 8px',
                        borderRadius: 20, background: '#1e3a5f', color: '#93c5fd',
                        border: '1px solid #2563eb44',
                      }}>
                        {analysis.powered_by}
                      </span>
                    </div>
                    <div style={{
                      fontSize: 13, color: '#94a3b8', lineHeight: 1.75,
                      whiteSpace: 'pre-wrap', fontFamily: 'Inter, sans-serif',
                    }}>
                      {analysis.analysis}
                    </div>
                    <div style={{ marginTop: 14, fontSize: 10, color: '#334155' }}>
                      Knowledge source: {analysis.knowledge_source}
                    </div>
                  </div>
                )}
              </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── WHY AGENTRY ─────────────────────────────────────────────────── */}
      <section style={{ background: '#060d1a', borderTop: '1px solid rgba(255,255,255,0.06)', padding: '64px 2rem' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div className="section-label" style={{ textAlign: 'center', marginBottom: 12 }}>
            {h.whyTitle}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24, marginTop: 32 }}>
            {h.why.map(([icon, title, desc]) => (
              <div key={title} style={{
                background: '#0d1829', border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 16, padding: '28px 24px',
              }}>
                <div style={{ fontSize: 28, marginBottom: 14, color: '#60a5fa' }}>{icon}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>{title}</div>
                <div style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.7 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── USE CASES ───────────────────────────────────────────────────── */}
      <section style={{ background: '#060d1a', borderTop: '1px solid rgba(255,255,255,0.06)', padding: '64px 2rem' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div className="section-label" style={{ textAlign: 'center', marginBottom: 12 }}>
            {t.analytics.ucBadge}
          </div>
          <h2 style={{ fontSize: 32, fontWeight: 800, color: '#f8fafc', textAlign: 'center', marginBottom: 40, marginTop: 8 }}>
            {t.analytics.ucTitle}
          </h2>
          <div className="uc-grid">
            {t.analytics.useCases.map(([num, title, desc]) => (
              <div key={num} className="uc-card">
                <div className="uc-num">{num}</div>
                <div className="uc-title">{title}</div>
                <div className="uc-desc">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
