import { useState } from 'react'

export function CheckinComposer() {
  const [fromName, setFromName] = useState('Michael')
  const [text, setText] = useState('')
  const [status, setStatus] = useState('')

  async function send() {
    if (!text.trim()) return
    const r = await fetch('/api/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from_name: fromName, text }),
    })
    if (r.ok) {
      setStatus('Queued — delivered when robot is IDLE')
      setText('')
    } else {
      setStatus('Failed to send')
    }
  }

  return (
    <div className="card">
      <h2 className="mb-2 text-[18px]">Check-in</h2>
      <p className="mb-4 text-[13px] text-[var(--color-charcoal)]">
        Robot delivers this attributed — never as you.
      </p>
      <input
        className="input-field mb-2"
        value={fromName}
        onChange={(e) => setFromName(e.target.value)}
        placeholder="From"
      />
      <textarea
        className="input-field mb-3 min-h-[88px] resize-y"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Hi Mom, thinking of you…"
      />
      <button type="button" className="btn-primary !min-h-11 !px-5 !py-2 !text-[14px]" onClick={send}>
        Send to robot
      </button>
      {status && (
        <p className="mt-3 text-[13px] text-[var(--color-forest-ink)]">{status}</p>
      )}
    </div>
  )
}
