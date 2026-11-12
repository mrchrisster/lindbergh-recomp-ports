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
