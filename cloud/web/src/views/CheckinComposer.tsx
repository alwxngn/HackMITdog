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
    <div className="rounded-lg bg-[var(--panel)] p-4">
      <h2 className="mb-2 text-lg">Check-in</h2>
      <p className="mb-3 text-xs text-[var(--muted)]">
        Robot delivers this attributed — never as you.
      </p>
      <input
        className="mb-2 w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm"
        value={fromName}
        onChange={(e) => setFromName(e.target.value)}
        placeholder="From"
      />
      <textarea
        className="mb-2 w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Hi Mom, thinking of you…"
      />
      <button
        className="rounded bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[#1a1408]"
        onClick={send}
      >
        Send to robot
      </button>
      {status && <p className="mt-2 text-xs text-[var(--muted)]">{status}</p>}
    </div>
  )
}
