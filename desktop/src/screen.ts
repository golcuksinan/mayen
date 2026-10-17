// Ekranın durumu. Mesajları Python süreci verir (window.mayenScreen); ekran çekirdeğe hiçbir
// şey göndermez, yalnızca son durumu, son sözleri ve her tool'un son sonucunu tutar.
import { useEffect, useState } from 'react'
import { parse, SchemaError, type SessionState, type ToolMessage, type UtteranceMessage } from './contract'

export type Connection = 'connecting' | 'live' | 'lost'

export type Card = ToolMessage & { at: number }

export type Screen = {
  connection: Connection
  state: SessionState
  words: UtteranceMessage[]
  cards: Card[] // en yenisi başta: öne gelen kart
  error: string | null
}

const WORDS = 40
const CARDS = 6

declare global {
  interface Window {
    mayenScreen?: (raw: string) => void
    mayenConnection?: (connection: Connection) => void
  }
}

const EMPTY: Screen = { connection: 'connecting', state: 'idle', words: [], cards: [], error: null }

// React bağlanmadan gelen mesajlar kaybolmasın: sayfa yüklenir yüklenmez kuyruğa alınır
const early: string[] = []
let earlyConnection: Connection | null = null
window.mayenScreen = raw => { early.push(raw) }
window.mayenConnection = connection => { earlyConnection = connection }

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
    case 'utterance':
      return { ...screen, words: [...screen.words, message].slice(-WORDS) }
    case 'tool': {
      // Aynı tool'un kartı tektir; yeni sonucu onu günceller ve öne alır
      const card = { ...message, at: Date.now() }
      return { ...screen, cards: [card, ...screen.cards.filter(c => c.tool !== message.tool)].slice(0, CARDS) }
    }
  }
}

export function useScreen(): Screen {
  const [screen, setScreen] = useState(EMPTY)
  useEffect(() => {
    window.mayenScreen = raw => setScreen(s => apply(s, raw))
    window.mayenConnection = connection => setScreen(s => ({ ...s, connection }))
    const queued = early.splice(0)
    const connection = earlyConnection
    setScreen(s => queued.reduce(apply, connection ? { ...s, connection } : s))
  }, [])
  return screen
}
