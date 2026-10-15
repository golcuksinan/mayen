// Çekirdeğin panele gönderdiği mesajlar. Tanımın aslı ports/panel.py; burası onun aynısıdır.
// Sürümü tutmayan mesaj gösterilmez: yanlış okunmuş bir alan, panelde yaşanmamış bir şeydir.

export const SCHEMA_VERSION = 1

// ports/events.py: EventKind ve SessionState
export type EventKind =
  | 'turn.started' | 'turn.interrupted' | 'turn.finished'
  | 'tool.requested' | 'tool.started' | 'tool.finished'
  | 'confirmation.closed' | 'stt.segment' | 'llm.usage' | 'state.changed'

export type SessionState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'awaiting_confirmation'

// ports/tools.py: Status
export type Status = 'ok' | 'error' | 'denied' | 'cancelled' | 'timeout' | 'started'

export type EventMessage = {
  type: 'event'
  id: string
  kind: EventKind
  source: string
  time: string
  session: string | null
  turn_id: string | null
  duration_s: number | null
  status: Status | null
  related: string[]
  body: Record<string, unknown>
}

export type UtteranceMessage = {
  type: 'utterance'
  id: string
  time: string
  session: string
  turn_id: string | null
  party: 'person' | 'assistant'
  role: string | null
  person_id: string | null
  text: string
  interrupted: boolean
}

export type LiveMessage = { type: 'live' }

export type Message = EventMessage | UtteranceMessage | LiveMessage
export type Item = EventMessage | UtteranceMessage

export class SchemaError extends Error {}

export function parse(raw: string): Message {
  const data = JSON.parse(raw) as { schema_version?: unknown; type?: unknown }
  if (data.schema_version !== SCHEMA_VERSION) {
    throw new SchemaError(`schema_version ${String(data.schema_version)}, panel speaks ${SCHEMA_VERSION}`)
  }
  if (data.type !== 'event' && data.type !== 'utterance' && data.type !== 'live') {
    throw new SchemaError(`unknown message type ${String(data.type)}`)
  }
  return data as Message
}
