import { handleBusMessage } from './store'
import type { Envelope } from './types'

/** Same-origin WS so Vite proxy + Cloudflare/ngrok tunnel work on phone. */
function wsUrl(): string {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL as string
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

let socket: WebSocket | null = null
let retries = 0
let stop = false
let pollTimer: ReturnType<typeof setInterval> | null = null

/** If the WebSocket can't connect (blocked by a proxy/tunnel), keep the UI live by polling. */
function startPolling() {
  if (pollTimer) return
  const tick = () =>
    fetch('/api/snapshot')
      .then((r) => r.json())
      .then((msg: Envelope) => handleBusMessage(msg))
      .catch(() => {})
  void tick()
  pollTimer = setInterval(tick, 2000)
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

export function connectBus() {
  stop = false
  open()
}

export function disconnectBus() {
  stop = true
  stopPolling()
  socket?.close()
  socket = null
}

function open() {
  if (stop) return
  const url = wsUrl()
  socket = new WebSocket(url)
  socket.onopen = () => {
    retries = 0
    stopPolling()
    console.info('[ws] connected', url)
  }
  socket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data) as Envelope
      handleBusMessage(msg)
    } catch (e) {
      console.warn('[ws] bad message', e)
    }
  }
  socket.onclose = () => {
    if (stop) return
    startPolling()
    const delay = Math.min(8000, 400 * 2 ** retries)
    retries += 1
    console.warn(`[ws] closed — reconnect in ${delay}ms`)
    setTimeout(open, delay)
  }
  socket.onerror = () => socket?.close()
}

export function sendBus(msg: Partial<Envelope>) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg))
  }
}
