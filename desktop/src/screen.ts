// Ekranın durumu. Mesajları Python süreci verir (window.mayenScreen); ekran çekirdeğe hiçbir
// şey göndermez, yalnızca son durumu, son sözleri ve her tool'un son sonucunu tutar.
import { useEffect, useState } from 'react'
import { parse, SchemaError, type ReminderMessage, type SessionState, type ToolMessage, type UtteranceMessage } from './contract'

export type Connection = 'connecting' | 'live' | 'lost'

export type Card = ToolMessage & { at: number }

export type Screen = {
  connection: Connection
  state: SessionState
  words: UtteranceMessage[]
  cards: Card[] // en yenisi başta: öne gelen kart
  reminder: (ReminderMessage & { at: number }) | null // son çalan hatırlatma
  activity: Activity | null // kişinin Mayen'e açtırdığı oyun ya da video: yerleşimi belirler
  night: Night | null // gece saatleri; istemcinin ayarı
  error: string | null
}

export type Activity = { kind: 'game' | 'video'; name: string }
export type Night = { from: number; to: number } // gün içindeki dakika

const WORDS = 40
const CARDS = 6

declare global {
  interface Window {
    mayenScreen?: (raw: string) => void
    mayenConnection?: (connection: Connection) => void
    mayenNight?: (span: string) => void
    pywebview?: { api: { fullscreen: () => void } }
  }
}

const EMPTY: Screen = {
  connection: 'connecting', state: 'idle', words: [], cards: [], reminder: null, activity: null, night: null, error: null,
}

// Yerleşim tool sonuçlarından (§7): açılan uygulamanın kategorileri (freedesktop) Game içeriyorsa
// oyun, Video ve Player içeriyorsa video; başlığı onun adını taşıyan pencereyi kapatma sonucuyla
// çıkılır. Başka bir uygulama açmak yerleşimi bozmaz. Elle kapatılan uygulama bilinmez.
function activity(current: Activity | null, m: ToolMessage): Activity | null {
  if (m.status !== 'ok') return current
  const categories = Array.isArray(m.data.categories) ? m.data.categories : []
  const name = String(m.data.opened)
  if (m.tool === 'apps' && categories.includes('Game')) return { kind: 'game', name }
  if (m.tool === 'apps' && categories.includes('Video') && categories.includes('Player')) return { kind: 'video', name }
  const title = typeof m.data.title === 'string' ? m.data.title.toLowerCase() : ''
  if (m.tool === 'window_close' && current && title.includes(current.name.toLowerCase())) return null
  return current
}

// "23:00-07:00" biçimi; okunamazsa gece yok
function night(span: string): Night | null {
  const m = /^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$/.exec(span.trim())
  if (!m) return null
  return { from: Number(m[1]) * 60 + Number(m[2]), to: Number(m[3]) * 60 + Number(m[4]) }
}

export function isNight(span: Night | null, now: number): boolean {
  if (!span) return false
  const d = new Date(now)
  const t = d.getHours() * 60 + d.getMinutes()
  return span.from <= span.to ? t >= span.from && t < span.to : t >= span.from || t < span.to
}

// React bağlanmadan gelen mesajlar kaybolmasın: sayfa yüklenir yüklenmez kuyruğa alınır
const early: string[] = []
let earlyConnection: Connection | null = null
let earlyNight: string | null = null
window.mayenScreen = raw => { early.push(raw) }
window.mayenConnection = connection => { earlyConnection = connection }
window.mayenNight = span => { earlyNight = span }

function apply(screen: Screen, raw: string): Screen {
  let message
  try {
    message = parse(raw)
  } catch (e) {
    return { ...screen, error: e instanceof SchemaError ? e.message : 'unreadable message' }
  }
  switch (message.type) {
    case 'state':
      return { ...screen, state: message.state }
    case 'reminder':
      return { ...screen, reminder: { ...message, at: Date.now() } }
    case 'utterance':
      return { ...screen, words: [...screen.words, message].slice(-WORDS) }
    case 'tool': {
      // Aynı tool'un kartı tektir; yeni sonucu onu günceller ve öne alır
      const card = { ...message, at: Date.now() }
      return { ...screen, activity: activity(screen.activity, message),
               cards: [card, ...screen.cards.filter(c => c.tool !== message.tool)].slice(0, CARDS) }
    }
  }
}

export function useScreen(): Screen {
  const [screen, setScreen] = useState(EMPTY)
  useEffect(() => {
    window.mayenScreen = raw => setScreen(s => apply(s, raw))
    // Kopunca durum boşa döner: yeni oturum boşta başlar ve bunu ayrıca bildirmez
    window.mayenConnection = connection =>
      setScreen(s => ({ ...s, connection, state: connection === 'live' ? s.state : 'idle' }))
    window.mayenNight = span => setScreen(s => ({ ...s, night: night(span) }))
    const queued = early.splice(0)
    const connection = earlyConnection
    const span = earlyNight
    setScreen(s => queued.reduce(apply, { ...s, ...(connection ? { connection } : {}), ...(span ? { night: night(span) } : {}) }))
  }, [])
  return screen
}
