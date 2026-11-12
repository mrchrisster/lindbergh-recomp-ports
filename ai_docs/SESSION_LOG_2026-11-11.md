# Session log – 2026-11-11 (conductor)

A record of all work done on the Virtua Tennis 3 Quest port on 2026-11-11, in
order. For *what to do next* read `HANDOFF.md` section 3.1 (checkpoint log,
newest first) and `CONDUCTOR_STATE.md`; for *how each fix works* read
`docs/VT3_PORTING_GUIDE.md` section 8 and `ai_docs/research/`. This file is
the history and the reasons.

Working method (owner's): a conductor plans and checks; each task goes to its
own Opus 5.5 worker; one worker at a time on the headset and build dirs;
read-only research runs alongside; workers checkpoint to `HANDOFF.md` after
every step because the usage limit cuts them off; nothing is pushed until the
owner says so.

## 1. Timeline of work

| # | Work | Submodule | Outer | Status |
|---|---|---|---|---|
| 1 | Steady camera between points, clean cuts; Quest shot buttons; splash map | `1b1988b` | `c82ec03` | pushed |
| 2 | Replays-off bug closed; live Replays-off skip; setMode wrap independent of FORCE_REPLAY; labels | `dca91c9` | `bfc19cd` | pushed |
| 3 | Live mode switch groundwork (off, no behaviour change) | `3a713ff` | `2525e67` | pushed |
| 4 | Music skipping fixed (SEGAAPI loop-end position), audio diagnostics | `fa83fd6`, `77875a4` | `80e69e9` | pushed (fork: submodule `77875a4`, outer `38b92e1`) |
| 5 | Crowd / shadow leads checked on the Quest (docs) | – | `38b92e1` | pushed |
| 6 | Whole stadium drawn in Immersive; stand stretch and crowd cut removed; Sky stadium / painted / off | `fade8ac` | `5f89c0d` | local; the match-start hang was not the stadium's but the GL queue's (item 8, fixed); stands cost +0.2 ms GPU |
| 7 | Handoff / conductor checkpoints; harvested runs; T3–T5 review; safety copies in `ai_docs/wip/` | – | `9f19b32`, `621f143`, `f37109d`, `dd271cf` | local |
| 8 | GL queue second-writer fix (the match-start hang / crash) | `373c5ae` | this commit (see `git log`) | **verified on the Quest**, local, installed |
| 9 | T3 sky fill behind the dome, T4 per-eye ground shadow mask, T5 GLES LOD bias | working tree | working tree (`quest/gl4es.patch`) | written, reviewed, **never run on the headset** |

Read-only designs produced (in `HANDOFF.md` sections 4 and 5): live Classic /
Immersive switch (steps 2–8 remain), in-scene scoreboards.

## 2. What each piece was

### 2.1 Steady camera, controls (item 1)
Uncommitted work from an earlier session was reviewed, tested and committed.
With Point cutaways off the win/lose loop is not entered and big points have
no serve close-up; camera mode stays 1 from first serve to game set and match
(Quest `prize`: 1949 -> 3013). Remaining cuts are clean (camera through the GL
queue, flat/world at the mode change, the cut's captured picture left out).
Review fix: the skip leaves a requested versus game to the game. Controls: the
cabinet has two shot buttons – trigger top spin, A/X slice, B/Y lob.

### 2.2 Replays (item 2)
Owner's report "some replays still play with Replays off" was the point
close-ups. Replay playback has one gate (`replay::isReplay_point`), already
wrapped; 0 `ReplayLoop` in long runs (arcade, Immersive, attract). Added: a
replay playing when Replays goes off ends through the game's skip path; the
`setMode` wrap is installed even with `LINDBERGH_FORCE_REPLAY=1`.
**Owner's decision:** Replays and Point cutaways stay two rows; both off in
Immersive.

### 2.3 Live mode switch groundwork (item 3)
`world_mode.c` target / game / GL latches, `world_mode_frame()`, switch
callback, `LINDBERGH_VT3_MODE_AT`, `XwState.live`. Nothing is live: no
callback is registered. Remaining steps: `HANDOFF.md` 4.6.

### 2.4 Music, stadium, shadows, sharpness (items 4–6, 9; another session)
See `ai_docs/research/audio-music-skipping.md`,
`crowd-and-upper-stands.md`, `shadow-resolution.md`. Owner's decisions: draw
the real stands, no stand stretch, use each court's own sky. Each court's sky
is only a TV-camera backdrop with a hard top edge; the painted sky fills the
rest (T3, unrun).

### 2.5 The cut-off regression, harvested (item 7)
The stadium worker was cut off mid-regression. From its logs and new runs:
- Immersive `prize` on the stadium build passed (two 600-frame slates, no
  black frames at cuts) – but with `LINDBERGH_BLACK_LOG=1`, whose per-frame
  readback hid the hang and made its frame rate (33 fps) meaningless.
- Classic `prize` passed (slates 602 / 600). One extra black frame at 9612,
  four frames into the third match's entrance fly-by; no older Classic
  black-log run to compare.
- Stands off: GPU 2.6–3.8 ms, 59.4–59.8 fps. Stands on: **still owed**.
- T3–T5 review: one defect fixed (LOD bias was on for every game sharing
  gl4es; now Virtua Tennis 3 only). Kill switches restore `fade8ac`:
  `LINDBERGH_VT3_MASK=0`, `LINDBERGH_LOD_BIAS=0`, `LINDBERGH_VT3_DOME_FP=0`.

## 3. The match-start hang / crash (item 8)

**Symptom.** Immersive froze or crashed at match start (frames ~2003–2328).
2 of 2 unattended stands-on runs; the owner hit it worn with no env at all.
Stands off ran through. An older build (`77875a4`, before the stadium) also
hung once. Classic never.

**Cause.** A second thread writes the GL queue. The game runs
`camera::gameRoutine` on one of its own worker threads. In Immersive the
camera feed (`h_vt3_game_routine`, `LINDBERGH_VT3_FEEDCAM`, default on) calls
`vt3_note_projection` -> `glq_job(vt3_cam_job)` from that thread every frame
until the game sets the world camera itself. The ring in `gl_thread.c` assumes
one writer (`g_head_mine`, `ring_take` / `ring_put` unlocked). Colliding writes
corrupt record sizes; the worker then replays stale records – spinning forever
while the main thread waits in `glq_wait` (the hang), or running old camera
jobs whose `Vt3Cam` was freed, double-freeing them (SIGSEGV in `calloc`; the
garbage `[arbprog] game projection` lines were host heap pointers).
More draws per frame (the stadium) means more collisions.

**How it was found.** A writer-thread check in the queue on a macOS ASan
build: 20+ `glq_job` calls from another thread in the first 20 match frames of
an Immersive run, backtrace `glq_job <- h_vt3_game_routine`. Classic: 0.
The owner's hung process (inspected read-only): main thread in `glq_wait` <-
`mirror_call` <- `TScene::Batch::updateDynamic`; the GL worker in state R at
~1 CPU, flat memory – spinning.

**Fix** (`gl_thread.c`, `crash_report.c`; safety copy
`ai_docs/wip/glq-second-writer-fix.diff`):
1. `glq_job` from a thread other than the queue's writer puts the job in a
   small locked list (`foreign_job`, 256); the writer queues it at its next GL
   call or job. Logged once: `[glq] job vt3_cam_job from thread ... handed to
   the game thread's next call`.
2. Lost wake-up fixed: the worker wakes the game when it goes idle (a full
   ring of plain calls could leave the game asleep).
3. Diagnostics: every record checked (`[glq] FATAL: bad record` + last 16
   records instead of replaying); `[glq] WARNING ... from thread` for GL calls
   from other threads; the hang watchdog prints queue positions and the GL
   worker's stack.

**Verified** (HANDOFF 3.1, runs in `/tmp/vt3q/P2/`): macOS ASan, Immersive
with the stadium, 11,611 frames, one "handed" line, no WARNING / FATAL.
Quest, installed clean `fade8ac`: 1 of 3 crashed at frame ~2009 (GL worker in
`cls()` on a garbage record id - a scrambled record); `LINDBERGH_VT3_FEEDCAM=0`
3 of 3 clean. Fix build (`fade8ac` + fix only): 5 of 5 Immersive stands-on
match starts clean (3 with no env but the pins, 2 with GPU_TIME +
KEEP_ON_PAUSE), full `prize` Immersive (4 matches, slates 600 frames) and
Classic (Winlose, Replay, Gamesetmatch, next round; black frames only the
game's own). Stands' GPU cost: +0.2 ms (3.6 vs 3.3-3.7 ms per frame in the
match), 60 fps unworn. Committed: submodule `373c5ae` and the outer commit
after it; that build is installed.

**Found on the way, not fixed:**
- `quest/gl4es.patch`: `mv_copy[64]` keeps `gltexture_t*` after
  `gl4es_glDeleteTextures` frees it (dangling read in `mv_framebuffer_left`,
  leaked `mvarray`, slots never freed).
- `kgsl GPU PAGE FAULT` ~900/s in every Quest logcat from boot frame ~1070
  (after `fragment program 21/22 ... units 0x8000 compare depth`), Classic
  too (checked on the fix build): a shader out-of-bounds read, unrelated to
  the hang.
- `ai_docs/README.md` said Immersive does not run on macOS; it does (corrected).

## 4. What the owner has seen worn, and said

- Before `1b1988b`: B button unmapped; 1 s camera changes after each point;
  stretched low-resolution audience, upper bleachers missing, crowd floating;
  low-resolution shadows; music skipping. Each has a fix above; none of the
  fixes had been confirmed worn before today's last builds.
- On the clean `fade8ac` build: **upper stands visible.** One launch **hung**
  at match start (the bug in 3). **"The sky dome looks different over 180
  degrees"** – the court's own sky covers only the broadcast view; beyond its
  edge the old painted sky shows and does not match. T3 addresses it; the seam
  needs the owner's eyes.
- First time he looked, the stands were missing: an unattended
  `LINDBERGH_VT3_STANDS=0` baseline was running on the headset and the
  installed APK was an earlier iteration. Lesson: **do not run unattended
  tests while the owner may put the headset on; tell him when a run is
  active; install only builds of committed code for him to judge.**
- Battery rule: stop runs at 3%.

## 5. Queue after the hang fix

1. T3 sky seam on three venues; Stadium / Painted / Off side by side for the
   owner. T4 per-eye ground shadow mask. T5 crowd / board sharpness. Each on
   the headset, then commit.
2. Stadium checks still owed: rounds 1 and 2, turned 180 and pitched 70; near
   end's lower seats have no crowd cards (probably data).
3. gl4es `mv_copy` dangling pointer; GPU page faults.
4. Live mode switch steps 2–8; in-scene scoreboards (placement defaults in
   `HANDOFF.md` 5.1 still unconfirmed by the owner); camera work (needs the
   owner's direction).
5. Worn checks by the owner: music, buttons and lob, steady camera, panel
   clicks, serve meter with the head turned, 72 / 90 / 120 Hz frame rate.
6. Push to `fork` when the owner says so (local only from `fade8ac` on).

## 6. Evening: T3-T5 on the headset (T3-T5 worker)

- WIP build smoke-tested (Immersive `prize`: slates 601 / 600, no compile
  errors, no `[glq]` FATAL / WARNING).
- **T5 LOD bias committed** (submodule `8004564`, outer `c07bad8`): crowd and
  boards sharper, no shimmer seen.
- **T4 per-eye shadow mask fails**: the players' ground shadows vanish with
  it on - not committed (`ai_docs/wip/`).
- **T3**: fp 180 is not the sky backdrop (a sun-glow term); the visible front
  sky and a lavender wedge stay in Painted / Off. The seam work needs the
  real backdrop draw found first (skip-bisect queue ready). Not committed.
- Unattended shots differ per launch (head pose): new test switch
  `LINDBERGH_XR_FIXED_HEAD=1` (WIP).
- Stopped on controller input during a run (headset possibly worn):
  env.txt emptied, vr.cfg unchanged, committed fix build re-installed.

## 7. Night: the sky (sky worker)

- Step 0: the committed build (`0dbcb6e` = fix + T5 + FIXED_HEAD switch)
  regression-passed and installed.
- The real sky found: `GAME_NO_SKY_Polygon`, one full-hemisphere draw with
  the venue's 360-degree panorama, clipped by the headset's reprojection to
  a front cone. Fixed (`9d68719`): Sega's sky all round; Sky Painted / Off
  act on it. Seam pictures in `~/Desktop/Claude/vt3-sky/`.
- Found: result-slate GPU spikes (20-40 ms) whenever the eyes are set while
  the session is stopped - possibly the worn slate path; to check.
