import { useEffect, useState } from 'react'
import type { Envelope } from '../lib/types'

interface Pairing {
  session_id: string
  caregiver_token: string
  phone_token: string
}

interface VoiceSnapshot {
  type: 'snapshot'
  phone_ready: boolean
  phone_online: boolean
  checkin: { status: string; needs_attention: boolean } | null
  utterance: { state: string } | null
  events: Envelope[]
}

const STORAGE = 'lantern-portal-voice'

function savedPairing(): Pairing | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(STORAGE) || 'null')
    return value?.session_id && value?.caregiver_token && value?.phone_token ? value : null
  } catch {
    return null
  }
}

async function request(path: string, body: unknown, token?: string) {
  const response = await fetch(`/voice/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the name and message, then try again.')
  return data
}

export function useVoiceCheckin() {
  const [pairing, setPairing] = useState<Pairing | null>(savedPairing)
  const [snapshot, setSnapshot] = useState<VoiceSnapshot | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!pairing) return
    let stopped = false
    let socket: WebSocket
    let heartbeat: ReturnType<typeof setInterval> | undefined
    let retry: ReturnType<typeof setTimeout> | undefined
    function open() {
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(`${protocol}//${location.host}/voice/ws/${pairing!.session_id}/caregiver`)
      socket.onopen = () => {
        socket.send(JSON.stringify({ token: pairing!.caregiver_token }))
        heartbeat = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'ping' }))
        }, 15000)
      }
      socket.onmessage = ({ data }) => {
        if (stopped) return
        const message = JSON.parse(data)
        if (message.type === 'snapshot') {
          setConnected(true)
          setSnapshot(message)
        }
      }
      socket.onclose = ({ code }) => {
        clearInterval(heartbeat)
        if (stopped) return
        setConnected(false)
        if (code === 4403) {
          sessionStorage.removeItem(STORAGE)
          setPairing(null)
          setSnapshot(null)
          setError('The phone session expired. Connect the phone again.')
        } else {
          retry = setTimeout(open, 2000)
        }
      }
    }
    open()
    return () => {
      stopped = true
      clearInterval(heartbeat)
      clearTimeout(retry)
      socket?.close()
    }
  }, [pairing])

  async function pair(patient: string, caregiver: string) {
    if (pairing) return
    setBusy(true)
    setError('')
    try {
      const result: Pairing = await request('/sessions', { patient, caregiver })
      sessionStorage.setItem(STORAGE, JSON.stringify(result))
      setPairing(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not connect the phone.')
    } finally {
      setBusy(false)
    }
  }

  async function send(text: string, fromName: string): Promise<boolean> {
    if (!pairing) return false
    setBusy(true)
    setError('')
    try {
      await request(`/sessions/${pairing.session_id}/checkins`, { text, from_name: fromName }, pairing.caregiver_token)
      return true
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send the check-in.')
      return false
    } finally {
      setBusy(false)
    }
  }

  const ready = connected && snapshot?.phone_ready && !['pending', 'speaking'].includes(snapshot?.utterance?.state || '')
  return { pairing, snapshot, connected, ready, error, busy, pair, send }
}
