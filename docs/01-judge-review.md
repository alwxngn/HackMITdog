# Judge review of "Project Aegis"

Read this as if I'm a healthcare-track judge at the table, and assume at least one judge in
your rotation is a clinician, a digital-health PM, or an MIT neuroscience grad student. That
assumption changes what you can get away with.

**Verdict up front:** the core instinct is right and the hardware is genuinely impressive, but
the plan as written has one problem that would disqualify you on the healthcare track, three
claims that a knowledgeable judge will dismantle in under a minute, and roughly three times
more scope than four people can ship in 36 hours. All of that is fixable, and the fixed
version is a stronger project than the original — the constraints force you toward the more
defensible idea.

Issues are ordered by how much damage they do, not by how hard they are to fix.

---

## P0-1: "Physical intercept" is robotic restraint, and it will end your healthcare run

> "the robot physically maneuvers to block the path, sits, and uses its voice agent to guide
> the patient safely back to bed"
>
> "The robot autonomously cuts across the stage, physically blocks his path"

This is the single biggest problem in the document, and it's in your demo script as the
climax.

Here's what a clinician hears. A person with dementia, disoriented, at 2 AM, possibly
experiencing sundowning — a state in which fear and paranoia are the dominant affect — has a
30-to-40-pound machine dart across the floor and position itself between them and where they
are trying to go. Three things follow:

- **It's a fall hazard, deliberately introduced.** Falls are the leading cause of injury death
  in adults over 65. You are putting a rigid obstacle at shin height into the path of an
  unsteady person in the dark. If the demo works exactly as designed and the patient stops,
  you got lucky. If they don't stop, you have engineered the exact accident the product
  claims to prevent.
- **It is a physical restraint.** Not legally identical to a bed rail or a lap belt, but
  functionally the same category: a device preventing a person from moving where they want to
  go, applied to someone who cannot consent to it. Restraint reduction has been the direction
  of travel in dementia care for thirty years. You are proposing to automate it.
- **It is contraindicated technique.** Blocking and confronting a person who is exit-seeking
  is what training programs explicitly teach staff *not* to do, because it escalates. The
  taught response is redirection: agree, validate, walk alongside, offer something else, let
  the impulse pass. A judge who has done that training will recognize instantly that you
  built the opposite.

The frustrating part is that the underlying insight — *a mobile agent can be present at the
moment of confusion in a way a fixed door alarm cannot* — is correct and is the best idea in
your document. It is the thing worth building. You've just attached the wrong actuation policy
to it.

**Fix: invert it from blocking to leading.** The robot never occupies the space between the
person and their goal. It positions itself *ahead and to the side*, inside their field of
view, at a respectful distance, and then moves *away from* the danger zone while talking — so
that following it is the path of least resistance. It exploits social attraction instead of
physical obstruction. If the person advances anyway, the robot yields, gets out of the way,
keeps talking, and escalates to the caregiver.

Write it down as a policy with actual parameters and you have something to put on a slide:

| Parameter | Value | Why |
|---|---|---|
| Min standoff distance | 1.5 m | Outside the trip envelope and outside intimate space |
| Approach sector | ±45° of the person's heading | Never approach from behind; being startled from behind is the failure mode |
| Max speed within 3 m of person | 0.3 m/s | Sudden motion reads as threat; slow motion reads as animal |
| Doorway occupancy | Forbidden, always | The exit is never obstructed |
| Yield rule | Person closes to <1.2 m → robot retreats along their intended vector | The person always wins the physical interaction |
| Announce-before-move | Voice cue precedes any approach within 3 m | No silent machines appearing in the dark |
| Time to escalate | 20 s of no redirection effect | The robot is buying the caregiver time, not solving it alone |

That table is more impressive to a healthcare judge than the intercept ever was, because it
demonstrates you understand that the hard part of this problem is *behavioral*, not
navigational. And it gives Engineer 2 a crisper spec than "collision logic."

**Bonus:** it also de-risks your demo. A robot that has to precisely cut off a moving human is
a demo that fails live. A robot that trots to a spot in front of the person and then walks
toward the bedroom while talking works every time, and looks gentler on camera.

---

## P0-2: The 40 Hz purr claim is the one a judge will actually fact-check

> "This clinically proven frequency lowers heart rate and reduces neurological distress."

Three separate problems, stacked.

**The evidence claim is false as stated.** The 40 Hz literature people know is gamma entrainment
(GENUS) out of Li-Huei Tsai's lab at the Picower Institute — 40 Hz light and sound, targeting
amyloid and tau pathology, strong in mice, early and still-unsettled in humans. That is a
disease-modifying hypothesis over weeks of daily exposure. It is *not* evidence that 40 Hz
vibration acutely lowers heart rate in an agitated person. Separately there's the cat-purr
folklore, which is a nice story with very little behind it. You have merged two unrelated
literatures into one sentence and labeled the result "clinically proven."

Now the part that should worry you: **HackMIT is at MIT.** The Tsai lab is at MIT. The odds that
someone in your judging rotation, or standing at the table next to you, knows this work
precisely are not small. Getting caught overclaiming on the one medical assertion in your
pitch costs you the credibility of everything else you said, including the parts that were
true.

**The physics doesn't work either.** 40 Hz through a small sealed speaker driver in a robot
chassis produces essentially no usable acoustic energy — you need displacement volume for low
frequencies, and the Go2's speaker has none. And vibroacoustic therapy is *contact* therapy:
it's delivered through a mat, chair, or vest touching the body. A robot standing 1.5 m away
vibrating at 40 Hz transmits nothing to the patient. You'd be doing an inaudible, unfeelable
nothing and narrating it as treatment.

**The third problem is that the good version is right next to it.** There *is* a real evidence
base for non-pharmacological calming in dementia agitation, and it's the one you're already
half-using: familiar voice, familiar music, and companion robots. PARO, the robotic seal, has
actual trial data for agitation in dementia and is an FDA-listed device. Personalized music
has solid support. A familiar family voice is the most reliable of the lot.

**Fix:** kill the DSP pillar. Replace it with **Calm Mode**, which is honest about what it is:

- The robot settles into a low, still posture at conversational distance — low posture reads as
  non-threatening, which is most of PARO's mechanism.
- It plays the patient's personalized music from their profile, at low volume.
- The family voice track speaks, slowly, short sentences, validating rather than correcting.
- Warm light, dimmed, steady — not blinking.
- *Optional and clearly framed as exploratory:* if the patient chooses to rest a hand on the
  robot's back, a gentle low-frequency motor hum is available. Contact-based, patient-initiated,
  and pitched as "we wanted to test whether tactile feedback helps — we don't have evidence yet."

Say on the slide: "modeled on PARO and personalized-music interventions, which have trial
evidence in dementia agitation; our implementation is untested and we're not claiming clinical
effect." You lose nothing. A judge who hears a team voluntarily state the limits of its own
evidence upgrades everything else you tell them.

This also frees Engineer 4 from building a DSP engine, which you'll need — see P0-4.

---

## P0-3: Voice cloning a family member is either your biggest ethics liability or your best slide

Cloning a daughter's voice to soothe a mother who cannot tell that the daughter is not there
is, on its face, deception of a cognitively impaired person. A judge will raise it. You want
to have already answered it, out loud, before they do.

The good news is that dementia care has already had this argument and landed somewhere usable.
Validation therapy and "therapeutic fibbing" are mainstream practice: you do not correct a
person who believes it's 1974, because correction causes suffering and changes nothing.
Recorded family voices are used in real memory care. So the practice is defensible — but only
with a specific structure around it.

**Fix — three concrete mechanics, all cheap to build:**

1. **Consent is from the voice owner, in the product.** The daughter records her own sample, in
   the portal, behind an explicit consent checkbox naming what it will be used for. This isn't
   just ethics theater; it's also what ElevenLabs' terms require, so you're demonstrating you
   read the sponsor's policy.
2. **The robot never claims to be the person.** This is the whole ballgame. It says *"Sarah
   recorded this for you"* or *"Sarah wanted me to tell you..."*. Familiar voice, honest
   framing. Recognition without impersonation. It also happens to be better technique — it
   gives the patient a reason the daughter isn't physically present, which is often the actual
   source of the distress.
3. **The patient's own preferences are on file, and the caregiver can revoke.** One toggle in
   the portal, off by default until consent is recorded.

Put a slide up titled "Familiar voice, not impersonation." You will be the only team at the
expo with an ethics slide that isn't boilerplate, and on a healthcare track that is worth real
points.

---

## P0-4: You have scoped roughly three hackathons

Count what's in the document: streaming STT with VAD and noise suppression, voice cloning with
emotional inflection control, an LLM dialogue agent, LiDAR SLAM mapping, semantic zone
labeling, autonomous navigation and interception, guided walk routines, a 40 Hz DSP engine, a
BLE pulse oximeter integration, a React onboarding wizard, a floorplan drawing canvas, a
sub-100 ms telemetry WebSocket, Twilio SMS, and a token-compression middleware layer with a
live savings counter.

That is fourteen workstreams for four people in 36 hours, on hardware, with a live demo at the
end. Each of the four pillars is a defensible hackathon project on its own. Attempting all four
means you arrive at hour 30 with four impressive halves and nothing that runs end to end, which
is the single most common way good hardware teams lose.

The tell is Engineer 4's row: "Token compression middleware + pulse oximeter + 40 Hz DSP" is
three unrelated things assigned to one person because they didn't fit anywhere else. Nobody
owns integration, and integration is the thing that's going to hurt you.

**Fix:** one demo spine that must work, everything else explicitly optional, and a person whose
entire job is the seam between the other three. Full detail in `03-build-plan.md`; the cut is:

- **Ship (the spine):** Night Watch detection → lead-away redirect → familiar-voice dialogue →
  caregiver escalation → event appears in portal timeline.
- **Ship if the spine is green by hour 20:** pacing detection, Calm Mode, live map view.
- **Stretch, genuinely fine to drop:** guided walk, token counter, vitals, multi-room mapping.
- **Cut now:** physical intercept, 40 Hz DSP engine, pulse oximeter as a core dependency.

---

## P0-5: Nobody owns integration, and hour 30 is coming

Related to the above but worth its own entry because it's the most actionable single change in
this review.

Your four roles are four vertical silos: voice, robot, web, misc. Every silo is productive
until hour 26, when you try to connect them and discover that E1 emits a transcript object E4
never agreed to, E2's robot state is polled while E3's dashboard expects a push, and nobody
can test anything without the robot physically present in the room.

**Fix, two parts:**

1. **Freeze the interfaces at hour 4.** Every message between subsystems gets a schema and a
   fake producer *before* anyone builds the real thing. `04-interfaces.md` is the draft; argue
   about it early, then stop arguing about it.
2. **Engineer 4 becomes the orchestrator owner, not the miscellaneous-hardware owner.** They own
   the state machine, the mock event bus, the demo runner, and metrics collection. From hour 6
   there is a fake robot, a fake patient, and a fake microphone, so the other three can each
   test end to end without waiting for hardware or for each other. This is what turns four
   people into a team instead of four people.

---

## P0-6: The demo format assumption is wrong, and it's a schedule problem

Your only demo artifact is a 3-minute stage script with a robot crossing a stage.

You will spend the overwhelming majority of judging time at a table in a crowded hall, doing
the demo 15–25 times to rotating judges, in maybe a 6-by-6-foot footprint, with people walking
through your space constantly. The stage happens only if you make finals. **You have planned the
demo you might give once and not the demo you will definitely give twenty times.**

Concrete consequences nobody has budgeted for:

- **SLAM in the expo hall is a different problem than SLAM at home.** Hundreds of moving people,
  no walls near you, changing geometry. A map built at 9 AM is wrong by noon. You need a
  pre-authored small map and a hard geofence around your own footprint, not live mapping.
- **Go2 battery is on the order of 1–2 hours of active use**, less with continuous locomotion.
  Twenty demos doesn't fit in one battery. Two packs and a charging rotation, or the robot
  idles between demos and only moves during the 40-second beat that needs it.
- **Ambient noise at an expo will wreck an open-mic voice demo.** Mumbled speech into an open
  mic in an 85 dB room is not going to transcribe. Use a headset or lav mic on the person
  playing the patient, and be honest that the home deployment uses a far-field array.
- **Judges arrive mid-loop.** The demo has to be re-enterable in under 10 seconds and idempotent.
  A one-key reset that returns everything to the start state is a real deliverable, not polish.

`05-demo.md` has a 90-second table demo built for these constraints, plus the stage version,
plus the fallback ladder.

---

## P0-7: There are no numbers anywhere in this document

Everything in the plan is an adjective: "instantly," "real-time," "sub-100 ms," "clinically
proven." The only quantities are two external statistics, one of which is wrong (below).

On a healthcare track, this is the clearest available differentiator. You cannot run a trial
in 36 hours and no judge expects one. But almost nobody at the expo will have measured
*anything*, and the team that says "we recorded 40 utterances in the speech patterns we're
targeting and our word error rate was X versus Y for the baseline" reads as a different species
of team. Four numbers, four hours of work, near the top of the marginal-value curve of anything
you can do with your last day.

The four to get (procedures in `07-evaluation.md`):

1. **Speech recognition on degraded speech.** Record 40 utterances — quiet, mumbled, mid-sentence
   restarts, repeated questions — and report WER against a baseline. This is also your
   strongest Deepgram-track artifact by a wide margin.
2. **End-to-end voice latency**, mic-open to first audio out, p50 and p95, measured not
   estimated. Latency is what makes a voice agent feel alive; you should know your own number.
3. **Pacing detection precision and recall** over 20 scripted trials, 10 positive and 10
   negative. Report the false positives. A team that reports its own false-positive rate is
   telling the judge it's honest.
4. **Time from event to caregiver's phone buzzing**, end to end, wall clock.

Also fix the two external stats. "Over 60% of dementia patients wander into dangerous
situations" overstates the Alzheimer's Association figure, which is that roughly 6 in 10 people
with dementia *will wander at some point* — a lifetime incidence, not a per-event danger rate.
And US memory care runs somewhere in the $5–8k/month range in most survey data, not $10,000; a
judge who works in aging services knows the number and will notice you rounded it up for
effect. The real numbers are alarming enough. Cite them and be unimpeachable.

---

## P0-8: The name

"Aegis" is a shield carried by a war goddess. It's also a Lockheed Martin combat system, a
dozen security companies, and several insurance firms. For a product whose entire thesis is
warmth and non-alienation for a frightened elderly person, the name is pointed in exactly the
wrong direction — it sounds like surveillance and defense, which is the criticism you're most
vulnerable to anyway.

**Recommendation: Lantern.** A light you carry through a dark house, that guides rather than
controls. It maps directly onto your best scenario, the 2 AM walk. It's warm, it's one word,
and it's easy to say at a table.

Alternatives if the team doesn't like it: **Wren** (small, unthreatening, animal), **Juniper**
(warm, domestic), **Pace** (avoid — "pacing" is one of the symptoms you're detecting).

Decide in the first hour and don't revisit it. The docs in this repo use Lantern.

---

## P1-1: The pulse oximeter is a weak sensor for this job

Asking a confused, agitated person at 2 AM to put a finger into a clamp will not work, and a
judge with clinical experience knows it won't work the moment they see it in your demo. Even
if compliance were perfect, heart rate is a poor agitation signal — it moves for a dozen
reasons, and you have no baseline for this patient.

Meanwhile you are ignoring two signals you already get for free, both of which are *better*:

- **Gait and trajectory from the robot's own odometry and SLAM.** Repeated back-and-forth
  traversal of the same corridor segment is the textbook pre-wandering behavior. You can detect
  it from data you're already computing, with no added hardware.
- **Vocal prosody from the audio you're already streaming.** Pitch variance, speech rate,
  volume, and repetition rate. Repeated questioning — the same question four times in two
  minutes — is one of the most reliable agitation markers, and you can detect it with string
  similarity over the transcript buffer. It is also *specific* to dementia in a way heart rate
  is not.

**Fix:** drop the pulse ox from the critical path. Detect pre-wandering from trajectory plus
prosody. This is strictly better technically, costs you no hardware risk, and gives you an
actual novel claim: *the robot's own navigation stack is the agitation sensor.* That's the most
interesting technical sentence available to you and it's currently not in the document.

If you have a spare hour at the end and a working pulse ox, add it as an optional calm-state
wellness check. Never as a trigger.

---

## P1-2: Token compression is a sponsor check-box wearing a pillar's costume

Compressing spatial RAG context is a real optimization, and the "tokens saved" counter is a
nice dashboard flourish. It is not a product pillar, and it must not consume an engineer for
a day. In the current table it's one third of Engineer 4's load, and Engineer 4 needs to be
doing integration.

**Fix:** it's a 2-hour task on the backend — compress the scene-graph and sensor JSON going
into the prompt, log before/after token counts, render a counter in the dashboard corner.
Assign it to whoever is green at hour 26. If nobody is green at hour 26, drop it without regret.

---

## P1-3: The Ramp fit is a slide, not an integration

"Reduces 24/7 memory care staffing overhead" is a market-sizing argument. Ramp is a corporate
card and spend-management platform, and their track will be judged on whether you *used their
product*. You have no Ramp API call anywhere in this architecture and no plausible reason to
add one — a family caring for a parent at home is not issuing corporate cards.

**Fix:** drop it. Chasing a track you can't integrate with costs you pitch time and makes the
rest of your track claims look scattershot. Four tracks you genuinely hit beats six you
gestured at. See `08-tracks.md`.

---

## P1-4: The "non-believer" angle is your best narrative and it's buried

Long Lake's "Convince a Non-Believer" is a storytelling track, and your project has the best
available story for it: the reason my grandmother won't use the tablet the family bought her
isn't that she's bad at technology, it's that the tablet demands she perform competence she no
longer has, and fails her publicly every time. A device with no screen, no login, no menus and
no correct way to hold it doesn't make that demand.

Right now this is one line in a matrix at the bottom of the document. It should be the second
thing out of your mouth at the table, because it's the part judges will remember and repeat to
each other. Put a real person in it — someone on the team has a grandparent, and that
30 seconds of specificity will beat every abstract claim in the deck.

---

## P1-5: Missing pieces a judge will notice

Five gaps, each about one paragraph of work to close, each of which someone will ask about:

- **What happens when it doesn't work?** There's no escalation ladder. If the person ignores the
  robot, what then? You need an explicit chain — redirect, familiar voice, caregiver's phone
  rings, emergency contact — with timeouts. `02-blueprint.md` §5.
- **Always-on microphone in the bedroom of someone who cannot consent to it.** This is the
  privacy question, and it's a good one. You need on-device wake conditions, no raw audio
  retention, a visible indicator, and a stated retention policy. One slide. `06-safety-ethics.md`.
- **Is it a medical device?** The honest answer is that it's positioned as a non-medical wellness
  and companion device that doesn't diagnose or treat, and isn't a substitute for supervision.
  Say it in one line before someone asks.
- **What if the person falls?** Your product is in the room when the worst thing happens. Even a
  crude "person is horizontal and not responding to voice → immediate escalation" is worth
  having, and its absence is conspicuous.
- **Did you talk to anyone?** The highest-leverage thing you can do that isn't code. One
  conversation with a memory-care nurse, an occupational therapist, or a family caregiver,
  and one quote on a slide — "I spoke with an RN in memory care, she told me X, so we changed
  Y" — outperforms a day of features. Caregiver support forums and subreddits will respond
  within hours. Do it at hour 2, while it can still change the build.

---

## What's genuinely strong here, and should not be touched

Not everything needs fixing, and it's worth being explicit about what to protect under time
pressure:

- **The problem is real, expensive, and underserved.** Nighttime exit-seeking is a top driver of
  the decision to move someone into a facility. Delaying that decision is worth an enormous
  amount to families. This is not a toy problem.
- **A mobile agent is a legitimately better answer than a fixed alarm.** A door sensor tells you
  after the fact and gives you no context. Something that can be present, see, and speak at the
  moment of confusion is a real capability difference, not a gimmick. This is the core insight
  and it holds up.
- **Screenlessness is a real design position**, not a feature cut. Defend it as such.
- **Voice plus embodiment is the right stack for this user.** You landed on it for good reasons.
- **The quadruped is actually justified here**, which is rare — it's the same argument as a
  guide animal, and it's the reason a wheeled base or a smart speaker doesn't substitute. Say
  the animal thing out loud; it makes the form factor feel inevitable rather than chosen for
  coolness.

The revised scope in `02-blueprint.md` keeps every one of these and removes the parts that put
them at risk.
