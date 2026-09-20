import { useEffect, useMemo, useRef, useState } from 'react'
import { useVoiceCheckin } from '../hooks/useVoiceCheckin'
import { useProjection } from '../hooks/useProjection'
import { DEFAULT_SENDER, HOUSEHOLD } from '../lib/household'

interface ChatMessage {
  id: string
  side: 'out' | 'in'
  name: string
  text: string
  ts: number
}

const clock = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

export function CheckinComposer({ onOpenSettings }: { onOpenSettings?: () => void }) {
  const [sender, setSender] = useState(DEFAULT_SENDER)
  const [text, setText] = useState('')
  const voice = useVoiceCheckin()
  const projection = useProjection()
  const patientConfig = projection.config.patient as { preferred_name?: string; name?: string } | undefined
  const patient = patientConfig?.preferred_name || patientConfig?.name || 'Arthur'
  const endRef = useRef<HTMLDivElement>(null)

  // The thread is rebuilt from the voice session's events, so it survives a reload.
  const messages = useMemo<ChatMessage[]>(() => {
    const out: ChatMessage[] = []
    for (const e of voice.snapshot?.events ?? []) {
      const p = e.payload as Record<string, unknown>
      if (e.type === 'checkin') {
        out.push({
          id: `${e.ts}-${e.seq}`,
          side: 'out',
          name: String(p.from_name || 'You'),
          text: String(p.text || '') || 'How are you feeling?',
          ts: e.ts,
        })
      } else if (e.type === 'transcript' && p.text) {
        out.push({ id: `${e.ts}-${e.seq}`, side: 'in', name: patient, text: String(p.text), ts: e.ts })
      }
    }
    return out
  }, [voice.snapshot?.events, patient])

  useEffect(() => {
    if (!voice.pairing && !voice.busy) void voice.pair(patient, 'Caregiver')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' })
  }, [messages.length])

  const statuses: Record<string, string> = {
    sent: 'Sending to Lantern…',
    speaking: `Lantern is saying it to ${patient} now…`,
    delivered: `Delivered. Waiting for ${patient} to reply.`,
    interrupted: `Delivered. ${patient} started talking.`,
    failed: 'It couldn’t play. Check that the speaker phone is on and unlocked.',
    unavailable: 'The speaker phone disconnected before it played.',
  }
  const lastOut = [...messages].reverse().find((m) => m.side === 'out')
  const checkinStatus = voice.snapshot?.checkin?.status ?? ''
  const lastIsWaiting = messages.length > 0 && messages[messages.length - 1].side === 'out'
  const status = lastIsWaiting ? statuses[checkinStatus] : ''

  const connected = Boolean(voice.snapshot?.phone_ready)
  const canSend = Boolean(voice.ready) && !voice.busy

  async function send(body: string) {
    if (await voice.send(body.trim(), sender)) setText('')
  }

  return (
    <div className="card flex flex-col gap-5 !p-5">
      <section aria-label="Who is this from?">
        <p className="eyebrow mb-3">From</p>
        <div className="flex flex-wrap gap-2">
          {HOUSEHOLD.map((m) => {
            const selected = m.name === sender
            return (
              <button
                key={m.name}
                type="button"
                disabled={!m.voiceReady}
                aria-pressed={selected}
                title={m.voiceReady ? undefined : 'Voice not recorded yet'}
                onClick={() => setSender(m.name)}
                className={`inline-flex items-center gap-2 rounded-full py-1.5 pl-1.5 pr-4 text-[14px] transition-colors ${
                  selected
                    ? 'bg-[var(--color-ink)] text-white'
                    : 'bg-[var(--color-panel)] text-[var(--color-ink)]'
                } ${m.voiceReady ? 'cursor-pointer' : 'cursor-not-allowed opacity-45'}`}
              >
                <span
                  className={`grid h-7 w-7 place-items-center rounded-full text-[12px] font-medium ${
                    selected ? 'bg-white text-[var(--color-ink)]' : 'bg-[var(--color-panel-2)]'
                  }`}
                >
                  {m.name[0]}
                </span>
                {m.name}
              </button>
            )
          })}
        </div>
        <p className="mt-3 text-[13px] text-[var(--color-ink-2)]">
          {patient} will hear it in {sender}’s voice. More voices can be added as they’re recorded.
        </p>
      </section>

      <section
        aria-label="Conversation"
        className="flex min-h-[220px] max-h-[46vh] flex-col gap-3 overflow-y-auto rounded-[18px] bg-[var(--color-panel)] p-4"
      >
        {messages.length === 0 && (
          <p className="m-auto max-w-[260px] text-center text-[14px] text-[var(--color-ink-2)]">
            Say something warm. {patient} will hear it out loud, and their reply will show up here.
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex flex-col ${m.side === 'out' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] px-4 py-2.5 text-[14px] leading-[1.45] ${
                m.side === 'out'
                  ? 'rounded-[18px] rounded-br-[6px] bg-[var(--color-ink)] text-white'
                  : 'rounded-[18px] rounded-bl-[6px] bg-[var(--color-surface)] text-[var(--color-ink)] shadow-[var(--shadow-card)]'
              }`}
              data-testid={m.side === 'in' ? 'checkin-reply' : undefined}
            >
              {m.text}
            </div>
            <p className="mt-1 px-1 text-[11px] text-[var(--color-ink-2)]">
              {m.name} · {clock(m.ts)}
            </p>
            {m.id === lastOut?.id && status && (
              <p role="status" className="px-1 text-[12px] text-[var(--color-ink-2)]">
                {status}
              </p>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </section>

      {voice.snapshot?.checkin?.needs_attention && (
        <p className="rounded-[14px] bg-[var(--color-accent-soft)] px-4 py-3 text-[13px] text-[var(--color-ink)]">
          That reply sounded like {patient} might need some help. It could be worth giving them a call.
        </p>
      )}

      {!connected && (
        <p className="rounded-[14px] bg-[var(--color-panel)] px-4 py-3 text-[13px] text-[var(--color-ink-2)]">
          Lantern’s speaker phone isn’t connected yet.{' '}
          {onOpenSettings && (
            <button type="button" className="text-[var(--color-ink)] underline" onClick={onOpenSettings}>
              Set it up in Settings
            </button>
          )}
        </p>
      )}

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim() && canSend) void send(text)
        }}
      >
        <div className="flex items-center gap-2">
          <input
            className="input-field !rounded-full !px-5"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={`Message ${patient}…`}
            aria-label={`Message ${patient}`}
            maxLength={500}
          />
          <button
            type="submit"
            aria-label="Send"
            disabled={!text.trim() || !canSend}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[var(--color-ink)] text-white transition-opacity disabled:opacity-35"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
        <button
          type="button"
          disabled={!canSend}
          onClick={() => void send('')}
          className="self-start rounded-full bg-[var(--color-panel)] px-3.5 py-1.5 text-[13px] text-[var(--color-ink)] disabled:opacity-40"
        >
          Ask how they’re feeling
        </button>
      </form>

      {voice.error && (
        <p role="alert" className="text-[13px] text-[var(--color-danger)]">
          {voice.error}
        </p>
      )}
    </div>
  )
}
