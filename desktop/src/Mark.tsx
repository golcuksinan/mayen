// Ortadaki M: logonun üç parçası (iki dikme ve aralarındaki ayrık V) duruma göre ayrı ayrı
// hareket eder. Parlama ve gradyan yok (logonun dili); çevresinde yalnızca köşeler.
// Hareket ölçülü: yay yok, hedefi aşmadan durur, genlikler küçük; boştayken hiçbir şey kıpırdamaz.
// Parçaların ölçüleri logo üreticisinden (insta-llm docs/logo/uret.py): 67.06 × 58.
import { motion, type Transition } from 'motion/react'
import type { SessionState } from './contract'

export type MarkState = SessionState | 'failed'

const W = 67.06
const H = 58
const BAR = 12.69
const V = 'M19.94,5.04L33.53,23.96L47.12,5.04L47.12,25.04L33.53,43.96L19.94,25.04Z'

/** Geçiş: hedefi aşmadan yavaşlayarak durur (köşe çiziminin eğrisi). */
const EASE: Transition = { duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }

const loop = (duration: number, delay = 0): Transition =>
  ({ duration, delay, repeat: Infinity, ease: 'easeInOut' })

type Pose = { x?: number | number[]; y?: number | number[]; scaleY?: number | number[]; opacity?: number | number[] }
type Poses = { left: Pose; right: Pose; v: Pose; tl?: Transition; tr?: Transition; tv?: Transition }

const REST: Pose = { x: 0, y: 0, scaleY: 1, opacity: 1 }

const POSES: Record<MarkState, Poses> = {
  idle: { left: { ...REST, opacity: 0.8 }, right: { ...REST, opacity: 0.8 }, v: REST },
  listening: { left: { ...REST, x: -3 }, right: { ...REST, x: 3 }, v: { ...REST, y: -2 } },
  thinking: { left: { ...REST, opacity: 0.75 }, right: { ...REST, opacity: 0.75 }, v: REST },
  speaking: {
    left: { ...REST, scaleY: [1, 0.9, 1] },
    right: { ...REST, scaleY: [1, 0.9, 1] },
    v: REST,
    tl: loop(1.1), tr: loop(1.1, 0.35),
  },
  awaiting_confirmation: {
    left: { ...REST, opacity: 0.55 }, right: { ...REST, opacity: 0.55 },
    v: { ...REST, opacity: [1, 0.35, 1] },
    tv: loop(1.6),
  },
  failed: {
    left: { ...REST, opacity: 0.6 }, right: { ...REST, opacity: 0.6 },
    v: { ...REST, y: [0, 4, 0] },
    tv: { duration: 0.7, ease: [0.2, 0.7, 0.2, 1] },
  },
}

// V boştayken gri, düşünürken beyaz, öteki her durumda logodaki kırmızısı
const V_FILL: Record<MarkState, string> = {
  idle: 'var(--kagit-3)',
  listening: 'var(--vurgu)',
  thinking: 'var(--kagit)',
  speaking: 'var(--vurgu)',
  awaiting_confirmation: 'var(--vurgu)',
  failed: 'var(--vurgu)',
}

function Brackets({ state, size }: { state: MarkState; size: number }) {
  const r = size * 0.09
  const half = size / 2
  const scale = state === 'listening' ? 0.9 : 1
  const color = state === 'awaiting_confirmation' || state === 'failed' ? 'var(--vurgu)'
    : state === 'idle' ? 'var(--cerceve)' : 'var(--cerceve-vurgu)'
  const corner = (d: string, i: number) => (
    <motion.path key={i} d={d} fill="none" strokeWidth={1.5} style={{ stroke: color, transition: 'stroke .5s' }}
      initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ ...EASE, delay: i * 0.05 }} />
  )
  return (
    <motion.g style={{ originX: '50%', originY: '50%' }} animate={{ scale }} transition={EASE}>
      {corner(`M${-half} ${-half + r} V${-half} H${-half + r}`, 0)}
      {corner(`M${half - r} ${-half} H${half} V${-half + r}`, 1)}
      {corner(`M${half} ${half - r} V${half} H${half - r}`, 2)}
      {corner(`M${-half + r} ${half} H${-half} V${half - r}`, 3)}
    </motion.g>
  )
}

// Eksik çizgili halka: bir yayı hep açık kalır; yalnızca düşünürken düzgün hızla döner
function Ring({ state, radius }: { state: MarkState; radius: number }) {
  const c = 2 * Math.PI * radius
  const spinning = state === 'thinking'
  return (
    <motion.circle r={radius} fill="none" strokeWidth={1}
      style={{ stroke: 'var(--kagit-3)', originX: '50%', originY: '50%' }}
      strokeDasharray={`${c * 0.86} ${c * 0.14}`}
      animate={spinning ? { rotate: [0, 360], opacity: 0.8 } : { opacity: state === 'idle' ? 0.35 : 0.7 }}
      transition={spinning ? { rotate: { duration: 2.4, repeat: Infinity, ease: 'linear' }, opacity: EASE } : EASE} />
  )
}

export function Mark({ state, size = 300 }: { state: MarkState; size?: number }) {
  const p = POSES[state]
  const scale = (size * 0.42) / W
  return (
    <svg width={size} height={size} viewBox={`${-size / 2} ${-size / 2} ${size} ${size}`} style={{ overflow: 'visible' }}>
      <Ring state={state} radius={size * 0.4} />
      <Brackets state={state} size={size * 0.62} />
      <g transform={`scale(${scale}) translate(${-W / 2} ${-H / 2})`}>
        <motion.rect width={BAR} height={H} style={{ fill: 'var(--kagit)', originY: '50%' }}
          animate={p.left} transition={p.tl ?? EASE} />
        <motion.rect x={W - BAR} width={BAR} height={H} style={{ fill: 'var(--kagit)', originY: '50%' }}
          animate={p.right} transition={p.tr ?? EASE} />
        <motion.path d={V} style={{ fill: V_FILL[state], originX: '50%', originY: '50%', transition: 'fill .4s' }}
          animate={p.v} transition={p.tv ?? EASE} />
      </g>
    </svg>
  )
}
