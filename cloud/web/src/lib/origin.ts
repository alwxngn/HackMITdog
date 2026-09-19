/**
 * Public origin for QR codes and share links.
 * Prefer VITE_PUBLIC_ORIGIN when the laptop is on localhost but a tunnel is up;
 * otherwise use window.location.origin (works when already opened via tunnel).
 */
export function publicOrigin(): string {
  const fromEnv = (import.meta.env.VITE_PUBLIC_ORIGIN as string | undefined)?.replace(/\/$/, '')
  if (fromEnv) return fromEnv
  if (typeof window !== 'undefined') return window.location.origin
  return 'http://127.0.0.1:5173'
}

export function publicUrl(path: string): string {
  const base = publicOrigin()
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}${p}`
}
