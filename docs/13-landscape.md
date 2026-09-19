# Prior art, with names

Closes P1-7. Whoever pitches needs this; everyone should know the top three.

`02-blueprint.md` §2 compares Lantern against categories — door alarms, GPS trackers, cameras,
smart speakers, facilities. Good table, and exactly the table you write when you haven't looked
at the market. A digital-health judge will name a product, and "we hadn't heard of that" ends
that conversation badly.

Details below were accurate as of writing; skim the two or three most likely names before you
pitch, because positioning changes.

## The eight a judge might name

| Product | What it is | Why Lantern is different |
|---|---|---|
| **ElliQ** (Intuition Robotics) | Tabletop voice-first AI companion for older adults: conversation, reminders, wellness, family messaging, caregiver app. Commercially shipping, published research, distributed through state aging-services programs. | The closest thing to our pillars 1 and 3 that exists — and it sits on a table. It cannot be in the hallway at 2 AM, cannot see that he's pacing, cannot walk him back. It's a companion; we're an intervention. |
| **Sensi.AI** | Camera-free in-home **audio** monitoring for home-care agencies. Claims detection of falls, distress, nighttime patterns and cognitive change, then alerts. Widely deployed in US home care. | Someone has built a real business on the passive half of our pillar 2, and they're better at it than we are. They observe and alert. Nothing in the house does anything at the moment it's happening. |
| **PARO** | Therapeutic robot seal for agitation in dementia. Actual trial data, FDA-listed. | The evidence base we're explicitly modelling Calm Mode on — say so, don't pretend to have invented it. No mobility, no awareness, no caregiver link. |
| **AngelSense / SmartSole / Project Lifesaver** | Wearable GPS and RF locators for people who wander. | Reactive by construction: they help you find someone already outside. And they're worn, which is the failure mode — the thing a person with dementia reliably does is take it off. |
| **WanderGuard BLUE and facility elopement systems** | Bracelet plus door controllers in memory-care facilities. | Institutional, threshold-triggered, and a tagged bracelet. It's the fire alarm; we're trying to be the thing that notices the smoke. |
| **Nobi** | Ceiling-lamp fall detection for senior living. Detects a fall, speaks to the person, alerts staff. | The nearest thing to our "device that talks to the person in the room" idea, and worth knowing. Fixed position, one room, fall-focused — it's for after the event, we're for before it. |
| **CarePredict Tempo** | Wrist wearable tracking activity-of-daily-living patterns; flags falls and health risks. | Wearable, passive, longitudinal. Pattern analytics for care teams, not a 2 AM intervention. |
| **Smart-home DIY rigs** | Bed-exit sensor plus motion sensors plus smart bulbs plus an Alexa routine. | What motivated families actually build today, and it's more capable than people assume. It's fixed, it's scripted, and it can't follow him into the hallway or hold a conversation. |

## The synthesis to say out loud

Every one of these is in exactly one of three boxes:

1. **Fixed and passive** — sees or hears, cannot act (Sensi.AI, cameras, Nobi, bed sensors).
2. **Worn** — depends on compliance from the person least able to comply (AngelSense,
   CarePredict, WanderGuard, and the Go2's own beacon-based follow mode).
3. **Mobile but not for this** — companion or assistive robots aimed at loneliness or fetching
   objects (ElliQ on a table, Labrador, telepresence robots).

**Nothing is mobile, unworn, and intervening at the moment of confusion.** That's the sentence.
It's a real gap, it survives contact with the actual market, and it's much stronger than the
generic table because it shows you went and looked.

## When a judge names one

Two sentences. Name it accurately, then the one structural difference.

- **"How is this different from ElliQ?"** — *"ElliQ is the closest thing to what we're doing on
  the conversation side, and it's a real product with real research behind it. It's also a
  tabletop device. The entire premise here is being in the hallway at 2 AM, which a table
  can't do."*
- **"Isn't this just Sensi.AI with a robot?"** — *"Sensi does the passive detection better than
  we do — audio monitoring across a whole house, deployed at scale. But detection ends at an
  alert to somebody who isn't there. We're trying to put something in the room that can
  actually redirect him before the caregiver even wakes up."*
- **"Why not a GPS tracker?"** — *"Because he takes it off. Removing the wearable is a symptom,
  not user error, and every worn solution is fighting the disease for compliance."*
- **"Hasn't PARO already shown this works?"** — *"PARO is why we believe Calm Mode is worth
  building — it's the trial evidence we're modelling on. It also weighs six pounds and stays
  where you put it."*

**Never disparage any of them.** Respectful and accurate about prior art reads as someone who
has done the reading. Dismissive reads as someone who hasn't.

## The honest weakness

If a judge pushes hard: ElliQ and Sensi.AI are shipping, supported products with clinical and
commercial validation, and we have a taped square on a convention-hall floor. The right answer
is that we're making an argument about a capability gap — mobile, unworn, present at the moment
of confusion — not claiming to have out-executed anyone. Conceding that cleanly is stronger
than pretending the gap is smaller than it is.
