// Yoğunluğa göre renk değerleri (insta-llm panelinin dili). Yoğunluk değişince App bunları kök
// öğede yayla canlandırır; bileşenler yalnızca CSS değişkenlerini okur, yoğunluğu bilmez.
import type { Level } from './model'

export const THEME: Record<Level, Record<string, string>> = {
  // Nötr, düşük kontrast: bakmasan da olur
  calm: {
    '--zemin': '#0E0E10',
    '--kagit': '#EDEAE3',
    '--yuzey': '#131316',
    '--yuzey-vurgu': '#18181C',
    '--cerceve': 'rgba(237, 234, 227, 0.26)',
    '--cerceve-vurgu': 'rgba(237, 234, 227, 0.62)',
    '--kagit-2': 'rgba(237, 234, 227, 0.56)',
    '--kagit-3': 'rgba(237, 234, 227, 0.30)',
    '--kagit-4': 'rgba(237, 234, 227, 0.10)',
    '--isaret': 'rgba(237, 234, 227, 0.56)',
  },
  // Sıcak ve daha kontrastlı: bir şey oluyor
  active: {
    '--zemin': '#15100A',
    '--kagit': '#FBE5C8',
    '--yuzey': '#21170D',
    '--yuzey-vurgu': '#2B1C0E',
    '--cerceve': 'rgba(255, 176, 92, 0.62)',
    '--cerceve-vurgu': 'rgba(255, 176, 92, 1)',
    '--kagit-2': 'rgba(251, 229, 200, 0.76)',
    '--kagit-3': 'rgba(251, 229, 200, 0.46)',
    '--kagit-4': 'rgba(251, 229, 200, 0.18)',
    '--isaret': 'rgba(255, 176, 92, 0.95)',
  },
  // Vurgu rengi her yerde: bak
  alert: {
    '--zemin': '#120D0D',
    '--kagit': '#F2E2DD',
    '--yuzey': '#1A1111',
    '--yuzey-vurgu': '#261312',
    '--cerceve': 'rgba(229, 72, 43, 0.50)',
    '--cerceve-vurgu': 'rgba(229, 72, 43, 1)',
    '--kagit-2': 'rgba(240, 226, 222, 0.66)',
    '--kagit-3': 'rgba(240, 226, 222, 0.38)',
    '--kagit-4': 'rgba(240, 226, 222, 0.13)',
    '--isaret': 'rgba(229, 72, 43, 1)',
  },
}
