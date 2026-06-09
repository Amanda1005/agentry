import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useLang } from '../contexts/LangContext'

export default function Nav() {
  const { pathname } = useRouter()
  const { lang, toggle, t } = useLang()

  return (
    <nav className="nav">
      <Link href="/" className="nav-brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Image src="/logo.png" alt="Agentry" width={28} height={28} style={{ borderRadius: 6 }} />
        Agentry
      </Link>
      <Link href="/"            className={pathname === '/'            ? 'active' : ''}>{t.nav.home}</Link>
      <Link href="/leaderboard" className={pathname === '/leaderboard' ? 'active' : ''}>{t.nav.leaderboard}</Link>
      <Link href="/analytics"   className={pathname === '/analytics'   ? 'active' : ''}>{t.nav.analytics}</Link>

      {/* Language toggle — pushed to the right */}
      <button onClick={toggle} style={{
        marginLeft: 'auto',
        background: 'rgba(255,255,255,0.07)',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: 8,
        padding: '5px 12px',
        cursor: 'pointer',
        display: 'flex',
        gap: 0,
        fontFamily: 'Inter, sans-serif',
        fontSize: 12,
        fontWeight: 600,
        overflow: 'hidden',
      }}>
        <span style={{ color: lang === 'en' ? '#60a5fa' : 'rgba(255,255,255,0.4)', transition: 'color 0.15s' }}>EN</span>
        <span style={{ color: 'rgba(255,255,255,0.2)', margin: '0 6px' }}>|</span>
        <span style={{ color: lang === 'zh' ? '#60a5fa' : 'rgba(255,255,255,0.4)', transition: 'color 0.15s' }}>繁中</span>
      </button>
    </nav>
  )
}
