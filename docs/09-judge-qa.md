# Anticipated judge questions

Everyone on the team should be able to answer all of these. Judges split up — whoever is
standing at the table when one arrives has to handle the whole thing alone.

Keep answers to about fifteen seconds. If they want more they'll ask.

---

**"Isn't a robot blocking a confused person dangerous?"**

Yes, which is why we removed it. Blocking an exit-seeking person is a fall hazard and
functionally a restraint, and it's what memory care training explicitly teaches staff not to
do because it escalates. Lantern leads instead — it positions ahead and to the side, at least
1.5 m away, never in the doorway, and if the person walks at it, it yields. Walk at it and
you'll see.

*Best possible answer, because they asked the question expecting to catch you.*

---

**"Why a quadruped? Couldn't this be a smart speaker, or a camera, or a wheeled robot?"**

It has to be where the person is, at the moment of confusion — a fixed device can't do that.
And the form factor isn't arbitrary: it's the guide-animal argument. People respond to
something that moves like an animal in a way they don't respond to a machine on wheels, and
following something that walks is close to automatic. Stairs and thresholds are the practical
reason too.

---

**"How are you actually tracking the person?"**

Right now, off a fixed camera covering the mapped area — pose detection, homography onto the
floor plane — because this is a taped square in a convention hall and live SLAM in here would
be a hazard, not a feature. In a home it's the robot's own LiDAR, and that's running too; it's
the same message either way, and the dashboard shows which tracker produced each track. What we
deliberately didn't use is the Go2's built-in follow mode, because it tracks a worn beacon, and
the whole premise is that the person isn't wearing anything.

*Volunteering the limitation is the move here. They'll believe the rest of your numbers.*

---

**"It's a quadruped with a two-hour battery. How does it watch the house all night?"**

It doesn't — it's docked and asleep. What stays awake overnight is the microphone and a bed-exit
signal, which is the cheap part. A trigger wakes it, it does ten minutes of work, it goes back
to the dock. Two or three episodes a night is well inside one charge. The dock is a commodity
part Unitree already sells; the bed sensor is a twenty-dollar part we didn't build.

*They are doing this arithmetic whether or not you say it. Say it first.*

---

**"How is this different from ElliQ?"**

ElliQ is the closest thing to what we're doing on the conversation side, and it's a real
shipping product with research behind it. It's also a tabletop device. The entire premise here
is being in the hallway at 2 AM, which a table can't do. Same answer for Sensi.AI on the
detection side — they do passive audio monitoring better than we do, but detection ends at an
alert to somebody who isn't in the room yet.

*See `13-landscape.md` for the other six.*

---

**"How do you know it's actually detecting agitation and not random?"**

It's a behavioral pattern, not a clinical diagnosis — repeated corridor traversal with
direction reversals, plus speech rate and repeated questioning. We measured it: 20 trials, 10
positive, 10 negative. [Precision / recall / false positives.] The false positives matter most,
because a device that wakes you for nothing at 3 AM gets unplugged inside a week.

---

**"Isn't cloning a daughter's voice deceptive?"**

It would be if it claimed to be her. It never does — it says "Sarah recorded this for you."
Familiar voice, honest framing. Sarah records it herself behind an explicit consent checkbox,
and the consent timestamp is a required field in our message schema: without it the system
refuses to speak in that voice. It's also better technique, because it gives the person a
reason their daughter isn't physically present, which is often what's actually distressing
them.

*If they follow up with "but what stops the model from claiming to be her?":* it isn't a prompt
instruction, it's a filter on both sides of the model. Identity questions never reach the model
— they get a fixed answer. And any generated text asserting first-person identity is dropped
before it's spoken. Ask it yourself: **"are you Sarah?"**

---

**"Always-on microphone in a bedroom, for someone who can't consent. How is that okay?"**

We don't retain audio — it's streamed for transcription and discarded. The caregiver sees events
and summaries, not a transcript of everything their parent said all day; the person keeps some
privacy from their own family. There's a physical light showing when it's listening. Events are
kept 30 days, transcripts 24 hours, audio never.

---

**"Is this a medical device?"**

No — it's positioned as a non-medical wellness and companion device. It doesn't diagnose,
treat, or monitor for medical purposes, and it isn't a substitute for supervision. If we
pursued the agitation-detection piece as a clinical product, that's where a regulatory pathway
would start.

---

**"What if the person just ignores it?"**

Then it did its secondary job, which is arguably the primary one. After 20 seconds it escalates
to the caregiver: SMS and push, then an actual phone call at 60 seconds, because texts don't
wake people at 2 AM. And it stays with the person and keeps talking while help comes. The claim
isn't that we prevent wandering — it's that we buy the caregiver time and tell them what's
happening.

---

**"What if it scares them? A robot appearing in the dark seems worse than nothing."**

Real risk, and visual misperception is common in dementia — especially Lewy body. So: it
announces with voice before it moves, approaches only from the front within their field of
view, caps at 0.3 m/s within 3 m, and carries a warm steady light. And distress overrides the
mission: if the person is more agitated after we approach, the robot retreats and escalates
early rather than pressing on.

---

**"What about the $10,000-a-month facility claim?"**

We corrected that — US memory care runs roughly $5–8k/month in survey data. We'd rather use the
real number. Same for the wandering stat: it's about 6 in 10 people with dementia who will
wander at some point, which is lifetime incidence, not a per-event danger rate.

*Nobody will ask this. But if a judge who works in aging services notices you quietly using
correct numbers, that's the credibility you can't buy.*

---

**"What's actually novel here?"**

Two things. The robot's own navigation stack is the agitation sensor — trajectory data we're
already computing detects pre-wandering pacing before anyone touches a door, with no added
hardware. And the intervention policy: leading rather than blocking, which as far as we can
tell nobody has specified as an actual controller with parameters.

---

**"How does it handle two people in the house? Multiple floors?"**

Out of scope for what we built. Single-occupant, single-floor. Multi-person tracking is a real
problem we haven't solved, and stairs are excluded by our safety policy anyway.

*Say "we didn't do that" cleanly. Judges have heard a hundred hedges today; a straight answer
is memorable and it makes everything else you claimed more believable.*

---

**"What breaks?"**

Silent battery death is the one that worries us most — a safety device that fails quietly is
worse than no device, because the family has stopped listening for the door. Low battery is
itself a caregiver alert for that reason. Beyond that: false positives at 3 AM, and a person
who's frightened by the robot rather than calmed. We have a mitigation for each and none of
them are fully solved.

---

**"How would you deploy this? Who pays?"**

The family, as an alternative to the decision they're actually facing, which is whether to move
someone into memory care. At $5–8k/month, delaying that by a year is worth a great deal. The
realistic channel is through the care agencies and geriatric case managers families are already
working with. We haven't validated any of that — it's the first thing we'd test.

---

**"What would you build next?"**

Talk to twenty family caregivers before writing more code. The thing we'd most want to know is
whether the morning report or the live intervention is what actually makes a family keep the
device — our instinct is the report, and if that's right it changes the product substantially.

*Answering "more user research" rather than "more features" reads as maturity, and it's true.*

---

## If the demo fails mid-pitch

Don't apologize twice and don't narrate the debugging. Move to the next fallback level and keep
telling the story:

> "The robot's out — battery. Let me run it against the simulator, everything else is live, and
> I've got 20 seconds of hardware video."

Judges see failed hardware all day. What they're actually evaluating in that moment is whether
you planned for it. A team that switches fallback modes smoothly looks *more* competent than
one whose demo happened to work.
