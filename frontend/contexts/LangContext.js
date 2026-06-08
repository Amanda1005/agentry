import { createContext, useContext, useState, useEffect } from 'react'
import en from '../locales/en'
import zh from '../locales/zh'

const LangContext = createContext()

export function LangProvider({ children }) {
  const [lang, setLang] = useState('en')

  useEffect(() => {
    const saved = localStorage.getItem('agentry_lang')
    if (saved === 'zh' || saved === 'en') setLang(saved)
  }, [])

  function toggle() {
    const next = lang === 'en' ? 'zh' : 'en'
    setLang(next)
    localStorage.setItem('agentry_lang', next)
  }

  const t = lang === 'zh' ? zh : en

  return (
    <LangContext.Provider value={{ lang, toggle, t }}>
      {children}
    </LangContext.Provider>
  )
}

export function useLang() {
  return useContext(LangContext)
}
