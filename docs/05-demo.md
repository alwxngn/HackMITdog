# Demo plan

## The format mismatch you have to fix first

The original plan has exactly one demo: a 3-minute stage script with a robot crossing a stage.

You will give the stage demo at most once, and only if you make finals. You will give the
**table demo 15 to 25 times**, to rotating judges, in a crowded hall, in roughly a 6-by-6-foot
footprint, with people walking through your space and a noise floor around 80 dB.

So the table demo is the primary artifact and the stage version is derived from it. Build it
in that order.

## Constraints the table imposes

| Constraint | Consequence |
|---|---|
| ~6×6 ft of floor | The robot cannot roam. Tape out a small "room" on the floor. The demo happens inside it. |
| Loud hall | Open-mic mumbling will not transcribe. Headset or lav on the person playing the patient. Say plainly that the home version uses a far-field array. |
| Go2 battery ~1–2 h active | Two packs minimum, rotating on the charger. Robot idles between demos; it only walks during the one beat that needs it. |
| Judges arrive mid-loop | Under-10-second reset, one key. Demo must be idempotent. |
| Hundreds of moving people | **No live SLAM.** Pre-authored map, hard geofence at the tape line. Live mapping here is a failure mode, not a feature. The taped corners double as the person-tracker's calibration (`11-perception.md`) — **re-calibrate once you're set up in the actual demo spot.** |
| People walking through your shot | The tracker needs an actor lock: on reset it latches onto whoever is standing in the start box and ignores everyone else. Otherwise a passing judge becomes the patient mid-demo. |
| Judge attention ≈ 90 s | One beat, done well, beats four beats rushed. |
| Judges may step toward the robot | The yield rule has to be real, because someone will test it. When it works, that's the best moment of your demo. |

## The 90-second table demo

Someone plays Arthur. Someone narrates. The laptop shows the dashboard. A phone sits face-up on
the table where the judge can see it.

**0:00–0:10 — The hook.** *"It's 2 AM. Arthur has dementia. He's about to try to leave the house
— and the way his daughter finds out today is a door alarm, after he's already outside."*

Set the scene before anything moves. Judges who don't have the frame don't understand what
they're watching.

**0:10–0:25 — Pacing.** Arthur walks back and forth across the taped area. Point at the
dashboard: agitation moves `calm` → `unsettled`, with the reason string rendering live —
*"3 direction reversals in 90 s."*

*"Nothing has happened yet. No door has opened. But it already knows something's starting."*

**0:25–0:45 — Attend and converse.** The robot announces from where it is, then approaches to
the front-sector standoff. Arthur mumbles *"where am I supposed to be"*. Transcript appears.
The robot answers in the familiar voice: *"It's night time, Arthur. You're home. Sarah recorded
this for you."*

*"It never corrects him, never tests his memory, never claims to be his daughter."*

**0:45–1:05 — Lead away.** Arthur turns toward the taped exit zone. Agitation goes `agitated`,
state goes `LEAD`. The robot moves to a point ahead and to the side — **never into the
doorway** — and walks slowly toward the safe zone while talking.

This is the line to say slowly, because it's the one that separates you:

*"Watch what it doesn't do. It doesn't block him. A robot blocking a person with dementia at
2 AM is a fall risk and it's a restraint. It leads instead — 1.5 m standoff, 0.3 m/s, always in
his field of view, and if he walks at it, it gets out of the way."*

**Invite the judge to test it.** "Walk at it." They do. It yields. `robot_status: yielded`
appears in the log. That ten seconds does more for you than any slide.

**1:05–1:20 — Escalate.** Arthur ignores the robot. Twenty seconds elapse. The phone on the
table lights up: *"Arthur is heading for the front door."* Dashboard goes to alert. The judge
can pick up the phone.

*"SMS first, then an actual phone call after sixty seconds — texts don't wake people at 2 AM."*

**1:20–1:30 — Morning report.** Click to the report. *"Two events overnight, both resolved by
redirection, he was up eleven minutes at 2:14."*

*"This is the part that makes a family keep the device. It's the first time they wake up
knowing what happened instead of guessing."*

**Then stop talking.** Let them ask. If they have three minutes and want the numbers slide, it's
ready. If they're already moving, they leave with a complete story.

## Fallback ladder

Decide these in advance, rehearse each one, and assume you will use at least one. Every team
does; the difference is whether it looks like a plan or a collapse.

| Level | When | What you do |
|---|---|---|
| **A — Full** | Everything up | The demo above. |
| **B — Sim robot** | Robot dead, battery out, SDK wedged | Run `mock_robot`. **Person tracking, dialogue, dashboard, and escalation are all still live** — a real human walks the taped area and the whole product responds; only the robot's motion is simulated on the map. Say: *"navigation is running against our simulator right now — the expo floor isn't a home. Here's the hardware video."* Then play 20 seconds of it. This is not embarrassing. Judges see dead hardware all day. |
| **C — Voice only** | Robot and map both down | Live voice conversation with the dialogue policy plus the dashboard replaying a logged event. The conversation alone is compelling with this user story. |
| **D — Video** | Laptop, network, or venue failure | The hour-30 backup video, 90 seconds, narrated, plus the slides. |

**Record the level-D video at 6 AM Sunday.** Not at 10. Record it while everything works — you
cannot record a working demo after things stop working, and that is precisely when you need it.
On a 24-hour clock that deadline lands when everyone most wants to sleep, which is exactly why
it has to be a deadline rather than an intention.

Two parts: a screen recording of the dashboard through a full event, and phone video of the
robot doing the lead-away in a quiet room. Cut together, narrated, under 90 seconds.

## Reset procedure

One key. Under ten seconds. Written down and tested by someone who didn't build it, because at
9 AM Sunday the person who built it may be asleep or talking to a judge.

- Orchestrator to `IDLE`, agitation cleared, alerts cancelled
- Robot to home pose inside the taped area
- Dashboard timeline cleared, map view re-centered
- Phone alert dismissed
- Voice pipeline flushed (no leftover audio in the buffer — this one will bite you)

## The stage version (finals only)

Same beats, more room, add one thing: **open with a real person.**

Thirty seconds of *"this is my grandmother, this is what happened in her house"* — a real name,
a real night. Then the demo. Stage judging rewards story in a way table judging doesn't, and
the technical content is identical.

Extra stage constraints: bigger space means the robot travels further, so rehearse the actual
distances; stage lighting is bright and hot; venue wifi will be saturated, so tether the
laptop to a phone hotspot and have the Twilio alert land on a phone you control. Do not build
the climax around a judge's phone receiving an SMS over congested cell service.

## Devpost

Draft it around 7 AM and **submit by 10:30**, not at 11:40. Lead with the 2 AM scene. Include
the safety envelope table and the measured numbers — the written submission is where the
judging-rubric points for rigor actually live, and it's the only artifact that's read without
you standing next to it. Include `CREDITS.md`; HackMIT requires open-source citation in the
submission.
