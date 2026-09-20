import { OTHER, RELATIONSHIPS, newPerson, validPhone, type Person, type PersonKind } from '../../lib/people'

const SECTIONS: { kind: PersonKind; title: string; blurb: string; add: string; phoneRequired: boolean }[] = [
  {
    kind: 'emergency',
    title: 'Emergency contacts',
    blurb: 'Lantern reaches these people first, in order, if something is wrong. A phone number is required.',
    add: 'Add emergency contact',
    phoneRequired: true,
  },
  {
    kind: 'household',
    title: 'Household members',
    blurb: 'Everyone who lives with or looks in on them. Phone numbers are optional.',
    add: 'Add household member',
    phoneRequired: false,
  },
]

function PersonCard({
  person,
  index,
  phoneRequired,
  onChange,
  onRemove,
}: {
  person: Person
  index: number
  phoneRequired: boolean
  onChange: (next: Person) => void
  onRemove: () => void
}) {
  const known = RELATIONSHIPS.includes(person.relationship)
  const selectValue = person.relationship === '' ? '' : known ? person.relationship : OTHER
  const badPhone = person.phone !== '' && !validPhone(person.phone)

  return (
    <li className="space-y-2.5 rounded-[20px] border border-[var(--color-line)] bg-[var(--color-surface)] p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="eyebrow">
          {person.kind === 'emergency' ? (index === 0 ? 'Primary' : index === 1 ? 'Secondary' : `Contact ${index + 1}`) : `Member ${index + 1}`}
        </span>
        <button
          type="button"
          onClick={onRemove}
          className="cursor-pointer text-[12px] font-semibold text-[var(--color-danger)] underline underline-offset-4"
        >
          Remove
        </button>
      </div>

      <input
        className="input-field"
        placeholder="Full name"
        aria-label="Name"
        autoComplete="off"
        value={person.name}
        onChange={(e) => onChange({ ...person, name: e.target.value })}
        maxLength={60}
      />

      <div>
        <input
          className={`input-field ${badPhone ? '!border-[var(--color-danger)]' : ''}`}
          type="tel"
          inputMode="tel"
          placeholder={phoneRequired ? 'Phone number' : 'Phone number (optional)'}
          aria-label="Phone number"
          aria-invalid={badPhone}
          autoComplete="off"
          value={person.phone}
          onChange={(e) => onChange({ ...person, phone: e.target.value })}
          maxLength={24}
        />
        {badPhone && <p className="mt-1 text-[12px] font-medium text-[var(--color-danger)]">Enter a full phone number.</p>}
      </div>

      <div className="flex gap-2">
        <select
          className="input-field"
          aria-label="Relationship to the patient"
          value={selectValue}
          onChange={(e) => onChange({ ...person, relationship: e.target.value === OTHER ? OTHER : e.target.value })}
        >
          <option value="">Relationship to them…</option>
          {RELATIONSHIPS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
          <option value={OTHER}>{OTHER}</option>
        </select>
        {selectValue === OTHER && (
          <input
            className="input-field"
            placeholder="Describe"
            aria-label="Other relationship"
            value={person.relationship === OTHER ? '' : person.relationship}
            onChange={(e) => onChange({ ...person, relationship: e.target.value || OTHER })}
            maxLength={30}
          />
        )}
      </div>
    </li>
  )
}

/** Emergency contacts + household members: name, phone number and relationship to the patient. */
export function PeopleEditor({ people, onChange }: { people: Person[]; onChange: (next: Person[]) => void }) {
  return (
    <div className="space-y-6">
      {SECTIONS.map((s) => {
        const list = people.filter((p) => p.kind === s.kind)
        return (
          <section key={s.kind} aria-label={s.title} className="space-y-3">
            <div>
              <h3 className="text-[16px]">{s.title}</h3>
              <p className="mt-0.5 text-[13px]">{s.blurb}</p>
            </div>
            {list.length > 0 && (
              <ul className="space-y-2.5">
                {list.map((p, i) => (
                  <PersonCard
                    key={p.id}
                    person={p}
                    index={i}
                    phoneRequired={s.phoneRequired}
                    onChange={(next) => onChange(people.map((x) => (x.id === p.id ? next : x)))}
                    onRemove={() => onChange(people.filter((x) => x.id !== p.id))}
                  />
                ))}
              </ul>
            )}
            <button
              type="button"
              className="btn-ghost !min-h-10 w-full !border-dashed !text-[13px]"
              onClick={() => onChange([...people, newPerson(s.kind)])}
            >
              + {s.add}
            </button>
          </section>
        )
      })}
    </div>
  )
}
