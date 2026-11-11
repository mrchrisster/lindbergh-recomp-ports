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
  in the environment are passed through. The headset's **env.txt is empty by
  default** now (Classic / Immersive is the panel's Mode, saved in vr.cfg);
  the script empties it again at exit. It **pins Classic, replays, point
  cutaways and arcade overlays on** (`LINDBERGH_VT3_IMMERSIVE=0`,
  `LINDBERGH_REPLAYS=1`, `LINDBERGH_VT3_CUTAWAYS=1`,
  `LINDBERGH_ARCADE_OVERLAYS=1`) unless the caller sets them, so the player's
  vr.cfg cannot change a test; set one to empty (`LINDBERGH_VT3_IMMERSIVE=`)
  to leave it to vr.cfg.
- Scenes: `round0` (normal first match), `forty` (every game starts 40-0 –
  **unsuitable for match-length tests**: forcing 40-0 at each game start keeps
  resetting the score when the AI wins, so it is endless even with replays on),
  `prize` (1P wins every
  point from 40-0: the match is over in two points), `replay`, `splitreplay`.
- Useful switches: `LINDBERGH_VT3_WIN=1` (1P wins every point),
  `LINDBERGH_VT3_CUTAWAYS=0|1` (the close-up after each point skipped / shown),
  `LINDBERGH_REPLAYS=0|1` (now works on macOS too), `LINDBERGH_VT3_FLOWLOG=1`
  (each arcade screen loop the game starts: `[flow] frame N: GameLoop` ...),
  `LINDBERGH_GAME_SHOT=<first>,<every>` (game picture), `LINDBERGH_GPU_TIME=1` (GPU ms per frame, unattended too), `LINDBERGH_XR_SHOT=...`
  (eye image without the compositor's layers).
- Headset panel tests (unattended; the unworn headset's session stops at
  state 6/1 or sits behind "Finding position in room", so the panel never
  shows in the eye or in `screencap`): `LINDBERGH_XR_FAKE_MENU=1` opens it,
  `LINDBERGH_XR_MENU_PAGE=0|1|2` (main / Classic advanced / Immersive
  advanced), `LINDBERGH_XR_MENU_HOVER=<row>` (a row highlighted),
  `LINDBERGH_XR_MENU_DUMP=1` (each painted panel as
  `vt3_Lindbergh/menu_p<page>_<frame>_<n>.ppm` - pull and look at them),
  `LINDBERGH_XR_MENU_CLICKS=<frame>:<row>,...` (rows chosen as a trigger pull
  would, panel open or not; logged `[xr] scripted panel click ... (label)`).
  A scripted restart writes `vt3_Lindbergh/xr_menu_clicks.done` so the next
  start does not click again - delete it to rerun. The restart itself
  (`restartGame`) is blocked by Android when the app is not in front
  (`BAL_BLOCK` in logcat: the process dies, nothing starts); worn, it works.
- Settings in `vt3_Lindbergh/vr.cfg` (written by the panel, fixed key list;
  unknown keys are dropped at the next save): `mode classic|immersive`;
  Classic: `replays`, `overlays`, `classic.cutaways`, `classic.shadow
  1024|2048|4096`; Immersive: `immersive.replays`, `.overlays`, `.cutaways`
  (on/off), `immersive.stand_y` (1 = off), `.dolly`, `.back` (game units,
  0.1 m), `.sky`, `.shadow`. A run's env variable wins over each, and is
  never written to vr.cfg (nor are `LINDBERGH_XR_SET` values). The run's
  values are logged at start: `[world] mode immersive (vr.cfg) dolly 200
  (default) ...`.
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

- 2026-11-11 **One steady camera between points; clean cuts** (`hle_sega.c`
  `h_vt3_set_mode`, `h_vt3_is_heatup`, `vt3_note_projection`; `stereo.c`
  `stereo_vt3_camera`, `screen_copy_stale`; guide section 8). With Point
  cutaways off (Immersive default) the win/lose loop is not entered at all
  (Pass -> Start / Changeend directly, the exit choice its `exec()` would
  make) and big points have no serve close-up (`match::isHeatup` answered no
  for the start loop) - camera mode stays 1 from serve to game set and match
  (`LINDBERGH_VT3_CAMMODE_LOG=1`, new; flow log `point cutaway left out`).
  The remaining cuts (cutaways/replays on, match end, slate): the world camera
  goes to the GL thread through the queue (it was read a frame early - a
  turned frame at each cut), flat/world follows the camera mode change and
  lens at once (was: lens > 8 held 6 frames), and the cut's captured picture
  is left out of world frames. `LINDBERGH_VT3_CUTLOG=1`, `_CUTFLAT=0`,
  `_CAM_QUEUE=0`, `_CAPTURE=1` to compare.
  Camera modes in Immersive (cutaways on): 1 court camera - world; 4 match
  intro (fly-by skipped) - world; 5 big-point serve close-up - world while
  its lens is short (~2.3-4), flat once it zooms past 8 (~20 frames in); 6
  replay - world; 7 point close-up - flat when its (random) camera's lens is
  past 8 (11.7-16.3 seen), world otherwise (one seen facing the crowd); 8
  change of ends (fly-by skipped) - stays on the court camera; 9 game set
  and match - flat once its lens passes 8 (11.2-35.6 seen), world before
  that (it starts at ~6.4; one cut short by the menu script's taps never
  zoomed and stayed world); 0xa result slate - flat (a menu state).
  Checked on the Quest (`prize`, Immersive, flow + camera-mode logs):
  cutaways and replays off - `point cutaway left out ... straight to change
  of ends (mode 9)` and `big-point serve close-up left out` at each point,
  no camera-mode change from the match's start (1949) to game set and match
  (3013), two matches and the next round's start in 270 s; cutaways and
  replays on - the original sequence (Winlose 7 flat at 2464, serve
  close-up 5 world then flat at 2568, Replay 6, Gamesetmatch 9, slate 600
  frames); Classic `prize` unchanged (Winlose, a 150-frame serve close-up,
  Replay, Gamesetmatch, StatsLoop 8563 -> 9163).

- 2026-11-11 **Quest shot buttons follow the cabinet** (`xr_controls.c`
  `lever_buttons`, `host_xr.c`, splash art; guide 3.4 and
  7.2). The cabinet has two shot buttons (left top spin, right slice, both
  a lob); "button 3" is no shot. Quest: trigger = top spin, A / X = slice,
  B / Y = lob (both bits), the same on both hands; on a lever cabinet a
  held Y no longer opens the panel (left Menu does). Splash art redrawn
  (`quest/tools/vt3_splash.py` regenerates `games/vt3/src/splash_art.c`
  byte for byte). `tests/test_xr_controls.py` covers it. Not tried worn.

- 2026-11-11 **Stale XR settings tests fixed** (`lindberghrecomp/tests`).
  `ec78b3b` (the eye's default = the headset panel, `LG_XR_NATIVE_*`; the
  panel's sizes 1216/1440/1680/1920/native, 5 not 6) was deliberate and
  documented; the tests still expected `0x2280` for invalid sizes and a
  6-step cycle. They now expect the build's native size (host: 2064x2280 on
  macOS, 2160x2160 on Linux) and the 5-step cycle, wrapping back to 1216.
  `python3 -m unittest tests.test_xr_settings tests.test_xr_panel` passes.

- 2026-11-11 **Blocky cloud patch in the sky** (`stereo.c` `sky_draw`).
  The cloud noise hashed each lattice corner with
  `fract(sin(dot(p, (127.1, 311.7))) * 43758.5)`; by the fifth octave p is
  in the hundreds and the sine's argument ~1e5, beyond the GPU's float
  (mediump by default in a GLES fragment shader): cells hashed alike in hard
  rectangles. Fixed by the frame-rate change (one fetch per octave from a
  256x256 random texture, lattice wrapped at 256, shader `highp`). Checked
  with the new `LINDBERGH_VT3_SKY_PITCH=<deg>` (test only: the sky turned
  down that far about the game camera's right, so a game shot shows the
  zenith): old shader at 60 deg - hard-edged rectangles and bands; new -
  smooth blue with soft clouds. Unpitched, the sky keeps its look (gradient,
  fair-weather clouds; the cloud pattern itself is a different random one).

- 2026-11-11 **Black frames at camera cuts in Immersive** (`stereo.c`, where
  `g_hud_fb_next` is set; guide section 8). `LINDBERGH_BLACK_LOG=1` (new: the
  left eye averaged each frame from the eye array, works unattended; logs a
  frame much darker than the last, and gives the next one the draw log and a
  game shot) found two fully black frames (HUD too) at every cut: 3 frames
  into the win/lose close-up, at the change of ends, at the serve camera,
  3 frames into game set and match, and at the match intro - Classic has none
  of these (only the game's own black at load -> match, frame ~1947, and at
  LoadLoop, which Immersive shares). Cause: at a cut the game blends the
  screen it captured (`fade::execCapture`, a whole-screen 2D draw of a
  screen copy into fb 0), which `stereo.c` took for the HUD, so fb 0 became
  "the HUD's target" for the next frame: none of that frame's world counted
  (`g_scene_draws` 0) - no sky, and the depth-of-field composite's colour
  clear was not dropped (that drop needs scene draws plus a screen copy) -
  so the eyes ended black, and the frame after likewise. Fix: in world mode
  fb 0 (the eyes) never becomes the HUD's target. Black log over a full
  `prize` match: 10 cut black frames before, 0 after; the game's own 3
  remain as in Classic. `LINDBERGH_GAME_SHOT` takes a 4th field, the last
  frame (`2455,1,0,2475`); `LINDBERGH_CLEAR_LOG=2` logs without the 60 cap.
  The menu-to-court tilted frame: likely the intro black pair (frames
  ~1951-52, now gone), not checked by eye.

- 2026-11-11 **Immersive frame rate: the sky, not the culling** (`stereo.c`
  `sky_draw`, `hle_sega.c` `h_vt3_is_visible`, `host_xr.c` `gpu_time`; guide
  section 8). Measured unattended (`prize`, Immersive, replays and cutaways
  off; the unworn headset's session stops at state 6 -> 1, so the game is
  paced at 60 by the clock, nothing is composited and `LINDBERGH_XR_PROF`
  says nothing - these are not 72/90 Hz numbers): new `LINDBERGH_GPU_TIME=1`
  (GPU time per frame by timer queries, works unpresented) and `[perf]`,
  match frames 2300-3150 / 4100-5300:
  before 53.7 fps, 44 frames over 25 ms per 5 s, GPU 4.6 ms (90% 6.8);
  `LINDBERGH_VT3_SKY=0` 59.6 fps / 2 / 2.8 ms; `LINDBERGH_SHADOW_SCALE=1`
  55.3 / 33; `LINDBERGH_SKIP_DRAWS=offscreen` 54.9 / 31; eyes at 1440
  (`LINDBERGH_XR_SET=resolution=1440`) 59.5 / 1; Classic 55.9 / 21.
  The sky's fragment shader (5 octaves x 4 sine hashes per pixel, full eye
  resolution) was the cost. Now value noise from a 256x256 random texture
  (one filtered fetch per octave, lattice wrapped) and no clouds below the
  horizon: 57.6 fps / 3 / GPU 3.2 ms, rally stretches at 60.0 fps with no
  late frame. The culling (`_sCamera::isVisible`) turned out not to matter:
  its only caller, `_sTree::addScene`, tests only trees with their culling
  flag, from `uva::SceneObject::addScene`; `LINDBERGH_VT3_CULLLOG=1` logged
  no call in whole runs (menus, match, slate), and `LINDBERGH_FRAMEMAP=2300`
  shows the same 283 draws with culling off, the game's or widened. The
  widened test is in anyway (default; eyes' frusta from `eye_projection`,
  sides pushed out `LINDBERGH_VT3_CULL_MARGIN` degrees, default 20; non-world
  cameras keep the game's test; `LINDBERGH_VT3_CULL=0` all visible as
  before, `=1` the game's). Not verified: 72/90 Hz worn, pop-in with
  `LINDBERGH_XR_FAKE_YAW` (needs a presenting session; moot while the test
  is never called).

- 2026-11-11 **Result slate in Immersive mode** (`hle_sega.c`
  `h_vt3_init_uva`; guide section 8, "Start-of-match cameras"). The slate
  (`usrAcStatsLoop`, mode 0xb) lasted ~4 frames in Immersive, 600 in
  Classic. Not this session's switches: `usrAcStatsLoop::init` sets camera
  mode 0xa and `camera::reset` starts a fly-by for it (`initUva(-1)`); the
  slate's `exec()` ends when `camera::isUvaFinished()` (no animation at
  `camera+0x224` counts as finished). World mode's intro skip
  (`LINDBERGH_VT3_SKIP_UVA`, on by default since 88e86e8) answered every
  `initUva`, so the slate ended at once. `camera::reset` starts fly-bys for
  modes 4 (entrance), 8 (change of ends), 0xa (StatsLoop, usrChResultLoop,
  usrChTotalResultLoop), 0xe (usrAcEndingLoop), 0x10 (usrPlayerintroLoop);
  only 4 and 8 are skipped now. Flow log (`prize`, Quest): Immersive
  StatsLoop 7367 -> LoadLoop 7371 before, 3262 -> 3863 and 7764 -> 8364
  after (= Classic 8577 -> 9176); GamesetmatchLoop 237 frames in both modes
  (unchanged; the first match's is shorter while the menu script's `z` taps
  run). A shot button still skips the slate as in the original.

- 2026-11-11 **Two-mode headset panel, Phase A** (guide 7.5 and 8). The
  mode is the panel's main-page **Mode** row (Classic / Immersive), saved as
  `mode` in vr.cfg and applied **on the next start** ("(on restart)" and a
  **Restart now** row while it differs from the running one); **Advanced
  settings** opens the saved mode's page. Classic: Replays, Point cutaways,
  Arcade overlays, Shadow quality, Frame rate counter, Restore Classic
  defaults. Immersive: Stand height, Camera closer, Step back, the same
  three, Sky, Shadow quality, Frame rate counter, Restore Immersive
  defaults. Replays / cutaways / overlays / stand / closer / step back / sky
  apply live (the running mode's page), shadow quality on restart; a row
  whose env variable is set shows "(env.txt)" and ignores clicks.
  Pieces: `world_mode.c` (resolves env > vr.cfg > the mode's default once,
  first thing in `vt3_jumps` - before any hook is chosen, before xr_init;
  replaces every `getenv("LINDBERGH_VT3_IMMERSIVE")`, and the dolly, back,
  stand, sky and shadow-scale reads, which are now live getters),
  `xr_world_panel.c` (pure: pages, items, clicks; the host shows its rows as
  `XP_COUNT + XW_x`, the shared `XP_` list and the Vulkan host unchanged),
  `xr_settings.c` (new keys appended; `LINDBERGH_XR_SET` keys saved as the
  file had them), `host_xr.c` (`cfg` = stored settings only - the old
  `cfg_load` wrote `LINDBERGH_REPLAYS` / `_ARCADE_OVERLAYS` into it, so the
  next click saved a test's choice: that is how the player's vr.cfg got
  `replays off`), `g_world_capable` (hle_sega.c, the camera symbols resolve).
  Verified on the Quest: env.txt `IMMERSIVE=1` and empty env.txt + vr.cfg
  `mode immersive` give the same `[sega]` lines and the same world in
  `prize` (only `(env)` / `(vr.cfg)` differs in `[world]`); `mode classic` the
  flat picture; panel images of all three pages (`LINDBERGH_XR_MENU_DUMP`);
  scripted clicks: Mode -> vr.cfg `mode` changed, Restart now shown, the
  next start in that mode; Immersive Replays / Point cutaways toggled at
  frame 2900 -> the match point replayed and the next point's close-up back
  to 122 frames, saved; `LINDBERGH_REPLAYS=1` -> "On (env.txt)", click
  ignored, two saves left `immersive.replays off` in vr.cfg; a full `prize`
  match ends in both modes. Unit tests: `tests/test_world_mode.py`,
  `tests/test_xr_world_panel.py`, `tests/test_xr_settings.py` (extended).
  Not done (Phase B): switching the mode live.

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

From `docs/VT3_QUEST_BACKLOG.md`: switching Classic / Immersive live
(Phase B: hooks always installed, the shader link key's world bit,
`g_flat` forcing), blocky cloud patch near the top of the sky, one black frame
at a camera change, camera and stand-height defaults (now adjustable in the
panel), HUD scoreboards in the scene,
macOS start-up screen.

Seen 2026-11-11 (VT3 build worker), not looked into:
- Crowd cards float in the sky above the side stands' top rows in
  Immersive (visible in any game shot; the crowd cut only covers the far end).
- `tests/test_xr_actions.py` does not compile on this Mac (its OpenXR header
  path under `deps/oxr/...`); not related to these changes.

Seen 2026-11-11 (verifying the steady camera), not looked into:
- A light-blue band along the bottom of some Immersive frames (sky showing
  where the near ground ends): game set and match's short-lens camera
  (`prize` frame ~3000) and the second round's court near a change of ends
  (~5200). Not checked whether older builds had it.
- In one point replay (camera mode 6, world) a large translucent rectangle
  hung in front of the net showing the live picture (`prize` frame 3200);
  another replay showed it as the stadium's video board at the far end. Most
  likely the board (fed by the per-frame screen copies 33/34, so
  `screen_copy_stale` does not apply) seen from a close replay camera - not
  confirmed.
- The desktop Controls menu (`host_settings.c`) still labels button 2
  "lob" and button 3 "slice"; the splash's "Menu SETTINGS" sub-label
  ("replays, overlays, screen size") predates the Mode row.

Seen while testing the panel (2026-11-11), not looked into:
- The menu script's `z` taps (to frame 3600) also skip the game's own
  screens: a shot button skips the point close-up after 15 frames, and the
  game-set-and-match and result screens - measure screen lengths after 3600.
