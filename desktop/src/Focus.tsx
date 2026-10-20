// Odak yerleşimi (deneysel): kişinin gözü başka yerdeyken (oyun, video, gece) ekran tek bir
// şey gösterir ve bakılmadan da olur. Neyin tetiklediği görünümü değiştirmez; ortada ne
// olduğunu o an önemli olan belirler (`center`): onay bekleyen soru > çalan hatırlatma > az
// önce gelen tool sonucu > bozulan parça > çalan müzik > saat; bozulan parça ortada değilse köşede tek satırdır. Echo Show / Nest Hub'ın ortam ekranı gibi: ayrı yerleşimler yok, ortadaki
// şey değişir. M köşede küçülür ama durumu yine gösterir, konuşmanın son sözü altta tek satırdır.
// Parçalar normal yerleşimdekilerle aynı layoutId'yi taşır: geçişte yerinden kayarak oturur.
import { AnimatePresence, motion } from 'motion/react'
import { YERLESIM } from '../../panel/src/hareket'
import type { FaultMessage } from './contract'
import { CardBody, failed, FAULT, TITLE } from './cards'
import { Mark, type MarkState } from './Mark'
import type { Card, Screen } from './screen'

const step = (i: number) => ({ ...YERLESIM, delay: i * 0.08 })

const str = (v: unknown) => (v === null || v === undefined ? '' : String(v))

// Az önce gelen tool sonucu bu kadar ortada kalır, sonra yerini öncekine bırakır
const RESULT_MS = 8_000
// Çalan hatırlatma bu kadar ortada kalır
const REMINDER_MS = 20_000
// Son söz bu kadar kalır, sonra kalkar: eski söz orada asılı kalmasın
const SUBTITLE_MS = 10_000

// Ortada yalnızca kendini belli etmeyen sonuçlar durur: çalan müzik zaten müzik olarak görünür,
// açılan uygulama ya da öne gelen pencere zaten ekranda.
const QUIET_TOOLS = new Set(['media', 'apps', 'window', 'window_close'])

type Center =
  | { kind: 'question'; text: string }
  | { kind: 'reminder'; text: string; due: string }
  | { kind: 'result'; card: Card }
  | { kind: 'music'; card: Card }
  | { kind: 'clock' }
  | { kind: 'fault'; fault: FaultMessage }

function center(screen: Screen, mark: MarkState, now: number): Center {
  if (mark === 'awaiting_confirmation') {
    const asked = [...screen.words].reverse().find(w => w.party === 'assistant')
    return { kind: 'question', text: asked?.text ?? '' }
  }
  const reminder = screen.reminder
  if (reminder && now - reminder.at < REMINDER_MS) return { kind: 'reminder', text: reminder.text, due: reminder.due }
  const recent = screen.cards.find(c => now - c.at < RESULT_MS && (failed(c) || !QUIET_TOOLS.has(c.tool)))
  if (recent) return { kind: 'result', card: recent }
  // Bozulan parça: ortada daha önemli bir şey yoksa; varsa köşede tek satırdır (`Faulted`).
  // Sonuç onu bastırmaz: ses bozukken cevabı ekrandan öğrenmenin tek yolu sonucun kendisidir.
  if (screen.fault) return { kind: 'fault', fault: screen.fault }
  // Çalıyor mu: bugün yalnızca son media sonucundan (durdurulmadıysa); istemci oynatıcıyı
  // kendisi izleyince oradan gelecek.
  const media = screen.cards.find(c => c.tool === 'media' && c.status === 'ok' && !c.data.players)
  if (media && media.arguments.action !== 'pause') return { kind: 'music', card: media }
  return { kind: 'clock' }
}

function Clock({ now }: { now: number }) {
  const time = new Date(now).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
  return <div className="sayi" style={{ fontSize: 220, letterSpacing: '0.04em', color: 'var(--kagit-2)', lineHeight: 1 }}>{time}</div>
}

function Music({ card }: { card: Card }) {
  const d = card.data
  return (
    <div style={{ textAlign: 'center', maxWidth: '80vw' }}>
      <div style={{ fontSize: 64, fontWeight: 600, fontStretch: '112%', lineHeight: 1.05 }}>{str(d.title) || str(d.player)}</div>
      <div style={{ fontSize: 24, marginTop: 14, color: 'var(--kagit-2)' }}>{str(d.artist)}</div>
      <div className="etiket soluk" style={{ marginTop: 18 }}>{str(d.player)}</div>
    </div>
  )
}

function Result({ card }: { card: Card }) {
  return (
    <div style={{ minWidth: 420, maxWidth: '60vw', transform: 'scale(1.6)', transformOrigin: 'center' }}>
      <div className="etiket soluk" style={{ marginBottom: 10 }}>{TITLE[card.tool] ?? card.tool.replace(/_/g, ' ')}</div>
      <CardBody card={card} />
    </div>
  )
}

function Question({ text }: { text: string }) {
  return (
    <div style={{ textAlign: 'center', maxWidth: '70vw' }}>
      <div className="etiket" style={{ color: 'var(--vurgu)', marginBottom: 18 }}>awaiting confirmation</div>
      <div style={{ fontSize: 48, fontWeight: 600, lineHeight: 1.15 }}>{text}</div>
    </div>
  )
}

function Reminder({ text, due }: { text: string; due: string }) {
  const time = new Date(due).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
  return (
    <div style={{ textAlign: 'center', maxWidth: '70vw' }}>
      <div className="etiket" style={{ color: 'var(--isaret)', marginBottom: 18 }}>reminder · <span className="sayi">{time}</span></div>
      <div style={{ fontSize: 64, fontWeight: 600, fontStretch: '112%', lineHeight: 1.1 }}>{text}</div>
    </div>
  )
}

function Fault({ fault }: { fault: FaultMessage }) {
  return (
    <div style={{ textAlign: 'center', maxWidth: '70vw' }}>
      <div className="etiket" style={{ color: 'var(--vurgu)', marginBottom: 18 }}>fault</div>
      <div style={{ fontSize: 64, fontWeight: 600, fontStretch: '112%', lineHeight: 1.1 }}>{FAULT[fault.part]}</div>
      <div className="soluk" style={{ fontSize: 18, marginTop: 18, overflowWrap: 'anywhere' }}>{fault.detail}</div>
    </div>
  )
}

function Faulted({ fault }: { fault: FaultMessage }) {
  return (
    <motion.div className="etiket" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      // M'nin (88 px) yüksekliğinde bir şerit: yazı onun ortasına hizalanır
      style={{ position: 'absolute', top: 0, right: 104, height: 88, display: 'flex', alignItems: 'center',
               lineHeight: 1, color: 'var(--vurgu)' }}>
      {FAULT[fault.part]}
    </motion.div>
  )
}

function Middle({ shown }: { shown: Center }) {
  const key = shown.kind === 'result' ? `result-${shown.card.tool}-${shown.card.at}` : shown.kind
  return (
    <AnimatePresence mode="wait">
      <motion.div key={key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, transition: step(1) }}
        exit={{ opacity: 0, y: -10, transition: { duration: 0.25 } }}>
        {shown.kind === 'clock' && <Clock now={Date.now()} />}
        {shown.kind === 'music' && <Music card={shown.card} />}
        {shown.kind === 'result' && <Result card={shown.card} />}
        {shown.kind === 'question' && <Question text={shown.text} />}
        {shown.kind === 'reminder' && <Reminder text={shown.text} due={shown.due} />}
        {shown.kind === 'fault' && <Fault fault={shown.fault} />}
      </motion.div>
    </AnimatePresence>
  )
}

function Subtitle({ screen, now, hidden }: { screen: Screen; now: number; hidden: boolean }) {
  const said = screen.words.at(-1)
  const last = !hidden && said && now - Date.parse(said.time) < SUBTITLE_MS ? said : undefined
  return (
    <motion.div layoutId="talk" transition={step(2)}
      style={{ position: 'absolute', left: '10vw', right: '10vw', bottom: 40, height: 32,
               display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: 12, overflow: 'hidden' }}>
      <AnimatePresence mode="wait">
        {last && (
          <motion.div key={`${last.time}-${screen.words.length}`} layout="position" transition={step(2)} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }} style={{ display: 'flex', gap: 12, alignItems: 'baseline', minWidth: 0 }}>
            <span className="etiket" style={{ flex: 'none', color: last.party === 'assistant' ? 'var(--isaret)' : 'var(--kagit-3)' }}>
              {last.party === 'assistant' ? 'mayen' : (last.role ?? 'unknown')}
            </span>
            <span style={{ fontSize: 18, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                           color: 'var(--kagit-2)' }}>{last.text}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function Focus({ screen, mark, now }: { screen: Screen; mark: MarkState; now: number }) {
  const shown = center(screen, mark, now)
  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center' }}>
      <motion.div layoutId="mark" transition={YERLESIM} style={{ position: 'absolute', top: 0, right: 0 }}>
        <Mark state={mark} size={88} />
      </motion.div>
      <AnimatePresence>
        {screen.fault && shown.kind !== 'fault' && <Faulted key="faulted" fault={screen.fault} />}
      </AnimatePresence>
      <Middle shown={shown} />
      {/* Onay sorusu ortadayken altta tekrar yazılmaz */}
      <Subtitle screen={screen} now={now} hidden={shown.kind === 'question'} />
    </div>
  )
}
