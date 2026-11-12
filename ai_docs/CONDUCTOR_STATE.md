# Conductor state – 2026-11-11 (written at the usage limit)

Read `ai_docs/README.md`, then `ai_docs/HANDOFF.md`, then this.

## Pushed to `fork` (branch `vt3-quest`)
Submodule `lindberghrecomp` 77875a4, outer 38b92e1: match-end fix, serve meter /
HUD anchors, two-mode panel, point cutaways / steady camera, buttons (trigger top
spin, A/X slice, B/Y lob), result slate, sky cost, black frames at cuts, music
skipping fix, live-switch groundwork (off), all research in `ai_docs/research/`.

## Local only, not pushed
- Submodule fade8ac / outer 5f89c0d: Sega's whole stadium drawn in Immersive
  (`h_vt3_field_draw`, `LINDBERGH_VT3_STANDS=0` off); stand stretch and crowd cut
  REMOVED (owner's decision); Sky setting stadium|painted|off. Seen on round 0
  Quest: Immersive `prize` regression PASSED (flow, slates 600 frames, next
  rounds, black frames only the game's own). Done with the hang fix: Classic
  `prize`, stands GPU cost (+0.2 ms, 60 fps), no audio `health` line with
  KEEP_ON_PAUSE. Still owed: rounds 1 and 2, turned 180 / pitched 70.
  Ready-to-paste run list: HANDOFF 3.1.
- Written, uncommitted or WIP, never run on the headset: court sky backdrop +
  painted sky behind it (T3), per-eye eye-sized ground shadow mask
  (`LINDBERGH_VT3_MASK=0` old path) (T4), GLES texture LOD bias
  (`LINDBERGH_LOD_BIAS=0`, `quest/gl4es.patch` regenerated; now default on
  for VT3 only) (T5). Safety copy + README in `ai_docs/wip/`. Self-shadow
  tile zoom (T6) not started. Details: `ai_docs/research/crowd-and-upper-stands.md`,
  `shadow-resolution.md`.

## Match-start hang - FIXED (2026-11-11, local)
Submodule `373c5ae` (on top of `fade8ac`): Immersive's camera feed queued GL
jobs from one of the game's worker threads, a second writer on the
single-writer GL queue (crash in calloc / hang in glq_wait at match start).
Verified on the Quest: 5 of 5 match starts, full `prize` both modes, stands
GPU cost +0.2 ms. **Installed: that build (fade8ac + 373c5ae, committed code
only).** The T3-T5 WIP is back in the working tree on top of it (unchanged
from `ai_docs/wip/`). Rule learnt: anything queued for the GL thread must
come from the game's main thread.

## Evening 2026-11-11 (T3-T5 worker) - read HANDOFF 3.1 first entry
- T5 LOD bias COMMITTED (submodule 8004564, outer c07bad8), not yet in an
  installed build. T4 per-eye mask BROKEN on the Quest (shadows vanish), T3:
  fp 180 is not the sky backdrop - both uncommitted in `ai_docs/wip/`.
- Testing stopped on controller input (possibly worn). Installed: the
  committed fix build (fade8ac + 373c5ae), env.txt 0, vr.cfg the owner's.
- Owed: rerun from HANDOFF 3.1 when the owner frees the headset (skip-bisect
  `scratchpad/q4.sh`, T4 debug, T5 build regression + install).

## Night 2026-11-11 (sky worker) - Installed build / headset state
- Installed: submodule `9d68719` build (fix + T5 + Sega's sky dome all
  round), regression PASSED (Immersive prize slates 601/600 + Classic prize
  601/600, next rounds, match starts on rounds 0-2, black frames only the
  game's own). APK copy
  `/private/tmp/claude-501/-Users-chrishelms-Desktop-Claude/786966e7-92df-442c-b205-476a682b88a2/scratchpad/w2/VirtuaTennis3VR_skyonly.apk`;
  previous good build `.../w2/VirtuaTennis3VR_0dbcb6e.apk`. App stopped,
  env.txt 0 bytes, vr.cfg = owner's (byte-identical). Owner to judge the sky
  worn; pictures `~/Desktop/Claude/vt3-sky/`.
- T4 shadow mask: still broken, only in `ai_docs/wip/` (opt-in there).

## Headset (check first)
`adb shell wc -c /sdcard/VirtuaTennis3/env.txt` must be 0; the installed APK may
be an unregressed test build (fade8ac or later). Last known-good APK copy:
`/private/tmp/claude-501/-Users-chrishelms-Desktop-Claude/123aec40-e8f4-4db0-ae75-fecb4ddcd54c/scratchpad/installed_77875a4.apk`
(scratch dir, may be gone – else rebuild at 77875a4). Owner's vr.cfg untouched
(`immersive.stand_y 1.5` is now ignored; `immersive.sky on` reads as stadium).

## Owner's decisions
- Push to `fork` only when the owner says so; never to lialan upstream.
- Replays and Point cutaways are separate rows, both off in Immersive.
- Draw the real stands; no stand stretch; use each court's own sky (it is only a
  TV-camera backdrop: hard top edge, nothing behind – painted sky fills the rest;
  owner must judge the seam worn).
- Checkpoint progress to files continuously (usage limit cuts workers off).

## Not yet checked worn by the owner
Music fix (and loudness / limiter distortion: `sound_gain`), buttons and lob,
steady camera between points, panel clicks and "Restart now", serve meter while
turning the head, frame rate at 72/90/120 Hz, the new stands and sky.

## Next, in order
1. Finish the owed Quest checks above; commit; install a regression-passed build.
2. T3 sky seam on three venues; T4 shadow mask; T5 LOD bias; then T6.
3. Near-end lower seats have no crowd cards when looking behind (round 0).
4. HANDOFF.md sections 3-5: live mode switch, in-scene scoreboards, cameras.

## Late evening 2026-11-11 (conductor checkpoint, near the usage limit)
- Sky worker running on the headset (agent a7afa4d451c30bcc6). Step 0 DONE:
  committed build (submodule 8004564 + 0dbcb6e FIXED_HEAD test switch, outer
  43b6e93) regressed and installed. It has stadium + hang fix + T5 sharpness.
- A test run is active (env.txt not empty) - owner must NOT wear the headset
  until env.txt is 0 bytes and a committed build is installed.
- Owner asked: "let me know when I should visually confirm a new build".
  Tell him at (1) the next pause with the committed build installed,
  (2) after the sky build is committed (images in ~/Desktop/Claude/vt3-sky/).
- Worker told to checkpoint HANDOFF 3.1 after every step, commit docs at
  once, keep wip diff current, pause and report before the next run.
- If cut off: resume from HANDOFF 3.1 top entry; first empty env.txt, check
  the installed build, then continue the sky backdrop search.
- After sky: T4 shadow mask debug, rounds 1/2 stadium checks, gl4es mv_copy,
  GPU page faults, live switch steps 2-8, scoreboards, cameras. Push to
  `fork` only on the owner's word.

## 2026-11-11 22:55 (conductor status check)
- **Sky: DONE, confirmed by the owner worn.** Pushed to `fork`: submodule
  9d68719, outer 1f3ec0f.
- T7 near-end crowd cards: parked by the owner.
- T8 (owner's worn reports on 9d68719: Classic top-down frame at match
  start; Immersive "image in image" before each serve): fixes written, test
  runs good, **NOT committed, regression NOT run** - worker cut off 20:55.
  Code in the submodule working tree = `ai_docs/wip/t8-flat-and-fade-lindberghrecomp.diff`.
  **Installed APK is that unregressed T8 test build**; env.txt 0 bytes.
- Research written (uncommitted until this commit):
  `ai_docs/research/card-reader-top-bar.md` - recommended fix: answer card
  R/W OFF (`backup::getCard_rw_1p_use/_2p_use` = -1). Not implemented.
- Next: (1) T8 regression both modes -> commit -> install; (2) card reader
  bar fix; (3) T4 shadow mask; then gl4es mv_copy, GPU page faults, live
  switch 2-8, scoreboards, cameras.

## 2026-11-11 ~23:10 (owner's feedback)
- **T8 confirmed worn by the owner** (image in image, Classic stray 3D, court
  from above) on the test build; regression + commit in progress (worker).
- New owner requests: **T9** Immersive distance choices 5/6/7/8 m (3 and 9
  too extreme) and a **camera height** row - given to the T8 worker to do
  after its commit; pictures to ~/Desktop/Claude/vt3-view/.
- Owner asks whether replay cameras can be immersive in Immersive mode:
  read-only research worker writing `ai_docs/research/immersive-replay-cameras.md`
  (not committed by it; conductor commits).
- **Owner's decision (replays in Immersive): option 1/A - the viewer stays
  where they are and the point replays in the world.** Research worker told to
  design that in depth; implementation is the task after T9.
- Replay research DONE: `ai_docs/research/immersive-replay-cameras.md` (option A = one extra matrix in `eye_projection`, 7 steps behind `LINDBERGH_VT3_REPLAY_VIEW=flat|follow|world`). **T10 = implement it, after T9.**

## 2026-11-11 ~23:30 (T8b worker)
- **T8 COMMITTED** (local only): submodule `2c3f4f4`. Exactly the build the
  owner confirmed worn (APK sha256 0fa1b111..., copy
  `/tmp/vt3q/T8b/VirtuaTennis3VR_2c3f4f4.apk`). GPU unchanged (2.8-3.1 ms).
- T9 (step back 5/6/7/8 m, Camera height row) written, on the headset now;
  see HANDOFF 3.1.
- **Owner (23:10): also experiment with option 2/B** - viewer placed at the
  replay camera's spot, natural (1:1) field of view, a fade at each cut
  ("closer to the TV feel"). So T10 builds BOTH as real, selectable choices:
  `LINDBERGH_VT3_REPLAY_VIEW=world` (A, stay in place) and `follow` (B, at
  the replay camera; needs: fade out/in at every replay cut and at replay
  start/end, decide whether the view pans with the camera or snaps per shot
  with the head free - try both, owner judges worn). Panel row: Replays:
  Off / Flat screen / In the world / Camera view. Design:
  `ai_docs/research/immersive-replay-cameras.md` (B is its "follow" step -
  there only a comparison step; promote it to a full option).
- **Owner (23:15): the reaction camera is included too** - the winner's
  close-up after a point (win/lose loop, camera mode 7; "Point cutaways") gets
  the same treatment in T10: both views (in the world from your seat / at the
  camera with natural FOV + fade). The 1-in-10 split screen must be suppressed
  in these views (test: `splitreplay`). Serve close-up on big points: ask the
  owner only if cheap; research says it adds nothing from the seat.
  Panel row: Point cutaways: Off / Flat screen / In the world / Camera view.
- **Owner (23:20): wants a POV (player's eyes) camera to experiment with**,
  towards "a real VR game". Read-only research worker writing
  `ai_docs/research/pov-camera.md` (conductor commits). Implementation = T11,
  after T10 (in-world replays + reaction camera).
- POV research DONE: `ai_docs/research/pov-camera.md` (steps 0-11, `LINDBERGH_VT3_VIEW=seat|behind|eyes|snap`; note `vr.scale` must be 10 in the POV path; analog view-relative stick via `pad::exec` wrap is realistic). T11.

## 2026-11-12 ~00:30 (T8b worker, stopped)
- Owner input seen in runs (headset awake): stopped, committed T8 build
  `2c3f4f4` installed, env.txt 0, vr.cfg = owner's 22:51 file.
- T9 written + mostly verified, NOT committed: owed slate at +2 m and a
  short Immersive + Classic regression (HANDOFF 3.1 step 8).

## 2026-11-12 ~00:10 (T8b worker, done)
- **T9 COMMITTED** (local): submodule `688a9b9`; installed (sha256
  744291d9...), env.txt 0, vr.cfg = owner's 22:51 file, app stopped.
- Checks skipped at the owner's request: Classic regression for T9.
- Owner's rule added to README: minimal headset testing (one ~2 min smoke
  run per change; the owner judges worn).
- Owner to judge worn: Step back 5-8 m, Camera height steps.

## 2026-11-12 00:20 (conductor)
- T9 committed + installed (submodule 688a9b9, outer fd2d213), headset idle,
  owner to judge Step back 5-8 m and Camera height worn. Dark band at the
  bottom at 6-8 m = the near end's front wall (real geometry, pre-existing).
- T10 worker started (in-world replays A + B, reaction camera): macOS only
  until the conductor grants the headset; one short smoke run per change.
- Local, not pushed: 2c3f4f4 (T8), 688a9b9 (T9) and all outer commits after
  1f3ec0f. Push to `fork` on the owner's word.

## 2026-11-12 00:50 (owner's menu changes = T12, given to the T10 worker after its commit)
- T10 (replay / reaction views): macOS-verified by logs, owner granted two
  short headset smoke runs; then commit + install.
- **T12, owner's decisions:** no "camera closer" row (always default); no Step
  back row (always 5 m); Camera height = Low / Medium / High (standard, +1 m,
  +2 m); at the far ("back") side of the court height is High by default, the
  three choices apply on the near side; mode choice as two large buttons
  "Classic" / "VR" at the top of the panel (VR = Immersive; user-visible name
  only, keys unchanged).
- Then T11 (POV camera, `ai_docs/research/pov-camera.md`), card reader bar,
  T4 shadow mask.

## 2026-11-12 ~01:30 (T10/T12 worker)
- **T10 committed + installed** (submodule 2e61a2c, outer 77a006a): replays /
  point cutaways Off / Flat screen / In the world / Camera view; Quest S1+S2
  smoke runs, vr.cfg restored byte-identical; strips ~/Desktop/Claude/vt3-replay/.
  Known: the game's replay intro wipe shows as a plate in the world; near
  ground washed white in replay frames (glare).
- **T12** (owner's menu changes): Classic / VR buttons on top, VR label,
  Camera closer / Step back removed (fixed 20 m / 5 m), Camera height Low /
  Medium / High, High at the far end (the far end exists: after a change of
  ends 1P plays from the far side; latched in the StartLoop after it).
  Status: see HANDOFF 3.1 top entry.

## 2026-11-12 ~01:30 (owner judged the T12 build worn) -> T13 (same worker)
- Installed + committed locally: submodule 9dd8505 (T10 2e61a2c + T12), outer c04faed.
- Owner: VR view fine; **Camera height default = Medium**; **delete "In the
  world"** from Replays / Point cutaways (confusing when the angle does not
  change) -> Off / Flat screen / Camera view. Fault: on high angled cameras
  the players are missing in Camera view. Direction: camera angles close to
  the original, with close-ups of the players (aim like the game camera,
  viewpoint moved forward along its line of sight to make up for the lens).
- T13 = the above; Mac first, one headset smoke run when granted.
- POV camera (T11) waits for the owner's word.
- **Open bug T14 (owner, worn, build 9dd8505):** a brief glitch still shows
  at the start of every point in VR ("not sure if it's still a top-down shot,
  disappears too quickly"). Worker told to capture it every-frame in the T13
  smoke run (strip: ~/Desktop/Claude/vt3-bugs/point_start_glitch.png) and fix
  if small.

## 2026-11-12 ~10:00 (T13/T14 worker)
- T13 + T14 committed locally (submodule 66ce3ff): macOS-verified, **Quest
  smoke run OWED** (headset off; not installed; installed = T12 9dd8505).
  T14 cause: StartLoop snaps the court camera ~10 m nearer / 3 m lower then
  glides back (TV hides it with a cross-fade) - now eased. Next: T15 (card
  reader bar), macOS only.

## 2026-11-12 ~10:10 (headset switched off; Mac-only work)
- T13 (Camera view reframed, "In the world" removed, height default Medium)
  and T14 (point-start glitch = StartLoop camera snap, now eased) are
  macOS-verified; worker told to commit locally, **Quest smoke run OWED**.
- **T15, owner's decisions:** card reader notice OFF by default, a Classic
  row to turn it back on; language English by default (region 2 = export)
  with a Language row. Mac only; Quest smoke owed.
- When the headset is back: ONE combined smoke run (T13+T14+T15), install
  the committed build, tell the owner. His vr.cfg has `immersive.height 0`
  stored = Low; he picks Medium himself.
- Owner asked for macOS runs in the background (no window popping up):
  worker adding a headless switch for `mac` runs, default on.
- **Card save (T16, owner's decision):** emulate the IC card as a save game,
  high level - skip the card screens, load / save the card data directly,
  **no profile picker, always the same player**. Read-only research worker
  writing `ai_docs/research/ic-card-save-emulation.md` (conductor commits).
  Opposite of T15's "card R/W OFF": becomes a setting (Save progress On/Off).
- Future: versus with a second Quest - read-only research worker writing `ai_docs/research/versus-two-quests.md` (conductor commits). No build planned yet.

## 2026-11-12 ~11:00 (T15 worker)
- T15 committed locally, macOS-verified, Quest smoke OWED: card readers off
  (Classic row "Card reader notice"), Language row (English default, region
  2), overlays Hidden closes the bar live; macOS runs headless
  (LINDBERGH_HEADLESS=1 default in vt3-repro.sh mac). Match start on macOS
  unchanged (1952); round0 venue now Dusseldorf (King level from backup).

## 2026-11-12 midday (headset unavailable for some hours)
- Committed locally, macOS-verified, **Quest smoke run OWED**: T13/T14
  (submodule 66ce3ff), T15 (298f90a: card readers off, Language, headless
  macOS runs); outer 848b315. Headset still has the T12 build (9dd8505).
- T17 (owner): Anti-aliasing switch (Off / 2x / 4x) - same worker, Mac only,
  default unchanged; joins the one combined smoke run.
- Research running (read-only): card save emulation (T16, option C, single
  player), versus with two Quests (Mac standing in for the second headset).
