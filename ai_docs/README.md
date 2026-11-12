# AI working notes – Virtua Tennis 3 on Quest 3

Read this first. It records what is done, what is being worked on and how to
test, so nothing gets researched twice. The user-facing tracking list is
`docs/VT3_QUEST_BACKLOG.md`; how each fix works is in `docs/VT3_PORTING_GUIDE.md`
section 8. Add to this file whenever a session finds something.

**Next agent: `ai_docs/HANDOFF.md` has the 2026-11-11 session summary, the to-do
queue in order, and the designs for the live mode switch and the in-scene
scoreboards.**
The day's history (what was done, in order, with commit hashes):
`ai_docs/SESSION_LOG_2026-11-11.md`.

Research reports in `ai_docs/research/` (read the relevant one before
working on its area):
- `audio-music-skipping.md` - SEGAAPI / ADX / lbrna audio path, the
  loop-end position bug (music skipped every 341 ms lap; fixed),
  audio diagnostics and the headset procedure.
- `crowd-and-upper-stands.md` - upper bleachers exist but `field::draw`
  hides group `GAME_NO` on the court camera; crowd cards float; crowd
  texture LOD bias lost in gl4es.
- `shadow-resolution.md` - the low-res shadow is the screen-space ground
  mask (1360x768), not the 2048 map; self-shadow tiles use 1/16 of the map.
- `replay-paths.md` - the single replay gate (`replay::isReplay_point`),
  replay loop modes, match end with Replays off.
- `serve-meter-hud-anchors.md` - serve meter / 1P marker anchoring in
  Immersive.
- `two-mode-menu-design.md` - Classic / Immersive panel design and code map
  (HANDOFF section 4 supersedes its Phase B steps).

## Ground rules

- Push only to the `fork` remote (mrchrisster/...), branch `vt3-quest`:
  the `lindberghrecomp` submodule first, then this repo. **No PRs or pushes to
  lialan's upstream repos** (origin push URLs are disabled on purpose).
- Never commit `games/*/generated`, game data or the APK. No decryption, no
  dongle circumvention.
- Don't turn Guardian off from adb; ask the user to confirm prompts in the
  headset ("Finding position in room" means the room is too dark).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Owner's rule (2026-11-12): keep headset testing minimal — one short smoke
  run per change (boot to a match start, ~2 minutes), no multi-run
  regressions unless the owner asks; the owner judges worn.**

## How to test

- Quest build: `JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ANDROID_NDK=$HOME/Library/Android/sdk/ndk/28.2.13676358 sh quest/build.sh vt3 > /tmp/qb.log; grep error: /tmp/qb.log; adb install -r quest/VirtuaTennis3VR.apk`
  ("1 errors" in the log is the old target-SDK lint notice; the APK is built.)
- macOS build: `ninja -C build-mac`. Game data: `~/code/quest_games/vt3`.
  Immersive runs on macOS too (`LINDBERGH_VT3_IMMERSIVE=1`, a flat window; checked
  2026-11-11 through two `prize` matches). `LINDBERGH_GL_THREAD=1` puts the GL on its
  own thread as on the Quest. Sanitizer builds of the runtime only (the lifted code
  reused): see the 2026-11-11 match-start hang entry under Done.
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
  (on/off), `.dolly`, `.back` (game units, 0.1 m), `.sky stadium|painted|off`,
  `.shadow` (`immersive.stand_y` is gone, ignored when read). A run's env variable wins over each, and is
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

- 2026-11-12 **T9: Immersive Step back 5 / 6 / 7 / 8 m and a Camera height
  row** (submodule `688a9b9`; guide section 8 "Step back"). `immersive.back`
  50-80 (default 60; a stored value off the list = the nearest),
  `immersive.height` -20..20 (0 = the camera's own; `LINDBERGH_VT3_HEIGHT`),
  both live. Quest: each step shot (head held), serve meter at -2/0/+2 m,
  slate at -2/+2 m, panel row, Immersive prize FLOWLOG+BLACK_LOG (slates
  360 tapped / 600, round 3, black only the game's own, no FATAL). **Skipped
  at the owner's request:** Classic regression (Classic code unchanged).
  Pictures: `~/Desktop/Claude/vt3-view/`. The dark band at the bottom at
  6-8 m is the near end's front wall just in front of the viewpoint (seen
  pitched down; already there at 6 m before T9), not a rendering fault.
  Test helper: count real controller input as `[cab] frame N: buttons V`
  with V not 0 / 0x1 / 0x10 (the old `[cab] buttons` grep never matched).

- 2026-11-11 late **T8: court from above at a match's start, Classic's stray
  3D frames, Immersive's "image within an image" before each serve - fixed,
  owner confirmed worn** (submodule `2c3f4f4`; guide section 8 "The fade
  before every serve ..."). `host_xr.c` holds the frame after
  `usrAcEntranceLoop::init` (`LINDBERGH_VT3_HOLD=0` off; GL copies per layer
  with `glCopyTexSubImage3D` - a blit into layer 1 of an array writes nothing
  on the Quest), VT3 Classic always flat (`LINDBERGH_FLAT_ALL=0` old rule),
  the StartLoop cross-fade left out of world frames (`arb_fp_units`;
  `LINDBERGH_VT3_CAPTURE=1` keeps). Quest: prize Immersive / Classic / cuts
  on, match starts rounds 0-2, GPU 2.8-3.1 ms (unchanged). **Testing note:
  `LINDBERGH_BLACK_LOG` sees nothing in Classic now** (the eye array is not
  the flat picture) - judge Classic by game shots. Strips:
  `~/Desktop/Claude/vt3-bugs/`.

- 2026-11-11 night **Immersive sky: Sega's own dome all round** (`arbprog.c`
  `vt3_sky_fix`; submodule `9d68719`; guide section 8 "The sky in
  Immersive"). The sky is `GAME_NO_SKY_Polygon`, a full hemisphere (r ~4000)
  with the venue's 360-degree panorama, drawn at the game's far plane; the
  eyes kept only a front cone, so our painted sky showed round it in another
  colour. Its vertices now get their true depth back and are pinned to the
  eyes' far plane; Sky Painted / Off collapse them; Stadium draws no painted
  fill. fp 180 is the sun, not the sky. Round 0 is Ger3M, 1 Aus1F, 2 Fra1F.
  GPU: Stadium ~0.2 ms over Off, ~1 ms under the old fill. Regression
  passed; installed (HANDOFF 3.1). `LINDBERGH_XR_FIXED_HEAD` now works
  unattended.

- 2026-11-11 **Texture LOD bias on GLES (T5)** (`arbprog.c`, `quest/gl4es.patch`;
  submodule `8004564`): crowd and boards one mip sharper on the Quest, VT3 only,
  `LINDBERGH_LOD_BIAS=0` off. T4 (per-eye shadow mask) failed on the headset
  (shadows vanish) and T3's "dome" is not fp 180 - both uncommitted, see
  HANDOFF 3.1. Unattended Quest pictures differ per launch (head pose): use
  `LINDBERGH_XR_FIXED_HEAD=1` (in the WIP) for comparable shots / GPU ms.

- 2026-11-11 **Immersive hang / crash at match start - fixed** (`gl_thread.c`,
  `crash_report.c`; submodule `373c5ae`; HANDOFF 3.1). The game runs
  `camera::gameRoutine` on one of its worker threads, and world mode's camera
  feed (`h_vt3_game_routine`, `LINDBERGH_VT3_FEEDCAM`) called `glq_job` from
  there every frame from the match's start: a second writer on the
  single-writer ring, records overwritten, the worker replaying old ones
  (freed camera jobs -> SIGSEGV in calloc; or spinning -> the main thread
  forever in `glq_wait`). Jobs from other threads are now held and queued by
  the game thread at its next GL call (`[glq] job ... handed to the game
  thread's next call`, once per run); worker wakes the game when idle (lost
  wakeup with a full ring); `[glq] FATAL: bad record` instead of replaying;
  `[glq] WARNING` for GL calls from other threads; the watchdog prints the
  queue and the GL worker's stack. Quest: clean fade8ac 1 of 3 crashed (worker
  in `cls()` on a garbage record), `LINDBERGH_VT3_FEEDCAM=0` 3 of 3 clean; with
  the fix 5 of 5 match starts clean, full `prize` Immersive (4 matches, slates
  600) and Classic; stands cost +0.2 ms GPU (3.6 vs 3.3-3.7 ms, 60 fps).
  **Rule: anything queued for the GL thread must come from the game's main
  thread** - VT3 runs game code on worker threads too. macOS sanitizer builds:
  `build-mac-asan` / `-tsan` (runtime only instrumented, configured through a
  `CMAKE_PROJECT_INCLUDE` file setting `-fsanitize` on `src/runtime/*.c`; the
  lifted objects and `.ninja_log` / `.ninja_deps` copied from build-mac so
  they are not recompiled). TSan dies at load. Found, not fixed: gl4es
  `mv_copy` dangling texture pointer; GPU page faults in every Quest run
  (both modes) - backlog.

- 2026-11-11 **Whole stadium in Immersive; stand stretch and crowd cut
  removed** (`hle_sega.c` `h_vt3_field_draw`; submodule `fade8ac`;
  `ai_docs/research/crowd-and-upper-stands.md` Outcome; guide section 8).
  Checked first on the Quest (installed `77875a4`): `LINDBERGH_SKIP_FP=158`
  removes every spectator (158 = crowd cards), `=229,230` the stadium shell
  (light-mapped stadium meshes; the guide had them swapped), and the crowd
  cut (fp 230) cut stadium parts (far light masts) not cards. The ground
  shadow is the screen mask (game texture 45, the frame's first of three
  whole-screen copies; unchanged at `LINDBERGH_SHADOW_SCALE=1` vs 4).
  Fix: `field::draw` (0x080FFB86) gets its trees' type bytes zeroed for the
  call in Immersive (per call; `LINDBERGH_VT3_STANDS=0` off) - GAME_NO
  (upper tiers, roof, towers, town, upper boards, sky dome vp 129 / fp 180)
  and both ends drawn. Removed: `LINDBERGH_VT3_STAND_Y/_FROM/_FP`,
  `LINDBERGH_VT3_CROWD_CUT/_FP`, `lg_world`, `u_stand`, `immersive.stand_y`
  (ignored when read), the Stand height row. `immersive.sky` is
  `stadium|painted|off` (old `on` = stadium), `LINDBERGH_VT3_SKY=0|1|2`
  (`off|on|stadium|painted` also read). Test switch
  `LINDBERGH_VT3_VIEW_TURN=<yaw>[,<pitch>]` (eyes turned about the viewpoint,
  for game shots of what an unworn headset cannot look at). Quest round 0:
  no floating spectators, stand behind present, both eyes. **Owed: GPU cost,
  rounds 1-2, full `prize` regression** (HANDOFF 3.1).

- 2026-11-11 **Music skipping - fixed** (`hle_segaapi.c` `mix`,
  `h_get_pos`; submodule `fa83fd6`; `ai_docs/research/audio-music-skipping.md`).
  A looping voice that ended a 1024-frame mix block exactly on its loop end
  kept `pos == loop end` until its next read. VT3's music ring is 16384
  frames (65536 bytes, 341 ms) = 16 blocks, so every lap `lbrna` read the
  ring size, took the ring for empty (free = play - write = 65536) and
  overwrote the whole queued lap: decoder output written / played 2.38
  (macOS), 2.19 (Quest, `LINDBERGH_SEGA_POS_WRAP=0`). Now wrapped after the
  block and never reported: 1.01 / 1.02, "position read as ring size" 0.
  Also: linear interpolation for voices off 48 kHz (effects at 22/44 kHz;
  `LINDBERGH_AUDIO_INTERP=0` off). Diagnostics: `[sega-api] health:` line
  (starvation, stream lead, late device blocks, lock/mix time, limiter
  load; every 10 s if anything went wrong, 2 s with `LINDBERGH_SEGA_METER=1`),
  `LINDBERGH_AUDIO_DUMP=<wav>` (+ `_STREAMS=1`, `_WRITES=1`),
  `LINDBERGH_SEGA_LOG=1` ring `update` lines, `[io] slow read` (>50 ms,
  `LINDBERGH_IO_SLOW_MS`), `LINDBERGH_IO_DELAY` / `LINDBERGH_IO_LOG`,
  `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1` (needed unattended on the Quest: the
  paused Activity pauses SDL's audio ~2 s in), `scripts/wav_glitches.py`.
  Found nothing else: 0 starvation, 0 late blocks (Quest gap max 27 ms),
  lead min 320 ms of 341, no slow reads. Measured only unworn (60 fps by
  the clock, no 120 Hz). The effects drive the mix up to 4x full scale into
  the soft limiter (up to 11% of samples over 1.0 in a 10 s window): left
  for the owner's ears.

- 2026-11-11 **"Some replays still play with Replays off" - closed: not
  replays** (`hle_sega.c` `h_vt3_set_mode`, `h_vt3_skip_winner`, the
  `isReplay_point` / `setMode` install; guide section 8, "The only way into
  a replay"). Facts (static analysis, confirmed by runs): replay playback
  (`usrAcReplayLoop`, camera mode 6) is entered only from
  `usrAcPassLoop::exec`'s `mtrLoopManager::setMode` at return **0x08086B17**,
  gated solely by `replay::isReplay_point` (0x0810E18E). Replay mode per loop
  manager: arcade 7, attract 6, challenge 9 (unreachable). Other return
  addresses: pass loop mode 8 0x08086C6D, replay loop's exit 0x0808A6A7,
  replay loop's skip check 0x0808A850 (win/lose's 0x0808E6CB). Runs with
  Replays off: macOS `round0` + `WIN=1` 400 s - 0 ReplayLoop, two matches
  (game set and match 7642 / StatsLoop 7879 -> LoadLoop 8480); baseline
  Replays on - ReplayLoop only at match point (7495, 17614; WIN=1 points
  rarely earn one); Quest Immersive `round0` 330 s both off - 0 ReplayLoop,
  camera mode 1 from 1949 to game set and match 7856 (and the next match
  likewise); macOS attract 5 min - no ReplayLoop, the demo cycles (matches
  start ~6400, ~12100, ~16300). The reported replays were the point
  close-ups (Point cutaways). Changes: (a) a replay already playing when
  Replays goes off ends via the game's own skip (answer yes at 0x0808A850;
  card waits still hold) - Quest `prize` Immersive, scripted Replays click
  at 3030 in a replay started at 3015: ended 3032 -> Gamesetmatch ->
  Stats -> next round; (b) the `setMode` wrap is installed with
  `LINDBERGH_FORCE_REPLAY=1` too (`replay` scene + cutaways off: Replay ->
  Start directly); (c) log-only `[vt3] ... replay requested with Replays
  off` and WARNING lines if the overrides fail. Also: desktop Controls
  labels (button 2 slice, button 3 no shot) and the splash's Menu
  sub-label ("mode, replays, cutaways").
  **Testing note:** a scripted panel click needs the env pin empty
  (`LINDBERGH_REPLAYS=`); frames of a replay vary between runs (the first
  `prize` replay came at 3012, 3015 and 3540) - toggle in a window
  (`LINDBERGH_XR_MENU_CLICKS` up to 32 clicks). Back up vr.cfg first.

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

- 2026-11-12 **T10: replays and point cutaways in the world (Immersive)** -
  built and checked on macOS by logs (guide section 8 "Replays and point
  cutaways in the world"), **uncommitted, waiting for the headset** (HANDOFF
  3.1 top entry: plan, APK, safety diff `ai_docs/wip/t10-replay-views-lindberghrecomp.diff`).
  macOS desktop stereo gives no usable pictures of VT3 (right eye without
  world, baseline too): pictures come from the Quest's `LINDBERGH_GAME_SHOT`.

- (superseded 2026-11-11 night: sky committed `9d68719`, T4 only in
  `ai_docs/wip/t4-on-sky-lindberghrecomp.diff`) 2026-11-11 **Uncommitted, never run on the headset** (HANDOFF 3.1 lists
  the checks): Sky modes drawn (`stereo.c` `sky_on`, `dome_left_out`,
  `LINDBERGH_VT3_DOME_FP`), the per-eye ground shadow mask (`stereo.c`
  `mask_copy`, `stereo_mask_twin`; `arbprog.c` `vt3_mask_unit`, `lg_mask`;
  gl4es `gl4es_multiview_copy_layers`; `LINDBERGH_VT3_MASK=0` off) and the
  LOD bias on GLES (gl4es keeps `GL_TEXTURE_LOD_BIAS` per texture,
  `gl4es_texture_lod_bias`; `arbprog.c` `lod_bias_on`, `u_lodb[16]` as
  texture2D's bias; `LINDBERGH_LOD_BIAS=0` off). `quest/gl4es.patch`
  regenerated with both gl4es changes (uncommitted). LOD bias default on for
  VT3 only (`world_mode_capable()`; other games unchanged). Safety copy of
  both diffs: `ai_docs/wip/` (unverified).

- 2026-11-11 **Switch Classic / Immersive without a restart (Phase B):
  groundwork landed, nothing live yet** (`world_mode.c/.h`,
  `xr_world_panel.c/.h`, `host_sdl.c`, `host_xr.c`). No behaviour change in
  either mode (macOS Classic `prize` flow log identical to the run before).
  What is in: three latches - `g_target` (atomic; the panel via
  `world_mode_update`, or the test switch), the game thread's mode
  (`world_mode_immersive()`, latched by the new `world_mode_frame(g_frame)`,
  called in `host_swap` just before the frame's `glq_job(frame_gl)`), and the
  GL thread's (`world_mode_drawing_immersive()`, set by
  `world_mode_gl_latch()`; nothing calls it yet, so it stays the start mode).
  Also `world_mode_target()`, `world_mode_live()`, `world_mode_on_switch(fn)`
  (the game's part of a switch, a callback because `host_sdl.c` is also the
  Vulkan host's, which has no `stereo.c`). **Live = a switch callback is
  registered and `LINDBERGH_VT3_LIVE_SWITCH` is not 0; no callback is
  registered yet**, so `world_mode_update` keeps the started mode as before.
  Live, it takes the env pin, else vr.cfg `mode` (capable game only), else
  the start - only a *change* of that request moves the target, so other
  rows' clicks keep a test switch's mode; values are resolved for both modes
  and the latched mode's become current at the latch; the shadow size stays
  as started. At the latch: `[world] frame N: mode -> immersive (panel|test)`
  and the callback, once. Test switch `LINDBERGH_VT3_MODE_AT=<frame>:<0|1>,...`
  (a frame passed counts; over an env pin and the kill switch; never saved;
  honoured only while a callback is registered, i.e. inert today). Panel:
  `XwState.live` (host_xr.c sets 0): live, no Restart now row, Mode without
  "(on restart)", the Mode click adds `XW_LIVE_CHANGED`. Tests:
  `tests/test_world_mode.py` (latch, callback once, MODE_AT, kill switch /
  env pin / incapable game keep the start), `tests/test_xr_world_panel.py`
  (live block). **Remaining (need the headset):** world-mode hooks installed
  always and gated per frame in `hle_sega.c` (which registers the callback:
  `g_replays` / `g_cutaways` / overlays / camera hooks for the new mode),
  `stereo_frame_begin` calling `world_mode_gl_latch` with the mode **carried
  through the GL queue** (the game thread runs up to a frame ahead, so the GL
  side must not read the game's latch directly), the shader link key's world
  bit, `g_flat` forced in Classic, `host_xr.c` `wpanel.live = world_mode_live()`;
  then Quest runs with `MODE_AT` both ways.

## Other open items

From `docs/VT3_QUEST_BACKLOG.md`: switching Classic / Immersive live
(Phase B: hooks always installed, the shader link key's world bit,
`g_flat` forcing), blocky cloud patch near the top of the sky, one black frame
at a camera change, camera and stand-height defaults (now adjustable in the
panel), HUD scoreboards in the scene,
macOS start-up screen.

Seen 2026-11-11 (VT3 build worker), not looked into:
- ~~Crowd cards float above the side stands~~ - fixed by drawing the stadium (`fade8ac`).
- Ita3F (round 0), view turned 180 deg: the near end's lower seats have no
  crowd cards (data, or the audience manager skipping the camera's end?).
- With the dome (fp 180) skipped and the painted sky off, a blue band of sky
  remains at one side: a second sky piece, not identified.
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

Seen while testing the panel (2026-11-11), not looked into:
- The menu script's `z` taps (to frame 3600) also skip the game's own
  screens: a shot button skips the point close-up after 15 frames, and the
  game-set-and-match and result screens - measure screen lengths after 3600.
