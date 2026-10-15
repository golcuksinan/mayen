// Yerleşim: geniş ekranda sayfa kaymayan sabit ızgara, dar ekranda (telefon) tek sütun.
// Renk değerleri yoğunluktan (theme.ts); yoğunluk oturumların durumundan.
import { LayoutGroup, motion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import logo from './mayen-yazi.svg?raw'
import { HISTORY_H, useFeed, type Connection } from './feed'
import { level, sessions, turns } from './model'
import { SessionsContent, StreamContent, Summary, TurnsContent } from './panels'
import { Panel } from './parts'
import { THEME } from './theme'

const WIDE = ['sessions turns stream', 'summary turns stream']
const NARROW = ['sessions', 'turns', 'summary', 'stream']

const CONNECTION: Record<Connection, string> = {
  connecting: 'connecting',
  history: 'loading history',
  live: 'live',
  lost: 'reconnecting',
  incompatible: 'incompatible core',
}

// Logo: koyu zemin dikdörtgeni atılır, harfler sayfanın zemininde durur; görünüm kutusu harflere daraltılır
const LOGO = logo
  .replace(/<rect[^>]*\/>/, '')
  .replace(/viewBox="0 0 (\S+) 200"/, (_, w: string) => `viewBox="40 71 ${+w - 80} 58" height="20"`)

function useScreen() {
  const [s, setS] = useState({ w: window.innerWidth, h: window.innerHeight })
  useEffect(() => {
    const f = () => setS({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [])
  return s
}

function useNow(ms: number) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const i = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(i)
  }, [ms])
  return now
}

export default function App() {
  const feed = useFeed()
  const screen = useScreen()
  const now = useNow(5000) // uyarı penceresi kaysın
  const all = useMemo(() => sessions(feed.items), [feed.items])
  const grouped = useMemo(() => turns(feed.items), [feed.items])
  const lvl = level(feed.items, all, now)
  const wide = screen.w >= 1100 && screen.h >= 640
  const busy = all.some(s => s.state !== 'idle')

  return (
    <motion.div initial={THEME.calm} animate={THEME[lvl]} transition={{ duration: 0.9, ease: 'easeInOut' }}
      style={{ height: wide ? '100vh' : 'auto', minHeight: '100vh', display: 'flex', flexDirection: 'column',
               padding: wide ? '20px 28px 24px' : '16px 14px', background: 'var(--zemin)' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, gap: 20, flex: 'none' }}>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}
          style={{ display: 'flex' }} dangerouslySetInnerHTML={{ __html: LOGO }} />
        <div style={{ display: 'flex', gap: 22, alignItems: 'baseline' }}>
          <motion.span key={feed.connection} className="etiket" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
            style={{ color: feed.connection === 'live' ? 'var(--isaret)' : 'var(--vurgu)' }}>
            {CONNECTION[feed.connection]}
          </motion.span>
          {wide && <span className="etiket soluk">last {HISTORY_H} h</span>}
        </div>
      </header>

      {feed.error && (
        <div className="etiket vurgu" style={{ marginBottom: 12 }}>{feed.error}</div>
      )}

      <LayoutGroup>
        <main style={{ flex: 1, minHeight: 0, display: 'grid', gap: 'var(--bosluk)',
                       gridTemplateColumns: wide ? 'minmax(0,0.8fr) minmax(0,1.6fr) minmax(0,1fr)' : 'minmax(0,1fr)',
                       gridTemplateRows: wide ? 'minmax(0,1fr) auto' : undefined,
                       gridTemplateAreas: (wide ? WIDE : NARROW).map(a => `"${a}"`).join(' ') }}>
          <Panel id="sessions" title="Sessions" order={0} accent={busy}
            style={{ gridArea: 'sessions', ...(wide ? {} : { maxHeight: 260 }) }}>
            <SessionsContent sessions={all} />
          </Panel>
          <Panel id="turns" title="Turns" order={1} accent={busy}
            style={{ gridArea: 'turns', ...(wide ? {} : { height: 520 }) }}>
            <TurnsContent turns={grouped} />
          </Panel>
          <Panel id="summary" title="Summary" order={2} right={`${HISTORY_H} h`} style={{ gridArea: 'summary' }}>
            <Summary items={feed.items} turns={grouped} />
          </Panel>
          <Panel id="stream" title="Events" order={3}
            style={{ gridArea: 'stream', ...(wide ? {} : { height: 360 }) }}>
            <StreamContent items={feed.items} />
          </Panel>
        </main>
      </LayoutGroup>

      {feed.connection === 'lost' && !feed.items.length && (
        <div className="etiket soluk" style={{ textAlign: 'center', marginTop: 24 }}>
          the core is unreachable, or this device is not the owner's, or this address is not in panel.origins
        </div>
      )}
    </motion.div>
  )
}
