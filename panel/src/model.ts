// Kayıtların ekrandaki biçimi: oturumlar ve turlar. Burada yalnızca gruplama ve sıralama var;
// durum çekirdeğin `state.changed` olayından okunur, olay sırasından çıkarılmaz.
import type { EventMessage, Item, SessionState, Status, UtteranceMessage } from './contract'

export type Session = { id: string; state: SessionState; since: string; last: string }

export type ToolStep = {
  kind: 'tool'
  id: string
  time: string
  tool: string
  arguments: unknown
  verdict: string | null // argümanı doğrulanamayan çağrıda karar yok
  status: Status | null // null: henüz bitmedi ya da onay bekliyor
  duration_s: number | null
  result: unknown
}

export type Step =
  | { kind: 'said'; id: string; time: string; utterance: UtteranceMessage }
  | ToolStep
  | { kind: 'confirmation'; id: string; time: string; event: EventMessage }

export type Turn = {
  id: string
  session: string | null
  start: EventMessage | null // geçmiş penceresinin öncesinde başlamış olabilir
  end: EventMessage | null // sürüyor
  steps: Step[]
  tokens: { prompt: number; completion: number }
  last: string
}

const isEvent = (i: Item): i is EventMessage => i.type === 'event'

export function sessions(items: Item[]): Session[] {
  const out = new Map<string, Session>()
  for (const i of items) {
    if (!i.session) continue
    const s = out.get(i.session) ?? { id: i.session, state: 'idle', since: i.time, last: i.time }
    s.last = i.time
    if (isEvent(i) && i.kind === 'state.changed') {
      s.state = i.body.state as SessionState
      s.since = i.time
    }
    out.set(i.session, s)
  }
  return [...out.values()].sort((a, b) => (a.last < b.last ? 1 : -1))
}

export function turns(items: Item[]): Turn[] {
  const out = new Map<string, Turn>()
  const calls = new Map<string, ToolStep>() // çağrı kimliği → adım; istek ve bitiş birleşir
  for (const i of items) {
    if (!i.turn_id) continue
    let t = out.get(i.turn_id)
    if (!t) {
      t = { id: i.turn_id, session: i.session, start: null, end: null, steps: [], tokens: { prompt: 0, completion: 0 }, last: i.time }
      out.set(i.turn_id, t)
    }
    t.last = i.time
    if (!isEvent(i)) {
      t.steps.push({ kind: 'said', id: i.id, time: i.time, utterance: i })
      continue
    }
    const b = i.body
    switch (i.kind) {
      case 'turn.started':
        t.start = i
        break
      case 'turn.finished':
      case 'turn.interrupted':
        t.end = i
        break
      case 'tool.requested': {
        const step: ToolStep = {
          kind: 'tool', id: i.id, time: i.time, tool: String(b.tool), arguments: b.arguments,
          verdict: (b.verdict as string | null) ?? null, status: null, duration_s: null, result: null,
        }
        t.steps.push(step)
        if (b.call_id) calls.set(String(b.call_id), step)
        break
      }
      case 'tool.finished': {
        const step = b.call_id ? calls.get(String(b.call_id)) : undefined
        if (step) {
          step.status = i.status
          step.duration_s = i.duration_s
          step.result = b.result
          step.arguments = b.arguments
        }
        break
      }
      case 'confirmation.closed':
        t.steps.push({ kind: 'confirmation', id: i.id, time: i.time, event: i })
        break
      case 'llm.usage':
        t.tokens.prompt += Number(b.prompt_tokens ?? 0)
        t.tokens.completion += Number(b.completion_tokens ?? 0)
        break
      default:
        break // tool.started bitişle birleşir; stt.segment'in sözü transkriptten gelir
    }
  }
  return [...out.values()].sort((a, b) => (a.last < b.last ? 1 : -1))
}

export type Level = 'calm' | 'active' | 'alert'

const ALERT_WINDOW_MS = 5 * 60_000

/** Arayüzün yoğunluğu: herkes boştaysa sakin, bir oturum çalışıyorsa faal, yakın zamanda bir
 *  hata ya da bekleyen bir onay varsa uyarı. */
export function level(items: Item[], all: Session[], now: number): Level {
  if (all.some(s => s.state === 'awaiting_confirmation')) return 'alert'
  const since = new Date(now - ALERT_WINDOW_MS).toISOString()
  for (let k = items.length - 1; k >= 0 && items[k].time >= since; k--) {
    const i = items[k]
    if (isEvent(i) && i.status === 'error') return 'alert'
  }
  return all.some(s => s.state !== 'idle') ? 'active' : 'calm'
}

export function clock(time: string): string {
  return new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

export function seconds(s: number | null): string {
  if (s == null) return '—'
  return s < 10 ? `${s.toFixed(2)} s` : `${s.toFixed(1)} s`
}
