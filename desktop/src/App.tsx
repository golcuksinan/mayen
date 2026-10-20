// Bir cihazın ekranı: solda durum ve konuşma, sağda tool kartları; odak yerleşimi Focus.tsx'te. Son çalışan tool'un kartı
// öne (sol üste) gelir, ötekiler yer açarak kayar. Renk yoğunluğu panelinkiyle aynı dildir.
import { AnimatePresence, LayoutGroup, motion } from 'motion/react'
import { useEffect, useState, type CSSProperties } from 'react'
import logo from '../../panel/src/mayen-yazi.svg?raw'
import { YERLESIM } from '../../panel/src/hareket'
import { Panel } from '../../panel/src/parts'
import { THEME } from '../../panel/src/theme'
import { CardBody, failed, FAULT, TITLE } from './cards'
import { Focus } from './Focus'
import { Mark, type MarkState } from './Mark'
import { isNight, useScreen, type Card, type Connection, type Screen } from './screen'

const LOGO = logo
  .replace(/<rect[^>]*\/>/, '')
  .replace(/viewBox="0 0 (\S+) 200"/, (_, w: string) => `viewBox="40 71 ${+w - 80} 58" height="20"`)

const CONNECTION: Record<Connection, string> = {
  connecting: 'connecting',
  live: 'live',
  lost: 'reconnecting',
}

const STATE: Record<MarkState, string> = {
  failed: 'failed',
  fault: 'fault',
  offline: 'no connection',
  idle: 'idle',
  listening: 'listening',
  thinking: 'thinking',
  speaking: 'speaking',
  awaiting_confirmation: 'awaiting confirmation',
}

const ALERT_MS = 8000

function useNow(ms: number) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const i = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(i)
  }, [ms])
  return now
}

const FAIL_MS = 1600

// Deneme kipi (D tuşu): konuşmadan bütün durumları sırayla gösterir
const DEMO: MarkState[] = ['idle', 'listening', 'thinking', 'speaking', 'awaiting_confirmation', 'failed', 'fault', 'offline']

function useDemo() {
  const [on, setOn] = useState(false)
  const [i, setI] = useState(0)
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'd' || e.key === 'D') setOn(v => !v) }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])
  useEffect(() => {
    if (!on) return
    setI(0)
    const t = setInterval(() => setI(k => (k + 1) % DEMO.length), 3500)
    return () => clearInterval(t)
  }, [on])
  return on ? DEMO[i] : null
}

// Odak: Mayen'e açtırılan oyun ya da video oynatıcı, yoksa gece saatleri. Tetikleyen ne olursa
// olsun yerleşim aynıdır. F elle açıp kapatır (deneme); durumdan gelen değişince el bırakılır.
function useFocus(screen: Screen, now: number): boolean {
  const auto = screen.activity !== null || isNight(screen.night, now)
  const [manual, setManual] = useState<boolean | null>(null)
  useEffect(() => { setManual(null) }, [auto])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === 'f' || e.key === 'F') setManual(v => !(v ?? auto)) }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [auto])
  return manual ?? auto
}

// F11 pencereyi tam ekrana alır ya da çıkarır; pencere Python'undur (pywebview), sayfa yalnızca iletir
function useFullscreen() {
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key !== 'F11') return
      e.preventDefault()
      window.pywebview?.api.fullscreen()
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])
}

function markState(screen: Screen, now: number): MarkState {
  if (screen.connection !== 'live') return 'offline'
  if (screen.fault) return 'fault'
  const last = screen.cards[0]
  if (last && failed(last) && now - last.at < FAIL_MS) return 'failed'
  return screen.state
}

function level(screen: Screen, now: number) {
  const recentFailure = screen.cards.some(c => failed(c) && now - c.at < ALERT_MS)
  if (screen.state === 'awaiting_confirmation' || recentFailure || screen.fault || screen.connection === 'lost') return 'alert'
  return screen.state === 'idle' ? 'calm' : 'active'
}

function Talk({ screen }: { screen: Screen }) {
  const end = useEnd(screen.words.length)
  return (
    <div className="kaydir" ref={end}>
      {screen.words.map((w, i) => (
        <motion.div key={`${w.time}-${i}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          style={{ padding: '6px 0', display: 'flex', gap: 12, alignItems: 'baseline' }}>
          <span className="etiket" style={{ width: 54, flex: 'none',
                color: w.party === 'assistant' ? 'var(--isaret)' : 'var(--kagit-3)' }}>
            {w.party === 'assistant' ? 'mayen' : (w.role ?? 'unknown')}
          </span>
          <span style={{ fontSize: 15, lineHeight: 1.4, opacity: w.interrupted ? 0.55 : 1 }}>{w.text}</span>
        </motion.div>
      ))}
    </div>
  )
}

function useEnd(count: number) {
  const [el, setEl] = useState<HTMLDivElement | null>(null)
  useEffect(() => { el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }) }, [el, count])
  return setEl
}

// Ortadaki işaret ve durumun adı
function State({ screen, mark, demo, size, style }:
  { screen: Screen; mark: MarkState; demo: MarkState | null; size: number; style: CSSProperties }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                      minHeight: 0, ...style }}>
      <motion.div layoutId="mark" transition={YERLESIM}>
        <Mark state={mark} size={size} />
      </motion.div>
      <motion.span key={mark} className="etiket" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
        style={{ fontSize: 13, color: mark === 'awaiting_confirmation' || mark === 'failed' || mark === 'fault' || mark === 'offline' ? 'var(--vurgu)' : 'var(--isaret)' }}>
        {mark === 'offline' && !demo ? CONNECTION[screen.connection]
          : mark === 'fault' && screen.fault ? FAULT[screen.fault.part] : STATE[mark]}
      </motion.span>
      {mark === 'fault' && screen.fault && (
        <motion.span key={screen.fault.detail} className="soluk" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ fontSize: 12, maxWidth: 320, textAlign: 'center', overflowWrap: 'anywhere' }}>
          {screen.fault.detail}
        </motion.span>
      )}
    </section>
  )
}

// Dikey ekran (telefon): üç sütun yerine üst üste işaret, konuşma ve son iki kart
const NARROW = '(max-aspect-ratio: 1/1)'

function useNarrow() {
  const [narrow, setNarrow] = useState(() => matchMedia(NARROW).matches)
  useEffect(() => {
    const query = matchMedia(NARROW)
    const change = () => setNarrow(query.matches)
    query.addEventListener('change', change)
    return () => query.removeEventListener('change', change)
  }, [])
  return narrow
}

function CardPanel({ card, order, first }: { card: Card; order: number; first: boolean }) {
  return (
    <Panel id={`card-${card.tool}`} title={TITLE[card.tool] ?? card.tool.replace(/_/g, ' ')}
      accent={first} order={order}>
      <motion.div key={card.at} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }}>
        <CardBody card={card} />
      </motion.div>
    </Panel>
  )
}

export default function App() {
  const screen = useScreen()
  const now = useNow(200)
  const demo = useDemo()
  useFullscreen()
  const focus = useFocus(screen, now)
  const narrow = useNarrow()
  const mark = demo ?? markState(screen, now)
  const lvl = demo
    ? (demo === 'awaiting_confirmation' || demo === 'failed' || demo === 'fault' || demo === 'offline' ? 'alert' : demo === 'idle' ? 'calm' : 'active')
    : level(screen, now)

  return (
    <motion.div initial={THEME.calm} animate={THEME[lvl]} transition={{ duration: 0.9, ease: 'easeInOut' }}
      style={{ height: '100vh', display: 'flex', flexDirection: 'column', padding: narrow ? '16px 16px 20px' : '20px 28px 24px', background: 'var(--zemin)',
               // Geçişte kayan parçalar pencereden taşabilir; pencere kaydırılmaz, içerik kendi alanında kayar.
               overflow: 'hidden' }}>
      <AnimatePresence initial={false}>
      {!focus && (
      <motion.header key="header" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.2 } }}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, flex: 'none' }}>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}
          style={{ display: 'flex' }} dangerouslySetInnerHTML={{ __html: LOGO }} />
        <div style={{ display: 'flex', gap: 22, alignItems: 'baseline' }}>
          {demo && <span className="etiket vurgu">demo</span>}
          <motion.span key={screen.connection} className="etiket" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
            style={{ color: screen.connection === 'live' ? 'var(--isaret)' : 'var(--vurgu)' }}>
            {CONNECTION[screen.connection]}
          </motion.span>
        </div>
      </motion.header>
      )}
      </AnimatePresence>

      {screen.error && <div className="etiket vurgu" style={{ marginBottom: 12 }}>{screen.error}</div>}

      <LayoutGroup>
        {focus ? <Focus screen={screen} mark={mark} now={now} /> : (
        narrow ? (
        <main style={{ flex: 1, minHeight: 0, display: 'grid', gap: 'var(--bosluk)',
                       gridTemplateColumns: 'repeat(2, minmax(0,1fr))',
                       gridTemplateRows: 'auto minmax(0,1fr) minmax(0,0.7fr)' }}>
          <State screen={screen} mark={mark} demo={demo} size={180} style={{ gridColumn: '1 / 3', gap: 16 }} />
          <Panel id="talk" title="Conversation" order={1} style={{ gridColumn: '1 / 3' }}>
            <Talk screen={screen} />
          </Panel>
          {screen.cards.slice(0, 2).map((card, i) => (
            <CardPanel key={card.tool} card={card} order={i + 2} first={i === 0} />
          ))}
        </main>
        ) : (
        <main style={{ flex: 1, minHeight: 0, display: 'grid', gap: 'var(--bosluk)',
                       gridTemplateColumns: 'minmax(0,1fr) minmax(0,1.25fr) minmax(0,1fr)',
                       gridTemplateRows: 'repeat(3, minmax(0,1fr))' }}>
          <Panel id="talk" title="Conversation" order={1} style={{ gridColumn: 1, gridRow: '1 / 4' }}>
            <Talk screen={screen} />
          </Panel>
          <State screen={screen} mark={mark} demo={demo} size={320} style={{ gridColumn: 2, gridRow: '1 / 4', gap: 28 }} />
          <div style={{ gridColumn: 3, gridRow: '1 / 4', minHeight: 0, display: 'grid', gap: 'var(--bosluk)',
                        gridTemplateRows: 'repeat(3, minmax(0,1fr))' }}>
            {screen.cards.slice(0, 3).map((card, i) => (
              <CardPanel key={card.tool} card={card} order={i + 2} first={i === 0} />
            ))}
          </div>
        </main>
        )
        )}
      </LayoutGroup>
    </motion.div>
  )
}
