# Handoff – Virtua Tennis 3 on Quest 3 (written 2026-11-11)

For the next agent. Read `ai_docs/README.md` first (ground rules, build, unattended
testing), then this. This file holds what the README does not: the session's
summary, the owner's decisions, the to-do queue in order, and two designs that
exist nowhere else (live mode switch, in-scene scoreboards).

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

## 1. State of the tree

Branch `vt3-quest` in both repos, clean, **nothing pushed**.

| Work | Submodule `lindberghrecomp` | Outer repo | Verified |
|---|---|---|---|
| Steady camera between points, clean cuts; Quest shot buttons; splash map | `1b1988b` | `c82ec03` | macOS + Quest unattended |
| Replays-off bug closed; live Replays-off skip; setMode wrap independent of FORCE_REPLAY; labels | `dca91c9` | `bfc19cd` | macOS + Quest unattended (final regression owed, see 3.1) |
| Live mode switch groundwork (off, no behaviour change) | `3a713ff` | `2525e67` | macOS Classic + unit tests; installed with the audio fix below |
| Music skipping fixed (loop-end position), audio diagnostics, keep-on-pause test switch | `fa83fd6`, `77875a4` | see `git log` | macOS + Quest unattended; Classic and Immersive `prize` regression on the Quest; **installed** |
| Crowd / shadow leads checked (docs only) | - | `38b92e1` | Quest unattended |
| Whole stadium in Immersive (GAME_NO + both ends + dome), stand stretch and crowd cut removed, Sky stadium/painted/off setting, `LINDBERGH_VT3_VIEW_TURN` | `fade8ac` | see `git log` | Quest shots round 0; Quest Immersive `prize` regression passed (flow, slates 600, no black frames at cuts; R2 2026-11-11); **owed: Classic `prize`, stands GPU cost (matched pair), audio health, rounds 1-2, turned 180 / pitched 70** (3.1 run list A) |
| **Uncommitted** in the submodule / outer tree: Sky modes drawn (painted fill behind the dome, dome left out for Painted/Off), per-eye ground shadow mask, LOD bias on GLES (`quest/gl4es.patch` regenerated) | working tree | working tree | **never run on the headset**; reviewed, LOD bias limited to VT3; macOS build, unit tests, macOS Classic `prize`, Quest APK build (not installed); safety copy `ai_docs/wip/` (3.1 run list B-F) |

Push rule (owner): push to `fork` only after the owner has confirmed progress
worn. Never push to or PR against lialan's upstream. Workers never push.

Nothing in this session was checked by a person wearing the headset.

## 2. What changed this session

### 2.1 Steady camera between points, clean cuts (Immersive)
- With Point cutaways off, the win/lose loop is not entered (Pass -> Start or
  Changeend) and big points have no serve close-up (`match::isHeatup` answered
  no for the start loop). Camera mode stays 1 from first serve to game set and
  match. Measured on Quest `prize` and `round0`.
- Remaining cuts (cutaways/replays on, match end, slate): world camera goes
  through the GL queue; flat/world follows the camera-mode change at once; the
  cut's captured picture is left out of world frames.
- Review fixes: the skip now also leaves a requested versus game
  (`vs::isReq_vs_game`, `mgr+0x94`) to the game; dead `g_vt3_cut_skip_frame`
  removed.
- Doc correction: game set and match is flat only once its lens passes 8
  (starts ~6.4; one short one stayed in 3D).

### 2.2 Controls
- The cabinet has two shot buttons. Quest: trigger = top spin, A/X = slice,
  B/Y = lob (buttons 1+2), both hands; left Menu opens the panel.
- Desktop Controls labels: "Button 2 (slice)", "Button 3 (no shot)" (bindings
  unchanged). Splash controller map and its settings hint redrawn
  (`quest/tools/vt3_splash.py` -> `games/vt3/src/splash_art.c`).

### 2.3 "Some replays still play with Replays off" – closed
- Static analysis + runs: replay playback has **one gate**,
  `replay::isReplay_point` (0x0810E18E), read by `usrAcPassLoop::exec`
  (call 0x08086EE7). The replay `setMode` is at return 0x08086B17 (arcade mode
  7, attract manager mode 6, challenge 9 unreachable). The existing wrap covers
  it. What was reported were the point close-ups (Point cutaways row).
- Runs with Replays off: 0 `ReplayLoop` in ~2.5 macOS arcade matches, two Quest
  Immersive matches, 5 min of attract.
- New: a replay already playing when Replays goes off ends through the game's
  own skip (`h_vt3_skip_winner` answers yes for return 0x0808A850; ended 2
  frames after the click on Quest). `h_vt3_set_mode` is installed even with
  `LINDBERGH_FORCE_REPLAY=1`. Log-only line
  `[vt3] ... replay requested with Replays off` (never fired). WARNING lines if
  the wraps fail to install.
- Testing note: replay frames vary between runs (3012 / 3015 / 3540 seen), so
  a single timed panel click misses; toggle over a window of frames.

### 2.4 Live Classic / Immersive switch – groundwork only (nothing live)
- `world_mode.c/.h`: target (atomic) / game-thread / GL-thread latches;
  `world_mode_target()`, `world_mode_live()`, `world_mode_on_switch(fn)`,
  `world_mode_frame(frame)` (called in `host_swap` before `frame_gl`),
  `world_mode_drawing_immersive()`, `world_mode_gl_latch()` (no caller yet).
- "Live" = a switch callback is registered and `LINDBERGH_VT3_LIVE_SWITCH` is
  not 0. No callback is registered yet, so behaviour is as before.
- Test switch `LINDBERGH_VT3_MODE_AT=<frame>:<0|1>,...` (inert without a
  callback; overrides env pin and kill switch; never saved).
- `xr_world_panel`: `XwState.live`; when live, no Restart row, Mode without
  "(on restart)", click returns `XW_LIVE_CHANGED`. `host_xr.c` sets `live = 0`.
- Notes from the implementer: pass the mode to the GL side **through the GL
  queue** (e.g. as `frame_gl`'s argument from `world_mode_frame`'s return) and
  call `world_mode_gl_latch(arg)` – do not read the game latch from the GL
  thread. `g_frame` is counted on the GL thread, so `[world] frame N` and
  MODE_AT frames are approximate.

## 3. To do, in order

The headset dropped off adb mid-session (`adb devices` empty). Everything
below except where noted needs it; ask the owner to reconnect, do not work
around it.

### 3.1 Headset state and the owed checks

**Run list for whoever has the headset next (ready to paste, in order).**
Each run: check the battery first (stop at 3%: kill the repro by PID,
`adb shell am force-stop org.lindbergh.vt3.vr`, empty env.txt), then
checkpoint below. `vt3-repro.sh` empties env.txt at exit; the `[ ... ]` line
after each run checks it. Results land in `$R/<name>` (vt3.log, game_*.ppm).
```
cd ~/code/quest_games/lindbergh-recomp-ports
R=/tmp/vt3q; mkdir -p $R
adb devices
adb shell dumpsys battery | grep -E 'level|status'
adb shell wc -c /sdcard/VirtuaTennis3/env.txt
adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.before
# --- A. the installed fade8ac build: what is still owed ---
OUT=$R/A1_classic LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_BLACK_LOG=1 LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 330
OUT=$R/A2_stands1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GPU_TIME=1 LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 170
OUT=$R/A3_stands0 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GPU_TIME=1 LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_GAME_SHOT=99999,1 LINDBERGH_VT3_STANDS=0 scripts/vt3-repro.sh prize quest 170
OUT=$R/A4_r1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh round1 quest 160
OUT=$R/A5_r1_turn180 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_VIEW_TURN=180 scripts/vt3-repro.sh round1 quest 160
OUT=$R/A6_r1_pitch70 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round1 quest 160
OUT=$R/A7_r2 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh round2 quest 160
OUT=$R/A8_r2_turn180 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_VIEW_TURN=180 scripts/vt3-repro.sh round2 quest 160
OUT=$R/A9_r2_pitch70 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round2 quest 160
# pass for A: A1 Classic flow Winlose/Replay/Gamesetmatch, StatsLoop -> LoadLoop 600 frames, next round, [black] only boot/load (0, ~1100, 1947, LoadLoop);
#   A2 vs A3 [gputime] frames 2100-3000 within +1.5 ms, A2 [perf] ~60 fps; no '[sega-api] health' line with 'starved' > 0; A4-A9 shots: no floating cards, stand behind, no doubles / z-fighting
# --- B. install the working-tree build (T3-T5, uncommitted; ai_docs/wip/) ---
JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ANDROID_NDK=$HOME/Library/Android/sdk/ndk/28.2.13676358 sh quest/build.sh vt3 > $R/qb.log 2>&1; grep error: $R/qb.log
adb install -r quest/VirtuaTennis3VR.apk
# --- T3 sky (Stadium on three venues, Painted / Off on round 0) ---
OUT=$R/T3_s1_r0_up LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=1 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round0 quest 160
OUT=$R/T3_s1_r0_180 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=1 LINDBERGH_VT3_VIEW_TURN=180 scripts/vt3-repro.sh round0 quest 160
OUT=$R/T3_s1_r1_up LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=1 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round1 quest 160
OUT=$R/T3_s1_r2_up LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=1 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round2 quest 160
OUT=$R/T3_s2_r0_up LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=2 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round0 quest 160
OUT=$R/T3_s2_r0_180 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=2 LINDBERGH_VT3_VIEW_TURN=180 scripts/vt3-repro.sh round0 quest 160
OUT=$R/T3_s0_r0_up LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=0 LINDBERGH_VT3_VIEW_TURN=0,70 scripts/vt3-repro.sh round0 quest 160
OUT=$R/T3_s0_r0_180 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_SKY=0 LINDBERGH_VT3_VIEW_TURN=180 scripts/vt3-repro.sh round0 quest 160
# pass: Stadium = dome + painted fill above/behind it (judge the seam); Painted = no dome; Off = neither ('[sky]' line says which)
# --- T4 ground shadow mask (shots, then GPU without shots, then cuts on) ---
OUT=$R/T4_mask1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,1,1,2305 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh prize quest 160
OUT=$R/T4_mask0 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,1,1,2305 LINDBERGH_SHOT_BOTH=1 LINDBERGH_VT3_MASK=0 scripts/vt3-repro.sh prize quest 160
OUT=$R/T4_gpu1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GPU_TIME=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 170
OUT=$R/T4_gpu0 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GPU_TIME=1 LINDBERGH_GAME_SHOT=99999,1 LINDBERGH_VT3_MASK=0 scripts/vt3-repro.sh prize quest 170
OUT=$R/T4_cuts LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=1 LINDBERGH_VT3_CUTAWAYS=1 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_BLACK_LOG=1 LINDBERGH_GAME_SHOT=2455,1,0,2475 scripts/vt3-repro.sh prize quest 200
# pass: '[stereo] ... ground shadow mask per eye' and '[arbprog] ground shadow mask read per eye on unit N' in T4_mask1 only; near player's shadow smoother both eyes; GPU within ~+0.5 ms; cut cross-fade / depth of field as before, no new [black]
# --- T5 LOD bias (consecutive frames: far crowd, ad boards, no shimmer) ---
OUT=$R/T5_lod1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2400,1,1,2405 scripts/vt3-repro.sh prize quest 160
OUT=$R/T5_lod0 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2400,1,1,2405 LINDBERGH_LOD_BIAS=0 scripts/vt3-repro.sh prize quest 160
OUT=$R/T5_classic LINDBERGH_GAME_SHOT=2400,1,1,2405 scripts/vt3-repro.sh prize quest 160
# --- final regression on the working-tree build ---
OUT=$R/F1_classic LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_BLACK_LOG=1 LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 330
OUT=$R/F2_imm LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_BLACK_LOG=1 LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 330
OUT=$R/F3_imm_gpu LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GPU_TIME=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 170
adb shell wc -c /sdcard/VirtuaTennis3/env.txt
adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.after
cmp $R/vr.cfg.before $R/vr.cfg.after
```
Look at results with `grep -E '^\[(world|sega|black|flow|gputime|perf|sky|stereo|arbprog)\]|health' $R/<name>/vt3.log`.
Never compare frame rates of a BLACK_LOG run with one without (the readback
halves the rate). If any T-run fails, `adb install -r` a build of the
committed submodule (or keep the `fade8ac` APK) before handing back.

**Checkpoint log (build worker, newest first):**
- **2026-11-13 item 6 (defaults) COMMITTED, macOS unit tests green.** Submodule
  13f9291: `LG_XR_SETTINGS_DEFAULT` msaa 2, aniso 4, imm_shadow 4096
  (`xr_settings.h`); `xw_restore_defaults` also resets aniso (row on both
  Advanced pages); msaa (main page) untouched by Restore. Desktop: msaa
  env-only as before, aniso 4 / Immersive shadow 4096 by default. Tests
  test_world_mode / test_xr_settings / test_xr_world_panel / test_xr_panel:
  34 OK. GPU headroom: no earlier headset `[gputime]` with msaa 2 + aniso 4 +
  4096 exists (T17's aa4 run was never made) - owner's worn judgement only
  until the combined run of this session measures it. Quest run owed
  (combined with items 1-5/7).
- **2026-11-12 ~23:45 T23 mask default ON, installed.** Submodule 02c86c8
  (on b8ddc4c): `LINDBERGH_VT3_MASK` unset = per-eye ground shadow mask in
  Immersive (arbprog.c `vt3_mask_unit`, stereo.c `mask_on`), `=0` the old
  1360x768 path. macOS build + rt selftest OK, Quest build OK; APK
  `/tmp/vt3q/T23/D/VirtuaTennis3VR_02c86c8.apk` installed (md5 checked).
  Launch check only (no run, env.txt empty, owner's vr.cfg = Immersive):
  vt3.log within 4 s, process up, force-stopped. env.txt 0 B, vr.cfg
  byte-identical. Both trees pin 02c86c8. Owner to judge the ground shadows
  worn. NOT pushed.
- **2026-11-12 ~23:35 T23 H1 DONE (unattended, Guardian not up).** Headset
  Asleep on vrshell HomeActivity, no Guardian dialog: the unchanged
  `vt3-repro.sh` sequence (prox_close + KEYCODE_WAKEUP until Awake, am start)
  started the game on launch 1. Why the 23:25 launches failed (logcat
  `/tmp/vt3q/T23/H1/logcat.txt`): START was accepted (`BAL_ALLOW_PERMISSION
  result code=0`, so not a background-start block), but HorizonOS holds the
  launch in `VolumetricWindowManagerServiceImpl: Timeout while requesting
  window placement` while Guardian's ClientMgr sends
  `sendExtendedInterstitialBroadcast ... packageName=org.lindbergh.vt3.vr,
  secondsSinceDetection=2515..` every 5 s (tracking lost = "Finding position
  in room"); `AppHealthMonitor: appLaunchFailureBroadcastReceived` follows.
  The process is never forked until tracking comes back.
  **B (T4 per-eye mask) PASS:** `[arbprog] ground shadow mask read per eye on
  unit 15` and `[stereo] frame 1949: ground shadow mask per eye, 2064x2208 x2`
  present; frame 2300 both eyes: near player's shadow full and smooth, far
  player's and line judges' shadows present, both eyes
  (`~/Desktop/Claude/vt3-shadows/near_both.png`, `far_both.png`,
  `full_f2300_left|right.png`; shots `/tmp/vt3q/T23_mask/png/`). No old shot at
  the same frame/resolution exists to compare.
  **C:** `[window] robust context refused (Could not create EGL context ...
  EGL_BAD_ATTRIBUTE) - made without` - the Quest's EGL refuses SDL's robust
  request, so H1 ran WITHOUT robust access and says nothing about the fault
  type. Faults: 231 lines in 130 s = the kernel's 10 lines / 5 s rate limit
  (same as T22's 1471), first at app start - still present; logcat line
  counts cannot measure the rate. (SDL asks EGL_CONTEXT_FLAGS_KHR robust bit,
  which KHR_create_context allows for desktop GL only; GLES needs
  EGL_EXT_create_context_robustness `EGL_CONTEXT_OPENGL_ROBUST_ACCESS_EXT` -
  more than a one-liner, not attempted.) After: env.txt 0 B, vr.cfg
  byte-identical (`/tmp/vt3q/T23/H1b/vr.cfg.before|after`), app stopped.
  Logs `/tmp/vt3q/T23/H1b/` (full logcat stream). Next: mask made default.
- **2026-11-12 ~23:25 T23 H1 retried under the Guardian prompt (owner: the
  prompt does not block): the game did NOT start.** Installed
  `/tmp/vt3q/T23/VirtuaTennis3VR_T23.apk` (runtime = b8ddc4c: 01b320c..b8ddc4c
  changes tests only; mask off by default), vt3-repro prize quest with
  MASK=1 GL_ROBUST=1: 3 launches (prox_close + wake only), no vt3.log; logcat
  shows ActivityTaskManager START for VirtuaTennis3VR but **no process was
  ever started** (no "Start proc", no SDL/LIBGL lines) while
  GuardianDialogActivity ("Finding position in room") is resumed. So no
  shots, no B result, no C fault count (0 faults in logcat = nothing drew).
  The GAME_SHOT-under-Guardian note likely holds only for a game already
  running when the prompt comes up. After: app stopped (no pid), env.txt 0 B,
  vr.cfg byte-identical (`/tmp/vt3q/T23/H1/vr.cfg.before|after`), the
  b8ddc4c-equivalent build stays installed. Logs `/tmp/vt3q/T23/H1/`.
- **2026-11-12 ~23:12 T23 headset run H1 (granted) NOT started: "Finding
  position in room" is up** (com.oculus.guardian GuardianDialogActivity top
  resumed; screencap `/tmp/vt3q/T23/H1/pre.png` - room dark). Stopped before
  any change, as the rule says: nothing installed (the installed build is
  still the previous one, d9fa89e per the T21c entry), app not started,
  env.txt 0 B, vr.cfg not touched, battery 100%. Needs someone in the
  headset (lights on) before H1 can run; H1 as planned below.
- **2026-11-12 ~23:10 T23 done (commits, nothing pushed):** submodule
  b8ef66f (T4) -> 01b320c (robust switch) -> b8ddc4c (the parallel worker's
  tests commit b347611 cherry-picked on top: it had been made on b8ef66f in
  virtuatennis3-vr's submodule; both trees now pin b8ddc4c, unit tests 82 OK).
  Old tree 13f0f4f, 40b7182, d149a53, d1c5cc1; virtuatennis3-vr aed5b39,
  83c3396, 7b955d9, 096527b. Headset run H1 (entry below) owed.
- **2026-11-12 ~23:05 T23 step C + headset plan (no adb used).** C: fp 21/22
  and vp 2/4/6 translated GLSL read on macOS (`LINDBERGH_ARB_DUMP=1`,
  `/tmp/vt3q/T23/mac_fp/vt3.log`): constant indices only, fp 22 one plain
  `texture2D(s2_0)` (TEX, not TXP - so the 0x8000/0x8001 compare mask never
  changes its code), fp 21 colour only; the only run-time indexing in the
  game's programs is the skinning vps 135-177 (clamped, match only). The
  0x8000 = a depth / compare texture left bound on unit 15 by the game in the
  menus, read by no program. The faulting block is the shader core's own
  loads (UCHE client SP: uniform blocks / arrays), addresses random 46-49
  bit values in clusters 0x80 apart (`/tmp/vt3q/T22/logcat.txt`, 1470
  faults). Checked and ruled out: the gl4es_MV block binding after a
  program-binary load (fill_program sets it), the matrix ring's range.
  Switch committed (submodule 01b320c): `LINDBERGH_GL_ROBUST=1` makes the
  context with robust buffer access (fallback without; `[window] robust
  buffer access context: ...` line). APK with A+B+C:
  `/tmp/vt3q/T23/VirtuaTennis3VR_T23.apk`. **Headset owed (ask first; one
  ~2 min smoke run per change):** H1 T4 `OUT=$R/T23_mask LINDBERGH_VT3_MASK=1
  LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0
  LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_GAME_SHOT=2300,1,1,2301
  LINDBERGH_SHOT_BOTH=1 LINDBERGH_GL_ROBUST=1 scripts/vt3-repro.sh prize
  quest 130` with `adb logcat -c` before and `adb logcat -d | grep -c 'GPU
  PAGE FAULT'` after (baseline ~900/s): pass = both players' ground shadows
  in both eye shots, the two mask log lines; fault count tells C. (If the
  owner wants them apart: robust off in H1, a second run for C.)
- **2026-11-12 ~23:00 T23 step B1: T4 per-eye mask - cause found (code), fixed,
  opt-in, NOT run on the headset.** Two faults in the WIP: (1) arbprog.c read
  `lg_mask(-u_scr.xy)` while stereo.c/upload() set u_scr = (-1/ew, +1/eh): y
  came out negative, the twin was read at its clamped bottom row (no shadow)
  in both eyes - the vanished shadows; now `lg_mask(vec2(-u_scr.x, u_scr.y))`.
  (2) `gl4es_multiview_copy_layers` blitted into layer 1 (T8: writes nothing
  on the Quest driver) - now glCopyTexSubImage3D per layer (gl4es.patch;
  host test covers it). Unused `arb_fp_local` dropped. Still opt-in
  `LINDBERGH_VT3_MASK=1`. macOS build, unit tests, gl4es test, Quest APK
  build OK. Safety diff `ai_docs/wip/t4-mask-fix-lindberghrecomp.diff`.
- **2026-11-12 ~22:55 T23 worker (A gl4es slots, B T4 mask, C page faults),
  step A1:** gl4es fix in `../deps/gl4es` (multiview.c `mv_texture_deleted`,
  called from `gl4es_glDeleteTextures` and glstate.c `free_texture`: copy-back
  slot cleared, array deleted, `mv_bound` cleared); `quest/gl4es.patch`
  regenerated (applies on 1891af32); host test `quest/tools/gl4es_multiview_test.{c,sh}`
  (mock driver + ASan: passes; fails with the hook disabled). libGL.a rebuilt,
  Quest build running (`/tmp/vt3q/T23/qbA.log`). Not committed yet.
- **2026-11-12 ~22:40 T21c: loading bar CAUSE FOUND and fixed (submodule
  d9fa89e).** Run P3 (room lit) cold-start screencaps (`/tmp/vt3q/T22/P3_cap3_half.png`
  at ~2 s: the panel cut off just below SETTINGS, no line, no ball;
  `P3_cap4_half.png` / `P3_cap5_left.png` 2-4 s later: whole panel, dark
  track, yellow fill and ball). Screencap does capture the quad layers (the
  start-up screen is quads only). Cause: splash_init's 1220 row uploads into
  the static swapchain image were released to the compositor without a
  glFinish - the driver sent the first rows and held the rest (the panel's
  bottom, the atlas's line colour cell and ball) until a later flush, which
  on a cold start comes seconds late. Fix: gl.Finish() before
  xrReleaseSwapchainImage. A cold-start check of the fix (`/tmp/vt3q/T22/c2`)
  hit "Finding position in room" again - fix NOT yet seen on the headset.
  Replay HUD (8c00191) proven in P3: REPLAY plate from (0.70,0.35) to
  (0.67,0.39) of the eye picture, both players in the replay
  (`/tmp/vt3q/T22/replay_hud_before_after.png`, `P3_replay_sheet.png`,
  `P3_both.png`); replay/close-up ends clean. Installed: d9fa89e build
  (`/tmp/vt3q/T22/VirtuaTennis3VR_T21c.apk`); vr.cfg identical, env.txt 0,
  startup_seconds 18, app stopped. README showcase pictures (not committed):
  `~/Desktop/Claude/vt3-github/` (6 + contact sheet).
- **2026-11-12 ~21:35 T21b proof run P2 also blocked:** before launch the
  headset showed passthrough with no dialog (`/tmp/vt3q/T22/pre2_s.png`), but
  each of the 3 launches brought up "Finding position in room" (vrshell
  GuardianDialogActivity, room too dark; screencaps `/tmp/vt3q/T22/P2_caps.png`)
  and the app never started (no vt3.log). Stopped, not worked around. State:
  build 8c00191 installed, app stopped, vr.cfg byte-identical, env.txt 0 B.
- **2026-11-12 ~21:40 T21b: proof run P1 did NOT start** - a Guardian
  setup flow is up on the headset (vrshell GuardianSetupFlow; "Finding
  position in room" in the dark), three launches came to nothing; needs
  someone in the headset. Replay-HUD change and loading bar both unproven
  on the headset. State: committed build 8c00191 installed, app stopped,
  vr.cfg byte-identical, env.txt 0 B, startup_seconds 18. Owner's log kept
  as `/sdcard/VirtuaTennis3/vt3_owner_session4.log`. To prove later (one
  run, ~2 min, room lit): `LINDBERGH_VT3_IMMERSIVE=1
  LINDBERGH_VT3_REPLAY_VIEW=camera LINDBERGH_VT3_CUTAWAY_VIEW=camera
  LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_VT3_RVSHOT=2 LINDBERGH_SHOT_BOTH=1
  LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh
  replay quest 110` plus screencaps in the first 10 s for the splash.
- **2026-11-12 ~21:30 T21b (loading bar, replay plates).** Loading bar: the
  owner's 20:16 first launch after the T21 install logs the line layer from
  frame 1 (`frame 1, 3 layers ... line 4%`, 14% at 2.5 s, 28% at 5 s, the
  game's frame at 7.3 s, off at 17.8 s) - the layer is submitted; cause NOT
  found. A cold start here (`/tmp/vt3q/T22/c1`) cannot be seen: the dark room
  puts up "Finding position in room" over every screencap. Needs the owner's
  description (panel shown? the 'loading' word, the dark track, the ball?) or
  a lit room for a screencap. Replay plates: the head-locked HUD screen is
  the court camera's width (corners ~30 deg out); during a replay / close-up
  in Camera view it is drawn 1/1.6 as wide (submodule 8c00191,
  `LINDBERGH_VT3_REPLAY_HUD`). APK `/tmp/vt3q/T22/VirtuaTennis3VR_T21b.apk`
  installed; proof run P1 (replay scene, RVSHOT=2, both eyes) running.
- **2026-11-12 ~19:50 T21 done: committed build INSTALLED** (submodule
  bc8f1c3, `/tmp/vt3q/T21/VirtuaTennis3VR_T21.apk`); vr.cfg byte-identical
  (cmp), owner's vt3_save.bin unchanged (cmp), startup_seconds put back to 18,
  env.txt 0 B, R1's game shots removed from the headset, app stopped. Owner's
  logs kept as `/sdcard/VirtuaTennis3/vt3_owner_session3.log`.
- **2026-11-12 ~19:45 T21 COMMITTED (submodule bc8f1c3) - APK
  `/tmp/vt3q/T21/VirtuaTennis3VR_T21.apk`.** Headset run R1 (diag build:
  replay scene, Camera view, every frame of replay 1 + close-up,
  `/tmp/vt3q/T21/R1`, sheets `/tmp/vt3q/T21/sheet_r1.png`, `ends.png`):
  (2) players vanish = the game's own model culling, `TScene::Scene::
  entryModelPacket` -> `TScene::Frustum::intersect(const Model&)` against the
  replay camera's 8-17 deg lens (drawView builds it from camera+0x118); the
  player left that narrow picture (frame 2514 of replay 2463-2542) and was
  dropped, his planar shadow stayed. Fix: hook returns inside while a replay
  / close-up is in Camera view or the world (+10 frames); macOS: ~60-80 more
  models a replay frame (`[cull] ... models` with LINDBERGH_VT3_CULLLOG=1);
  `LINDBERGH_VT3_MODEL_CULL=1` keeps the game's test. Not headset-checked.
  (3) end glitch: the shot-kept fix was in R1 - replay->close-up and
  close-up->court frames clean (2541-2548, 2627-2642). (1) Save on by default.
  (4) splash line: cause NOT pinned (every log shows the line layer from
  frame ~2); hardening: line drawn from frame 1 (min 4%), expected time
  clamped 8-60 s, a start > 90 s not stored, log line every 300 frames shows
  the line %, and `[xr] splash: not shown - ...session was not running` if
  the splash is skipped. Owner to re-check; if still missing, his vt3.log
  splash lines tell which.
- **2026-11-12 ~17:30 T21 worker (in progress, UNCOMMITTED in the submodule):**
  (1) Save progress default On (xr_settings.h; tests updated; macOS prize run
  `/tmp/vt3q/T21/mac2`: `save on (default)`, fresh record PLAYER, written at
  the judge). (3) replay / close-up end: the game names the next camera mode
  2-3 frames before it moves the camera; those frames were drawn as the court
  through the replay's long lens, hidden only by the 3-frame end dip exactly
  (macOS) - now the shot is kept while the camera has not cut (<1 m, <5 deg a
  frame, 6 frames max) and the end dip starts on the new camera
  (`[rview] ... camera not cut yet - the shot kept`). Diagnostics added:
  `LINDBERGH_VT3_RVSHOT=<n>` (game shot of every frame of the first n Camera
  view segments + 30 after, `[rvshot]` lines), `LINDBERGH_VT3_PROJLOG=1`.
  Headset idle (owner's game, last input frame 4564): owner's log copied to
  `/sdcard/VirtuaTennis3/vt3_owner_session3.log`, vr.cfg `/tmp/vt3q/T21/vr.cfg.before`,
  his `vt3_save.bin` backed up `/tmp/vt3q/T21/owner_vt3_save.bin` (sha1 776e11c1).
  Diag APK installed, ONE run `R1` (replay scene, Camera view, RVSHOT=3,
  splash screencaps) running. Items 2 (players vanish) and 4 (no bar on first
  launch) open.
- **2026-11-12 ~17:10 T20 (Mac only): "players in view 0/2, OUT OF VIEW" was
  a LOG fault on macOS, not a regression or scene change.** `rv_players_seen`
  (stereo.c) tests against the eye's field `g_tan`, which only the XR host
  sets (`stereo_set_eye`); on macOS stereo never starts, `g_tan` is all 0, so
  every shot logged out of view. The framing itself (`rv_frame_shot`)
  already falls back to a 90-degree eye (tan 1) - unaffected. Fix: the log
  test uses the same fallback (submodule 43b712d; Quest unchanged: g_tan > 0
  there). Rerun `/tmp/vt3q/T20/macref2`: shots 1-6 all "the target's player
  in view" (1-2 of 2 players). Mac window shows the game's flat camera, not
  the VR eye (`/tmp/vt3q/T20/mac_camera_view_3440_3520.png`). Outer pins: old
  tree 57a4b9a, virtuatennis3-vr 631ecce. APK (NOT installed):
  `/tmp/vt3q/T20/VirtuaTennis3VR_T20_inview_log.apk`. Note: rally lengths
  differ run to run (first ReplayLoop 2948 vs 2488) - read the window for
  Quest run 1's shots from the run's own FLOWLOG, not from the mac numbers.
- **2026-11-12 ~17:10: T19 APK installed for the owner's worn test, no smoke
  run done; the owed checks remain** (combined T13-T19 run, T16 save run;
  plan and frame numbers in the entry below). Owner wearing the headset: no
  adb until he hands it back.
- **2026-11-12 ~17:05 headset worker (T20): committed build INSTALLED for the
  owner, no test runs (conductor: owner said "install now").** Installed
  `/tmp/vt3q/T19/VirtuaTennis3VR_T19_libcg_from_player.apk` (byte-identical
  to `quest/VirtuaTennis3VR.apk`; no source file newer than it, tree clean =
  submodule 1addfc1 + outer 1db0343/a883ff8). Headset `lib/libCg.so` present,
  2,170,374 B, SHA-256 da2f7604...736c. Owner's idle game (last input frame
  44307) force-stopped; his vt3.log kept as `/sdcard/VirtuaTennis3/vt3_owner_session2.log`
  and `/tmp/vt3q/T20/owner_vt3.log`. vr.cfg backup `/tmp/vt3q/T20/vr.cfg.before`
  (sha1 dc1c662e...), unchanged (cmp); env.txt 0 B; app stopped. Combined
  T13-T19 smoke run and T16 save run STILL OWED. Prepared: mac reference
  (replay scene, Immersive, Camera views; `/tmp/vt3q/T20/macref`): StartLoop
  1898, ReplayLoop 2948, WinloseLoop 3032, StartLoop 3122, so Quest run 1 =
  `LINDBERGH_GAME_SHOT=2930,1,0,3175 LINDBERGH_SHOT_BOTH=1` (replay +
  close-up + point start +-40, every frame); helper with input watcher and
  splash screencaps: scratchpad `t20run.sh <name> <scene> <secs>`. Note: the
  mac run logs every Camera-view shot as `players in view 0/2, the target's
  player OUT OF VIEW` - check against the Quest shots (T13 said in view).
- **2026-11-12 T19 COMMITTED (submodule 1addfc1 + outer) - libCg.so is no
  longer in the app; macOS-verified, Quest smoke run OWED.** Sizes: mac
  `build-mac/vt3` 70,181,888 -> 68,052,576 B; APK libmain.so 74,052,080 ->
  71,925,648 B (APK 25,347,451 -> 24,604,459 B); sampled libCg.so byte runs
  found: 323/328 -> 0/328 in both. APK (= T18 APK + T19):
  `/tmp/vt3q/T19/VirtuaTennis3VR_T19_libcg_from_player.apk` (also
  `quest/VirtuaTennis3VR.apk`). The app now NEEDS the player's
  `/sdcard/VirtuaTennis3/lib/libCg.so` (2,170,374 B, SHA-256
  da2f7604a1046e841e4a3e28d63c6a8d80ef9dcae996d6c06cad1b32585c736c, the
  Rev. C disk0/lib copy). `quest/install.sh` pushes `lib` (GAME_PARTS), so an
  install made with it has the file; the old builds never read it, so its
  presence on the headset is NOT verified yet. **Owed, folded into the ONE
  combined smoke run (install this APK instead of the T18 one; same run):**
  ```
  R=/tmp/vt3q/T19; adb shell ls -l /sdcard/VirtuaTennis3/lib/libCg.so
  adb shell sha256sum /sdcard/VirtuaTennis3/lib/libCg.so    # da2f7604...736c
  adb install -r $R/VirtuaTennis3VR_T19_libcg_from_player.apk
  OUT=$R/smoke LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ANISO=8 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_GAME_SHOT=2300,1,1,2301 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh prize quest 150
  grep -E '^\[solib\]|\[xr\] splash|texture filtering|FATAL' $R/smoke/vt3.log | head
  adb logcat -d -s VirtuaTennis3VR | grep -E 'game library|lib' | tail -3
  ```
  Pass: `[solib] libCg.so read from /sdcard/VirtuaTennis3/vt3_Lindbergh/../lib/libCg.so
  (2170374 bytes, SHA-256 verified), 6721 relocations applied`, then
  `libCg.so loaded at 0xb4000000`, match flow as usual (shaders compile).
  If `ls` shows no file: `adb push <disk0>/lib /sdcard/VirtuaTennis3/` first
  (or the app shows the Toast "The game's libCg.so is missing: copy the game's
  lib folder too, so that it is at /sdcard/VirtuaTennis3/lib/libCg.so." and
  closes - that is the error path; optional: check it once by renaming the
  file over adb, then rename back). Not needed as a separate run.
- **2026-11-12 T19 step 4 (macOS) PASSED.** Headless `prize` Classic
  (`/tmp/vt3t19/classic`) and Immersive (`/tmp/vt3t19/imm`), 330 s each:
  `[solib] libCg.so read from .../vt3_Lindbergh/../lib/libCg.so (2170374
  bytes, SHA-256 verified), 6721 relocations applied`, shaders compile, full
  match flow (Load..Gamesetmatch, Stats, next round) rounds 1-4, no crash.
  Error path, exit 1 before anything starts: missing (`LINDBERGH_SOLIB_DIR`
  empty dir, and the real file renamed then restored - SHA rechecked),
  wrong file (libCgGL.so as libCg.so: "that file is 251074 bytes").
  Next: Quest APK build + byte check.
- **2026-11-12 T19 step 2-3: code done (uncommitted in the submodule; safety
  diffs `ai_docs/wip/t19-libcg-*.diff`).** solib.py now writes
  `recomp_solib_relocs.c` (6,721 relocations, file size/SHA, image SHA) +
  `recomp_solib.txt`; re-lift in a scratch stage gave byte-identical
  `recomp_solib_funcs_*.c` / `recomp_solib.h`, and its image SHA
  2d2a9ee6...7e5c equals the old embedded array's. Old `recomp_solib_img.c`
  moved out of generated/ (scratchpad). solib.c reads `../lib/libCg.so`,
  checks, relocates; selftest + `tests/test_solib_relocs.py` pass. No
  fallback switch. Mac binary 70,181,888 -> 68,052,576 B, 0 of 328 runs.
  Quest app: `R.string.solib_check` check in VirtuaTennis3VR.java. Classic
  `prize` mac run in progress (`/tmp/vt3t19/classic`).
- **2026-11-12 T19 (libCg.so out of the binary) step 1 - findings.** What the
  embedded image is for: libCg's CODE is already lifted to C
  (`recomp_solib_funcs_*.c`); `recomp_solib_img.c` is the whole loaded image
  (2,211,840 bytes: every PT_LOAD, relocated by `tools/recomp/solib.py` at lift
  time) that `src/runtime/solib.c` memcpy's to guest 0xB4000000 on first use -
  the lifted code reads its data / rodata / GOT / PIC switch tables / init
  arrays from there (the text bytes are copied but not run). Baseline: 323 of 328
  sampled 48-byte runs of libCg.so found in both `build-mac/vt3` (70,181,888 B)
  and the APK's libmain.so (74,052,080 B). Plan: solib.py emits a relocation
  table (offset, type, resolved symbol address - no file bytes) + the file's
  size/SHA-256 + the relocated image's SHA-256; solib.c reads `../lib/libCg.so`
  (relative to the executable's folder), checks, loads PT_LOADs, applies the
  table. Other games: hotdex and gse use the same path (their generated/ is
  empty here). libCg sha256 da2f7604...736c (disk0 = revc copy).
- **2026-11-12 ~14:45: icon letter artefact fixed** (owner: a thin dark line
  with dots through the "3" where it meets the T - a white rim sliver and a
  dark pocket between the touching glyphs). `vt3_icon.py` now closes the
  union of the letters' outline masks (`close_mask`) before drawing the rim
  and keyline: 5, 6, 7 clean at 1024 / 192 / 96 / 48. Icons reinstalled,
  `~/Desktop/Claude/vt3-icon/` regenerated, APK rebuilt (same path).
- **2026-11-12 ~14:40 build worker: owner's fixes COMMITTED.** Icon = candidate
  7 "VT3 orange", no specular spot on the ball (installed; 5/6 share the ball
  code, same change). Start-up screen: the logo + TM + VR group, and the
  fallback title, centred on the screen's centre line by their drawn pixels
  measured at run time (submodule `splash_logo.c`); previews
  `~/Desktop/Claude/vt3-splash/layout_A_font_1.png` (group centre ~764 of
  768 - the badge's soft shadow) and `..._fallback_no_game_files.png`. APK
  rebuilt: `/tmp/vt3q/T18/VirtuaTennis3VR_aniso_icon_splash.apk` (checked:
  carries the orange icon). Smoke-run checks below unchanged (icon: the
  orange "VT3" tile on court blue; splash: the logo group centred).
- **2026-11-12 ~14:50 build worker: icon + splash COMMITTED - built for the
  Quest, headset checks OWED; release-rule audit done.** Submodule 4929c07
  (splash_logo.c: the game's title logo read at start-up from
  `resource/sprite/I_ADV_titlelogo_us_KB.abr`, own DXT5 decoder, VR badge,
  our own title as fallback; ball on the progress line, no digits). Outer:
  icon 9fcb08f (candidate 5 "VT3 chrome"), splash art layout A, DIN labels
  (owner's picks). APK (= T13-T17 + T16 + aniso/save name/Reset save + icon +
  splash): `/tmp/vt3q/T18/VirtuaTennis3VR_aniso_icon_splash.apk`.
  **Owed, folded into the ONE combined smoke run (no extra run):** install
  that APK, then during the usual `prize` run:
  ```
  R=/tmp/vt3q/T18; mkdir -p $R
  adb install -r $R/VirtuaTennis3VR_aniso_icon_splash.apk
  OUT=$R/smoke LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ANISO=8 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_GAME_SHOT=2300,1,1,2301 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh prize quest 150
  grep -E '\[xr\] splash|texture filtering|FATAL' $R/smoke/vt3.log | head
  adb shell wc -c /sdcard/VirtuaTennis3/env.txt
  ```
  Pass: `[xr] splash: the game's title logo from resource/sprite/I_ADV_titlelogo_us_KB.abr (908x388, shown ...) with VR`
  (if it says `our own title (...)`, the reason is in the brackets - the file
  is looked up relative to the game folder vt3_Lindbergh); `[gl] texture
  filtering: anisotropic 8x`; flow as usual. **Owner, worn (at that start):**
  the start-up panel shows the Virtua Tennis 3 logo with VR after it, the two
  thin-line controllers with callouts, the line with the ball moving (no
  digits); then in the Library ("Unknown Sources") the app's icon is the orange "VT3
  in front of a ball" tile on court blue (if the old one shows: launcher cache, reinstall
  or reboot). Advanced pages: "Texture filtering" and "Reset save" rows.
  **Release-rule audit:** no Sega art in the repo's code / generated C /
  committed art (splash, icons: ours; other games' icons are drawn
  crosshairs); VIOLATIONS: (1) the APK embeds `libCg.so` byte for byte
  (`games/vt3/generated/recomp_solib_img.c`, not committed, but in
  libmain.so) - NVIDIA's Cg runtime from the game's disk; (2) the repo
  carries game screenshots `docs/{ghostsquadevolution,hotd4,hotd4sp,hotdex,lgj}/mac-*.jpg`
  (outer, upstream 6bdb6e2) and `lindberghrecomp/docs/attract.png`
  (submodule, upstream b675020). Not changed (upstream files; owner to
  decide). The splash / icon text is rendered from Apple system fonts (DIN,
  Avenir Next) - swap for OFL fonts before a public release.
  Unit tests: 80, all pass except `test_xr_actions` (pre-existing: OpenXR
  header path; xr_actions.c untouched).
- **2026-11-12 ~14:45 build worker: TASK 1 COMMITTED (submodule 992a066)
  - macOS-verified, Quest smoke run OWED.** Texture filtering (aniso),
  save name (default PLAYER), Reset save, card result windows shut, LOSE,
  `lose` scene. Headless macOS: `/tmp/vt3w/aniso` (`[gl] texture filtering:
  anisotropic 8x`, flow same as `/tmp/vt3w/aniso0`), `/tmp/vt3w/name`
  (record named ACE, written at both judges), `/tmp/vt3w/lose` (Stats ->
  Continue 4544 -> Gameover 5206, then attract; frame 4560 shows CONTINUE?).
  Icon committed (outer 9fcb08f). Splash: `splash_logo.c` (logo read at
  start-up, DXT5 decode, fallback) written + tested; the owner then asked
  for a FRESH splash design (left/right controller drawings, no big
  digits) - in progress.
- **2026-11-12 ~15:00 build worker (inherited aniso / save name / lose / Reset
  save) - reviewed, UNCOMMITTED, macOS runs in progress.** The diff is more
  than the conductor listed: also a **Reset save** row (both Advanced pages,
  pull twice; `vt3_save_reset` moves the file + .bak aside, desktop Game menu
  "Reset Save..."), the card result windows ("Remove Card.") kept shut with
  Save progress on, a desktop `LINDBERGH_PICK` draw probe. Default save name
  is the neutral `PLAYER`; the tests' personal name replaced by `RALLY`.
  Unit tests (save, world_mode, settings, panels, controls: 53) pass. Next:
  headless runs `/tmp/vt3w/{aniso,aniso0,name,lose}`, then commit; then the
  release-rule audit, icon, splash.
- **2026-11-12 T16 COMMITTED locally - macOS-verified, Quest smoke run OWED**
  (Save progress; guide section 8, research Outcome). Default Off. macOS
  evidence: `/tmp/vt3t16/run1..3`, `off`, `corrupt` (vt3.log), pictures
  `~/Desktop/Claude/vt3-save/result_slate_off_on.png`, `record_bytes.txt`.
  Quest APK builds (`/tmp/vt3q/T16/VirtuaTennis3VR_t16.apk` = T13-T17 + T16).
  **Owed, ONE Quest run (~2.5 min)** (after the combined smoke run; the save
  file goes to a scratch name so the owner's save is never touched):
  ```
  R=/tmp/vt3q/T16; adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.before
  OUT=$R/save LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_VT3_SAVE=1 LINDBERGH_VT3_SAVE_FILE=vt3_save_test.bin LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_GAME_SHOT=99999,1 scripts/vt3-repro.sh prize quest 150
  adb shell ls -l /sdcard/VirtuaTennis3/vt3_Lindbergh/ | grep vt3_save; adb shell rm /sdcard/VirtuaTennis3/vt3_Lindbergh/vt3_save_test.bin*
  adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.after; cmp $R/vr.cfg.before $R/vr.cfg.after; adb shell wc -c /sdcard/VirtuaTennis3/env.txt
  grep -E '^\[save\]|Save progress|\[flow\] frame [0-9]+: (Judge|Gameset|Stats|Load)' $R/save/vt3.log
  ```
  Pass: `Save progress on`, `fresh record` at ~1500, `written to
  vt3_save_test.bin` at the match's judge, Gamesetmatch -> Stats -> Load, the
  file listed (one record = 668 bytes, in the game directory), no FATAL. Then the
  owner tries it worn: set "Save progress: On", restart, play, quit, play
  again - and says whether it should default On.
- **2026-11-12 T16 (save game) step 1 - written, UNCOMMITTED, macOS runs in
  progress** (safety diff `ai_docs/wip/t16-save-lindberghrecomp.diff`):
  `vt3_save.c/.h` (file: versioned header, CRC-32, tmp+fsync+rename, .bak,
  unreadable file moved aside), `hle_sega.c` hooks (player::reset_card_data
  from exec_no_card's decision 0x0812A8DD = load; playerManager::calcCard_data
  = save; playerManager::resetUse_card = save at session end), setting
  `save on|off` / `LINDBERGH_VT3_SAVE` / `LINDBERGH_VT3_SAVE_FILE`, panel row
  "Save progress" on both Advanced pages, macOS Game menu. Run 1 (fresh save,
  prize): record created at frame 1501, saved at the match's judge (20 bytes
  changed), no stall; the result slate showed "(null)" under the name (fixed
  since by calling setRealPlayerName, not yet rerun). Next: run 2 (load),
  Off baseline, corrupt file, then docs + commit.
- **2026-11-12 T17 COMMITTED locally - macOS-checked, Quest smoke run OWED**
  (anti-aliasing; guide section 8 "Anti-aliasing (T17)"). Default Off = today's
  path (no gl4es call, same GL calls); 2x / 4x opt-in by panel row / vr.cfg
  `msaa` / `LINDBERGH_MSAA`. Quest APK builds (gl4es rebuilt, `quest/gl4es.patch`
  regenerated). Unit tests: `test_world_mode` (msaa), `test_xr_settings`
  (round trip, off-list values), `test_xr_world_panel` (row, cycle, pins).
  macOS desktop 4x window: picture and screen copies fine, net tape smooth,
  net mesh not (texture) - `~/Desktop/Claude/vt3-aa/desktop_net_off_vs_4x.png`.
  **Owed, ONE Quest run (~2 min), after the combined T13-T15 smoke run (which
  covers the Off path) with the committed build installed:**
  ```
  R=/tmp/vt3q/T17; mkdir -p $R
  adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.before; adb shell wc -c /sdcard/VirtuaTennis3/env.txt
  OUT=$R/aa4 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0 LINDBERGH_ARCADE_OVERLAYS=0 LINDBERGH_MSAA=4 LINDBERGH_GPU_TIME=1 LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_GAME_SHOT=2300,1,1,2302 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh prize quest 150
  adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.after; cmp $R/vr.cfg.before $R/vr.cfg.after; adb shell wc -c /sdcard/VirtuaTennis3/env.txt
  grep -E 'anti-aliasing|incomplete|refused|\[world\] mode|gputime|FATAL|\[flow\]' $R/aa4/vt3.log | head -40
  ```
  Pass: `LIBGL: multiview: framebuffer N drawn with 4x anti-aliasing` and
  `[stereo] anti-aliasing: 4x asked, 4x granted`, no `incomplete` / `refused`;
  flow as usual (match start ~1949, Gamesetmatch, Stats, next round); the
  frames 2300-2302 both eyes show the court with the players' ground shadows
  at their feet (the shadow mask copy reads the resolved eyes) and nothing
  drawn after the mask copy showing through (stands / net / players whole -
  the risk: the extension leaves the multisampled depth undefined after a
  mid-frame resolve; Adreno reloads it, if not, later draws z-fight);
  `[gputime]` over frames 2100-3000 within ~+1.5 ms of the combined run's
  Off value (same scene, `LINDBERGH_GPU_TIME=1` there too). Pictures for the
  owner: crop the net (rows ~45-55 % of the eye height, centre half of the
  width) of `$R/aa4/eye_2300.ppm` and the combined run's frame 2300 (if it
  had shots; else rerun Off only if the owner asks), 3x nearest, into
  `~/Desktop/Claude/vt3-aa/quest_net_off_vs_4x.png`. If it fails: nothing to
  undo (default Off); log the failure and keep `msaa 0`. The owner judges
  2x / 4x worn by setting the row and restarting.
- **2026-11-12 T17 inherited (build worker, step 0) - UNVERIFIED, does not
  link on the Quest.** A cut-off worker left the T17 setting half-done in the
  submodule working tree (safety copy `ai_docs/wip/t17-antialiasing-lindberghrecomp.diff`,
  described in `ai_docs/wip/README.md`): vr.cfg `msaa`, `LINDBERGH_MSAA`, panel
  row, desktop multisampled window, and a call to a gl4es function
  `gl4es_multiview_msaa` that does not exist yet. Next: write the gl4es side
  and the resolve accounting, unit tests, then T16.
- **2026-11-12 T15 COMMITTED locally - macOS-verified, Quest smoke run OWED**
  (card reader off / Classic row, overlays-hidden closes the bar, Language
  row English default; headless macOS runs). Not installed. The combined
  T13+T14+T15 smoke run when the headset is back: install a fresh build of
  the committed tree, then the T13 command below plus a boot-to-match check
  (`[sega] system data region 2`, `card readers off`, no bar, English
  texts, match start frame - expected sooner than 1949? record it), owner's
  vr.cfg unpinned for one start (`LINDBERGH_VT3_IMMERSIVE=
  LINDBERGH_ARCADE_OVERLAYS= LINDBERGH_REPLAYS= LINDBERGH_VT3_CUTAWAYS=`).
- **2026-11-12 T13/T14 COMMITTED locally - macOS-verified, Quest smoke run
  OWED** (submodule `66ce3ff`; not installed - the headset is off; installed
  is still T12 `9dd8505`). Owed smoke run (combined with T15 when granted):
  `adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg /tmp/vt3q/T13/vr.cfg.before; adb install -r /tmp/vt3q/T13/VirtuaTennis3VR_t13.apk;`
  `OUT=/tmp/vt3q/T13/S LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_VT3_REPLAY_VIEW=camera LINDBERGH_VT3_CUTAWAY_VIEW=camera LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_VT3_CAMMODE_LOG=2 LINDBERGH_VT3_CUTLOG=1 LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_GAME_SHOT=2640,4,0,2900 LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh replay quest 130`
  (watcher on real input; then cmp vr.cfg, env.txt 0; a point start window: GAME_SHOT=<StartLoop-40>,1,0,<+40>)
- **2026-11-12 T13 worker, step 2 - macOS verified, T14 cause found and
  eased; waiting for the headset.** macOS: replay type cycle, 17 Camera-view
  shots (all 7 types + close-ups), the target's player in view every time;
  close-up 2.8 m. T14: StartLoop snaps the court camera ~10 m nearer / 3 m
  lower then glides back (CAMMODE_LOG=3) - now eased over 60 frames, logged
  `court camera snapped ... eased`; far-end height eased too. Docs: guide
  section 8 "Camera view reframed ...", backlog. Uncommitted (safety diff
  `ai_docs/wip/t13-camera-view-lindberghrecomp.diff`). Smoke plan: one ~2
  min run, Quest `replay` scene with the owner's vr.cfg pins off except
  views: `LINDBERGH_VT3_REPLAY_VIEW=camera LINDBERGH_VT3_CUTAWAY_VIEW=camera
  LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_VT3_CAMMODE_LOG=2 LINDBERGH_VT3_CUTLOG=1
  LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_GAME_SHOT=<start-40>,1,0,<start+40>
  LINDBERGH_SHOT_BOTH=1` round the first point start, plus 4-frame shots
  through the first replay / close-up.
- **2026-11-12 T13 worker, step 1 - Camera view reframed, In the world off
  the panel, height default Medium (uncommitted; macOS only).** stereo.c
  `rv_frame_shot` / `rv_look_at`: Camera view looks along the game camera's
  aim (pitch included) from a point moved toward its target (camera+0x44) to
  d - k(d - d tan(game)/tan(eye)), k = `LINDBERGH_VT3_REPLAY_CLOSE` (0.6),
  >= 2 m from the target, not under ground / through the net / inside a
  player; close-up 2.8 m; fixed per shot (default) or
  `LINDBERGH_VT3_REPLAY_FOLLOW=1`; `LINDBERGH_VT3_REPLAY_LEVEL=1` standing
  height + level gaze; replay start dip holds 16 frames (over the intro
  wipe); per-shot log `[rview] ... camera ... aim ... lens ... eye ...
  players in view n/m`. `LINDBERGH_VT3_REPLAY_PAN` removed. Test switch
  `LINDBERGH_VT3_REPLAY_TYPE=<0..6>|cycle` (camera::setReplayType).
  Rows Off / Flat screen / Camera view (stored `world` = camera; env world
  for tests). Default Camera height Medium (stored values kept - NB the
  owner's vr.cfg says `immersive.height 0`, written by an old save).
  `LINDBERGH_VT3_CAMMODE_LOG=3` logs every world camera note (T14 hunt).
  T14 (point-start glitch) logged in the backlog. Unit tests pass. Running:
  macOS replay scene, camera views, replay type cycle (`/tmp/vt3t10/c13`).
- **2026-11-12 T12 worker, step 2 - T12 COMMITTED and installed** (submodule
  `9dd8505`; APK `/tmp/vt3q/T12/VirtuaTennis3VR_t12.apk`, sha256 5f7fa9fe...;
  app stopped, env.txt 0, owner's vr.cfg byte-identical - note: the first
  panel click with this build rewrites vr.cfg without `immersive.dolly` /
  `.back`). Smoke run P1 (Immersive round0, panel open, 120 s, input 0): the
  panel shows the Classic / VR buttons (VR chosen, hovered), "VR runs (set by
  env.txt)", no Camera closer / Step back rows; match start 1949, four
  points, world normal, no FATAL. macOS: far end latched at 6818 (StartLoop
  after the change of ends at 6815), never in a rally. Not seen worn: the
  far-end High on the headset, the panel clicks on the buttons (pointer).
  Picture `~/Desktop/Claude/vt3-view/panel_T12.png` (left: headset dump;
  right: the VR page from the unit test painter).
- **2026-11-12 T12 worker (same session), step 1 - menu changes written.**
  T10 committed (submodule `2e61a2c`, outer `77a006a`) and its build
  installed (`/tmp/vt3q/T10/VirtuaTennis3VR_t10b.apk`). T12 uncommitted,
  safety diff `ai_docs/wip/t12-menu-lindberghrecomp.diff`: Camera closer /
  Step back rows gone (fixed 200 / 50 units = 5 m back; vr.cfg keys no longer
  read or written; env `LINDBERGH_VT3_DOLLY` / `_BACK` for tests), Camera
  height Low / Medium / High (0 / 10 / 20; older negatives = Low), far end =
  High (`hle_sega.c` `vt3_far_end_note`: human player z vs court camera eye
  z, latched outside GameLoop after 10 notes, handed with the camera to
  `stereo_vt3_far_end`; `LINDBERGH_VT3_FAR_HIGH=0` off; an env height wins),
  Classic / VR buttons on top of every page (`xm_paint_modes`,
  `xm_row_at_modes`, `XW_MODE_CLASSIC/_VR` as the first two rows, a note line
  "Classic runs now - VR after a restart"; Restart now first row under them),
  "Immersive" -> "VR" in labels. Unit tests updated, passing. Running: macOS
  `round0` cutaways/replays off 230 s (`/tmp/vt3t10/far`) for the far-end latch.
- **2026-11-12 T10 worker, step 5 - headset runs done, T10 committed.** S1
  and S2 (`/tmp/vt3q/T10/S1`, `S2`; input 0 both), vr.cfg restored
  byte-identical (cmp), env.txt 0. A: stadium exactly where it was in the
  rally; B: dip, level view from the corner cameras, players visible;
  cutaway B: dip clearing over the winner close up. Strips in
  `~/Desktop/Claude/vt3-replay/`. Known (README Done): the replay intro wipe
  as a plate in the world, white near ground (glare) in replay frames.
  Next: install the committed build, force-stop; then T12 (menu changes).
- **2026-11-12 00:42 T10 worker, step 4 - headset granted (two smoke runs).**
  Owner's game (pid 15602, last real input ~12000 frames earlier, headset
  asleep) force-stopped; owner's vr.cfg backed up
  `/tmp/vt3q/T10/vr.cfg.owner` (sha1 47c9e2b4..., immersive, back 50,
  shadow 4096); his vt3.log copied to `/sdcard/VirtuaTennis3/vt3_owner_session.log`.
  T10 APK installed. S1 (replays world, cutaways follow) running via
  scratchpad `t10run.sh` (watcher kills on real input). Next: S2
  (`t10run.sh S2 follow world`), restore vr.cfg, strips, commit.
- **2026-11-12 T10 worker, step 3 - macOS-verified build ready; WAITING FOR
  THE HEADSET (conductor's grant).** Code uncommitted (submodule working tree
  = `ai_docs/wip/t10-replay-views-lindberghrecomp.diff`); test APK
  `/tmp/vt3q/T10/VirtuaTennis3VR_t10.apk`. macOS logic runs (`/tmp/vt3t10/q_*`,
  `r_*`): prize Immersive, replays world + cutaways camera - Winlose 7 camera
  view (start dip, 1 shot, end dip), `big-point serve close-up left out (Point
  cutaways in the world)`, Replay 6 in the world (anchored), Gamesetmatch ->
  Stats -> Load -> next round, twice; replay scene, replays camera + cutaways
  world - 7 replays, each one start + end dip, a type-0 ace replay's rewind
  found (`reverseFrame`) with the camera's move a frame later settled in the
  same dip (fixed after this run: it was a second dip); splitreplay with
  cutaways world - `split-screen close-up left out` at all 6 points; Classic
  splitreplay unchanged (`split-screen camera forced`, no `[rview]`); flat
  views give no `[rview]` correction lines; no crash / FATAL. Unit tests pass.
  **Headset plan (one ~2 min smoke run each; back up vr.cfg, empty env.txt,
  watcher on real input):**
  ```
  R=/tmp/vt3q/T10; adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.before
  adb install -r $R/VirtuaTennis3VR_t10.apk
  # S1: replays In the world, cutaways Camera view (shots through the first replay + close-up)
  OUT=$R/S1 LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_VT3_REPLAY_VIEW=world LINDBERGH_VT3_CUTAWAY_VIEW=follow LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_VT3_CAMMODE_LOG=2 LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_GAME_SHOT=<first replay -10>,6,0,<+200> LINDBERGH_SHOT_BOTH=1 scripts/vt3-repro.sh replay quest 130
  # S2 (if granted): the other pair - REPLAY_VIEW=follow CUTAWAY_VIEW=world
  adb pull /sdcard/VirtuaTennis3/vt3_Lindbergh/vr.cfg $R/vr.cfg.after; cmp $R/vr.cfg.before $R/vr.cfg.after; adb shell wc -c /sdcard/VirtuaTennis3/env.txt
  ```
  The first replay's frame on the Quest: read it from the run's `[flow] ...
  ReplayLoop` (macOS: 2409 in the replay scene; the Quest's match starts at
  ~1949, so expect ~2460 - start shots at 2380 every 6 to 2700 if unknown).
  Look for: stadium in the same place as the last rally frame (A), players
  replaying, shadows at the feet, no flat frame in modes 6/7, black dips
  (B), ball trail / hit flash facing; then commit the submodule and the docs.
- **2026-11-12 T10 worker, step 2 - logic verified by logs on macOS; macOS
  pictures useless.** `LINDBERGH_STEREO=1` on the desktop shows the left eye
  tiny and the right eye black (the second-eye replay draws no world) in
  every view, baseline included - so pictures must come from the headset's
  `LINDBERGH_GAME_SHOT`. Logs (replay scene): replay lens 3.0-3.2 (type 4
  camera behind the near baseline, eye ~1 m high), close-up 2.8-9.6; three
  world camera notes per frame + the pixel camera; **the game's first frame
  in a new camera mode still carries the old view** - anchor now taken only
  from mode 1/2 frames after their first, Camera view's start dip begins on
  that stale frame and the first real frame is its first shot (no second
  dip). Unit tests extended and passing (world_mode, world_panel, settings).
  Running: `/tmp/vt3t10/r_{follow,split,prize,classic}` (logic checks).
- **2026-11-12 T10 worker, step 1 - code written, first macOS runs going.**
  Uncommitted; safety diff `ai_docs/wip/t10-replay-views-lindberghrecomp.diff`
  (`git apply` in the submodule). What is in: vr.cfg `immersive.replays` /
  `.cutaways` `off|flat|world|camera` (old `on` = flat; `LG_VIEW_*`),
  `WmValues.replay_view/cutaway_view`, env `LINDBERGH_VT3_REPLAY_VIEW` /
  `_CUTAWAY_VIEW=flat|world|follow|camera` (an on/off env pin alone = flat),
  panel rows cycle Off / Flat screen / In the world / Camera view; stereo.c
  `stereo_vt3_view` (GL thread, from `vt3_cam_job`; anchor = last mode 1/2
  view; correction C in `eye_projection`; flat rules off while `g_rv.active`;
  Camera view: level per-shot heading, `LINDBERGH_VT3_REPLAY_PAN=1|2`, dip
  to black `rv_fade_draw`, `LINDBERGH_VT3_REPLAY_FADE`), `arb_note_projection`
  returns what it took, `replay::reverseFrame` counted (worker thread, handed
  on by the main thread's camera), split screen suppressed via the
  `initWinlose` rand (thread-local flag), serve close-up off in in-world
  views, `LINDBERGH_SHOT_UNTIL` (mac shots). No headset used. Next: look at
  `/tmp/vt3t10/m_world`, `/tmp/vt3t10/m_follow` (replay scene, mac, shots
  2380-2600 every 4).
- **T8b worker, step 14 - T9 COMMITTED and installed; testing stopped at the
  owner's request ("too excessive").** Submodule `688a9b9` (= the tested
  working tree, identical to the wip diff), APK
  `/tmp/vt3q/T8b/VirtuaTennis3VR_688a9b9.apk` (sha256 744291d9...) installed,
  app stopped, env.txt 0, vr.cfg = owner's 22:51 file byte-identical.
  Q_imm (Immersive prize 220 s, input 0) passed: Gameset 3107 -> Stats 3172
  -> Load 3532 (360, tapped), Stats 7094 -> Load 7694 (600), round 3 start;
  black 0-1, 1185, 1947-8, 3534-5, 3776-7, 7697-8 (load / match start, the
  game's own); 0 FATAL/WARNING/watchdog. **Skipped (owner):** Q_cls Classic
  regression. B1: band = the near end's front wall. Next worker: follow the
  owner's new rule (README ground rules) - one ~2 min smoke run per change.
- **T8b worker, step 13 - slate at +2 m OK** (L20b, input 0: StatsLoop
  3082, shot 3250 = slate, flat, both eyes; sheet
  `~/Desktop/Claude/vt3-view/result_slate_at_heights.png` updated). Q_imm /
  Q_cls running.
- **T8b worker, step 12 - band identified (B1, input 0).** With the view
  pitched down 35 deg (`/tmp/vt3q/T8b/B1/game_02300.ppm`) the dark band is
  the near end's front wall / barrier right in front of the viewpoint (its
  top is the straight edge; a line judge's chair sits below it): geometry,
  not a mask or texture edge. At 6-8 m back the eye stands just behind it, at
  5 m it is mostly below the view. Also in the sky build (`9d68719`) at 6 m:
  not new with T9. Not changed. seq4 continues (L20b, Q_imm, Q_cls).
- **T8b worker, step 11 - conductor's go (owner: headset off, controllers
  down).** T8+T9 test build installed, device vt3.log removed, seq4.sh
  RUNNING again (`/tmp/vt3q/T8b/seq4.out`, `SEQ4_DONE` / `INPUT_SEEN`).
- **T8b worker, step 10 - STOPPED AGAIN on real controller input
  (~23:47 MST, headset `Awake`).** B1's log (`/tmp/vt3q/T8b/B1/vt3.log`) has
  buttons 0x9001 / 0x8001 / 0x10000 / 0x10010 from frame 1204 - not the
  script's. Watcher stopped the run; app force-stopped, env.txt 0, vr.cfg =
  owner's 22:51 file byte-identical, **installed: committed T8 `2c3f4f4`**.
  T9 still uncommitted (wip diffs as in step 8); still owed: B1 (band, view
  pitched down), L20b (slate +2 m), Q_imm, Q_cls - just rerun
  `.../786966e7-.../scratchpad/seq4.sh` after `adb install -r
  /tmp/vt3q/T8b/VirtuaTennis3VR_t8t9.apk` and `adb shell rm -f
  /sdcard/VirtuaTennis3/vt3.log` (the watcher reads the device log; its
  device-side grep now has `2>/dev/null` - a missing log printed an error
  line that counted as input, so the first trigger at launch may have been
  that bug; the log then showed real input anyway).
- **T8b worker, step 9 - resumed (owner handed the headset back; his
  22:51 vr.cfg is the one to restore).** Helper fixed: `t8run.sh` now counts
  real input (`[cab] frame N: buttons V` not 0 / 0x1 / 0x10). Installed the
  T8+T9 test build again; running `.../scratchpad/seq4.sh` (log
  `/tmp/vt3q/T8b/seq4.out`, marker `SEQ4_DONE`; a watcher greps the device's
  vt3.log every 10 s and kills the run on real input -> `INPUT_SEEN`):
  B1 (band: view pitched down 35), L20b (slate at +2 m, shots 3250-3650),
  Q_imm (FLOWLOG+BLACK_LOG 220 s), Q_cls (FLOWLOG, shots every 150 frames).
  Dark band at the bottom at 6 m: also in the sky build's R_m0 shot
  (`/tmp/vt3q/X/R_m0/game_02300.ppm`) - not new with T9.
- **T8b worker, step 8 - STOPPED: controller input (owner in the headset,
  `mWakefulness=Awake`) during L-20 (from frame ~4346), L20 and Q_imm.**
  Done at once: seq3 and its run killed by PID, app force-stopped, env.txt 0
  bytes, vr.cfg = the owner's 22:51 file byte-identical
  (`/tmp/vt3q/T8b/vr.cfg.owner2251`), **installed: committed T8 build
  `2c3f4f4`** (`/tmp/vt3q/T8b/VirtuaTennis3VR_2c3f4f4.apk`, sha256 0fa1b111...).
  **T9 NOT committed** (code in the submodule working tree and
  `ai_docs/wip/t9-view-lindberghrecomp.diff`; its guide/backlog text in
  `ai_docs/wip/t9-view-docs.diff` - `git apply` it). T9 verified so far:
  step back 5-8 m, heights -2..+2 m, serve meter at -2/0/+2 m, panel row
  (`~/Desktop/Claude/vt3-view/immersive_advanced_panel.png`), slate at -2 m
  (`result_slate_at_heights.png`: the +2 m shot at 3500 is play, not the
  slate - L20 was disturbed). V1 Classic capture clean (strips
  `vt3-bugs/classic_court_from_above_1949_{BEFORE,AFTER}.png`).
  **Owed for T9:** slate at +2 m, Q_imm / Q_cls regression (220 s, FLOWLOG +
  BLACK_LOG) on a T8+T9 build (`/tmp/vt3q/T8b/VirtuaTennis3VR_t8t9.apk` =
  the current working tree), then commit + install + restore vr.cfg.
  **Testing bug found:** the helpers' `cab_count.txt` (`grep -c '\[cab\]
  buttons'`) never matches (`[cab] frame N: buttons ...`) - always 0. Real
  check: `grep -E '^\[cab\] frame' vt3.log | awk '$5 !~ /^(0x1|0|0x10),$/'`
  outside the script's own keys (z = 0x1, coin = 0x10). Earlier runs
  G1..MP clean by that check.
- **T8b worker, step 7 - serve meter OK at -2 / 0 / +2 m** (S-20/S0/S20,
  cab 0): meter beside the player both eyes; sheet
  `~/Desktop/Claude/vt3-view/serve_meter_at_heights.png`. seq3 continues
  (V1, MP, L-20/L20, Q_imm, Q_cls).
- **T8b worker, step 6 - seq3 RUNNING** (`.../786966e7-.../scratchpad/seq3.sh`,
  log `/tmp/vt3q/T8b/seq3.out`, marker `SEQ3_DONE`): S-20/S0/S20 serve meter
  (round0, SERVESHOT **needs `LINDBERGH_VT3_SERVELOG=1`** - the first S
  runs had none and took no shots), V1 Classic 1944-1960, MP panel dump
  (Immersive page), L-20/L20 slate at 3500, Q_imm/Q_cls 220 s regression.
  Installed: T8+T9 test build. If cut off: wait for / kill seq3 by PID, then
  judge, commit T9 (`git -C lindberghrecomp add -A src tests` minus
  .DS_Store), install, restore `/tmp/vt3q/T8b/vr.cfg.owner2251`.
- **T8b worker, step 5 - T9 height verified (shots).** H-20/-10/10/20
  (`/tmp/vt3q/T8b/H*`, cab 0): the eye moves along up as set, both eyes;
  sheet `~/Desktop/Claude/vt3-view/camera_height_steps.png` (game moment at
  2300 differs per run). The 3200 shot is Gamesetmatch (flat close-up, fine),
  not the slate - slate shots at 3500 for -20/+20 added to seq3 (runs L-20,
  L20). Guide / backlog text for T9 written (uncommitted). Next: S* serve
  meter runs (running), then seq3.
- **T8b worker, step 4 - T8 COMMITTED (submodule `2c3f4f4`, outer
  `44efc1a`), T9 step back verified.** D50-D80 (`/tmp/vt3q/T8b/D*`): the
  view steps back as set, both eyes; sheet
  `~/Desktop/Claude/vt3-view/step_back_5_6_7_8m.png`. At 6-8 m a dark band
  (the near stand's shadow / near apron) along the bottom; at 8 m the top of
  something (rail?) at the bottom edge - for the owner to judge. No
  controller input in any run (cab 0); device vr.cfg still = owner's 22:51
  (`vr.cfg.owner2251`). seq2 continues (H*, S*); then
  `.../scratchpad/seq3.sh` (V1 Classic capture, MP panel dump, Q_imm/Q_cls).
- **T8b worker, step 3 - T8 verified; T9 runs going.** On the T8 build
  (0fa1b111): G1 GPU (prize, Immersive, FIXED_HEAD, VIEW_TURN 0,20) match
  2.8 / 2.8 / 3.1 ms (sky build G_new 3.2 / 3.1 / 3.0) - no cost; slate
  20-40 ms frames as before (known FIXED_HEAD finding). V2 (Immersive,
  every frame 1940-1985 both eyes): 1949 held (black like 1947-48, both
  eyes), fade left out from 1950, clean court. Strips
  `~/Desktop/Claude/vt3-bugs/immersive_court_from_above_1949_{BEFORE,AFTER}.png`.
  **Installed now: T8+T9 test build** (`/tmp/vt3q/T8b/VirtuaTennis3VR_t8t9.apk`).
  Running: `.../786966e7-.../scratchpad/seq2.sh` (D50-D80 step back, H-20..H20
  height + slate at 3200, S-20/S0/S20 serve meter round0) -> `/tmp/vt3q/T8b/`,
  marker `SEQ2_DONE`. Then: V1 Classic capture 1944-1960, contact sheet to
  `~/Desktop/Claude/vt3-view/`, regression, commits.
- **T8b worker, step 2 - T9 code written (uncommitted, unbuilt for Quest).**
  T9 (owner, via conductor): Immersive Step back choices 5/6/7/8 m (was
  0/3/6/9/12, default 6 m = `immersive.back 60` stays; stored values off the
  list snap to the nearest, `xr_settings_nearest` in `xr_settings.h`), new
  row **Camera height** (`immersive.height`, game units, -20/-10/0/10/20 =
  2 m lower .. 2 m higher, default 0 = the camera's own; env
  `LINDBERGH_VT3_HEIGHT`; live like Step back; `stereo.c` eye_projection
  moves the viewpoint along the world's up). Unit tests updated and pass
  (`tests.test_xr_settings`, `_xr_world_panel`, `_world_mode`, `_xr_panel`).
  Copy: `ai_docs/wip/t9-view-lindberghrecomp.diff` (+ the 2-line stereo.c
  note at its end). T8 runs G1 (GPU) / V2 (Immersive 1940-1985) running via
  `.../786966e7-.../scratchpad/seq1.sh`. Next: T8 commit with
  `git apply --cached /tmp/t8only.diff` (= the T8 wip diff) so T9 stays out.
- **T8b worker (2026-11-11 23:00), step 1 - state found.** The T8 worker
  went on after its last checkpoint: hold for frame 1949 written (wip diff
  now refreshed from the working tree, outer `ae51cd3`), APK built 21:10
  (`quest/VirtuaTennis3VR.apk` sha256 0fa1b111..., copy
  `.../123aec40-.../scratchpad/VirtuaTennis3VR_t8.apk`); a rebuild of the
  working tree now gives the **same bytes**, and that is what is installed.
  Its regression ran on it (`.../123aec40-.../scratchpad/t8reg.sh`, results
  `/tmp/vt3q/T8/{P1,R_imm,R_cls,R_cuts,R_m0,R_m1,R_m2}`, `REG_DONE`), unit
  tests OK (`/tmp/vt3q/T8/ut_*.txt`). F6-F8 (Classic) show 1949 held both
  eyes (F4 = an earlier blit version: right eye still from above). R_imm:
  Stats->Load 3082->3442 (360: the menu script's tap at 3440 skips it),
  6974->7574 (600), round 3 reached; black only the game's own; R_cls
  flow fine; R_cuts fine; no FATAL/WARNING/watchdog. **BLACK_LOG is blind in
  Classic now** (flat: only frames 0-1 logged) - judge Classic by game shots.
  **The owner played worn on this build ~22:30-22:51 and confirmed all
  three T8 fixes** (conductor). He changed vr.cfg himself at 22:51 (mode
  immersive, immersive replays/overlays/cutaways on): **that is now the
  owner's vr.cfg** - `/tmp/vt3q/T8b/vr.cfg.owner2251` (restore this one, not
  the 20:31 `vr.cfg.owner`). His session log: `/tmp/vt3q/T8b/owner_session_vt3.log`.
  Next: GPU_TIME run + Immersive 1944-1985 capture (`/tmp/vt3q/T8b/`, helper
  `.../786966e7-.../scratchpad/t8run.sh`), commit T8, then T9 (viewer
  distance 5/6/7/8 m + camera height row).
- **T8 worker, step 1 - both bugs captured, fixes written (test build
  installed, NOT committed).** Strips: `~/Desktop/Claude/vt3-bugs/`
  (`classic_topdown_match_start_BEFORE/AFTER.png`,
  `classic_match_start_GAMES_OWN_macos.png`,
  `immersive_image_in_image_first_serve_BEFORE/AFTER.png`). (a) Classic,
  every match start (EntranceLoop): frame 1949 stadium from above (lens 1.45),
  1950 wrong world view, 1951-56 black - stereo.c judged them world frames;
  fix: VT3 Classic always flat (`flat_all` default, `LINDBERGH_FLAT_ALL=0`
  old). (b) Immersive, every StartLoop with cutaways off (~30 frames): the
  game's cross-fade quad (fp 54, screen copies 34/40 on units 0/1, re-copied
  each frame) drawn on the HUD plane; fix: HUD 2D into the eyes reading a
  screen copy on any unit the program reads (`arb_fp_units`, new) is left out
  of world frames (`LINDBERGH_VT3_CAPTURE=1` keeps). Test runs F1/F3
  (`/tmp/vt3q/T8/`): inset gone, Classic fly-by from 1950; **the one frame
  from above at 1949 remains in both modes** (game draws with the unset
  camera, lens 1.45; macOS shows the VS screen there). Diff:
  `ai_docs/wip/t8-flat-and-fade-lindberghrecomp.diff`. Installed: the test
  build (not for the owner). Next: frame 1949; after-point strips;
  regression (BLACK_LOG, cuts on, Classic + Immersive prize); commit;
  reinstall a committed build.
- **T8 worker (2026-11-11 late), step 0.** Conductor's queue now: T8
  (owner's worn reports on `9d68719`: (a) Classic, "when we switch to 3d for
  a split second the court can be seen from a top down shot"; (b) Immersive,
  "a split second before every point ... an image within an image") -
  capture + present strips in `~/Desktop/Claude/vt3-bugs/`, then fix each;
  then T4 (ground shadow), then T6. **T7 (near-end crowd) DROPPED by the
  owner** - parked in the backlog's "Later / parked" (lead:
  `CAudience2DManager::draw` crowd level). T4 untouched so far (the WIP
  diff in `ai_docs/wip/` is as the sky worker left it). Headset: installed
  `9d68719` (sha 990f1a81, copy
  `.../123aec40-.../scratchpad/VirtuaTennis3VR_9d68719.apk`), owner's vr.cfg
  backed up (`/tmp/vt3q/T8/vr.cfg.owner`, scratchpad `vr.cfg.owner`: mode
  classic, replays on, classic.cutaways on, overlays off; immersive
  replays/cutaways/overlays off). Runs: `/tmp/vt3q/T8/<name>`, helper
  `scratchpad/t8run.sh`. Running: C1 (Classic owner settings, prize, every
  frame 1880-2060, MODE/FLOW/CAMMODE/CUT logs).
- **Sky worker, group 3 - conductor's go; regression of `9d68719` RUNNING**
  (`.../w2/reg.sh`: installs `VirtuaTennis3VR_skyonly.apk`, then R_imm prize
  Immersive 330 s FLOWLOG+BLACK_LOG, R_cls Classic 330 s, R_m0/1/2 Immersive
  match starts rounds 0-2 100 s; results `/tmp/vt3q/X/R_*`). Owner's vr.cfg
  unchanged after his worn session. If cut off: check `R_*` logs, then
  `adb shell am force-stop org.lindbergh.vt3.vr`, empty env.txt.
  R_imm PASSED: Gamesetmatch 3264 -> Stats 3352 -> Load 3953 (601), Stats
  7524 -> Load 8124 (600), round 3 to Stats 11679; black only 0-1, 1085-6,
  1947-8, 3955-6, 8127-8 (the game's own); no FATAL / WARNING / watchdog;
  the sky line and the one `[glq] job ... handed` line present.
  R_cls (Classic prize 330 s) PASSED flow: Winlose 2551, Replay 3371,
  Gamesetmatch 3442, Stats 3532 -> Load 4133 (601), Stats 8539 -> Load 9139
  (600), next rounds; no sky line (inert), no FATAL. BLACK_LOG: 0-1, 1947-8,
  LoadLoop 4134/9141, load->match 4376/9383 **and 3446-7 / 8306-7 (4 frames
  into Gamesetmatch)** - Classic code paths are unchanged by `9d68719`, so
  checking the same on the old `0dbcb6e` build (O_cls, running).
  R_m0/1/2 (Immersive match starts on Ger3M / Aus1F / Fra1F, 100 s): clean,
  sky line present, shots fine (`/tmp/vt3q/X/R_m*/game_02300.ppm`).
  O_cls (old `0dbcb6e`, Classic prize 150 s BLACK_LOG): black at 3963 = 4
  frames into Gamesetmatch 3959 too - the game's own fade, not new.
  **Regression of `9d68719` PASSED. Installed now: `9d68719` build**
  (`w2/VirtuaTennis3VR_skyonly.apk`, sha256 990f1a81...), app stopped,
  env.txt 0, vr.cfg byte-identical to the owner's, battery 84%. PAUSED for
  the owner to judge the sky worn (Sky: Stadium default; Painted / Off in
  the Immersive advanced page).
- **Sky worker, group 2 (2026-11-11 night) - sky COMMITTED, regression
  of it still owed; PAUSED for the conductor.** Submodule `9d68719` (sky
  dome fix + test switches; T4 left out, kept as
  `ai_docs/wip/t4-on-sky-lindberghrecomp.diff`, opt-in there). APK of
  exactly this code: `.../786966e7-.../scratchpad/w2/VirtuaTennis3VR_skyonly.apk`.
  **Installed now: the regressed `0dbcb6e` build** (`w2/VirtuaTennis3VR_0dbcb6e.apk`),
  app stopped, env.txt 0, vr.cfg byte-identical, battery 81%.
  GPU (prize, FIXED_HEAD, view pitched 20, match windows 2400-3000):
  Stadium new 3.0-3.2 ms (90% 4.3-4.4), Off 2.8-3.0, old behaviour
  (`LINDBERGH_VT3_DOME=0 LINDBERGH_VT3_SKY_FILL=1`) 4.1, Painted 4.0;
  59-60 fps in play - the new sky costs ~0.2 ms and saves ~1 ms over the
  old painted fill. Cuts on (`Q_cuts`): Winlose 2463, Replay 3355,
  Gamesetmatch 3442, Stats 3532 -> Load 4133 (601), next round; black only
  0-1, 1085-6, 1947-8, 4135-6 (the game's own); no FATAL / WARNING.
  **New finding (not the sky):** in every run with the eyes set while the
  session is stopped (FIXED_HEAD now acts unattended; also with
  `LINDBERGH_VT3_DOME=0`) the result slate has 60-80 frames of 20-40 ms
  GPU and 43-48 fps; the old committed build without a held head had 2.
  Suspect the head-locked HUD / flat-panel path (`head_ok` is set by
  `set_eyes`), which a worn session always takes - check worn, or A/B
  unattended with and without FIXED_HEAD (`G_*` vs `Z_gdef`). Shots for
  the owner: `/Users/chrishelms/Desktop/Claude/vt3-sky/` (per venue Before
  / Stadium / Painted / Off x forward / up 70 / left 90 / behind, ten
  directions of Stadium, seam before/after rounds 0 and 2). Runs:
  `/tmp/vt3q/X/{A,B,C}_r{0,1,2}`, `G_*`, `Q_cuts`.
  macOS check of `9d68719`: Classic shaders carry no `u_sky` (0 of all
  programs, `/tmp/vt3q/X/mac_cls`), Immersive 44 (`mac_imm`) - inert outside
  Immersive (other games are never Immersive).
  **Next (after the conductor's go):** install `w2/VirtuaTennis3VR_skyonly.apk`
  and run the regression (prize Immersive 330 s FLOWLOG + BLACK_LOG, prize
  Classic 330 s, 3 Immersive match starts 80 s), e.g.
  `bash .../w2/g3.sh` minus its first four GPU lines; if it passes, leave
  that build installed, app stopped, env.txt empty, vr.cfg restored.
- **Sky worker, group 1 - the real sky found and fixed (working tree, not
  yet committed).** macOS probe (vertex dump with the draw's own indices):
  the sky is **GAME_NO_SKY_Polygon = one draw, a whole hemisphere of radius
  ~4000 game units** (32 segments x 8 rings, apex y 4000; Ger3M's reaches y
  -780), drawn with vp 111 (plain MVP, locals 0-3) and a texture-times-
  colour fp (118 on round 0, 122 on rounds 1/2 - not stable), unit 0 the
  stadium atlas (4096x1024 / 4096x512) with uv 0..0.5 x 0..0.5 = the
  2048x512 panorama wrapped **once round the full 360 deg** (u 0 at azimuth
  -125 deg, v 0.499 horizon -> 0.001 zenith). fp 180 = the SUN sprite
  (vp 129, a small quad at ~(860, 350, -1740)). The game draws the dome at
  its far plane: round 1/2 with the projection's depth row = w (z = w),
  round 0 at true depth (~4000 > far 3000). The eyes reproject from the
  game's clip space, so only a front cone survived - that was the
  "lavender sky in front" (the panorama's own lavender) next to our painted
  fill. Round 0 is **Ger3M (Duesseldorf)**, not Ita3F (atlas shows
  Duesseldorf Open). Fix (`arbprog.c` `vt3_sky_fix`, `u_sky`): in Immersive
  world draws, vertices > 3000 from their model origin get the true clip
  depth back before `u_reproj`, then are pinned to the eye's far plane;
  Painted / Off collapse them (no wedge, no band). Stadium no longer draws
  the painted fill (`LINDBERGH_VT3_SKY_FILL=1` test). Quest shots
  (`/tmp/vt3q/X/A_r*`, `B_r*`, `C_r*`; fixed head): one continuous Sega
  sky forward / 60 / 90 / 120 / 180 / up 40 / 70 / 89, both eyes identical
  in the sky (disparity 0 px at pitch 70); Off black sky, no wedge; Painted
  ours only. T4 defaulted off (opt-in `LINDBERGH_VT3_MASK=1`) and kept out
  of the sky commit. `LINDBERGH_XR_FIXED_HEAD` now works with the session
  stopped.
- **Sky worker (2026-11-11 night), step 0 - committed build regression PASSED.**
  Submodule `0dbcb6e` = `8004564` (fix + T5 LOD bias) + the test switch
  `LINDBERGH_XR_FIXED_HEAD=1` committed alone (host_xr.c). WIP (T3/T4) set
  aside (identical to `ai_docs/wip/`), built, installed; copy
  `/private/tmp/claude-501/-Users-chrishelms-Desktop-Claude/786966e7-92df-442c-b205-476a682b88a2/scratchpad/w2/VirtuaTennis3VR_0dbcb6e.apk`
  - **this is the owner's build now (installed)**. Runs (`/tmp/vt3q/X/Z_*`):
  Immersive `prize` 330 s BLACK_LOG: Gamesetmatch 3106 -> Stats 3172 -> Load
  3532 (script taps), Stats 7128 -> Load 7728 (600), next rounds; black only
  0-1, 1185-6, 1947-8, LoadLoop 3534/7730, load->match 3776/7972 (the game's
  own). Classic `prize` 330 s: Winlose/Replay/Gamesetmatch, slates 601 / 600
  / 601, next rounds. Match starts without BLACK_LOG: 5 of 5 clean (3 plain +
  the 2 GPU runs), each with the one `[glq] job ... handed` line, no FATAL /
  WARNING / watchdog, no `health` line. GPU pair (FIXED_HEAD, GPU_TIME,
  frames 2100-3000): default 3.8 / 4.1 / 4.3 ms, `LINDBERGH_LOD_BIAS=0` 3.6 /
  3.6 / 3.6 ms (LOD bias ~+0.4 ms), 59.2-60.0 fps both. **Found: FIXED_HEAD
  never acted unattended** (no `head held fixed` line in these runs nor in
  the T3-T5 worker's F_/G_ runs except two): the unworn session stops before
  the game locates a view, so the eyes keep whatever they had. Fixed in the
  working tree (`fixed_head()` also while the session is not running). No
  controller input. env.txt 0, vr.cfg byte-identical. WIP restored.
- **T3-T5 worker, group 2 - STOPPED: controller input during H_def.**
  `H_def` (prize, GPU_TIME, fixed head) logged real controller input from
  frame 3727 (`[cab] buttons 0x5001 ... 0xa010`: stick and shot bits, not the
  script's start taps) and the frame rate fell to ~50 fps from frame ~8900;
  the Quest shell's control bar was the resumed activity afterwards. Taken as
  **worn**: runs stopped by PID, app force-stopped, env.txt 0 bytes, vr.cfg
  byte-identical to the owner's (pulled before), and the **committed fix
  build re-installed** (`scratchpad/VirtuaTennis3VR_fade8ac_glqfix.apk`) so the
  owner does not play the WIP. Battery 85%.
  **T5 committed** (submodule `8004564`, outer: this commit): LOD bias. Fixed-
  head pair F_def / F_lod0 (frame 2300, both eyes): far crowd and boards
  sharper (edge energy crowd 50.3 vs 44.5, boards 29.6 vs 23.5), board text
  steady over 2300-2305 (frame-to-frame change in proportion to the extra
  detail; no shimmer seen). GPU (random pose, so +-0.5 ms noise): default
  4.0-4.3 vs off 3.8-3.9 ms; fixed-head H_def 3.9-4.7 ms; H_lod0 not run.
  **T4 FAILS on the headset**: with the per-eye mask (default) the ground
  shadows of **both players are gone** in both eyes (F_def crops
  `/tmp/vt3q/W/t4_near.png`, `t4_far.png`); `LINDBERGH_VT3_MASK=0` shows them.
  The twin is used (log lines present) but reads no shadow: suspects - the
  sampler2DArray on unit 15 not getting the twin's array (gl4es binds the 2D
  texture; the layered lookup may need `mv_layered` handled at bind for an
  extra unit), the blit sizes (`d->mv_w` 0 before `array_for`?), or the mask
  being in a channel the eye copy lacks. Not committed; needs a debug run
  (e.g. output `lg_mask` as colour). **T3: the dome is not fp 180.** Fill
  lit with fp 180's constants came out black (k0 = k1 = 0, k2 = 1, sun
  0.462 0.383 -0.800, e 50: fp 180 is a sun-glow term, not the sky), and the
  front sky with clouds plus a lavender wedge **stay in Painted and Off**
  (`/tmp/vt3q/W/d2.png`: rows Stadium / Painted / Off, views 0,0 / 0,70 /
  90 / 180 / 60,30 / 120). So the Sky setting's "leave the dome out"
  removes the wrong draw, and the visible backdrop is another program
  (candidates from the frame: 232-246 / 227, 199, 217, 186, 148, 140 -
  skip-bisect queue `scratchpad/q4.sh` written, not run). The dome-matching
  code (dome_note, u_dome) is wrong as it stands and stays uncommitted.
  Working tree after this: T3/T4 WIP + test switches restored on top of
  `8004564` (`ai_docs/wip/`).
- **T3-T5 worker (2026-11-11 evening), group 1** (`/tmp/vt3q/W/*`; helper
  `.../786966e7-.../scratchpad/run.sh` = battery check + repro + summary +
  worn check). Owner's vr.cfg pulled first (`/tmp/vt3q/W/vr.cfg.before`, copy
  `scratchpad/vr.cfg.owner_w`). WIP APK built and installed (copy
  `scratchpad/VirtuaTennis3VR_wip_t345.apk`). **S1 smoke** (Immersive `prize`
  200 s): `[arbprog] ground shadow mask read per eye on unit 15 (16 units)`,
  `[stereo] frame 1949: ground shadow mask per eye, 2064x2208 x2 (game texture
  45)`, `[sky] ... behind the stadium's own sky dome`; 0 `does not compile` /
  `does not link`, no `[glq]` FATAL/WARNING, no watchdog; flow Gamesetmatch
  3166 -> Stats 3262 -> Load 3863 (601), Stats 7462 -> Load 8062 (600), next
  rounds. **Finding: unattended shots are not comparable between runs** - the
  unworn headset's pose differs per launch (anchor yaw -54 vs 2 deg), so the
  frame-2300 pictures and the GPU ms (view-dependent: 3.7-4.3 ms) differed by
  run, not by switch. Added test switches (working tree): `LINDBERGH_XR_FIXED_HEAD=1`
  (host_xr.c: head level at the anchor, facing ahead), `LINDBERGH_VT3_VIEW_TURN`
  list `<yaw>,<pitch>@<frame>/...`, `LINDBERGH_VT3_SKY_AT=<0|1|2>@<frame>/...`,
  `LINDBERGH_VT3_SKY_DEBUG=1` (fill magenta); test APK
  `scratchpad/VirtuaTennis3VR_wip_t345_test.apk` installed. GPU (random pose,
  frames 2100-3000, 60 fps all): default 3.1/4.3/4.3/4.0, LOD_BIAS=0
  2.5/3.9/3.8, MASK=0 2.6/3.7/3.7/3.7 ms - to be redone with FIXED_HEAD.
  Sky: the dome texture is a 2048x512 panorama strip at the top left of each
  stadium's atlas (`S_<court>_B_sk_sky_NY_tga`, DXT1 4096x512/1024, extracted
  to `/tmp/vt3q/W/sky/`): deep blue at its top row, haze + tree line at the
  bottom. The fill was lavender (123,138,200) next to the dome's (72,128,212).
- **Hang fix committed and installed.** Submodule `373c5ae`, outer `2b7d4fe`
  (local, not pushed). Installed: the fix build (fade8ac + 373c5ae, committed
  code only; copy `.../786966e7-.../scratchpad/VirtuaTennis3VR_fade8ac_glqfix.apk`,
  unstripped lib `libmain_glqfix_unstripped.so` beside it). Afterwards the
  T3-T5 WIP was put back on top (stereo.c, arbprog.c, quest/gl4es.patch,
  `../deps/gl4es` re-applied and libGL rebuilt; build-mac rebuilt) and checked
  byte-identical to `ai_docs/wip/` (the diffs did not move: the fix touches
  other files). Headset: app stopped, env.txt 0 bytes, vr.cfg = the morning's
  copy, battery 74% charging. Next for whoever has the headset: the T3-T5
  run list above (section B on), now on top of `373c5ae`.
- **Phase 2, group 1 (installed clean fade8ac, A2's env: Immersive pinned,
  GPU_TIME, KEEP_ON_PAUSE, `prize` 90 s; `/tmp/vt3q/P2/C*`)**: owner's hung
  pid 17044 force-stopped after a last logcat / vt3.log
  (`.../scratchpad/owner-crash/*_final*`); installed libmain sha 49935863 =
  clean fade8ac; battery 72%, env.txt 0, vr.cfg = morning's. C1 ok (to
  4390), **C2 SIGSEGV on the GL worker at frame ~2009 in `cls()`
  (gl_thread.c:417) called from `worker` with a garbage record id - a
  corrupted ring record**, C3 ok (to 4201): 1 of 3. GPU page faults in all
  three logcats. Next: FEEDCAM=0 x3.
  **Group 2, `LINDBERGH_VT3_FEEDCAM=0`, same build/env (`P2/F*_nofeed`)**:
  3 of 3 clean (to 4500 / 4700 / 4580), no feed lines. **Fix build**
  (fade8ac + `glq-second-writer-fix.diff` only; WIP backed up in
  `.../scratchpad/wip_backup/`, `../deps/gl4es` reset to the committed
  patch and libGL rebuilt; libmain has `foreign_job`, no WIP gl4es symbols;
  copies `.../scratchpad/VirtuaTennis3VR_fade8ac_glqfix.apk`,
  `libmain_glqfix_unstripped.so`) **installed**. Next: 5 verification runs.
  **Group 3, fix build, Immersive stands on, no BLACK_LOG, `prize` 80 s
  (`P2/V*_fix_*`)**: V1-V3 owner-style (no GPU_TIME, no KEEP_ON_PAUSE), V4-V5
  A2's env (GPU_TIME + KEEP_ON_PAUSE): **5 of 5 clean**, each to ~4450-4580,
  no watchdog / signal / `[glq] FATAL` / WARNING, each with the one `[glq]
  job ? from thread ...: handed to the game thread's next call` (Android's
  dladdr names no static function). GPU page faults in every logcat. Next:
  GPU pair (G1 stands on / G0 off, GPU_TIME, 170 s), full `prize` Immersive
  and Classic.
  **Group 4, fix build (`P2/G*`, `P2/P_*`), all with the one handoff line,
  no watchdog / signal / FATAL / WARNING.** Stands GPU cost (the owed
  matched pair, GPU_TIME + KEEP_ON_PAUSE, no shots / black log), frames
  2100-3000: stands on 2.7 / 3.6 / 3.7 / 3.6 ms (90% 4.2-5.1), off 2.7 / 3.3 /
  3.7 / 3.3 ms (90% 4.7-4.8; one 38.7 ms timer artefact) - **about +0.2 ms,
  inside the +1.5 ms budget**; `[perf]` 59.5-60.0 fps both. **Immersive
  `prize` 330 s** (FLOWLOG, KEEP_ON_PAUSE): Game 1979 -> Gamesetmatch 3108 ->
  Stats 3173 -> Load 3532 (first slate cut by the script's `z` taps), three
  more matches with slates 7042 -> 7642, 11208 -> 11809, 15295 -> 15896 (600
  each), round 5 at 16652; 18,020 frames; no `health` line. **Classic
  `prize` 330 s** (FLOWLOG, BLACK_LOG): Winlose 2794, Replay 4804,
  Gamesetmatch 4860, Stats 4915 -> Load 5120, next round. The slate was 205
  frames because someone handled the controller during the run (it opened
  the panel, clicked Mode - "pinned by env.txt" - and pulled the trigger,
  `[cab] buttons 0x10` 5017-5117: a shot button skips the slate, as in the
  original). Black frames only the game's own (0-1, 1947-52, 5120-21,
  5362-63). vr.cfg afterwards had been re-saved in normalised form
  (`immersive.stand_y` dropped, `sky on` -> `stadium`: the same settings),
  put back byte for byte from the morning's copy. GPU page faults
  (hypothesis 3) in **every** logcat - clean build, FEEDCAM=0, fix build and
  **Classic** - not Immersive-specific; not chased. Battery 71%, env.txt 0,
  app stopped. Next: commit, then restore the T3-T5 WIP.
- **ROOT CAUSE FOUND (macOS, by the new writer check): a second thread writes
  the GL queue.** Virtua Tennis 3 runs `camera::gameRoutine` on one of its
  own worker threads (not the main thread). In Immersive, world mode's camera
  feed (`hle_sega.c` `h_vt3_game_routine`, LINDBERGH_VT3_FEEDCAM, on by
  default) calls `vt3_note_projection` -> `glq_job(vt3_cam_job)` from there,
  **every frame from the match's first frame (~1897) on** while the game has
  not set the world camera itself - concurrently with the main thread's
  ~17,000 GL records a frame. `gl_thread.c`'s ring is single-writer
  (`g_head_mine`, `ring_take`/`ring_put` unlocked): two writers overwrite each
  other's records / sizes, the worker then takes a wrong size and runs old
  records again (A2b: its camera jobs' freed Vt3Cams printed as garbage in
  a repeating cycle, double frees -> SIGSEGV in calloc; owner / A2: the
  worker spinning through stale records at 100% CPU, main thread waiting in
  `glq_wait` forever). Backtrace (ASan build, macOS Immersive):
  `glq_job <- h_vt3_game_routine <- dispatch <- L_080A992A <- L_080A529E <-
  L_08176EA0 ...`, thread != the queue's writer, 20+ times in the first 20
  frames of the match. Classic: 0 (the feed is Immersive only) - why Classic
  never crashed. Stands on only made a collision likelier (more records per
  frame); A3 (stands off) fed 40 x 60 frames and got lucky. Predates fade8ac
  (the feed exists in 77875a4: D_nocut hung too).
  **Fix (working tree, `gl_thread.c`, uncommitted, not yet on the headset):**
  `glq_job` from any thread but the queue's writer no longer touches the
  ring: the job is kept in a small locked list (`foreign_job`, 256) and the
  writer queues it at its next GL call or job (`FOREIGN_FLUSH` at the top of
  `glq_hook` / `glq_job`; one acquire load per call); such a job returns 0
  (cannot be waited for). A job queued from the worker itself runs inline.
  GL calls from another thread are still only warned about (`[glq] WARNING`;
  none seen). Also fixed: lost wakeup - the worker going idle now wakes the
  game (`wake_game()`), which could otherwise sleep forever in `ring_take`
  waiting for room when the ring filled with plain calls (big uploads).
  **Checked on macOS** (ASan, Immersive, GL thread, 200 s): one line `[glq]
  job vt3_cam_job from thread ... handed to the game thread's next call`, no
  WARNING / FATAL, the feed still works (`world camera built` each 60
  frames, projections arrive), flow Load -> Game 1928 -> change of ends ->
  Gamesetmatch 3124 -> Stats 3212 -> Load 3573 -> next match 3848, 11,611
  frames at 60 fps, ASan clean. Safety copy of the fix + diagnostics:
  `ai_docs/wip/glq-second-writer-fix.diff` (gl_thread.c, crash_report.c;
  separate from the T3-T5 WIP, which is unchanged). `build-mac` was rebuilt
  with the working tree (WIP + fix). **Phase 2 (headset):** build fade8ac +
  this diff only (stash stereo.c / arbprog.c / gl4es.patch WIP), reproduce on
  the installed clean fade8ac first, then >= 5 Immersive stands-on runs to
  ~2600 (the fix build should print the `[glq] job vt3_cam_job ... handed`
  line once and no `[glq] FATAL`), `LINDBERGH_VT3_FEEDCAM=0` on the clean
  build as the discriminating test (should not hang), full `prize` both modes.
  Other findings, not this bug: gl4es multiview patch keeps `gltexture_t*`
  in `mv_copy[64]` after `glDeleteTextures` frees it (dangling read in
  `mv_framebuffer_left`, the texture's `mvarray` leaks, slots never freed);
  GPU page faults (UCHE BR_SP) from boot frame ~1070 in every Quest log.
- **Crash investigation (worker "match-start hang"), Phase 1, step 1 - evidence.**
  Copies: `/private/tmp/claude-501/-Users-chrishelms-Desktop-Claude/786966e7-92df-442c-b205-476a682b88a2/scratchpad/owner-crash/`
  (owner's worn hang: vt3.log, logcat.txt, `logcat_live_*.txt` taken with the
  process still hung). Unstripped lib of the installed clean `fade8ac` APK:
  `build-quest/vt3/libmain.so` (build id c3bfd3f4..., same as the APK's).
  (1) A2b's SIGSEGV symbolizes to GL thread `worker -> stereo exec -> th_glBegin
  -> gl4es_glBegin -> alloc_renderlist -> calloc` (heap already corrupt).
  (2) A2b's garbage `[arbprog] game projection` lines come from `vt3_cam_job`
  (the Vt3Cam the game thread mallocs, the GL thread prints and frees): the
  garbage words are 64-bit tagged host heap pointers (`0xb4000078_471d40cd`
  ...), zeros, and int runs 0..20 - other host allocations' contents - and the
  10 lines repeat a fixed cycle (garbage, zeros, ints, pixel camera, world
  camera, garbage, zeros, pixel, world): the GL thread ran the same set of
  camera jobs again and again with pointers to freed blocks - the pattern of
  the worker replaying old ring records (use-after-free + double free ->
  calloc crash), not of one block overwritten once.
  (3) Owner's worn hang (no env, vr.cfg immersive) hung at frame **2328**, not
  2003 (so not the scripted `z` tap): main thread in `glq_wait` from
  `mirror_call` (gl_thread.c:922, the first map's size job) from
  `TScene::Batch::updateDynamic`; guest threads idle on conditions. Live
  process (pid 17044, read-only, no root, not debuggable - no stacks):
  thread **17180 = the GL worker** (it made the OpenXR BeginFrame calls) is
  **state R, ~1 CPU (55% user / 45% kernel), no page faults, RSS flat** -
  spinning, not blocked or dead. VrApi FPS lines stop 14:34:56.
  (4) **GPU page faults** (`kgsl-3d0: GPU PAGE FAULT ... FAULTING BLOCK: UCHE:
  BR_SP`, ~900/s, rate-limited to 10 lines / 5 s) in every VT3 process with
  a saved logcat (A2b pid 12571, V2 pid 16039, owner pid 17044), starting at
  boot frame ~1070 (right after `fragment program 21/22 ... units 0x8000
  compare depth`), long before the match - a shader reading an unmapped GPU
  address. Separate pre-existing fault; whether Classic has it is unknown.
  (5) macOS sanitizer builds (`build-mac-asan`, `build-mac-tsan`: runtime
  `src/runtime/*.c` + `games/vt3/src` instrumented, the lifted code reused
  from build-mac's objects; config via CMAKE_PROJECT_INCLUDE
  `.../786966e7-.../scratchpad/san/san.cmake`, runner `san/mac_run.sh`).
  `LINDBERGH_GL_THREAD=1` (the Quest's queue) **ASan clean**: Classic `prize`
  240 s (13,700 frames, several matches) and **Immersive with the whole
  stadium** 120 s (6,860 frames; 17,324 queued calls and 29 mirrored maps
  per frame - the Quest's numbers). Immersive does run on macOS now. So the
  shared host code (queue, mirror, hle_sega hooks, arbprog/stereo desktop
  paths) does not overrun the host heap there: the fault is in Quest-only
  code (gl4es + its multiview patch, stereo.c/arbprog.c `LINDBERGH_GL4ES`
  paths, host_xr.c) or timing that only the Quest has. TSan build dies at
  load (SIGKILL, before the queue starts; only benign stats races in
  `guest_trace_dispatch` / `gmalloc` reported) - not pursued.
  (6) Diagnostics added (working tree, `gl_thread.c`, `crash_report.c`): the
  worker checks every record (size, kind, inside the ring, not past the head)
  and aborts with `[glq] FATAL: bad record ...` and its last 16 records
  instead of replaying old ones; GL calls / jobs from any thread but the
  queue's writer are logged `[glq] WARNING: ... from thread` (0 on macOS
  Classic and Immersive); the hang watchdog now prints `[glq] hang: head ...
  tail ...` + the record the worker is in, and signals the GL worker for its
  host stack.
- **V2** (unpinned, `LINDBERGH_VT3_VIEW_TURN=180`, `/tmp/vt3q/V2_unpinned_turn180`):
  behind the viewer the near-end stand is drawn (lower seats, upper tier with
  covered boxes, Düsseldorf Open boards, light mast) - the near-end lower
  seats have no crowd cards (the known open item). Stopped here for the
  conductor: app force-stopped, env.txt 0 bytes, vr.cfg identical to the
  morning's, battery 33% charging. Installed: clean `fade8ac`. Run list
  position: A1 done (pass), A2 crashed twice (see below), A3 done; continue
  at A2 (investigate the crash) / A4. Working tree still holds the T3-T5 WIP
  (identical to `ai_docs/wip/`), `../deps/gl4es` at the WIP patch.
- On the clean `fade8ac` install: **V1** (`round0`, `LINDBERGH_VT3_IMMERSIVE=1`
  only, script defaults otherwise; `/tmp/vt3q/V1_imm_r0`): `[sega] ...
  stadium draw wrapped (Immersive: upper stands, both ends and the sky dome
  drawn)`, `[vt3] frame 1765: the whole stadium drawn (5 trees ...)`; shot
  2600 (clay court) shows the red upper tiers both sides, light masts,
  buildings at the far end (2300 was a point close-up - cutaways pinned on).
  **V3 unpinned** (`LINDBERGH_VT3_IMMERSIVE=` and the other three pins empty,
  so the owner's vr.cfg decides; `/tmp/vt3q/V3_unpinned_r0`): `[world] mode
  immersive (vr.cfg) ... sky stadium (vr.cfg) ... replays off cutaways off
  (vr.cfg)`, the same two stadium lines; shot 2300 (grass court) shows the
  far-end upper stand with crowd, the light towers and the side stands. Code:
  the only gates are `LINDBERGH_VT3_STANDS` and `world_mode_immersive()`
  (`h_vt3_field_draw`); `immersive.stand_y` is ignored, `immersive.sky on`
  reads as stadium - nothing in the owner's vr.cfg can hide the stands.
  Battery 30 -> 32%. V2 (unpinned, turned 180) running.
- Owner wore the headset during A3 and saw no upper stands - A3 was the
  `LINDBERGH_VT3_STANDS=0` run (stands off on purpose). A3 itself (STANDS=0,
  same env as A2): ran through, no crash, GPU 2.6-3.8 ms in the match.
  Installed APK was from 12:55 headset time (PST) = 13:55 MST, before the
  `fade8ac` commit (14:12): an earlier iteration. **Now installed: a clean
  build of submodule `fade8ac` / outer HEAD** (WIP stashed, `../deps/gl4es`
  put back to the committed `quest/gl4es.patch` and rebuilt; installed 14:20
  PST; copy `.../786966e7-.../scratchpad/VirtuaTennis3VR_fade8ac_clean.apk`).
  Afterwards the WIP was popped and checked byte-identical to `ai_docs/wip/`,
  and `../deps/gl4es` put back to the WIP patch and rebuilt. Next:
  verification runs V1 (Immersive pinned, round0, shots), V2 (turned 180),
  V3 (unpinned: vr.cfg decides).
- A2 (STANDS=1, GPU_TIME, KEEP_ON_PAUSE, `prize` 170 s; `/tmp/vt3q/A2_stands1`)
  **hung at frame 2003** (54 frames into the first match, just after a
  scripted `z` tap and a link of fp 184): `[watchdog] frame 2003 has not
  advanced for 10 s`; the game's main thread waits in `glq_wait` (from guest
  0x08191DEC), i.e. the GL thread never finished the frame - the GL thread's
  own stack is not dumped by the watchdog; logcat had rolled. First hang seen
  with `fade8ac` (R2 / R3 had the same switches and ran through). Retrying
  once as A2b to tell a flake from a pattern.
  **A2b (same env): crashed at the same place** - SIGSEGV on the GL thread
  (`no CPU registered`) inside libc `calloc` (heap corruption), frame ~2003,
  right after `[arb] frame 2002: fragment program 184 (vertex 185) linked`;
  just before it `[arbprog] game projection:` printed garbage (50689.5 /
  40256.8 ..., zeros, and the integers 0,1,2,... read as floats) - memory
  that holds program parameters was already overwritten. So: a memory
  corruption at the first match's ~frame 2000 (the menu script's `z` tap at
  2000), 2 of 2 with STANDS on, no BLACK_LOG, KEEP_ON_PAUSE on. R2 (same plus
  BLACK_LOG, which makes the GL thread wait for the GPU every frame) ran
  through. Not new with `fade8ac` alone: in the old scratchpad `D_nocut`
  (77875a4, CROWD_CUT=0, SHADOW_SCALE=4) hung at 4241 and `F_skip180`
  (`fade8ac` test build, SKIP_FP=180) took a SIGSEGV - both ignored at the
  time. Looks like a race between the game thread (running a frame ahead) and
  the GL thread over memory a queued GL call still points at; the wider
  stadium may only make it likelier. **The `fade8ac` build is not
  regression-clean until this is understood.** Next: A3 (STANDS=0, same env).
- A1 done (installed `fade8ac`, `/tmp/vt3q/A1_classic`, battery 20 -> 21%):
  Classic `prize` 330 s **passes**: `[world] mode classic (env)`, Winlose 2695,
  Replay 3463, Gamesetmatch 3532, Stats 3770 -> Load 4372 (602), Stats 8763 ->
  Load 9363 (600), third match running; no `health` line with
  KEEP_ON_PAUSE on, 0 slow reads. Black: 0, 1947, 4372 / 4614, 9365 / 9607
  (LoadLoop and load -> match, the game's own) **plus 9612** (4 frames into
  the third match's EntranceLoop, Classic's fly-by; not at a cut in play). No
  older Classic BLACK_LOG run exists to compare - check on the next Classic
  BLACK_LOG run (F1) whether 9612-like frames recur.
- Review of the uncommitted T3-T5 code (no headset). One defect fixed: the
  LOD bias (T5) was on for every gl4es game (hotd4, lgj, gse would have had
  their fragment shaders changed and the bias applied); now default on only
  when `world_mode_capable()` (VT3, both modes), `LINDBERGH_LOD_BIAS=1|0`
  forces. Checked and fine: the layered copy (`gl4es_multiview_copy_layers`)
  saves / restores read and draw framebuffers and scissor (a blit needs no
  more); T3 / T4 are gated on `world_mode_immersive()` (Classic and other
  games untouched; `mask_copy` returns before any GL call); the new shader
  text depends only on per-run statics plus the `scr` bit already in the
  link key, and the disk cache is keyed by the GLSL text, so variants cannot
  mix; sampler `sl_<mask unit>` gets its unit by name at link; kill switches
  `LINDBERGH_VT3_MASK=0`, `LINDBERGH_LOD_BIAS=0`, `LINDBERGH_VT3_DOME_FP=0`
  give back `fade8ac`'s shader text / draws (Stadium sky already drew the
  painted sky behind the dome in `fade8ac`). Risks left (headset will tell):
  if the game's program used the mask unit itself (unit 15, or 7 if gl4es
  reports 8 units) its shader would fail to compile; the twin assumes the
  frame's first whole-screen copy is the mask in every world frame (replay /
  slate frames not looked at). Cosmetic: in `multiview.h` the two new
  declarations sit between `gl4es_multiview_copy`'s comment and itself.
  Note: Classic logs `stadium draw wrapped (Immersive: ...)` too (fade8ac;
  the wrap is gated per call, text only). Builds: `ninja -C build-mac` OK;
  unit tests OK (all but test_xr_actions); macOS Classic `prize` 200 s
  (FLOWLOG): Winlose 2501, Replay 3322, Gamesetmatch 3392, Stats 3482 ->
  Load 4083 (601), Stats 8513 -> Load 9114 (601), next rounds - as
  documented; Quest APK built (14:53, not installed). `quest/gl4es.patch` ==
  `git -C ../deps/gl4es diff` and applies cleanly to gl4es `1891af3`.
  Safety copy: `ai_docs/wip/` (README + both diffs). Headset back on adb
  at 18% charging, env.txt 0 bytes, vr.cfg identical to the morning's backup.
- Harvest of the cut worker's runs (installed `fade8ac`; outputs in the
  old scratchpad `.../123aec40-.../scratchpad/runs/`). **R1 Classic `prize`:
  did not run** (env pushed at 14:44, no vt3.log - the headset dropped; battery
  had read 24 -> 18 -> 12). **R2 Immersive `prize` 330 s (BLACK_LOG, FLOWLOG,
  GPU_TIME): completed.** `[world] mode immersive (env) ... sky stadium
  (vr.cfg) shadow 2048`, `[sega] ... stadium draw wrapped (Immersive: upper
  stands, both ends and the sky dome drawn)`, the usual other `[sega]` lines.
  Flow: Load 1703 -> Game 1979 -> change of ends 2464 (cutaway left out) ->
  Gamesetmatch 3179 -> Stats 3262 -> Load 3864 (**slate 600**) -> round 2
  match -> Gamesetmatch 7173 -> Stats 7410 -> Load 8010 (**600**) -> round 3
  match to Gamesetmatch 11286 when the run ended. Black log: frames 0, 1185
  (boot black after the white logo), 1947 (load -> match), 3865 and 8013
  (LoadLoop) - the game's own (the same set as pre-`fade8ac` runs: 0, ~1065,
  1947, LoadLoop); **none at the cuts** (change of ends, game set and match).
  No `[sega-api] health` line (only printed when something went wrong) - but
  the run lacked `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1`, so the mixer was paused
  ~2 s in: audio health is **not** proven by it. **R3 `LINDBERGH_VT3_STANDS=0`
  170 s (GPU_TIME): completed** (`stadium draw wrapped (... court-camera cut
  kept)`): match frames 2400-3000 GPU 3.4 / 3.7 / 3.4 ms (90% 4.7-5.0),
  59.4-59.8 fps. **R2's frame rate (~33 fps, "submit" ~20 ms) and its GPU
  numbers (5.1 / 7.4 ms) are not usable for the stands cost**: BLACK_LOG reads
  the eye back every frame (waits on the GPU); a pre-`fade8ac` BLACK_LOG run
  (old scratchpad `w2/t2_off`) shows the same ~35 fps. So the **stands GPU
  cost is still owed** (a STANDS=1 run with the same env as R3, no BLACK_LOG).
  The isolated 40-45 ms single-frame `[gputime]` readings appear in both R2 and
  R3 (timer artefact, as before). Satisfied for `fade8ac`: Immersive `prize`
  flow, slate, next rounds, no black frames at cuts. Still owed: Classic
  `prize` regression, stands GPU cost (matched pair), audio health with
  KEEP_ON_PAUSE, venues rounds 1 / 2, view turned 180 and pitched 70.
- Headset back (24% battery, USB charging slowly - stop below ~12%); the
  conductor emptied env.txt; vr.cfg unchanged. Running on the installed
  `fade8ac` build: R2 Immersive `prize` 330 s (BLACK_LOG, FLOWLOG, GPU_TIME),
  R3 `LINDBERGH_VT3_STANDS=0` 170 s (GPU baseline), R1 Classic `prize` 330 s.
  Static finding: `CAudience2DManager::draw` (0x08090096) has no camera-end
  rule (trees 0..level-1, then the standing tree), so the empty near-end
  seats on Ita3F are most likely data (the broadcast camera sits at z ~ -324,
  Ita3F's 1F cards span z -160..306). Next: venues rounds 1/2 incl. turned
  180, then install the working-tree build (T3-T5) for sky / mask / LOD runs.
  The working-tree code (stereo.c, arbprog.c, quest/gl4es.patch) is
  described below and under "Uncommitted" in the state table.

**2026-11-11 (build worker, crowd/stands/shadow/LOD tasks) - read first.**
The owner unplugged the headset to charge it in the middle of an unattended
perf run (`P_stands0`). When it comes back, before anything else (done by the conductor at reconnect):
1. `adb shell cat /sdcard/VirtuaTennis3/env.txt` - it was left holding the cut
   run's env (`LINDBERGH_AUTOSTART=1`, scripted `LINDBERGH_KEYS`,
   `LINDBERGH_VT3_IMMERSIVE=1`, `LINDBERGH_VT3_STANDS=0`, ...): empty it
   (`adb shell "printf '' > /sdcard/VirtuaTennis3/env.txt"`) and
   `adb shell am force-stop org.lindbergh.vt3.vr`.
2. vr.cfg: the owner's file (backup of the morning's copy in the worker's
   scratchpad `vr.cfg.orig`; `mode immersive`, `immersive.stand_y 1.5`,
   `immersive.sky on`, `refresh 120`, ...). No run changed it.
3. Installed APK: a **test build** (submodule `fade8ac` state + T3-T5 code is
   NOT in it; it is the `fade8ac` code with the old `sky_on`), installed for
   the T2 captures and never regression-run. Either run the regression below
   and keep it, or put back the last regression-passed APK (`77875a4`;
   `adb install -r` of a build of `77875a4`, or the pulled copy
   `installed_77875a4.apk` in the worker's scratchpad).
Then the owed checks, in order (all unattended, `scripts/vt3-repro.sh`, Immersive
pinned with `LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=0 LINDBERGH_VT3_CUTAWAYS=0`;
**pass each LINDBERGH_ variable as its own word** - a zsh `$G` holding two
assignments reaches env.txt as one line):
- T2 cost: `prize` 160 s, `LINDBERGH_GPU_TIME=1 LINDBERGH_GAME_SHOT=99999,1`,
  with `LINDBERGH_VT3_STANDS=0` and without; compare `[gputime]` / `[perf]`
  over frames 2100-3000 (budget: +1.5 ms, steady 60 unworn). FRAMEMAP and
  game shots break the GPU timer (5117 ms readings) - leave them out.
- T2 venues: `LINDBERGH_VT3_ROUND=1` and `=2` (and more if cheap) with
  `LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1`, plus
  `LINDBERGH_VT3_VIEW_TURN=180` and `=0,70`: floating cards, stand behind,
  doubles / z-fighting, roofs at the far plane.
- T3 (uncommitted code): `LINDBERGH_VT3_SKY=1|2|0` each with
  `LINDBERGH_VT3_VIEW_TURN=0,70` and `=180`: Stadium = painted sky filling
  above / behind the dome, the seam where the dome's top edge meets it;
  Painted = no dome; Off = neither (a blue band seen with fp 180 skipped -
  find which draw that is if Off must be clean). Side by side for the owner.
- T4 (uncommitted): `LINDBERGH_VT3_MASK=0` vs default, crops of the near
  player's shadow both eyes (`LINDBERGH_SHOT_BOTH=1`), `[stereo] ... ground
  shadow mask per eye` and `[arbprog] ... unit N` lines; GPU ms; replays and
  cutaways on (`LINDBERGH_REPLAYS=1 LINDBERGH_VT3_CUTAWAYS=1`) - the cut's
  cross-fade and depth of field unchanged; Classic unchanged.
- T5 (uncommitted): `LINDBERGH_LOD_BIAS=0` vs default, crop of the far-end
  crowd and the ad boards; check board text does not shimmer
  (`LINDBERGH_GAME_SHOT=<f>,1,1` several consecutive frames).
- Regression before keeping any build installed: `prize` Classic and
  Immersive to the slate (~600 frames) and the next round, `LINDBERGH_BLACK_LOG=1`
  (no new black frames at cuts), `[sega-api] health` clean, then env.txt empty.

1.-4. Done 2026-11-11 (audio worker): env.txt was emptied by the conductor;
   vr.cfg checked unchanged before and after (`mode immersive`, `replays on`,
   `classic.cutaways on`, `immersive.replays off`, `immersive.cutaways off`,
   `refresh 120`); the APK with `3a713ff` + `fa83fd6` + `77875a4` is
   **installed**; regression passed: Classic `prize` slates 3988 -> 4589,
   8994 -> 9594, 13979 -> 14580 and Immersive `prize` 7534 -> 8135 (601
   frames each; Immersive's first slate 3173 -> 3533 is cut by the menu
   script's `z` taps to 3600), next rounds start, `[world]` / `[sega]` lines
   as before.

**Music: what the owner should listen for (worn, this APK).** Music in
menus and between points should now play continuously. Before, it jumped
about every third of a second. If it still sounds wrong, run this with the
owner wearing the headset at their settings (120 Hz). Nothing changes vr.cfg:
```
D=/sdcard/VirtuaTennis3/vt3_Lindbergh
printf 'LINDBERGH_SEGA_METER=1\nLINDBERGH_AUDIO_DUMP=%s/mix.wav\nLINDBERGH_AUDIO_DUMP_STREAMS=1\n' $D | adb shell "cat > /sdcard/VirtuaTennis3/env.txt"
adb logcat -c; adb shell am start -n org.lindbergh.vt3.vr/org.lindbergh.vt3.VirtuaTennis3VR
# owner plays a match (~5 min), then:
adb shell am force-stop org.lindbergh.vt3.vr
adb pull /sdcard/VirtuaTennis3/vt3.log; adb pull $D/mix.wav; adb pull $D/mix.wav.streams.wav
adb shell "printf '' > /sdcard/VirtuaTennis3/env.txt; rm -f $D/mix.wav $D/mix.wav.streams.wav"
grep -E 'mixing at|health|slow read|\[perf\]' vt3.log
.venv/bin/python scripts/wav_glitches.py mix.wav.streams.wav --from 30
```
Pass: every `health:` line `starved 0 events`, `device 0 late` (an
occasional late block with gap max < 43 ms is inaudible: OpenSL holds two
blocks), `stream lead min` >= ~250 ms, no `[io] slow read`; streams clicks
well under ~150 / min (the decoder's own transients give ~100). Fail and
where to look: `starved > 0` -> refill stalled (slow reads -> the file
thread; none -> the ADX vsync thread's CPU time under the worn load);
`late > 0` with gap > 43 ms -> the SDL audio thread is starved (try a
2048-frame block for Android in `open_output`, or AAudio via
`SDL_AUDIODRIVER=aaudio`); limiter `% over 1.0` high while the owner hears
distortion -> lower VT3's `sound_gain` (game profile; LGJ uses 0.4).
`LINDBERGH_SEGA_POS_WRAP=0` brings the old skipping back for an A/B by ear.
Unattended runs need `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1` (else the mixer stops
~2 s in) and are paced at 60 by the clock, so they say nothing about 120 Hz.

5. Owner's report after a full match worn on 2026-11-11 (on the build
   *before* `1b1988b`; "we are getting close to a first release"; all
   progress and research to be written to docs):
   - "button A is slice and button B is not mapped" - addressed in
     `1b1988b` (trigger top spin, A/X slice, B/Y lob). Owner to confirm worn.
   - "quick 1s camera changes after every point" - addressed in `1b1988b`
     (steady camera with Point cutaways off). Owner to confirm worn.
   - Audience stretched and low resolution; upper bleachers missing, crowd
     floats in mid air - the upper stands exist and are now drawn
     (`fade8ac`), stretch removed; the low resolution part is the LOD bias
     (uncommitted T5). Owner to see worn once 3.1 is done.
   - Shadows look low resolution (Immersive, High 2048) - it is the ground
     shadow's screen mask (confirmed: unchanged at 1024 vs 4096); per-eye
     mask written, uncommitted (T4), owed on the headset.
   - Music plays skipping / not clean - skipping FIXED (`fa83fd6`, the
     loop-end position bug; measured on macOS and Quest), owner to confirm by
     ear; possible limiter distortion in loud moments left for his ears.
     Procedure below.

### 3.1b Open bugs
- **T14** point-start glitch in VR (backlog Bugs): being traced in the T13
  smoke run (every-frame shots round two point starts).

### 3.2 Crowd cards above the side stands (Immersive) - fixed by the real stands
Superseded (2026-11-11): the floaters stood on the hidden `GAME_NO` tiers;
`fade8ac` draws them, and the crowd cut (which cut stadium meshes, not
cards) is removed. Owed: other venues (3.1). Open: the near end's empty
lower seats seen with the view turned 180 deg on Ita3F (crowd doc, Outcome).

### 3.3 Live mode switch – Quest-side steps (design in section 4)

### 3.4 Scoreboards in the scene (design in section 5)

### 3.5 Camera work (guide section 8.2) – not designed yet
Head-tracked offset on the game camera, then chosen cameras (behind player,
first person, umpire). Needs the owner's direction on which cameras first.

### 3.6 Small / unlooked-at
- Light-blue band along the bottom of some Immersive frames (game-set-and-match
  camera ~frame 3000, round-2 court ~5200 in `prize`). Not checked against
  older builds.
- In one replay (frame ~3200) a large see-through rectangle showing the live
  picture hung in front of the net – probably the stadium video board from a
  close replay camera. Not confirmed.
- Attract demo: after the first demo match, later ones show no `usrAc*` flow
  lines (other loops?).
- Defaults for Camera closer (20 m), Step back (6 m): owner's call, worn.
  (Stand height is gone: the real stands are drawn.)
- macOS start-up screen; `tests/test_xr_actions.py` does not compile on this
  Mac (OpenXR header path).
- Not verified worn, ever: 72/90 Hz frame rate, `LINDBERGH_XR_FAKE_YAW`
  checks, real button presses and the lob, the panel's trigger clicks.

## 4. Design: live Classic / Immersive switch (remaining steps)

### 4.1 Two traps
- **Classic is flat only by accident.** Without the camera hooks,
  `g_game_world_ok` is 0, `arb_env_projection` reads crowd/banner matrices as
  lenses of 100-320 (`keep_shape` 0), so `g_lens_seen` > 8 and `g_flat` = 1.
  Installing the world hooks in Classic gives the real lens (3.2): Classic
  would become a 3D window. Force flat explicitly:
  `g_flat = flat_all || (world_mode_capable() && !g_im) || ...` in
  `stereo_frame_begin`.
- **Entering Immersive without a reset gives black frames** (in Classic fb 0
  is the HUD target, so `g_scene_draws` is 0 and `g_menu` goes 1 after 120
  frames) – the same mechanism as the black frames at cuts.

### 4.2 Hooks: install whenever the game is world-capable, gate per call
| Hook | Change |
|---|---|
| `camera::gameRoutine` (`h_vt3_game_routine`) | Feed only when `feed_env && world_mode_immersive()`; always record `g_vt3_camera` |
| `camera::initUva` | Skip modes 4/8 only if env is 1, or env unset and game mode Immersive. Keep the 4/8 test (skipping all ended the slate in 4 frames) |
| `_sCamera::isVisible` | Always the wrap; `h_vt3_is_visible` handles cull modes 0/1/2 and calls through in Classic |
| `_sRender::setProjectCameraMatrix` (`h_vt3_proj_cam`) | Always post the camera (fresh `g_game_world_*` at a switch); harmless in forced-flat Classic |
| `hud::getScreenPosFrom3DPos` (`h_vt3_screen_pos`) | If anchor off (not Immersive) and SERVELOG off: call the original and return |

`g_replays`, `g_cutaways`, `g_arcade_overlays` hooks are already always
installed and live-safe.

### 4.3 Cached statics that must read the latched mode
GL mode (`world_mode_drawing_immersive()`): `stereo.c` capture `keep` static
(~1933), "fb 0 never the HUD target" (~2036), `sky_on`, `stereo_vt3_camera`
static `on` and the cut block in the draw path (~1913); `arbprog.c` decal
offset static `du` (~2433), `keep_shape` (~3208).
`eye_projection`'s `static deep`: pass `deep` as a parameter – GL mode from GL
callers, game mode from `stereo_vt3_hud_anchor` and `stereo_vt3_cull_planes`.

### 4.4 Shaders: Option A (recommended) – one program set
`vt3_screen_fix()` and `vt3_crowd_prog()` test capable + env, not the mode.
Per-draw uniforms are already gated by `stereo_draw_world()` (`!g_flat &&
WORLD`), so a world-feature program in a flat frame draws like Classic's. No
relink, no hitch. Classic's first run rebuilds its disk shader cache once.
Option B (a world bit in the `link_pair` key) only if A measurably slows
Classic: ~100+ pairs relink at the first switch (hundreds of ms from disk,
seconds from scratch); prewarming is impractical (`scr` / `cmp2d` depend on
bound textures).

### 4.5 Switch point and reset
`world_mode_frame()` (game thread, before `glq_job(frame_gl)`) latches the
game mode, fires the callback (register it in `hle_sega.c`): set `g_replays`,
`g_cutaways`, `g_arcade_overlays` from `world_mode_*()`, then post the mode
through the GL queue. `stereo_frame_begin(N+1)` applies it first, then resets:
- `g_hud_fb = g_hud_fb_next = ~0u`
- `g_menu = 0`, `g_menu_frames = 0`, the `world_frames` static (make it
  file-scope)
- `g_zoom_frames = 0`, `g_lens_seen = 0`
- `g_vt3_flat_next = -1`, `g_vt3_cam_mode = ~0u`, `g_vt3_cam_long = -1`
- entering Immersive: `g_vt3_cut_from = g_frame`, `g_vt3_cut_until = g_frame + 1`
  (first eye draw's lens picks flat or world)
- `g_screen_lens` back to 1.732 / 1.732*W/H; `g_cam_n = 0`
- new `arb_world_mode_changed()`: clear `arb_env_projection`'s `good` /
  `have_good`
- keep the screen-copy list/map; culling planes, feed state and sky need
  nothing
- log `[stereo] frame N: world mode on|off (...)`

Shadow quality stays restart-only. The serve meter keeps its latched position
until the next serve after a switch – accept.

### 4.6 Steps (each leaves the game working)
0. Baseline, no code: Classic and Immersive `prize` + `round0` with
   `LINDBERGH_MODE_LOG=1 LINDBERGH_BLACK_LOG=1 LINDBERGH_VT3_FLOWLOG=1
   LINDBERGH_GPU_TIME=1 LINDBERGH_GAME_SHOT=2455,1,0,2475`. Does Classic ever
   log `flat 0` in play? If so, compare shots after step 3.
1. ~~world_mode API~~ – done (`3a713ff`).
2. Cached statics -> latched reads; per-call gates. Proof: step 0 runs
   identical in both modes.
3. Classic forced flat. Proof: Classic `MODE_LOG` only `flat 1` from the match
   on; same shots and black count.
4. Hooks installed whenever capable. Proof: Classic logs the fly-by kept
   (camera mode 4), flow as baseline, no `[override] table full`.
5. Shaders Option A. Proof: Classic GPU time / fps on the **second** run vs
   step 0.
6. GL-side switch + callback (this turns "live" on). Proof on Quest: `round0`
   with `LINDBERGH_VT3_MODE_AT=4000:1,5000:0,6000:1,7000:0`,
   `LINDBERGH_GAME_SHOT=3998,1,0,4004`: one `mode ->` and one `world mode on`
   line per switch, no new black frames, a whole flat frame then a whole world
   frame with sky, no GPU frame over 25 ms. Repeat inside a WinloseLoop, a
   replay, the slate (~3300 in `prize`), menus (~1000) and an EntranceLoop
   frame. Unsure: switching into Immersive during a running fly-by (mode 4/8).
7. Panel live: `host_xr.c` sets `running = world_mode_target()` and `live`;
   log `[xr] mode immersive saved - switching now`. Proof: unit tests; Quest
   with `LINDBERGH_VT3_IMMERSIVE=` empty, **vr.cfg backed up and restored**,
   `LINDBERGH_XR_FAKE_MENU=1 LINDBERGH_XR_MENU_DUMP=1
   LINDBERGH_XR_MENU_CLICKS=4000:0`.
8. Docs.

Do not: change projections to make Classic flat (`GAME_CAM=1/2` blacked out
the picture); add camera hooks (`procMain`, `ab`, `calcParameter`,
`setLook_down` hang); let env pins or the test switch reach `cfg` / vr.cfg.

Worn only: how the switch feels, whether the world faces the right way with
the head turned (maybe set `anchor_pending`), Classic screen placement after
switching back, a real trigger pull on Mode.

## 5. Design: scoreboards in the scene (Immersive)

### 5.1 Owner's decisions (defaults proposed, not yet objected to – confirm)
- Move: score box, stage, serve speed, both name plates, centre POINT/GAME
  plate. Serve meter and 1P marker stay beside the player; change-ends, LIVE,
  credits, WINS, slate stay as they are.
- Two court-side boards left/right just beyond the net line ~5.5 m up, a small
  centre board above the far baseline, turned toward the viewer.
- Size: today's angular size x1.25; panel size row 1.0 / 1.25 / 1.5.
- On by default in Immersive; row "Scoreboard: Court-side / Screen".

### 5.2 Facts (from the binary)
- HUD drawing is deferred: `hud::draw` / `hud::exec` only update state; GL
  draws come later on the main thread, sorted
  (`AbManager::draw` -> `AbkTrunk::ServerDraw` -> `addPrimitive` ->
  `_sScene::execute`). **Bracketing game-thread HUD functions does not bracket
  their GL draws.** Sprite vertices are transformed on the CPU.
- `ab_game_info` = `[[0x85061a4]+0x7c]`. Handle +0x24 (`I_GME_NEW_info_C_TK`):
  speed meter (branches 1, 7), score box (2, 6, 8-0xb), centre board (3, 4, 5,
  0xe, 0xf), stage board (0xc, 0xd). Handles +0x28 / +0x2c: left / right name
  plates (faded by `hud::drawGameInfoPlate` when a player's screen position,
  `getScreenPosFrom3DPos` call returning to 0x0811082C, overlaps). +0xc/+0x10
  markers, +0x14/+0x18 serve meter (already anchored).
- `AbHandle::setMatrix(_sMatrix44)` is 0x818f4c2; default matrix at 0x850e300;
  row-major, translation at [3]/[7]/[11]. Game code never sets a matrix on the
  info handles.
- Today these are pixel-camera draws classed world into fb 0: a 1360x768-unit
  sheet ~846 units ahead of the viewpoint.
- The stadium has its own live boards (`ScoreBoard` objects from
  `field::createTree`, `field` = `[[0x85061a4]+0x64]`, +0x5c score, +0x68
  timer, +0x74 speed) on the far wall, ~2-3 deg wide – unreadable. Enlarging
  them is a later experiment.

### 5.3 Recommended approach: tag by depth, place per group
- Game side (Immersive only): each frame, a wrap of `hud::draw` or
  `ab_game_info::exec` calls `AbHandle::setMatrix` on handles +0x24/+0x28/+0x2c
  with default x `T(0,0,-K_i)` (e.g. K = 16/32/48). The offset rides through
  the CPU vertex transform into every draw of that handle.
- GL side (`stereo.c`): for a draw that `cam_exact`-matched the pixel camera,
  on world frames into fb 0 only, read the vertex clip w (~989.09 + K_i -> tag
  i); split handle +0x24 by NDC x (left = score/stage, right = speed, centre =
  centre board).
- Place: `out = eye_projection(g_game_world_P, ...) * V_bc * A_i`, `V_bc` =
  the queued world camera (`g_game_view`), `A_i` = affine from the group's
  pixel-eye rectangle (K undone) to its world rectangle. Untagged draws, flat
  frames, board off: `out * T(0,0,+K)` – identical to today. Force
  `g_proj_dirty` when the tag changes.
- Stop the plate fade: in `h_vt3_screen_pos`, in board mode, answer a far-off
  position for return 0x0811082C.

Default placement (game units; viewer's end at +z, mirror by camera z sign per
end with hysteresis; viewpoint ~(0, 54, 216)); scale `s = k*D/846` units per
HUD pixel, k = 1.25:

| Board | Content | Centre | Distance | Scale |
|---|---|---|---|---|
| Left | Stage, score box, left plate | (-115, 55, -20) | ~265 | ~0.39 u/px |
| Right | Speed, right plate | (+115, 55, -20) | ~265 | ~0.39 u/px |
| Centre | POINT/GAME plate | (0, 75, -170) | ~387 | ~0.57 u/px |

Settings: `immersive.scoreboard` (+ optional `immersive.scoreboard_size`),
env `LINDBERGH_VT3_SCOREBOARD=0|1`, test `LINDBERGH_VT3_SCOREBOARD_POS`;
touches `world_mode.c/.h`, `xr_world_panel.c`, `xr_settings.c` and their three
tests.

### 5.4 Steps
0. No code: Quest Immersive `round0`, `LINDBERGH_FRAMEMAP=5200`,
   `LINDBERGH_DRAW_LOG=5200` – depth-test / clear / blend state around the
   pixel-camera draws (decides whether true depth is possible).
1. Tag + logging, no visible change (`LINDBERGH_VT3_HUD_TAG=1`,
   `LINDBERGH_VT3_HUDLOG=1`): every info-board draw incl. text and digits
   carries K; meter and markers do not; game shots with/without tag
   pixel-identical (`LINDBERGH_GAME_SHOT=5150,1,0,5160`, `LINDBERGH_SHOT_BOTH=1`).
2. Board transform behind `LINDBERGH_VT3_SCOREBOARD=1`: both-eye shots during
   a serve; `LINDBERGH_VT3_SERVESHOT=2,3700` (meter/marker unchanged); `prize`
   with cutaways and replays on (flat cuts, replay, slate unaffected);
   `LINDBERGH_BLACK_LOG=1`.
3. Plate-fade answer (0x0811082C).
4. Forced depth test for board draws, only if step 0 allows.
5. Panel row, vr.cfg key, tests.
6. Worn: readability, placement, size.

Unverified: text (`_sFontManager::draw`) may not carry the tag (fallback:
split by region); sort order may shift with K; the camera may flip at a change
of ends; replays draw boards relative to the replay camera (may need hiding);
boards may hide the far stadium board. Never classify by lens alone
(`GAME_CAM=1/2` blacked out the picture); never make fb 0 the HUD target;
place on the GL thread with the queued camera.

## 6. Owner's decisions this session
- Replays and Point cutaways stay **two separate panel rows**. In Immersive
  both are off for now (the defaults; the owner's vr.cfg already has them off).
- Push to `fork` only after the owner confirms worn.
- Working style asked for: a conductor plans and checks; each task goes to its
  own Opus 5.5 worker; one worker at a time on the headset and build dirs;
  read-only research can run alongside.
