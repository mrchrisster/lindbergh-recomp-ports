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
- Installed: `0dbcb6e` build (fix + T5 LOD bias + FIXED_HEAD test switch),
  regression PASSED (prize Immersive + Classic, 5 match starts). APK copy
  `/private/tmp/claude-501/-Users-chrishelms-Desktop-Claude/786966e7-92df-442c-b205-476a682b88a2/scratchpad/w2/VirtuaTennis3VR_0dbcb6e.apk`.
  App stopped, env.txt 0 bytes, vr.cfg = owner's (byte-identical).
- Committed, not yet regression-run: submodule `9d68719` - Sega's sky dome
  all round in Immersive (the seam the owner reported). APK
  `.../w2/VirtuaTennis3VR_skyonly.apk`. Pictures `~/Desktop/Claude/vt3-sky/`.
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
