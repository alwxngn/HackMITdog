import { patchConfig } from './store'

/** Turn the warning/danger zones on or off. Returns an error message, or null on success. */
export async function setNightWatch(enabled: boolean): Promise<string | null> {
  try {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ night_watch_enabled: enabled }),
    })
    if (!r.ok) throw new Error(String(r.status))
    patchConfig({ night_watch_enabled: enabled })
    return null
  } catch {
    return 'Couldn’t reach Lantern. Check that the server is running.'
  }
}
