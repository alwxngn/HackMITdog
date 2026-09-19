import { handleBusMessage } from './store'
import type { Envelope } from './types'

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ||
  `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:8000/ws`

let socket: WebSocket | null = null
let retries = 0
let stop = false

export function connectBus() {
  stop = false
  open()
}

export function disconnectBus() {
  stop = true
  socket?.close()
  socket = null
}

function open() {
  if (stop) return
  socket = new WebSocket(WS_URL)
  socket.onopen = () => {
    retries = 0
    console.info('[ws] connected', WS_URL)
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
