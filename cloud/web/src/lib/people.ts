export type PersonKind = 'emergency' | 'household'

export interface Person {
  id: string
  name: string
  phone: string
  /** relationship to the patient, e.g. "Daughter" */
  relationship: string
  kind: PersonKind
}

export const RELATIONSHIPS = [
  'Daughter',
  'Son',
  'Spouse / partner',
  'Sibling',
  'Grandchild',
  'Friend',
  'Neighbor',
  'Caregiver',
  'Doctor',
]

export const OTHER = 'Other'

export const newPerson = (kind: PersonKind): Person => ({
  id: `p_${Math.random().toString(36).slice(2, 8)}`,
  name: '',
  phone: '',
  relationship: '',
  kind,
})

export const phoneDigits = (p: string) => p.replace(/\D/g, '')

/** Loose check: at least a 7-digit local number. */
export const validPhone = (p: string) => phoneDigits(p).length >= 7

/** An emergency contact is only useful if we can actually reach them. */
export const emergencyReady = (p: Person) => p.kind === 'emergency' && p.name.trim() !== '' && validPhone(p.phone)

/** Fake numbers (the reserved 555-01xx fiction range) for the demo family. Never overwrite typed ones. */
const PRESET_PHONES: Record<string, string> = {
  jenny: '(617) 555-0101',
  mark: '(617) 555-0102',
  javiar: '(617) 555-0103',
}

/** Fill in a preset number for anyone in the demo family who has none. */
export function withPresetPhones(people: Person[]): Person[] {
  return people.map((p) => {
    const preset = PRESET_PHONES[p.name.trim().toLowerCase()]
    return preset && p.phone.trim() === '' ? { ...p, phone: preset } : p
  })
}

/** The one household member whose voice is recorded for the demo; always present. */
export const DEMO_MEMBER = { name: 'Javiar', relationship: 'Son' }

const isDemoMember = (p: Person) =>
  p.kind === 'household' && p.name.trim().toLowerCase() === DEMO_MEMBER.name.toLowerCase()

/** Make sure the demo member is in the list, adding him if he is missing. */
export function withDemoMember(people: Person[]): Person[] {
  const all = people.some(isDemoMember) ? people : [...people, { ...newPerson('household'), ...DEMO_MEMBER }]
  return withPresetPhones(all)
}

/** Starting point for the demo family; numbers are filled in from the server if it has them. */
export function seedPeople(known: { name: string; phone: string | null }[]): Person[] {
  const phone = (n: string) => known.find((k) => k.name.toLowerCase() === n.toLowerCase())?.phone ?? ''
  return withDemoMember([
    { ...newPerson('emergency'), name: 'Jenny', relationship: 'Daughter', phone: phone('Jenny') },
    { ...newPerson('emergency'), name: 'Mark', relationship: 'Son', phone: phone('Mark') },
  ])
}
