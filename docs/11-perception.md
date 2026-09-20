# Person tracking — the dependency nobody specified

Closes P0-10. Owner: **E2**, with E4 consuming.

`04-interfaces.md` defines `person_track` precisely and never says where it comes from. Six
things depend on it (see `10-second-pass.md` P0-10), including all three safety-envelope rules.
This document specifies how the message actually gets produced, and in what order to build it.

## What has to be true

A `person_track` at ~10 Hz carrying, in the **map frame** (metres, origin at a corner of the
mapped area):

| Field | Source | Notes |
|---|---|---|
| `x`, `y` | tracker | Floor position, not image position |
| `vx`, `vy` | finite difference + smoothing | Smooth it; raw frame-to-frame difference is noise |
| `heading` | velocity vector when moving, body orientation when still | **Both cases matter** — the lead-away controller needs a heading from a person standing still and deciding where to go |
| `posture` | keypoint geometry | `standing` / `sitting` / `lying`; `lying` outside a bed zone is the fall signal |
| `confidence` | detector score × track age | Let the orchestrator ignore weak tracks rather than guess |

Anything that emits this message is a valid tracker. That is the whole point of the schema: the
tracker is swappable, so pick the one you can make reliable and upgrade only if there's time.

**Add one field to the schema** (do it now, before the freeze):

```json
{ "type": "person_track", "payload": {
  "tracker": "overhead_cam",
  "...": "everything else as specified in 04-interfaces.md"
}}
```

`tracker`: `overhead_cam` | `lidar_cluster` | `onboard_fusion` | `mock`. Render it in the
dashboard corner. When a judge asks how you're tracking the person, pointing at a live field
that says which sensor is in use is a better answer than a description, and it keeps you honest
about which one you're actually demoing.

**No `gps` tracker — outdoor guided walks don't need one.** All three trackers in this document
are indoor and taped-area-relative, but that's fine: the Tier 2 guided-walk feature
(`14-companion-and-caretaker.md` §6–9) uses `onboard_fusion` outdoors exactly as it's used
indoors for the `FOLLOW` radius check (robot-relative, so location doesn't matter), and homing
("take me home") runs on the robot's own `pose` odometry rather than on `person_track` at all —
specified separately in the companion-and-caretaker doc.

---

## Tracker A — fixed camera over the mapped area

**Build this one first. It is the one that makes your demo deterministic.**

A webcam or a phone on a small tripod at the corner of your taped area, looking down across it.
Person detector (YOLO-pose or MediaPipe Pose, whichever imports fastest) on the laptop. Foot
midpoint from the keypoints, projected to the floor plane through a homography.

**Calibration is the four corners of tape you were already going to lay down.** Click them in
the image, name their real-world coordinates, `cv2.getPerspectiveTransform`, done. Fifteen
minutes including finding the tripod.

Why this first, despite feeling like a cheat:

- **It works when the robot doesn't.** Charging, rebooting, SDK wedged, battery swapped — the
  tracker keeps running, which means the dashboard, the orchestrator, the pacing detector, and
  fallback level B all keep running. That is the single biggest de-risking move available to
  you in a 24-hour event.
- **E2 can develop the lead-away controller against a real human immediately**, with no robot
  in the loop, from the first hour.
- **The map frame is the taped rectangle**, so there is no SLAM, no drift, and no localization
  problem. `05-demo.md` already told you not to do live SLAM in the venue; this is what that
  decision looks like implemented.
- **It sees the person the whole time.** Tracker B cannot (see below).

**The expo-hall failure mode is other people walking through frame.** Handle it with an actor
lock: on demo reset, the tracker latches onto the single track whose feet are inside the start
box, and follows that track ID. Everyone else in frame is ignored. Ten lines of code, and it
also stops a judge stepping into the taped area from becoming the patient mid-demo.

**Say the honest sentence, unprompted:** *"Right now the person tracking runs off a fixed camera
covering the mapped area, because this is a taped square in a convention hall. In a home it's
the robot's own sensors — same message either way, and here's the onboard tracker running."*
Then show Tracker C if you got it working. Volunteering the limitation costs you nothing and
buys you the judge's trust for everything else.

---

## Tracker C — LiDAR cluster tracking (the upgrade to build second)

Listed before B because it is more useful and more likely to work.

The Go2's 4D LiDAR is **360°** (L1 is 360°×90°, L2 is 360°×96°, both at 21,600 samples/s with a
5 cm minimum range). Take a horizontal band of the point cloud roughly 0.3–1.2 m above the
floor, subtract the static map, cluster what remains (DBSCAN or a grid), and track centroids
with nearest-neighbour association and a constant-velocity model.

No identity, no posture. For a single-occupant demo that doesn't matter.

**The reason this beats the camera approach on the robot: during lead-away, the robot walks away
from the person.** That is the entire behavior — position ahead, then move toward the safe zone
while the person follows. The person is *behind* the robot for most of the beat, outside a
120° forward camera FOV. A tracker that loses the person exactly when the lead-away starts is
useless for the thing you are demoing. The LiDAR is 360°; it does not have this problem.

Posture stays with Tracker A (or gets dropped — `lying` detection is a Tier 2 nicety, not part
of the spine).

---

## Tracker B — onboard camera + LiDAR fusion (only if you have EDU and spare time)

Person detection on the Go2's HD camera (120° FOV, 720p/1080p at 15 fps) gives bearing; LiDAR
returns in that bearing wedge give range; the robot's pose transforms it into the map frame.

This is the "real" answer and it is the one to describe as future work. It needs camera-LiDAR
extrinsics, a robot pose you trust, and the Jetson Orin compute module — which is **EDU-only**.
15 fps is fine for a person moving at walking speed; the extrinsics and the pose drift are what
will cost you the night. It also inherits the FOV problem above.

Do not start here. If Tracker A and C are both green and it is somehow still Saturday, then
consider it.

---

## What to do about ISS 2.0 (the built-in follow mode)

The Go2's Intelligent Side-follow System tracks the **wireless vector positioning module** — a
device, not a person. It is also not available on the Air SKU.

Using it means the person with dementia is wearing a beacon, which directly contradicts
`02-blueprint.md` §2, where you dismiss wearables because they are "frequently removed or
forgotten, which is precisely the symptom." A judge who knows the platform will spot it, and
that one detail takes down the differentiation the whole pitch rests on.

**Recommendation: don't use it in the demo, and have the answer ready.** *"The Go2's built-in
follow tracks a beacon. We deliberately didn't use it — the whole premise is that the person
isn't wearing anything, because the thing they reliably do is take it off. We track them from
the sensors on the robot."* That is a strong twenty seconds and it turns a platform limitation
into evidence you thought about the user.

---

## The yield reflex does not use the tracker

**This is the most important paragraph in the document.**

`06-safety-ethics.md` requires the robot to retreat when a person comes within 1.2 m, and
requires it as a controller-level reflex rather than a state transition. Implement it against
**raw forward LiDAR minimum range**, or the Go2's own obstacle avoidance — not against
`person_track`.

Reason: the tracker is the most complex and most failure-prone thing in the stack, and the yield
rule is the one behavior that must work when everything else is broken. A safety reflex that
depends on a perception pipeline is not a safety reflex. It also means the rule fires correctly
for a judge who walks up from an angle the tracker never saw, which is exactly what a judge
will do.

Same reasoning for the doorway exclusion: it is a geometric constraint on the robot's own pose
against the map, and needs no knowledge of where the person is. Both rules should be provably
true from the robot's own state alone.

---

## Build order and budget

| Step | Who | Budget | Done when |
|---|---|---|---|
| 1. Tape the area, measure corners, write them down | E2 | 15 min | Four (x, y) pairs in a file |
| 2. Homography + detector → floor coordinates | E2 | 60 min | Walking the area draws a sane path on a plot |
| 3. Velocity, heading, smoothing, actor lock | E2 | 45 min | Track survives a judge walking through frame |
| 4. Emit `person_track` on the bus at 10 Hz | E2 | 20 min | E4's orchestrator reacts to a real human walking |
| **Gate** | | | **The spine can be demoed with a person and no robot** |
| 5. Posture from keypoints | E2 | 30 min | `lying` fires when someone lies down |
| 6. LiDAR cluster tracker behind the same schema | E2 | 2–3 h | Robot tracks the person through 360° |
| 7. Onboard fusion | — | — | Future work. Say so. |

Step 4 is the real milestone. Once the orchestrator is reacting to a live human, you have a
demoable product with zero hardware risk, and every hour you spend on the robot after that is
upside rather than exposure.

## Tuning notes

- **Smooth velocity over about 0.5 s.** The pacing detector counts direction reversals; raw
  jitter manufactures reversals and your false-positive rate is a number you promised to report.
- **Heading when standing still** comes from the shoulder-keypoint line, disambiguated by which
  way the nose keypoint faces. Falling back to a stale velocity heading makes the lead-away
  controller position itself behind someone who has turned around — a direct violation of the
  ±45° approach sector.
- **Detector at 10 Hz is plenty**, and downsampling leaves CPU for everything else on the laptop.
- **Log every frame to the JSONL bus log.** Metric 3 is computed from it, and you cannot re-run
  twenty pacing trials at 9 AM Sunday.
