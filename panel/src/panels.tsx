// Paneller: veriyi parçalara döker. Yerleşime karışmaz; o App'tedir.
import { AnimatePresence, motion } from 'motion/react'
import type { EventMessage, Item } from './contract'
import { CEVIK } from './hareket'
import { clock, seconds, type Session, type Step, type Turn } from './model'
import { Row, StateMark } from './parts'

const STATE_NAME: Record<Session['state'], string> = {
  idle: 'idle',
  listening: 'listening',
  thinking: 'thinking',
  speaking: 'speaking',
  awaiting_confirmation: 'awaiting confirmation',
}

export function SessionsContent({ sessions }: { sessions: Session[] }) {
  if (!sessions.length) return <span className="etiket soluk">no sessions</span>
  return (
    <div className="kaydir">
      <AnimatePresence initial={false}>
        {sessions.map(s => (
          <motion.div key={s.id} layout transition={CEVIK}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 0',
                     borderBottom: '1px solid var(--kagit-4)' }}>
            <StateMark state={s.state} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="sayi" style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.id}
              </div>
              <motion.div key={s.state} className="etiket" initial={{ opacity: 0, y: -3 }} animate={{ opacity: 1, y: 0 }}
                style={{ color: s.state === 'idle' ? 'var(--kagit-3)' : 'var(--isaret)', marginTop: 3 }}>
                {STATE_NAME[s.state]} · {clock(s.since)}
              </motion.div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

function json(value: unknown): string {
  return JSON.stringify(value)
}

function StepRow({ step }: { step: Step }) {
  if (step.kind === 'said') {
    const u = step.utterance
    const mine = u.party === 'assistant'
    return (
      <div style={{ display: 'flex', gap: 10, padding: '4px 0' }}>
        <span className="etiket soluk" style={{ width: 64, flex: 'none' }}>{mine ? 'mayen' : (u.role ?? 'person')}</span>
        <span style={{ fontSize: 13.5, lineHeight: 1.4, color: mine ? 'var(--kagit)' : 'var(--kagit-2)' }}>
          {u.text}{u.interrupted && <span className="vurgu"> ✂</span>}
        </span>
      </div>
    )
  }
  if (step.kind === 'tool') {
    const failed = step.status !== null && step.status !== 'ok'
    return (
      <div style={{ padding: '4px 0 4px 74px' }}>
        <div className="sayi" style={{ fontSize: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--isaret)' }}>{step.tool}</span>
          <span className="soluk" style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{json(step.arguments)}</span>
        </div>
        <div className="etiket" style={{ marginTop: 2, color: failed ? 'var(--vurgu)' : 'var(--kagit-3)' }}>
          {step.verdict ?? 'malformed'} · {step.status ?? 'open'} · {seconds(step.duration_s)}
        </div>
      </div>
    )
  }
  const b = step.event.body
  return (
    <div style={{ padding: '4px 0 4px 74px' }}>
      <span className="etiket" style={{ color: step.event.status === 'ok' ? 'var(--isaret)' : 'var(--vurgu)' }}>
        confirmation · {String(b.confirmation)} · {seconds(step.event.duration_s)}
      </span>
    </div>
  )
}

function TurnCard({ turn }: { turn: Turn }) {
  const s = turn.start?.body
  const end = turn.end
  const requester = s?.requester as { role?: string } | undefined
  const running = !end
  return (
    <motion.article layout transition={CEVIK} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
      style={{ padding: '12px 0', borderBottom: '1px solid var(--kagit-4)' }}>
      <header style={{ display: 'flex', gap: 14, alignItems: 'baseline', marginBottom: 6, flexWrap: 'wrap' }}>
        <span className="etiket" style={{ color: running ? 'var(--isaret)' : undefined }}>
          {String(s?.source ?? '?')}{requester?.role ? ` · ${requester.role}` : ''}
        </span>
        <span className="sayi soluk" style={{ fontSize: 11.5 }}>{turn.start ? clock(turn.start.time) : '…'}</span>
        <span className="sayi soluk" style={{ fontSize: 11.5 }}>
          {running ? 'running' : `${end.kind === 'turn.interrupted' ? `interrupted (${String(end.body.fate)})` : 'finished'} · ${seconds(end.duration_s)}`}
        </span>
        {(turn.tokens.prompt > 0 || turn.tokens.completion > 0) && (
          <span className="sayi soluk" style={{ fontSize: 11.5 }}>{turn.tokens.prompt}→{turn.tokens.completion} tok</span>
        )}
        {end?.body.unanswered === true && <span className="etiket vurgu">unanswered</span>}
      </header>
      {turn.steps.map(step => <StepRow key={step.id} step={step} />)}
    </motion.article>
  )
}

export function TurnsContent({ turns }: { turns: Turn[] }) {
  if (!turns.length) return <span className="etiket soluk">no turns yet</span>
  return (
    <div className="kaydir" style={{ paddingRight: 6 }}>
      <AnimatePresence initial={false}>
        {turns.slice(0, 100).map(t => <TurnCard key={t.id} turn={t} />)}
      </AnimatePresence>
    </div>
  )
}

const isEvent = (i: Item): i is EventMessage => i.type === 'event'

export function StreamContent({ items }: { items: Item[] }) {
  const events = items.filter(isEvent).slice(-200).reverse()
  return (
    <div className="kaydir">
      <AnimatePresence initial={false}>
        {events.map(e => (
          <motion.div key={e.id} layout transition={CEVIK} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
            style={{ display: 'grid', gridTemplateColumns: '64px 1fr auto', gap: 8, padding: '3px 0', alignItems: 'baseline' }}>
            <span className="sayi soluk" style={{ fontSize: 11 }}>{clock(e.time)}</span>
            <span className="sayi" style={{ fontSize: 11.5, color: e.status && e.status !== 'ok' ? 'var(--vurgu)' : 'var(--kagit-2)' }}>
              {e.kind}{e.kind === 'state.changed' ? ` → ${String(e.body.state)}` : ''}
            </span>
            <span className="sayi soluk" style={{ fontSize: 11 }}>{e.duration_s != null ? seconds(e.duration_s) : ''}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

export function Summary({ items, turns }: { items: Item[]; turns: Turn[] }) {
  const tools = turns.flatMap(t => t.steps).filter(s => s.kind === 'tool')
  const failed = tools.filter(s => s.kind === 'tool' && s.status !== null && s.status !== 'ok').length
  const done = turns.filter(t => t.end?.duration_s != null).map(t => t.end!.duration_s!)
  const median = done.length ? [...done].sort((a, b) => a - b)[Math.floor(done.length / 2)] : null
  return <>
    <Row name="turns">{turns.length}</Row>
    <Row name="tool calls">{tools.length}{failed ? ` · ${failed} failed` : ''}</Row>
    <Row name="median turn">{seconds(median)}</Row>
    <Row name="records">{items.length}</Row>
  </>
}
