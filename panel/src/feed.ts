// Çekirdeğin /events ucuna bağlantı: önce son HISTORY_H saatin kayıtları, sonra canlı akış.
// Kopunca yeniden bağlanır ve geçmişi baştan ister; kayıtlar kimlikle tekilleşir.
import { useEffect, useState } from 'react'
import { parse, SchemaError, type Item } from './contract'

export const HISTORY_H = 24
const LIMIT = 5000 // ekranda tutulan en çok kayıt; eskisi düşer
const RETRY_MS = [1000, 2000, 5000, 10000]

export type Connection = 'connecting' | 'history' | 'live' | 'lost' | 'incompatible'

export type Feed = { items: Item[]; connection: Connection; error: string | null }

function url(since: Date): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${location.host}/events?since=${encodeURIComponent(since.toISOString())}`
}

function merge(items: Item[], incoming: Item[]): Item[] {
  const seen = new Set(items.map(i => i.id))
  const fresh = incoming.filter(i => !seen.has(i.id))
  if (!fresh.length) return items
  const all = [...items, ...fresh]
  // Damgalar sabit genişlikte ISO-8601 UTC: metin sırası zaman sırasıdır.
  all.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
  return all.slice(-LIMIT)
}

export function useFeed(): Feed {
  const [feed, setFeed] = useState<Feed>({ items: [], connection: 'connecting', error: null })

  useEffect(() => {
    let socket: WebSocket | null = null
    let attempt = 0
    let timer: number | undefined
    let stopped = false
    let pending: Item[] = []
    let frame = 0

    // Geçmiş yüzlerce mesaj olarak gelir; her biri için ayrı çizim yerine kare başına bir kez.
    const flush = () => {
      frame = 0
      const batch = pending
      pending = []
      setFeed(f => ({ ...f, items: merge(f.items, batch) }))
    }

    const open = () => {
      setFeed(f => ({ ...f, connection: 'connecting' }))
      socket = new WebSocket(url(new Date(Date.now() - HISTORY_H * 3600_000)))
      socket.onopen = () => setFeed(f => ({ ...f, connection: 'history', error: null }))
      socket.onmessage = ev => {
        try {
          const message = parse(String(ev.data))
          if (message.type === 'live') {
            attempt = 0
            setFeed(f => ({ ...f, connection: 'live' }))
            return
          }
          pending.push(message)
          if (!frame) frame = requestAnimationFrame(flush)
        } catch (e) {
          stopped = true // sürümü tutmayan çekirdeğe yeniden bağlanmak aynı sonucu verir
          socket?.close()
          setFeed(f => ({
            ...f,
            connection: 'incompatible',
            error: e instanceof SchemaError ? e.message : String(e),
          }))
        }
      }
      socket.onclose = ev => {
        if (stopped) return
        setFeed(f => ({
          ...f,
          connection: 'lost',
          error: ev.code === 1011 ? 'the panel fell behind the feed' : null,
        }))
        timer = window.setTimeout(open, RETRY_MS[Math.min(attempt++, RETRY_MS.length - 1)])
      }
    }

    open()
    return () => {
      stopped = true
      window.clearTimeout(timer)
      if (frame) cancelAnimationFrame(frame)
      socket?.close()
    }
  }, [])

  return feed
}
