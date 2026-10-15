// Ortak hareket dili. Her animasyon buradaki değerlerden birini kullanır; bileşenin içinde
// yeni bir süre ya da yay yazılmaz — hareket hissi tek yerden ayarlansın.
import type { Transition } from 'motion/react'

/** Yerleşim değişimi: ağır ama oturaklı, hafif taşıp yerine oturur. */
export const YERLESIM: Transition = { type: 'spring', stiffness: 210, damping: 28, mass: 1 }

/** Küçük öğeler (satır, rozet): daha çevik. */
export const CEVIK: Transition = { type: 'spring', stiffness: 420, damping: 34 }

/** Değer göstergeleri (yay, çubuk): veri değişince yumuşak takip. */
export const DEGER = { stiffness: 90, damping: 20 }

/** Açılış sırası: panel başına gecikme ve panel içindeki parça başına gecikme (sn). */
export const SIRA = { panel: 0.07, parca: 0.05 }

/** Çerçeve köşelerinin çizilme süresi. */
export const CIZIM: Transition = { duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }
