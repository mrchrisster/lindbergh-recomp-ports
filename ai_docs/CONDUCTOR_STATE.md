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
- Card save research DONE: `ai_docs/research/ic-card-save-emulation.md` - card = 612-byte per-player record at player+0x490; option C keeps the reader OFF and loads/saves that record (one record per character, `vt3_save.bin`); DES card encryption and the dongle calls are NOT touched. Build = T16, after T17; open: name entry, card-only pages with the reader off, King level.

## 2026-11-12 afternoon (T17/T16 build worker)
- Headset not on adb. Inherited T17 diff saved as
  `ai_docs/wip/t17-antialiasing-lindberghrecomp.diff` (setting + panel row done,
  gl4es side missing - Quest build would not link). Working on T17, then T16.
- T17 COMMITTED locally (submodule ca127f5), macOS-checked, Quest smoke run
  OWED (one ~2 min run with LINDBERGH_MSAA=4, HANDOFF 3.1 top). Default Off =
  unchanged path. MSAA smooths polygon edges only; net mesh / court lines
  need alpha-to-coverage / anisotropic filtering (backlog follow-up).
  Headset still not on adb. Next: T16 (save game), macOS only.
- T16 COMMITTED locally (submodule 891dd47), macOS-verified, default Off,
  Quest smoke run OWED (HANDOFF 3.1 top). Save carries over (3 sessions);
  Off = no file, flow unchanged; corrupt file handled. Open for the owner:
  default On?, a name for the save ("noname" now), lose path untested.
  Headset never appeared on adb this session: the combined T13-T17 smoke run
  is still owed; nothing installed (headset has T12 9dd8505).

## 2026-11-12 14:15 (conductor, after the usage-limit reset)
- Another client worked 10:46-11:21 and left UNCOMMITTED work (safety copies
  committed now): submodule +566 lines - anisotropic filtering row ("Sharp"),
  save name (`save_name`, LINDBERGH_VT3_SAVE_NAME), LINDBERGH_VT3_LOSE ->
  `ai_docs/wip/uncommitted-2026-11-12-aniso-savename-lindberghrecomp.diff`;
  `lose` scene in vt3-repro.sh -> `...-lose-scene-script.diff`; launcher icon
  candidates (`quest/tools/vt3_icon.py`, 5 PNGs replaced with the "headset"
  candidate, `ai_docs/wip/vt3-icon-notes.md`, ~/Desktop/Claude/vt3-icon/).
- **Owner's decisions:**
  - **Keep the app free of game data so it stays releasable: YES.** Ship only
    recompiled code + original art; anything of Sega's is read at run time
    from the player's own game files.
  - **Launcher icon:** simply "VT3" with a tennis ball behind it, shaded in a
    similar way to the game (original drawing; replaces the headset candidate).
  - **Loading screen:** the game's own Virtua Tennis 3 logo from the start
    screen, read at start-up from the player's data, with "VR" added; a simple
    small controller layout underneath; minimal fonts and style, on brand.
- Quest smoke runs owed (headset away): T13-T17 combined, then T16 save run.

## 2026-11-12 ~14:50 (build worker: inherited work, icon, splash, release audit)
- COMMITTED locally (never pushed), macOS-verified / Quest-built, **Quest smoke
  run OWED** (HANDOFF 3.1 top, folded into the combined run): submodule
  992a066 (Texture filtering, save name PLAYER, Reset save, card result
  windows shut, LOSE) and 4929c07 (splash logo read at start-up); outer
  4c1969d (lose scene, docs, release rule in README), 9fcb08f (icon "VT3
  chrome"), plus the splash art / docs commit after it.
- Owner's picks applied: splash layout A, DIN labels; icon candidate 5.
- Release-rule VIOLATIONS found (not fixed, owner to decide): libCg.so
  embedded in the APK (recomp_solib_img.c); upstream game screenshots in
  docs/*/mac-*.jpg and lindberghrecomp/docs/attract.png. Apple system fonts
  in the rendered splash / icon: swap for OFL before a public release.
- ~14:40: owner's fixes committed - icon candidate 7 "VT3 orange" without the
  ball's specular spot (installed); splash logo group and fallback title
  centred by measured drawn pixels. APK rebuilt (/tmp/vt3q/T18/). Smoke run owed.

## 2026-11-12 ~15:20 (T19 build worker: libCg.so out of the app)
- COMMITTED locally (never pushed), **macOS-verified, Quest smoke run OWED**
  (HANDOFF 3.1 top, folded into the combined run): submodule 1addfc1, outer
  commit after it. The embedded image was libCg's whole relocated load image
  (data/rodata/GOT/tables the lifted code reads; its code was already lifted
  to C). Now read from the player's `lib/libCg.so` at start-up, size +
  SHA-256 checked, relocated from a generated table (no file bytes), result
  checked against the lift-time image hash (identical). libmain.so 74.05 ->
  71.93 MB, libCg byte runs 323/328 -> 0/328 (mac binary the same).
  No fallback switch. Missing/wrong file: clear error naming the path (log,
  exit 1; Quest: Toast + HOW-TO file before start).
- Same violation, NOT fixed (owner to decide): Ghost Squad Evolution's
  released APK embeds CRI `snd_util.so` + `librnalindbergh_jr.so` (146/274 and
  232/265 sampled runs found); HOTD EX lifts the same two. Fix = re-lift with
  the new solib.py + copy the Java check; hotd4, hotd4sp, lgj load none.

## 2026-11-12 (owner: publish)
- **Published PUBLIC: github.com/mrchrisster/virtuatennis3-vr** (VT3-only, fresh history, MIT, no game files; README states the port is built against `vt3_Lindbergh_HD` and does not emulate/answer the dongle). Owner decided public ("up to the user to supply the game file").
- Pushed lindberghrecomp fork `vt3-quest` 9d68719..1addfc1 (T8-T19 runtime) - needed by the new repo submodule.
- From now on VT3 work lands in virtuatennis3-vr; this repo stays for the other games.

## 2026-11-12 evening (owner's worn test of the T19 build)
- Installed T19 (submodule 1addfc1) for the owner, no smoke run. Camera-view
  "out of view" log was a macOS-only log fault (fixed 43b712d, not installed).
- **T21 (owner):** (1) Save progress ON by default; (2) player models sometimes
  vanish during a replay; (3) a one-frame camera glitch at the end of a
  replay; (4) start-up loading bar missing on the first launch. Same worker.
- **Owner confirmed worn (T21 build bc8f1c3): "All good"** - replays keep the players, no replay-end flash, loading bar shows, save on by default. Not yet pushed: lindberghrecomp 43b712d, bc8f1c3 (fork vt3-quest at 1addfc1); virtuatennis3-vr 631ecce, 561aa44.
- Correction: owner says item 4 (loading bar missing on first launch) is NOT solved on bc8f1c3; worker diagnosing from his log + up to 3 cold starts. Push waits until this is fixed.

## 2026-11-12 ~23:35 (T23 H1 build/headset worker)
- Unattended launch: works when the headset is on vrshell HomeActivity (Asleep is fine) - vt3-repro.sh unchanged sequence started the game on launch 1. The 23:25 failures: launch held by HorizonOS while tracking was lost (window placement timeout + Guardian interstitial for our package; START itself accepted, no BAL block). Prompt cleared by itself with the headset asleep within ~3 min. Recipe in README "Guardian ... and unattended runs"; vt3-repro.sh now detects it and sleeps the headset 60 s between tries.
- H1: B (T4 per-eye ground shadow mask) PASS in both eyes (crops ~/Desktop/Claude/vt3-shadows/). C: robust context REFUSED by EGL (EGL_BAD_ATTRIBUTE) - no result on the fault type; faults still present (rate-limited 10 lines/5 s). Details: lindbergh-recomp-ports HANDOFF 3.1 top.
- Next (this worker): mask default ON in Immersive (LINDBERGH_VT3_MASK=0 = old path), commit, build, install, launch check.

## 2026-11-12 ~23:45 (T23 worker done)
- Per-eye ground shadow mask ON by default in Immersive: lindberghrecomp 02c86c8 (both trees pin it); build installed (launch-checked only). env.txt empty, vr.cfg the owner's, app stopped. Nothing pushed.
- Open from T23: GL_ROBUST test needs an EGL_EXT_create_context_robustness path (SDL's request refused on the Quest) before C can be answered.

## 2026-11-13 (build/headset worker: owner's six items + item 7)
- Item 6 done (submodule 13f9291): defaults msaa 2, aniso 4, immersive.shadow
  4096; Restore defaults resets Texture filtering too. Unit tests green.
  GPU evidence: owner's worn judgement only so far; the combined headset run
  logs `[gputime]`.
- Item 6 widened: VT3-only defaults = the owner's headset settings (VR first;
  other games unchanged), one row "Replays and reaction cams", 3D choice labelled
  "VR". Committed; unit tests green; Quest run owed.
- Items 1-3 committed (submodule 024359e): end/attract screens flat, flat by
  camera mode (0 stray world frames in macOS replay runs, was ~2500), continue
  coin with Coins Automatic (stick click continues). Quest run owed.
- Item 5 committed: start-up screen in Inter (OFL, bundled), small solid VR tag,
  shared LOB/SLICE legend, no note; renders in ~/Desktop/Claude/vt3-splash/.
- Item 4 committed (92b6f7b): far-end height decided per point. macOS ok.
- Quest R1/R2 done, build 92b6f7b installed, env.txt 0, vr.cfg identical, app
  stopped. Item 7 diagnosed (MSAA-only ghost), not fixed. GPU 4.0-4.3 ms avg
  with msaa 2/aniso 4/4096 (unworn).
