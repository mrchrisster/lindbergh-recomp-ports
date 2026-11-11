# AI working notes – Virtua Tennis 3 on Quest 3

Read this first. It records what is done, what is being worked on and how to
test, so nothing gets researched twice. The user-facing tracking list is
`docs/VT3_QUEST_BACKLOG.md`; how each fix works is in `docs/VT3_PORTING_GUIDE.md`
section 8. Add to this file whenever a session finds something.

## Ground rules

- Push only to the `fork` remote (mrchrisster/...), branch `vt3-quest`:
  the `lindberghrecomp` submodule first, then this repo. **No PRs or pushes to
  lialan's upstream repos** (origin push URLs are disabled on purpose).
- Never commit `games/*/generated`, game data or the APK. No decryption, no
  dongle circumvention.
- Don't turn Guardian off from adb; ask the user to confirm prompts in the
  headset ("Finding position in room" means the room is too dark).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## How to test

- Quest build: `JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ANDROID_NDK=$HOME/Library/Android/sdk/ndk/28.2.13676358 sh quest/build.sh vt3 > /tmp/qb.log; grep error: /tmp/qb.log; adb install -r quest/VirtuaTennis3VR.apk`
  ("1 errors" in the log is the old target-SDK lint notice; the APK is built.)
- macOS build: `ninja -C build-mac`. Game data: `~/code/quest_games/vt3`.
  **Immersive mode does not run on macOS** (the window closes right after start).
- Unattended runs: `scripts/vt3-repro.sh <scene> quest <secs>` or
  `... <scene> mac ~/code/quest_games/vt3 <secs>`. Extra `LINDBERGH_*` variables
  in the environment are passed through. The script **empties the headset's
  env.txt** at exit; restore with
  `adb shell "echo LINDBERGH_VT3_IMMERSIVE=1 > /sdcard/VirtuaTennis3/env.txt"`.
- Scenes: `round0` (normal first match), `forty` (every game starts 40-0 –
  **unsuitable for match-length tests**: forcing 40-0 at each game start keeps
  resetting the score when the AI wins, so it is endless even with replays on),
  `prize` (1P wins every
  point from 40-0: the match is over in two points), `replay`, `splitreplay`.
- Useful switches: `LINDBERGH_VT3_WIN=1` (1P wins every point),
  `LINDBERGH_VT3_CUTAWAYS=0|1` (the close-up after each point skipped / shown),
  `LINDBERGH_REPLAYS=0|1` (now works on macOS too), `LINDBERGH_VT3_FLOWLOG=1`
  (each arcade screen loop the game starts: `[flow] frame N: GameLoop` ...),
  `LINDBERGH_GAME_SHOT=<first>,<every>` (game picture), `LINDBERGH_XR_SHOT=...`
  (eye image without the compositor's layers).
- `adb exec-out screencap -p` captures the **composited** headset view
  (quad layers, system dialogs), 4128x2208 both eyes.
- Headset logs: `adb logcat -v time -s 'vt3:*'`, or `vt3.log` in
  `/sdcard/VirtuaTennis3/vt3_Lindbergh/`. Start logcat right before launching,
  because the Quest's log buffer rolls over within minutes.
- **Scripting a serve:** 1P serves on its own when no button is pressed:
  the meter fills to full (state 2), falls back and the serve goes off. The
  menu script's `z` taps (to frame 3600) swing the first serves early, so the
  first untouched 1P serve in `round0` comes at ~frame 5150 and the next at
  ~6800 (game 2 at ~7300 is COM's serve, 1P then at the far end). Frames
  through a serve: `LINDBERGH_VT3_SERVESHOT=<n>[,<from frame>]` takes a
  full-size game shot as 1P's power passes 0.3/0.5/0.7/0.85/0.9/0.95 and
  every 3rd frame for 45 frames after, for n serves (`LINDBERGH_SHOT_BOTH=1`
  for the right eye; set `LINDBERGH_GAME_SHOT=99999,1` so the script's
  default shots stay out of the way). `LINDBERGH_VT3_SERVELOG=1` logs each
  frame's meter (player, state, power) and each screen position, game vs
  re-anchored. Extra taps: `VT3_EXTRA_KEYS="frame:z,..."` (repro script; a
  tap is a press and release in the same frame - press during the meter to
  hit at that power). E.g.
  `LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_VT3_SERVELOG=1 LINDBERGH_VT3_SERVESHOT=2,3700 LINDBERGH_SHOT_BOTH=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh round0 quest 165`.
- Callees/callers of a game function by name: a small script that scans
  `games/vt3/generated/recomp_funcs_*.c` for `call 0x...` and maps addresses
  with `recomp_symbols.h` (keep the longest body when a function appears in
  several files). Symbols are mangled, e.g. `_ZN3hud14drawServePowerEv`.

## Done (see the backlog's Done list for the full set)

- 2026-11-11 **Point cutaways switch** (`hle_sega.c` `h_vt3_skip_winner`,
  `g_cutaways`, `LINDBERGH_VT3_CUTAWAYS=0|1`; guide section 8). After each
  point `usrAcWinloseLoop::exec` (mode 8) counts `this+0x20` to 120; it ends
  early when `playerManager::check_skip_button_winner()` (a shot button) is
  true and the count is past `playerManager::getCnt_skip_max()` (`+0x78`, 15
  from the constructor), with the same exit as at 120. Off, the wrap answers
  yes for the call from the win/lose loop (return 0x0808E6CB) only - start,
  game-set-and-match and replay loops also ask it. Measured (flow log):
  WinloseLoop 121-122 frames -> 17; POINT plate shown ~0.3 s, the score box
  has the new score; ChangeendLoop, GamesetmatchLoop -> StatsLoop -> next
  round unchanged (macOS `round0` + `LINDBERGH_VT3_WIN=1`, `prize`; Quest
  `prize`). Card-writing waits and challenge mode (checkMode 4) still hold
  the loop as the game's own skip does.

- 2026-11-10 **Serve meter and 1P marker in immersive mode** (guide section 8,
  "HUD items at 3D points"). Two faults: (1) the gauge's fill is a sprite
  scaled along y; `arb_env_projection` took its matrix apart as a camera with
  a y lens times the scale, rejected below ~0.85 (last good lens: looked
  right) but **taken** from 0.85 to 1.0 - the bar drawn full height, shifted
  down out of its frame - and stored as the good lens, so the fall back
  after full was wrong too. Pixel-camera draws are now matched exactly
  (`arbprog.c`, `LINDBERGH_VT3_PIXCAM=0` off). (2) `hud::getScreenPosFrom3DPos`
  places the meter / marker by the game camera, but the eyes see the HUD
  plane from the dollied viewpoint: they sat below the feet (near end) or
  ~1.6x too far out (far end). A wrap re-solves the position per eye
  (`stereo_vt3_hud_anchor`, `LINDBERGH_VT3_HUD_ANCHOR=0` off). The meter is
  latched once per serve (`hud+0x60`); no drift seen, so it is not re-anchored
  each frame. Many other HUD sprites with uniform scale pops (x1.1, x0.5,
  x2) were also drawn unscaled before; now as the game scales them.
  Verified on the headset with `SERVESHOT` frames both eyes, near and far
  end, each switch alone, classic mode frame-compared with the previous
  build. **Not verified:** `LINDBERGH_XR_FAKE_YAW=25` - unattended, the XR
  session stops before the match (state 6/1), and the fake yaw only applies
  to located views; needs someone wearing the headset. Also fixed while there
  (log-only): `LINDBERGH_VT3_ATTACHLOG` and `LINDBERGH_VT3_CAMLOG` read their
  arguments one slot off (handlers get esp at argument 0, the return address
  at esp-4); `h_vt3_game_routine` read `this` at esp+4, which a log showed is
  the caller's saved ebx holding the same camera, now argument 0 (no change
  in behaviour).

- 2026-11-10 **Start-up screen** (`host_xr.c` splash section, art from
  `quest/tools/vt3_splash.py` -> `games/vt3/src/splash_art.c`). Verified in
  headset captures, both before the game's first frame (thread) and over the
  game's black boot. Startup timing: ~1.5 s to the XR session, ~8 s to the
  game's first frame, ~20 s of the board's own black boot, then the white logo.
  macOS still starts on black (not done).
- 2026-11-10 **Match ends with Replays off** (`hle_sega.c` `h_vt3_set_mode`,
  guide section 8). In arcade mode only `usrAcReplayLoop::exec` carries a
  finished match on (match event bit 0x1000 of `match+0x1c`, set with
  `match+0xd6` by `match::setEvent(12)`): mode 0xa Gamesetmatch / 0xb Stats.
  With replays off the pass loop sets mode 8 (Winlose) instead, so a wrap of
  `mtrLoopManager::setMode` turns that mode 8 (from 0x8086c6d, match bit up)
  into the replay loop's choice. The closing replay is skipped. Verified with
  `prize` + `LINDBERGH_REPLAYS=0` + `LINDBERGH_VT3_FLOWLOG=1` on macOS and the
  Quest: `match over with Replays off - closing replay skipped, game set and
  match (mode 0xa)` -> `GamesetmatchLoop` -> `StatsLoop` -> next round, no
  third game; ordinary points still Pass -> Winlose; Replays on unchanged
  (Pass -> ReplayLoop -> Gamesetmatch). `isReplay_point` is the only way
  into the replay loop. Also: the override table (64) was full with the
  diagnostic logs on (JVS entry points went missing and the run never reached a match), now 128.
  The loser path (0xb + `sound::stopSoundAll`) is untested (`prize` always wins).
- 2026-11-10 Start-of-match cameras, floating crowd, HUD on head movement, sky,
  shadow map, ad flicker, stands, blotches, shadows – all in the guide.

## In progress

(nothing)

## Other open items

From `docs/VT3_QUEST_BACKLOG.md`: two-mode headset menu (Classic / Immersive,
advanced settings each; Immersive defaults replays and arcade overlays off),
blocky cloud patch near the top of the sky, one black frame at a camera change,
camera and stand-height tuning, HUD scoreboards in the scene, culling widened to
the headset's view, macOS start-up screen.

Note for the menu redesign: defaulting Immersive to Replays off is safe now
(the match-end fix is done).
