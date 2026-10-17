// Tool kartlarının içleri. Her kart yalnızca tool'un sonucunu gösterir; metni model yazmaz.
// Bilinmeyen bir tool genel kartla görünür: yeni bir skill ekranı bozmaz, yalnızca sade görünür.
import { motion } from 'motion/react'
import { Row } from '../../panel/src/parts'
import { DEGER } from '../../panel/src/hareket'
import type { Card } from './screen'

const FAILED = new Set(['denied', 'error', 'unsupported', 'timeout', 'cancelled'])

export const TITLE: Record<string, string> = {
  media: 'Media',
  weather: 'Weather',
  window: 'Windows',
  window_close: 'Windows',
  volume: 'Volume',
  audio_output: 'Output',
  apps: 'Apps',
  time: 'Time',
  note_add: 'Notes',
  note_search: 'Notes',
  note_delete: 'Notes',
  reminder_add: 'Reminders',
  reminder_list: 'Reminders',
  reminder_delete: 'Reminders',
}

export const failed = (card: Card) => FAILED.has(card.status)

const str = (v: unknown) => (v === null || v === undefined ? '' : String(v))

function Big({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 30, fontWeight: 600, fontStretch: '112%', lineHeight: 1.1, marginBottom: 10 }}>{children}</div>
}

function Failure({ card }: { card: Card }) {
  return <>
    <Big><span className="vurgu">{card.status}</span></Big>
    {card.error && <div className="soluk" style={{ fontSize: 13 }}>{card.error}</div>}
  </>
}

function Media({ d }: { d: Record<string, unknown> }) {
  const players = d.players as Record<string, unknown>[] | undefined
  if (players) {
    return <>{players.map(p => (
      <div key={str(p.id)} style={{ padding: '6px 0' }}>
        <div style={{ fontSize: 16 }}>{str(p.title) || str(p.name)}</div>
        <div className="etiket soluk">{[p.artist, p.name, p.status].map(str).filter(Boolean).join(' · ')}</div>
      </div>
    ))}</>
  }
  return <>
    <Big>{str(d.title) || str(d.player)}</Big>
    <div style={{ fontSize: 15 }}>{str(d.artist)}</div>
    <div className="etiket soluk" style={{ marginTop: 8 }}>{str(d.player)}</div>
  </>
}

function Weather({ d }: { d: Record<string, unknown> }) {
  return <>
    <div className="etiket soluk">{str(d.place)}{d.default_location ? ' · default' : ''}</div>
    <Big><span className="sayi">{str(d.temperature_c)}°</span> <span style={{ fontSize: 18, fontWeight: 400 }}>{str(d.condition)}</span></Big>
    <Row name="feels like">{str(d.feels_like_c)}°</Row>
    <Row name="humidity">{str(d.humidity_percent)}%</Row>
    <Row name="wind">{str(d.wind_m_s)} m/s</Row>
  </>
}

function Windows({ card }: { card: Card }) {
  const d = card.data
  const list = d.windows as Record<string, unknown>[] | undefined
  if (list && card.status === 'ok') {
    return <>{list.map(w => (
      <div key={str(w.window)} style={{ display: 'flex', gap: 10, padding: '4px 0', alignItems: 'baseline',
                                        opacity: w.minimized ? 0.5 : 1 }}>
        <span className="sayi soluk" style={{ width: 18 }}>{str(w.window)}</span>
        <span style={{ fontSize: 13.5, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                       color: w.active ? 'var(--isaret)' : undefined }}>{str(w.title)}</span>
      </div>
    ))}</>
  }
  const action = card.tool === 'window_close' ? 'closed' : str(card.arguments.action)
  return <>
    <div className="etiket soluk">{action}</div>
    <Big>{str(d.title)}</Big>
    <div className="etiket soluk">{str(d.app)}</div>
  </>
}

function Volume({ d }: { d: Record<string, unknown> }) {
  const level = Number(d.level ?? 0)
  return <>
    <Big><span className="sayi">{level}</span>{d.muted ? <span className="vurgu" style={{ fontSize: 16 }}> muted</span> : null}</Big>
    <div style={{ height: 4, background: 'var(--kagit-4)' }}>
      <motion.div style={{ height: '100%', background: 'var(--isaret)' }}
        initial={{ width: 0 }} animate={{ width: `${Math.min(level, 100)}%` }} transition={{ type: 'spring', ...DEGER }} />
    </div>
  </>
}

function Generic({ card }: { card: Card }) {
  const entries = Object.entries(card.data).filter(([, v]) => typeof v !== 'object').slice(0, 6)
  return <>
    {entries.map(([k, v]) => <Row key={k} name={k.replace(/_/g, ' ')}>{str(v)}</Row>)}
    {card.records.slice(0, 6).map((r, i) => (
      <div key={i} style={{ fontSize: 13.5, padding: '3px 0' }}>
        {str(r.data.text ?? r.data.body ?? Object.values(r.data)[0])}
      </div>
    ))}
    {card.withheld > 0 && <div className="etiket soluk">{card.withheld} withheld</div>}
  </>
}

export function CardBody({ card }: { card: Card }) {
  if (failed(card)) return <Failure card={card} />
  switch (card.tool) {
    case 'media': return <Media d={card.data} />
    case 'weather': return <Weather d={card.data} />
    case 'window':
    case 'window_close': return <Windows card={card} />
    case 'volume': return <Volume d={card.data} />
    default: return <Generic card={card} />
  }
}
