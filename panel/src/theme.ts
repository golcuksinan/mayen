// Yoğunluğa göre renk değerleri (insta-llm panelinin dili, soğuk paleti). Yoğunluk değişince App bunları kök
// öğede yayla canlandırır; bileşenler yalnızca CSS değişkenlerini okur, yoğunluğu bilmez.
import type { Level } from './model'

export const THEME: Record<Level, Record<string, string>> = {
  // Nötr, düşük kontrast, mavimsi: bakmasan da olur
  calm: {
    '--zemin': '#0B0D11',
    '--kagit': '#E3E8EF',
    '--yuzey': '#10141A',
    '--yuzey-vurgu': '#141A22',
    '--cerceve': 'rgba(227, 232, 239, 0.24)',
    '--cerceve-vurgu': 'rgba(227, 232, 239, 0.60)',
    '--kagit-2': 'rgba(227, 232, 239, 0.56)',
    '--kagit-3': 'rgba(227, 232, 239, 0.30)',
    '--kagit-4': 'rgba(227, 232, 239, 0.10)',
    '--isaret': 'rgba(227, 232, 239, 0.56)',
  },
  // Buz mavisi, daha kontrastlı: bir şey oluyor
  active: {
    '--zemin': '#08111A',
    '--kagit': '#D6ECFA',
    '--yuzey': '#0D1A26',
    '--yuzey-vurgu': '#112233',
    '--cerceve': 'rgba(92, 190, 255, 0.55)',
    '--cerceve-vurgu': 'rgba(92, 190, 255, 1)',
    '--kagit-2': 'rgba(214, 236, 250, 0.76)',
    '--kagit-3': 'rgba(214, 236, 250, 0.46)',
    '--kagit-4': 'rgba(214, 236, 250, 0.18)',
    '--isaret': 'rgba(92, 190, 255, 0.95)',
  },
  // Vurgu rengi her yerde: bak. Soğuk zeminde tek sıcak renk
  alert: {
    '--zemin': '#120C10',
    '--kagit': '#F0E1E4',
    '--yuzey': '#1A1016',
    '--yuzey-vurgu': '#26121B',
    '--cerceve': 'rgba(240, 70, 100, 0.50)',
    '--cerceve-vurgu': 'rgba(240, 70, 100, 1)',
    '--kagit-2': 'rgba(240, 225, 228, 0.66)',
    '--kagit-3': 'rgba(240, 225, 228, 0.38)',
    '--kagit-4': 'rgba(240, 225, 228, 0.13)',
    '--isaret': 'rgba(240, 70, 100, 1)',
  },
}
