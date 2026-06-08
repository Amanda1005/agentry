import '../styles/globals.css'
import { LangProvider } from '../contexts/LangContext'

export default function App({ Component, pageProps }) {
  return (
    <LangProvider>
      <Component {...pageProps} />
    </LangProvider>
  )
}
