import { useRef, useState } from 'react'
import { CheckinComposer } from './CheckinComposer'

export function CheckinButton() {
  const dialog = useRef<HTMLDialogElement>(null)
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" className="btn-primary fixed bottom-6 right-6 z-20 !min-h-11 !px-5 !py-2 !text-[14px]" onClick={() => {
        setOpen(true)
        dialog.current?.showModal()
      }}>Check in</button>
      <dialog ref={dialog} aria-label="Check in with Lantern" onClose={() => setOpen(false)} className="fixed inset-0 m-auto max-h-[90dvh] w-[min(440px,calc(100%-32px))] overflow-y-auto rounded-[14px] bg-[var(--color-cream-paper)] p-4 text-[var(--color-forest-ink)] backdrop:bg-black/30">
        <div className="mb-2 flex justify-end"><button type="button" className="btn-ghost !min-h-8 !px-3 !py-1" onClick={() => dialog.current?.close()}>Close</button></div>
        {open && <CheckinComposer />}
      </dialog>
    </>
  )
}
