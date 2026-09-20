import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { useVoiceCheckin } from '../hooks/useVoiceCheckin'
import { useProjection } from '../hooks/useProjection'
import { publicUrl } from '../lib/origin'

/** Settings row: pair the phone that rides on Lantern and speaks messages out loud. */
export function SpeakerPhone() {
  const voice = useVoiceCheckin()
  const projection = useProjection()
  const [open, setOpen] = useState(false)
  const [qr, setQr] = useState('')
  const [copied, setCopied] = useState(false)
  const patientConfig = projection.config.patient as { preferred_name?: string; name?: string } | undefined
  const patient = patientConfig?.preferred_name || patientConfig?.name || 'Susan'

  const link = voice.pairing
    ? `${publicUrl('/voice/phone')}#${new URLSearchParams({ session: voice.pairing.session_id, token: voice.pairing.phone_token })}`
    : ''

  useEffect(() => {
    if (!voice.pairing && !voice.busy) void voice.pair(patient, 'Caregiver')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    let cancelled = false
    if (link) {
      QRCode.toDataURL(link, { width: 200, margin: 1, color: { dark: '#0e1116', light: '#ffffff' } }).then((src) => {
        if (!cancelled) setQr(src)
      })
    }
    return () => {
      cancelled = true
    }
  }, [link])

  const status = voice.snapshot?.phone_ready
    ? 'Connected and ready'
    : voice.snapshot?.phone_online
      ? 'Connected. Tap Start Lantern on the phone.'
      : 'Not connected yet'
  const dot = voice.snapshot?.phone_ready
    ? 'var(--color-safe)'
    : voice.snapshot?.phone_online
      ? 'var(--color-watch)'
      : 'var(--color-tint)'

  async function copy() {
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard can be blocked on plain http */
    }
  }

  return (
    <div className="p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[16px] text-[var(--color-ink)]">Speaker phone</p>
          <p className="flex items-center gap-2 text-[13px]">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: dot }} />
            {status}
          </p>
        </div>
        <button
          type="button"
          className="btn-ghost !min-h-9 !shrink-0 !px-3 !py-1 !text-[13px]"
          onClick={() => setOpen((v) => !v)}
          disabled={!link}
        >
          {open ? 'Hide QR code' : 'Show QR code'}
        </button>
      </div>

      {open && (
        <div className="mt-4 rounded-[14px] bg-[var(--color-panel)] p-5 text-center">
          <p className="mb-3 text-[13px] text-[var(--color-ink-2)]">
            Scan this with the phone that sits on Lantern. It will say your messages out loud to {patient}.
          </p>
          {qr && <img src={qr} alt="Connect the speaker phone" className="mx-auto h-44 w-44 rounded-[10px] bg-white p-1" />}
          <p className="mt-3 break-all text-[11px] text-[var(--color-ink-2)]">{link}</p>
          <button type="button" className="btn-ghost mt-2 !min-h-8 !px-3 !py-1 !text-[12px]" onClick={copy}>
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>
      )}
      {voice.error && (
        <p role="alert" className="mt-3 text-[13px] text-[var(--color-danger)]">
          {voice.error}
        </p>
      )}
    </div>
  )
}
