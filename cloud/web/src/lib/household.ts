/**
 * Preset household for the demo. Only one voice is actually recorded, so only that
 * member can send a check-in; the rest show up greyed out to sketch the full product.
 */
export interface HouseholdMember {
  name: string
  /** A voice sample exists, so Lantern can speak in this person's voice. */
  voiceReady: boolean
}

export const HOUSEHOLD: HouseholdMember[] = [
  { name: 'Alex', voiceReady: false },
  { name: 'Ally', voiceReady: false },
  { name: 'Javier', voiceReady: true },
  { name: 'Lamine', voiceReady: false },
]

export const DEFAULT_SENDER = HOUSEHOLD.find((m) => m.voiceReady)?.name ?? HOUSEHOLD[0].name
