import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { useVoiceCheckin } from '../hooks/useVoiceCheckin'
import { useProjection } from '../hooks/useProjection'
import { publicUrl } from '../lib/origin'

export function CheckinComposer() {
  const [fromName, setFromName] = useState('')
  const [text, setText] = useState('')
  const [qr, setQr] = useState('')
  const [qrOpen, setQrOpen] = useState(false)
  const [sentOnce, setSentOnce] = useState(false)
  const voice = useVoiceCheckin()
  const projection = useProjection()
  const patientConfig = projection.config.patient as { preferred_name?: string; name?: string } | undefined
  const patient = patientConfig?.preferred_name || patientConfig?.name || 'Arthur'
  const link = voice.pairing ? `${publicUrl('/voice/phone')}#${new URLSearchParams({ session: voice.pairing.session_id, token: voice.pairing.phone_token })}` : ''
  const reply = [...(voice.snapshot?.events || [])].reverse().find(event => event.type === 'transcript')
  const statuses: Record<string, string> = {
    sent: 'Sent — waiting for playback', speaking: 'Lantern is speaking…', delivered: 'Delivered — waiting for a reply',
    responded: 'Reply received', interrupted: 'Speech interrupted', failed: 'Audio did not play. Check the phone.',
    unavailable: 'Phone disconnected before delivery.',
  }
  const status = sentOnce && voice.snapshot?.checkin ? statuses[voice.snapshot.checkin.status] : ''

  useEffect(() => {
    if (!voice.pairing && !voice.busy) void voice.pair(patient, 'Caregiver')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    let cancelled = false
    if (link) QRCode.toDataURL(link, { width: 200, margin: 1, color: { dark: '#0f3e17', light: '#fffefc' } }).then(src => { if (!cancelled) setQr(src) })
    return () => { cancelled = true }
  }, [link])

  async function getQr() {
    if (!voice.pairing && !voice.busy) await voice.pair(patient, 'Caregiver')
    setQrOpen(true)
  }

  async function send() {
    if (await voice.send(text.trim(), fromName)) {
      setText('')
      setSentOnce(true)
    }
  }

  return (
    <div className="card">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[18px]">Check-in</h2>
        <button type="button" className="btn-ghost !min-h-9 !px-3 !py-1 !text-[13px]" onClick={getQr} disabled={voice.busy}>
          Get QR
        </button>
      </div>
      {qrOpen && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/30" onClick={() => setQrOpen(false)}>
          <div
            role="dialog"
            aria-label="Phone pairing QR code"
            className="rounded-[14px] bg-[var(--color-cream-paper)] p-6 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            {qr && <img src={qr} alt="Pair Lantern voice on your phone" className="mx-auto h-44 w-44" />}
            <button type="button" className="btn-ghost mt-4 !min-h-9 !px-4 !py-1 !text-[13px]" onClick={() => setQrOpen(false)}>
              Close
            </button>
          </div>
        </div>
      )}
      <input
        className="input-field mb-2"
        value={fromName}
        onChange={(e) => setFromName(e.target.value)}
        placeholder="From"
        aria-label="From"
        maxLength={60}
      />
      <textarea
        className="input-field mb-3 min-h-[88px] resize-y"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Hi Mom, thinking of you…"
        aria-label="Check-in message"
        maxLength={500}
      />
      <button type="button" className="btn-primary !min-h-11 !px-5 !py-2 !text-[14px] disabled:opacity-50" onClick={send} disabled={!voice.ready || voice.busy}>
        Send
      </button>
      {status && (
        <p role="status" className="mt-3 text-[13px] text-[var(--color-forest-ink)]">{status}</p>
      )}
      {voice.error && <p role="alert" className="mt-3 text-[13px]">{voice.error}</p>}
      {reply && <p className="mt-3 text-[14px]" data-testid="checkin-reply"><strong>{patient}:</strong> {String(reply.payload.text)}</p>}
      {voice.snapshot?.checkin?.needs_attention && <p className="mt-2 text-[13px]">Please review this reply. No emergency call has been placed.</p>}
    </div>
  )
}
