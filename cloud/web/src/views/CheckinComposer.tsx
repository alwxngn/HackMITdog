import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { useVoiceCheckin } from '../hooks/useVoiceCheckin'
import { useProjection } from '../hooks/useProjection'
import { publicUrl } from '../lib/origin'

export function CheckinComposer() {
  const [fromName, setFromName] = useState('Michael')
  const [text, setText] = useState('')
  const [showPairing, setShowPairing] = useState(false)
  const [qr, setQr] = useState('')
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
  const status = voice.snapshot?.checkin ? statuses[voice.snapshot.checkin.status] : voice.snapshot?.phone_ready ? 'Phone ready' : voice.pairing ? 'Open the phone link and tap Start Lantern.' : ''

  useEffect(() => {
    let cancelled = false
    if (link) QRCode.toDataURL(link, { width: 200, margin: 1, color: { dark: '#0f3e17', light: '#fffefc' } }).then(src => { if (!cancelled) setQr(src) })
    return () => { cancelled = true }
  }, [link])

  async function send() {
    if (await voice.send(text.trim(), fromName)) setText('')
  }

  return (
    <div className="card">
      <h2 className="mb-2 text-[18px]">Check-in</h2>
      <p className="mb-4 text-[13px] text-[var(--color-charcoal)]">
        Robot delivers this attributed — never as you.
      </p>
      <button type="button" className="btn-ghost mb-3 !min-h-10 !px-3 !py-2 !text-[13px]" disabled={voice.busy} onClick={() => {
        setShowPairing(!showPairing)
        void voice.pair(patient, fromName)
      }}>
        {voice.snapshot?.phone_ready ? 'Phone connected' : 'Connect phone'}
      </button>
      {showPairing && link && (
        <div className="mb-4 rounded-[14px] border border-[var(--color-border-mist)] p-4 text-center">
          {qr && <img src={qr} alt="Pair Lantern voice on your phone" className="mx-auto h-40 w-40" />}
          <p className="my-2 text-[13px]">Scan on your phone, then tap Start Lantern.</p>
          <a href={link} target="_blank" rel="noopener noreferrer" className="break-all text-[12px] underline">Open phone voice</a>
          <button type="button" className="btn-ghost ml-2 !min-h-8 !px-2 !py-1 !text-[12px]" onClick={() => {
            void navigator.clipboard.writeText(link).catch(() => setShowPairing(true))
          }}>Copy link</button>
          {(link.includes('127.0.0.1') || link.includes('localhost')) && <p className="mt-2 text-[12px]">Open this portal through its HTTPS tunnel before pairing a physical phone.</p>}
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
        Send to robot
      </button>
      <p className="mt-2 text-[12px] text-[var(--color-charcoal)]">Leave blank to ask how {patient} is feeling.</p>
      {status && (
        <p role="status" className="mt-3 text-[13px] text-[var(--color-forest-ink)]">{status}</p>
      )}
      {voice.error && <p role="alert" className="mt-3 text-[13px]">{voice.error}</p>}
      {reply && <p className="mt-3 text-[14px]" data-testid="checkin-reply"><strong>{patient}:</strong> {String(reply.payload.text)}</p>}
      {voice.snapshot?.checkin?.needs_attention && <p className="mt-2 text-[13px]">Please review this reply. No emergency call has been placed.</p>}
    </div>
  )
}
