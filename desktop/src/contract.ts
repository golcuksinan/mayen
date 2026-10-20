// Çekirdeğin ekrana gönderdiği mesajlar. Tanımın aslı ports/screen.py; burası onun aynısıdır.
// Sürümü tutmayan mesaj gösterilmez: yanlış okunmuş bir alan, ekranda yaşanmamış bir şeydir.
import type { SessionState } from '../../panel/src/contract'

export type { SessionState }
export const SCHEMA_VERSION = 1

// ports/tools.py: Status
export type Status =
  | 'ok' | 'error' | 'denied' | 'unsupported' | 'cancelled' | 'timeout' | 'started'

export type StateMessage = { type: 'state'; state: SessionState }

export type UtteranceMessage = {
  type: 'utterance'
  time: string
  party: 'person' | 'assistant'
  role: string | null
  text: string
  interrupted: boolean
}

// Modele giden hâliyle, yetki süzgecinden sonra
export type ToolMessage = {
  type: 'tool'
  tool: string
  arguments: Record<string, unknown>
  status: Status
  data: Record<string, unknown>
  records: { sensitivity: string; data: Record<string, unknown> }[]
  error: string | null
  withheld: number
}

// Çalan hatırlatma: kişinin kendi sözleri, kaydından (§12)
export type ReminderMessage = { type: 'reminder'; text: string; due: string; priority: string }

// Sistemin bir parçası bozuldu (§5.4 hata kanalı). Tool'un `error` durumundan ayrıdır: o, bir
// isteğin yerine getirilemediği; bu, Mayen'in bir parçasının çalışmadığı.
export type FaultPart = 'model' | 'stt' | 'tts' | 'wake' | 'vad' | 'other'
export type FaultMessage = { type: 'fault'; part: FaultPart; detail: string }

export type Message = StateMessage | UtteranceMessage | ToolMessage | ReminderMessage | FaultMessage

export class SchemaError extends Error {}

export function parse(raw: string): Message {
  const data = JSON.parse(raw) as { schema_version?: unknown; type?: unknown }
  if (data.schema_version !== SCHEMA_VERSION) {
    throw new SchemaError(`schema_version ${String(data.schema_version)}, screen speaks ${SCHEMA_VERSION}`)
  }
  if (data.type !== 'state' && data.type !== 'utterance' && data.type !== 'tool' && data.type !== 'reminder'
      && data.type !== 'fault') {
    throw new SchemaError(`unknown message type ${String(data.type)}`)
  }
  return data as Message
}
