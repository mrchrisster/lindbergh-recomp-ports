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
  rounds, black frames only the game's own). Still owed: Classic `prize`, the
  stands' GPU cost (R2 was confounded by BLACK_LOG's readback, ~33 fps on any
  build; needs a STANDS=1 run matched to R3's 3.4-3.7 ms / 60 fps), audio
  health with KEEP_ON_PAUSE, rounds 1 and 2, turned 180 / pitched 70.
  Ready-to-paste run list: HANDOFF 3.1.
- Written, uncommitted or WIP, never run on the headset: court sky backdrop +
  painted sky behind it (T3), per-eye eye-sized ground shadow mask
  (`LINDBERGH_VT3_MASK=0` old path) (T4), GLES texture LOD bias
  (`LINDBERGH_LOD_BIAS=0`, `quest/gl4es.patch` regenerated; now default on
  for VT3 only) (T5). Safety copy + README in `ai_docs/wip/`. Self-shadow
  tile zoom (T6) not started. Details: `ai_docs/research/crowd-and-upper-stands.md`,
  `shadow-resolution.md`.

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
