// Görsel dilin temel parçaları (insta-llm panelinden). Paneller yalnızca bunları kullanır.
import { motion } from 'motion/react'
import type { CSSProperties, ReactNode } from 'react'
import type { SessionState } from './contract'
import { CEVIK, CIZIM, SIRA, YERLESIM } from './hareket'

/** Panel: tam kenarlık yok, yalnızca dört köşe. Bulunduğu ızgara bölgesini doldurur. */
export function Panel({ id, title, right, accent, order, style, children }: {
  id: string; title: string; right?: ReactNode; accent?: boolean; order: number
  style?: CSSProperties; children: ReactNode
}) {
  const delay = order * SIRA.panel
  return (
    <motion.section
      layout
      layoutId={id}
      transition={YERLESIM}
      style={{ ...style, position: 'relative', padding: '16px 20px 18px', minWidth: 0, minHeight: 0,
               display: 'flex', flexDirection: 'column',
               background: accent ? 'var(--yuzey-vurgu)' : 'var(--yuzey)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { delay, duration: 0.25 } }}
    >
      <Corners accent={accent} delay={delay} />
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12, flex: 'none' }}>
        <span className="etiket" style={{ color: accent ? 'var(--isaret)' : undefined }}>{title}</span>
        {right && <span className="etiket soluk">{right}</span>}
      </header>
      <motion.div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0, transition: { delay: delay + 0.25, ...YERLESIM } }}>
        {children}
      </motion.div>
    </motion.section>
  )
}

function Corners({ accent, delay }: { accent?: boolean; delay: number }) {
  const r = 14
  // Köşelere sabitlenmiş dört ayrı SVG: panel büyüyüp küçülürken köşeler gerilmez
  const corner = (style: CSSProperties, d: string, i: number) => (
    <svg key={i} width={r} height={r} style={{ position: 'absolute', overflow: 'visible', ...style }}>
      <motion.path d={d} fill="none" strokeWidth={1.5}
        style={{ stroke: accent ? 'var(--cerceve-vurgu)' : 'var(--cerceve)' }}
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
        transition={{ ...CIZIM, delay: delay + i * 0.04 }} />
    </svg>
  )
  return <>
    {corner({ left: 0, top: 0 }, `M0 ${r} V0 H${r}`, 0)}
    {corner({ right: 0, top: 0 }, `M0 0 H${r} V${r}`, 1)}
    {corner({ right: 0, bottom: 0 }, `M${r} 0 V${r} H0`, 2)}
    {corner({ left: 0, bottom: 0 }, `M${r} ${r} H0 V0`, 3)}
  </>
}

/** Etiket + değer satırı. */
export function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, padding: '4px 0' }}>
      <span className="etiket soluk">{name}</span>
      <span className="sayi" style={{ fontSize: 12.5 }}>{children}</span>
    </div>
  )
}

/** Durumun işareti. Her durumun kendi hareketi var; metin yok, işaret konuşma değil veridir. */
export function StateMark({ state, size = 18 }: { state: SessionState; size?: number }) {
  const c = size / 2
  const stroke = 'var(--isaret)'
  switch (state) {
    case 'listening': // dışa açılan halka
      return (
        <svg width={size} height={size}>
          <circle cx={c} cy={c} r={c * 0.32} fill={stroke} />
          <motion.circle cx={c} cy={c} fill="none" stroke={stroke} strokeWidth={1.25}
            initial={{ r: c * 0.35, opacity: 0.9 }} animate={{ r: c * 0.95, opacity: 0 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeOut' }} />
        </svg>
      )
    case 'thinking': // dönen yay
      return (
        <motion.svg width={size} height={size} animate={{ rotate: 360 }}
          transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}>
          <circle cx={c} cy={c} r={c * 0.7} fill="none" stroke="var(--kagit-4)" strokeWidth={2} />
          <path d={`M${c} ${c * 0.3} A${c * 0.7} ${c * 0.7} 0 0 1 ${c * 1.7} ${c}`}
            fill="none" stroke={stroke} strokeWidth={2} strokeLinecap="round" />
        </motion.svg>
      )
    case 'speaking': // üç çubuk
      return (
        <svg width={size} height={size}>
          {[0, 1, 2].map(k => (
            <motion.rect key={k} x={size * (0.18 + k * 0.25)} width={size * 0.14} rx={1} fill={stroke}
              initial={{ height: size * 0.2, y: size * 0.4 }}
              animate={{ height: [size * 0.2, size * 0.7, size * 0.2], y: [size * 0.4, size * 0.15, size * 0.4] }}
              transition={{ duration: 0.7, repeat: Infinity, delay: k * 0.15, ease: 'easeInOut' }} />
          ))}
        </svg>
      )
    case 'awaiting_confirmation': // yanıp sönen eşkenar dörtgen, vurgu renginde
      return (
        <svg width={size} height={size}>
          <motion.path d={`M${c} ${c * 0.2} L${c * 1.8} ${c} L${c} ${c * 1.8} L${c * 0.2} ${c} Z`}
            fill="var(--vurgu)" animate={{ opacity: [1, 0.25, 1] }}
            transition={{ duration: 1, repeat: Infinity }} />
        </svg>
      )
    default: // boşta
      return (
        <svg width={size} height={size}>
          <motion.circle cx={c} cy={c} r={c * 0.28} fill="var(--kagit-3)"
            initial={{ scale: 0.6 }} animate={{ scale: 1 }} transition={CEVIK} />
        </svg>
      )
  }
}
