import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useLang } from '../contexts/LangContext'

export default function Nav() {
  const { pathname } = useRouter()
  const { t } = useLang()

  return (
    <nav className="nav">
      <Link href="/" className="nav-brand" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Image src="/logo.png" alt="Agentry" width={28} height={28} style={{ borderRadius: 6 }} />
        Agentry
      </Link>
      <Link href="/"            className={pathname === '/'            ? 'active' : ''}>{t.nav.home}</Link>
      <Link href="/leaderboard" className={pathname === '/leaderboard' ? 'active' : ''}>{t.nav.leaderboard}</Link>
      <Link href="/analytics"   className={pathname === '/analytics'   ? 'active' : ''}>{t.nav.analytics}</Link>
    </nav>
  )
}
