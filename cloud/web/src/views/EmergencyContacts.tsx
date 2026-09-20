import { useEffect, useState } from 'react'

interface Contact {
  name: string
  role: string
  phone: string | null
}

const dial = (phone: string) => `tel:${phone.replace(/[^\d+]/g, '')}`

export function EmergencyContacts({ onClose }: { onClose: () => void }) {
  const [contacts, setContacts] = useState<Contact[] | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/contacts')
      .then((r) => r.json())
      .then((d: { contacts?: Contact[] }) => !cancelled && setContacts(d.contacts ?? []))
      .catch(() => !cancelled && setContacts([]))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Emergency contacts"
      className="fixed inset-0 z-[60] overflow-y-auto bg-[var(--color-bg)]"
    >
      <div className="mx-auto flex min-h-full w-full max-w-[460px] flex-col gap-4 px-4 pb-10 pt-5">
        <header className="pb-1 pt-2">
          <p className="eyebrow mb-1">Get help</p>
          <h1 className="text-[30px] leading-[1.1]">Who do you want to call?</h1>
        </header>

        <section className="card !p-5">
          <p className="eyebrow mb-1">Emergency services</p>
          <p className="mb-4 text-[14px] text-[var(--color-ink-2)]">
            If they are in danger, call now. Tell the dispatcher where Lantern last saw them.
          </p>
          <a
            href="tel:911"
            className="btn-primary w-full !bg-[var(--color-danger)] !text-white"
            style={{ background: 'var(--color-danger)', color: '#fff' }}
          >
            Call 911
          </a>
        </section>

        <section className="card flex flex-col divide-y divide-[var(--color-line)] !p-0">
          <p className="eyebrow p-5 pb-3">Your contacts</p>
          {contacts === null && <p className="p-5 text-[14px] text-[var(--color-ink-2)]">Loading…</p>}
          {contacts?.length === 0 && (
            <p className="p-5 text-[14px] text-[var(--color-ink-2)]">
              No contacts yet. Add them under Settings → Edit home.
            </p>
          )}
          {contacts?.map((c) => (
            <div key={c.name} className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <p className="text-[16px] text-[var(--color-ink)]">{c.name}</p>
                <p className="text-[13px] text-[var(--color-ink-2)]">
                  {c.role}
                  {c.phone ? ` · ${c.phone}` : ''}
                </p>
              </div>
              {c.phone ? (
                <a href={dial(c.phone)} className="btn-primary shrink-0 !min-h-10 !px-5 !py-2">
                  Call
                </a>
              ) : (
                <span className="shrink-0 text-[13px] text-[var(--color-ink-2)]">No number saved</span>
              )}
            </div>
          ))}
        </section>

        <button type="button" className="btn-ghost mt-2 w-full" onClick={onClose}>
          Back
        </button>
      </div>
    </div>
  )
}
