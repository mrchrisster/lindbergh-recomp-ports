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
| Whole stadium in Immersive (GAME_NO + both ends + dome), stand stretch and crowd cut removed, Sky stadium/painted/off setting, `LINDBERGH_VT3_VIEW_TURN` | `fade8ac` | see `git log` | Quest shots round 0 only; unit tests, macOS; **regression and GPU cost owed** (3.1) |
| **Uncommitted** in the submodule / outer tree: Sky modes drawn (painted fill behind the dome, dome left out for Painted/Off), per-eye ground shadow mask, LOD bias on GLES (`quest/gl4es.patch` regenerated) | working tree | working tree | **never run on the headset**; macOS build, unit tests, Quest APK build only |

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

**Checkpoint log (build worker, newest first):**
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
