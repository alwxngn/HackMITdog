# Safety, ethics, and claims discipline

This is the document that wins or loses the healthcare track. Robot teams are common at
hackathons; robot teams that can articulate their safety envelope in numbers are not.

## 1. The safety envelope

Enforced **in the robot controller**, not in the demo script and not in the orchestrator. The
layer closest to the motors is the one that has to be trusted, because it's the one that's
still correct when the state machine has a bug.

| Parameter | Value | Reasoning |
|---|---|---|
| Minimum standoff from person | 1.5 m | Outside the trip envelope; outside intimate space. Closer reads as confrontation. |
| Approach sector | within ±45° of the person's heading | Never approach from behind. Being startled from behind by something you can't identify is the failure mode, and visual misperception is common in dementia — especially Lewy body. |
| Max speed within 3 m of a person | 0.3 m/s | Sudden movement reads as threat; slow movement reads as animal. |
| Max speed generally | 0.6 m/s | This is a home with rugs and a person who falls easily. |
| Doorway / egress occupancy | **Forbidden, unconditionally** | The exit is never obstructed. Not "usually" — never. |
| Yield rule | person within 1.2 m or advancing → robot retreats along their intended vector | The person always wins the physical interaction. |
| Announce before approach | voice cue precedes any approach within 3 m | No silent machines in the dark. |
| Stairs | robot never operates within 2 m of a stair zone while a person is present | It is itself a trip hazard, and the consequence there is catastrophic. |
| Illumination | warm low light on while moving at night, steady, never strobing | Visibility to the person, and orientation. Blinking reads as alarm. |
| Motion profile | damped accel/decel, low-speed gait | Servo whine and jerky motion are agitation triggers. |
| Escalation timeout | 20 s of ineffective redirection | The robot buys time; it does not solve the problem alone. |
| Hard stop | any caregiver dashboard control, any loud verbal distress | Distress overrides the mission, always. |

**On the yield rule:** implement it as a genuine reflex at the controller level, not a state
transition in the orchestrator. If the person advances, the robot backs off — regardless of
what state the agent thinks it's in or what command is executing. Report it as
`robot_status: yielded`. Judges will step toward the robot to test this, and it working is
worth more than any slide.

## 2. What we removed, and why

Worth saying out loud in the pitch. Describing something you deliberately cut on safety grounds
is one of the strongest credibility signals available at a hackathon, because almost nobody
does it.

### Physical intercept and path blocking — removed

A robot that positions itself between a disoriented person and where they are trying to go is:

- **a deliberately introduced fall hazard** — a rigid shin-height obstacle in the path of an
  unsteady person in the dark, in the population with the highest fall-mortality rate;
- **a physical restraint** applied to someone who cannot consent, which runs directly against
  thirty years of restraint-reduction practice in dementia care;
- **contraindicated technique** — blocking and confronting an exit-seeking person is what staff
  training explicitly teaches you not to do, because it escalates. The taught response is
  redirection.

Replaced by lead-away: attract, don't obstruct. Same goal, opposite physics.

### 40 Hz vibroacoustic therapy — removed

Two problems, either of which is fatal.

**The claim was wrong.** "Clinically proven to lower heart rate and reduce neurological distress"
merges two unrelated literatures. The 40 Hz work people know is gamma sensory entrainment
(GENUS, Tsai lab, MIT) — light and sound, targeting amyloid and tau, strong in mice, early and
unsettled in humans, over weeks of daily exposure. That is not evidence for acute anxiolysis
from chassis vibration. The cat-purr literature is folklore with very little behind it.
**HackMIT is at MIT**; the odds someone in the room knows the actual work are high, and getting
caught overclaiming costs you the credibility of everything true you said.

**The physics also didn't work.** A small sealed driver in a robot chassis produces essentially
no energy at 40 Hz — low frequencies need displacement volume. And vibroacoustic therapy is
*contact* therapy, delivered through a mat or chair. A robot 1.5 m away transmits nothing.

Replaced by **Calm Mode**: low still posture (the PARO mechanism), personalized music, familiar
voice, warm dimmed light. Modeled on interventions that do have trial evidence in dementia
agitation. Stated on the slide as modeled-on, not proven.

### Pulse oximetry as a trigger — removed

Asking a confused, agitated person at 2 AM to put a finger in a clamp doesn't work, and heart
rate is a weak agitation proxy with no per-patient baseline. Replaced by trajectory and
prosody, which we already have. Optional as a calm-state wellness check; never a trigger.

## 3. Consent and the voice question

The hardest ethical question in the project, and the one a judge is most likely to raise. Have
the answer ready before they ask.

**The concern:** synthesizing a family member's voice to soothe someone who cannot tell that the
family member isn't there is deception of a cognitively impaired person.

**The context:** dementia care has already litigated this. Validation therapy and therapeutic
fibbing are mainstream — you don't correct someone who believes it's 1974, because correction
causes suffering and changes nothing. Recorded family voices are used in real memory care. The
practice is defensible; the structure around it is what makes it so.

**The three mechanics, all enforced in code:**

1. **Consent from the voice owner, in the product.** The family member records their own sample
   behind an explicit checkbox naming the use. `consent_recorded_ts` is a required field, and
   the orchestrator refuses any `say` carrying a `voice_id` without one. This is also what
   ElevenLabs' terms require — worth mentioning, since it shows you read the sponsor's policy.
2. **Never impersonate.** The robot says *"Sarah recorded this for you,"* not *"it's Sarah."*
   Familiar voice, honest framing. `attribution` is a field in the `say` schema, not a prompt
   instruction. It's also better technique — it gives the patient a reason the daughter isn't
   physically present, which is frequently the actual source of the distress.
3. **Revocable, and off by default.** One toggle. No cloned voice until consent exists.

Slide title: **"Familiar voice, not impersonation."**

## 4. Privacy

An always-on microphone in the bedroom of someone who cannot consent to it. Own this before
someone asks.

- **No raw audio retention.** Audio is streamed for transcription and discarded. Nothing written
  to disk. (For the demo's evaluation set we record deliberately, from consenting teammates,
  and we say so.)
- **Transcripts are minimized.** The caregiver sees events and summaries, not a running log of
  everything their parent said. The person retains some privacy from their own family; this
  matters more than it sounds and caregiving professionals will notice you thought of it.
- **Visible indicator.** The robot's light shows when it is listening. Physical, not buried in
  an app.
- **Retention policy.** Events 30 days, transcripts 24 hours, audio never.
- **Local-first where practical.** VAD and pacing detection run on the Jetson. Only speech
  segments leave the device.
- **Family, not platform.** Data belongs to the household. No training on patient audio.

One slide. Six bullets. It takes fifteen seconds and it closes a line of questioning.

## 5. Claims discipline

Rules for every sentence in the pitch, the UI, and the README:

| Don't say | Do say |
|---|---|
| "Clinically proven" | "Modeled on interventions with trial evidence; ours is untested." |
| "Prevents wandering" | "Attempts redirection and escalates to a caregiver." |
| "Monitors vitals" | "Optional wellness check during calm periods." |
| "Detects agitation" | "Detects a behavioral pattern associated with agitation." |
| "Replaces a caregiver" | "Buys a caregiver time and information." |
| "Medical device" | "Non-medical wellness and companion device." |

And the line to have ready for the regulatory question: *"Lantern is positioned as a
non-medical wellness and companion device. It doesn't diagnose, treat, or monitor for medical
purposes, and it isn't a substitute for supervision. If we pursued the agitation-detection
feature as a clinical product, that's where a regulatory pathway would begin."*

That answer takes ten seconds and tells a healthcare judge you know what category you're in —
which is a question that ends a lot of hackathon pitches badly.

## 6. Failure modes we acknowledge

Listing your own failure modes reads as confidence, not weakness. Judges ask "what breaks?"
precisely to see whether you've thought about it.

| Failure | What happens | Mitigation |
|---|---|---|
| Person ignores the robot entirely | Redirect fails | 20 s escalation; robot stays and keeps company |
| Person is frightened *by* the robot | Agitation increases | Distress overrides mission: retreat, lower posture, familiar voice only, escalate early |
| False positive at 3 AM | Caregiver woken for nothing | One-tap `false_alarm`; repeated false alarms are why families unplug devices |
| Robot is a trip hazard itself | Fall | Standoff, speed cap, illumination, stairs exclusion |
| Person falls | Worst case | `posture: lying` outside a bed zone + no voice response → immediate level-4 escalation |
| Two people in the home | Wrong person tracked | Out of scope for the demo; say so rather than pretending |
| Multi-floor home | Robot can't follow | Out of scope. Stairs are excluded by policy anyway. |
| Robot battery dies overnight | Silent failure — the dangerous one | Dashboard shows battery; low battery is itself a caregiver alert |

That last row matters more than it looks. A safety device that fails silently is worse than no
device, because the family has stopped listening for the door. Having noticed that is exactly
the kind of thing that distinguishes a team that thought about deployment from one that thought
about a demo.

## 7. If you only do one non-code thing

**Talk to one person who does this work.** A memory care nurse, an occupational therapist, a
geriatric social worker, or a family caregiver. Caregiver forums and subreddits respond within
hours. Send it by noon Saturday so the answer can still change the build.

One quote on a slide — *"I spoke with an RN who runs a memory care unit; she told me the first
thing they teach is never to block someone who's exit-seeking, so we rebuilt the intervention
around leading instead"* — is worth more than any feature you could add in the same time. It
turns your safety envelope from a design choice into a validated one.
