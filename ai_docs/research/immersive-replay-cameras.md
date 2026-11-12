# Virtua Tennis 3: replays (and point cutaways) in the world in Immersive

Read-only study, 2026-11-11. Nothing built, run or edited. The addresses are
from the original ELF (`~/code/quest_games/vt3/disk0/vt3_Lindbergh/vt3_Lindbergh`,
`objdump -d --x86-asm-syntax=intel -C`). The code references are to
`lindberghrecomp/src/runtime/` at the time of writing.

**Owner's decision (2026-11-11): option A.** You stay where you are, and the
point replays in the stadium in front of you. Options B, C and D are kept
below as one short paragraph each.

## Short answer (for the owner)

Yes, it can be done, and the cost is moderate. Today a world frame is always
drawn from wherever the game's camera is: the headset view is the game
camera's own position, moved forward 200 units ("Camera closer") and back 60
("Step back"), with your head on top of that. The replay camera is a long
lens from fixed positions around the stadium. So a replay in the world today
would throw you out to that camera, and while the lens is past 8 we show it
flat instead. That is the flat picture you see.

Option A ignores where the replay camera is and keeps your view where it was
during the rally. The players and the ball replay the point in the stadium in
front of you, in slow motion where the game slows it.

- **The game already does the hard part.** It keeps the replay going itself:
  the recorded players, the slow motion, the REPLAY plate, the skip button
  and the match's end.
- **Our part:**
  1. Remember your view from the rally.
  2. During the replay, convert each draw from the replay camera to that
     view. This is one extra matrix where the eye projection is built.
  3. Stop treating the replay's long lens as a reason to show it flat.
- **Most things the camera could break are not a problem here:**
  - The game's culling is never called.
  - The stadium is drawn in full anyway.
  - The crowd cards are fixed in the world, not turned to face the camera.
  - The depth-of-field and blur pass is already left out in world frames.
- **The risks:**
  - The painted sky's direction (simple to fix).
  - The ground shadow mask, which must still line up (expected to, but it
    has to be checked).
  - Small effects that may be built to face the replay camera, such as the
    ball trail and the hit flash (not checked).
- **Comfort is the best of all the options.** Nothing moves you, nothing
  turns you, and there are no cuts. The game's own rewind (some replays show
  the shot twice) is a jump in time only, not in place.

It would be a three-way setting in the Immersive page: **Replays: Off / Flat
screen / In the world**. Each step below can be switched off on its own.

**Point cutaways** (the winner's close-up after a point, the serve close-up
on big points) can use the same method, but they gain less. From your seat a
"close-up" is only the players' celebration poses at full distance. The
1-in-10 split-screen close-up would need its own handling (two pictures of
the same scene). Recommendation: do replays first. Then, optionally, add "In
the world" for the winner's close-up with the split screen turned off. Leave
the serve close-up off: it adds nothing from your seat.

## 1. What the game does in a point replay

### Which loop

- Pass loop -> `mtrLoopManager::setMode(7)` at return 0x08086B17, only when
  `replay::isReplay_point` (0x0810E18E) says yes.
- -> `usrAcReplayLoop`: init 0x0808A2FA, exec 0x0808A538, finish 0x0808A4A8;
  `draw` (0x0808A934) is empty.
- See `replay-paths.md` for the gate. In practice, the arcade replays seen in
  logs were all at **match point** (`isMatch`). Other points earn one for a
  smash (+0x6f8), a high volley (+0x6f9), a service ace (+0x700) or the flag
  at +0x703.

### `usrAcReplayLoop::init` (verified)

1. `replay::start()` on `[mgr+0x90]`, which (0x0810D4A4):
   - picks a **replay type** and calls `camera::setReplayType` (0x080B17C6,
     stores `camera+0x1f0`). The types:

     | Type | When |
     |---|---|
     | 6 | the final round (`match::isFinal_round`) |
     | 1 | word +0x700 == 0x101 |
     | 0 | ace, +0x700 |
     | 3 | smash, +0x6f8 |
     | 2 | high volley, +0x6f9 |
     | 4 | +0x703 |
     | 5 | anything else (typical for an ordinary match point) |

   - saves the players;
   - finds the playback start in a **120-frame ring** of recorded frames
     (0x78; entries indexed mod 0x78);
   - sets the active bytes, then `exec()`s once.
2. Camera mode: `cam = [mgr+0x38]`; `cam+0x40 = cam+0x38` (the old mode is
   saved); `cam+0x38 = 6`. Then the camera's vtable +0x10 is called, which
   (inferred) is the reset that runs `camera::initReplay` (0x080B17D8) for
   mode 6. The guide confirms mode 6 is set only here.
3. Also in init:
   - `CAudience2DManager::make(1,0)` (crowd), `field::setGlare(1)` (glare
     on), `ball::set_model_game_shadow`;
   - cloth, hair and spring resets, `setAll_env`;
   - `[mgr+0x74]+0x28 = 1` (a "replay" byte; cleared in finish).
4. HUD: `ab_game_info::finishCenterInfoBoard()` (the POINT plate goes), then
   **AB resource 0x7a** is created and played (`createResource(0x7a)`,
   `AbManager::createHandle`, `AbHandle::play`). This is the REPLAY plate,
   drawn through the pixel camera, so it lands on our HUD plane. Card windows
   (`CCardResultWindowManager::init`, `window_open_card`) are opened when a
   card is in.

### The replay camera (verified unless marked)

`camera::initReplay`:

- clears the shot state;
- `+0x200` = a 50% coin;
- runs `TScene::CameraPhysics::init()` on `camera+0x220`, a **spring-damped
  camera** with a goal for its eye and for its target;
- picks a shot from the type and a 0-99 roll (jump table 0x838688C):

| Type | Shots (roll) |
|---|---|
| 0 ace | ≤9 `initReplayCharA` (+0x1fc 20); 10-19 `initReplayCharB` (20, two passes); else `initReplayCharToBall` |
| 1 | ≤19 `initReplayLineA`; else `CharToBall` |
| 2 high volley | `CharToBall` |
| 3 smash | ≤9 `CharA` (25); 10-29 `CharB` (25, two passes); else `CharToBall` |
| 4 | ≤4 `CharB` (25); 5-64 `CharToBall`; 65-84 `initReplayCharToBoundPosA`; else `...BoundPosB` |
| 5 default | `initReplayBall` |
| 6 final round | ≤19 `CharB` (two passes); else `CharToBall` |

`initReplayBall` (0x080AF046) is the common match-point shot:

- **The eye is a fixed point** taken from the venue's camera list:
  - `[field+0x50]` is the vector of `CameraData` (`field+0x4c`, filled by
    `field::setCameraData` -> `CameraData::initialize` from the venue's data);
  - point 19, 20, 29 or 30 with 30% probability, 37 or 42 with 30%, 48 or 52
    with 40%.
- **The target is the ball**: first its first bounce (`replay::
  getBound1_ball_pos`), then `CameraPhysics::setTargetGoal(ball)` each frame.
  The camera **pans to follow** with physics smoothing (`+0x88` 60, `+0x8c`
  1000).
- **The FOV** is `rad2fov(25)` (0x080AC7D4: 2*atan(25 / distance), at most
  0.698 rad = 40 deg). That frames about a 2.5 m ball-sized circle from far
  off, which is why the lens is long (inferred: well past 8 at stadium
  distances; the README saw no lens numbers for mode 6).
- **A slow FOV drift**: +0x5c+0x18 = 0.1 or -0.05 times the FOV, depending
  on the ball's side. So it zooms slowly, and the lens can cross 8 within the
  shot. That gives a flat/world flip in today's code (inferred).

The other shots (`CharA/B`, `CharToBall`, `LineA`, `BoundPos`) were not
traced in detail. They aim at a player or the line. In `camera::replay` they
read a player's position (`player+0x1574`) or the ball as the target goal
(`+0x1d8`: -1 = ball, -2 = bounce point, n = player n).

**Per frame** (`camera::replay`, 0x080B196C):

- the target goal is updated;
- `CameraPhysics::exec(1/60 x slow speed)` runs. In slow motion the camera
  slows too (`replay::isSlow_seq` -> `getSlow_speed`);
- the target (`+0x44`) and the FOV in degrees (`+0x5c` = 57.3 x the physics
  FOV) are written.

Shot-specific steps:

- **Two-pass shots** (`+0x208 = 2`): at a set frame,
  `replay::reverseFrame(30)` rewinds 30 frames and `initReplayCharB` picks a
  second angle. The same moment is seen twice.
- **`BoundPosA`**: at its switch frame it calls `fade::setFade(60)`, then
  re-aims (`initReplayCharToBoundPosASub`).
- **Slow motion** is started by the camera (`replay::startSlow` when the
  frame counter +0x1f8 reaches 0 at the ball's impact).
- **`replay::end_forced`** ends the replay early once `+0x1f8` reaches
  `+0x1fc / speed`. CharA and CharB set 20 or 25.

### Duration and end

- `replay::exec` (0x0810D738) plays the ring's frames, slowed by `execSlow`
  and `setMotion_slow_speed`. It calls `TScene::Scene::captureFrame()` in
  slow motion: an inferred motion-blur or interpolation capture.
- It ends at the ring's end (0x78), at `end_forced`, or at the skip:
  `check_skip_button_winner` at return 0x0808A850, past 15 frames.
- That is about 2 s of play shown, longer in slow motion. The total was not
  measured; the flow log gives it.
- `exec` then picks the next loop:
  - match over -> 0xa Gamesetmatch / 0xb Stats;
  - else -> Winlose (8), redirected by our `h_vt3_set_mode` when cutaways are
    off (0x0808A6A7).
- It restores `cam+0x38 = cam+0x40` (mode 1), calls `fade::setFade(30)` and
  `sound::fadeoutBgm_replay`.
- The replay music starts in Pass (`playBgm_replay`).

### What today's code does with it in Immersive

- **The view.** `stereo.c` `eye_projection` builds the eyes from the draw's
  projection:
  - the game's own depth is undone with its matrix;
  - the eye frustum is applied;
  - then the head pose;
  - then `T(back, dolly)` in the game camera's eye space.

  So **the viewer's body is the game camera**, whichever camera it is.
- **Flat or world.** The camera's mode and lens go through the GL queue:
  `h_vt3_proj_cam` -> `stereo_vt3_camera_post(mode, p[0])`. Then
  `stereo_vt3_camera` makes the frame flat when the lens is over
  `zoom_limit()` = 8, and the frame-start rule
  `g_flat = flat_all || menu_state() || g_zoom_frames >= 6` holds it.
- **The REPLAY plate** is a pixel-camera draw: HUD plane, unchanged.
- **The cut cross-fades** are already left out of world frames
  (`screen_copy_stale` and the multi-unit check).

## 2. Option A in depth: you stay at your seat, the point replays in the world

### The idea

A world draw in mode 6 has `MVP = P_r * V_r * M`, where `_r` is the replay
camera. Today the eyes compute `E * H * T * inv(P_r) * MVP`, which is the
replay camera's eye space handled as if it were your body. A inserts one
correction:

```
eye = E * H * T * C * inv(P_r) * MVP,    C = V_a * inv(V_r)
```

- `V_a` is the **anchor**: the last broadcast (mode 1) view before the
  replay, as a 4x4.
- `V_r` is the replay camera's view (`g_game_view`, from
  `setProjectCameraMatrix`).
- `C` turns the replay camera's eye space into the anchor's. After that,
  everything is as in mode 1: the same dolly, step back and head.
- The court, the stadium and the sky dome stay exactly where they were
  during the rally. Only the players and the ball move.

### What must change, piece by piece

1. **Camera feed (GL thread, in order).**
   - Add the camera mode to `Vt3Cam` (`hle_sega.c` `vt3_note_projection`;
     `h_vt3_proj_cam` already reads `rd32(g_vt3_camera+0x38)`).
   - In `arb_note_projection` (`arbprog.c`), or a new
     `stereo_vt3_note_view(mode, view)` called from `vt3_cam_job`: while the
     mode is 1 (or 2), copy the view to `g_vt3_anchor_view`; while it is 6,
     freeze it.
   - It must go through the queue (the rule from the match-start hang: GL
     state only from the game's main thread, through `glq_job`). Read
     straight, the last rally frame would get the replay's anchor.
   - `h_vt3_game_routine`'s built camera (feeding, `g_vt3_feeding`) only
     runs when the game has set no camera for 3 frames. During a replay the
     game sets it every frame (inferred from mode 6 being drawn), so nothing
     to do there. If the anchor were ever missing (a replay before any
     mode-1 frame, as in the attract demo's first point), fall back to
     today's behaviour.
2. **The correction in the eye matrix.**
   - In `eye_projection`, in the deep branch, just before the dolly/back
     translation (`stereo.c` ~line 440), when `replay_in_world()` is true
     (Immersive, setting "world", camera mode 6 latched on the GL side,
     anchor valid): `out = out * T(t) * C`. `C` is computed once per camera
     job, not per draw.
   - The step-back direction uses `g_game_up_eye` (the world's up in the
     camera's space). During A it must be the **anchor's** up
     (`V_a`'s row 1). Store an `anchor_up` and use it while A is active.
   - Every draw that gets the replay projection (exact match `cam_exact`, or
     the lens read) goes through this one place: the court, players,
     stadium, crowd, the sky dome (fp 180, pinned to the far plane) and the
     shadows.
   - **Not** the pixel camera (HUD, REPLAY plate) and not the flat/fill
     passes. Those keep their own path. (`n > 10` already separates the
     pixel camera.)
3. **Flat or world.**
   - In `stereo_vt3_camera`: mode 6 with A gives `lng = 0`.
   - At frame start: `g_zoom_frames` is not counted up in mode 6 with A (the
     `g_lens_seen > zoom_limit()` line).
   - The per-draw `facts.zoom` (`zoom = persp && lens > zoom_limit &&
     g_zoom_frames >= 6`, which classes a draw as HUD) must also be off.
     Otherwise long-lens draws go to the HUD plane.
   - Also check `g_screen_lens` and the `g_world_persp[0] < zoom_limit()`
     test (~line 3809). It decides `g_lens_seen` / the world lens for the
     frame: the replay's lens must not be taken as "the world's lens" for
     the next mode-1 frame.
4. **Painted sky (`sky_draw`).**
   - It builds view directions from `inv(P*V)` with `g_game_view`. During A,
     use `V_a` (and the anchor's lens for the eye directions). Otherwise the
     painted dome turns with the replay camera behind a still stadium.
   - Sky "Stadium" (Sega's dome, a game draw) needs nothing beyond (2).
   - Sky "Off": nothing.
5. **Culling: nothing to do (verified earlier).**
   - `_sCamera::isVisible` is never called in arcade runs
     (`LINDBERGH_VT3_CULLLOG=1`).
   - `field::draw` drops `GAME_NO` and the end behind the camera only in
     camera modes 1 and 2, and our `h_vt3_field_draw` draws everything in
     Immersive anyway.
   - The widened test (`h_vt3_is_visible`) applies "world cameras" only. If
     it were ever reached, mode 6 under A would want the eyes' frusta, which
     it already uses.
6. **Level of detail: inferred nothing.**
   - No LOD symbol exists apart from texture LOD bias fields.
   - The crowd cards are static world quads with no billboarding
     (`crowd-and-upper-stands.md`).
   - Players are drawn as in rallies.
   - Check in the shots: player meshes from a seat during a replay should
     look the same as during a rally.
7. **Depth of field / blur / glare: already handled.**
   - In world frames the game's whole-screen composite (DOF, blur, glare;
     `v59/f60`) is left out, and the clear before it is dropped (`stereo.c`
     ~1712).
   - `field::setGlare(1)` at replay start changes nothing for us.
   - Slow motion's `Scene::captureFrame()`: if it is a whole-screen copy
     drawn back (a motion trail), the stale-copy / multi-unit rule leaves it
     out of world frames. Not checked: look for `[cutlog]` lines in a slow
     section.
8. **Ground shadows (risk, expected fine).**
   - The shadow mask is drawn by world draws (reprojected per eye, so
     through `C`).
   - The plane test in `arbprog.c` ~2068 works in the replay camera's space
     before reprojection (`g_game_view` and `g_game_world_P` stay the replay
     camera's), so it is consistent.
   - Check: the players' shadows at their feet in replay shots, both eyes.
9. **Camera-facing effects (risk, not checked).**
   - The ball trail, hit flashes, dust and the sun flare may be built
     facing the replay camera. Seen from the seat they would be edge-on or
     turned. Small.
   - If one looks wrong, it can be left out in A frames by its programme
     number (as `LINDBERGH_SKIP_FP` does).
10. **Slow motion: nothing to do.**
    - The game slows the players, the ball and the replay camera itself.
    - From the seat you see the point in slow motion: good in VR, and no
      motion is forced on the viewer.
11. **HUD.**
    - The REPLAY plate (AB resource 0x7a) and any card windows are
      pixel-camera draws, so they stay on the HUD plane as now.
    - The score box / POINT plate is finished by the game.
    - Optional later: a small "REPLAY" tag is enough, and the game's own
      plate is that already.
12. **Cuts inside a replay.**
    - Two-pass shots rewind 30 frames (`reverseFrame(30)`). Under A that is
      a jump in time only: the players snap back. A 6-10 frame dip to dark
      over the jump would read as a TV cut. Optional; hook
      `replay::reverseFrame` (0x0810DF7A) or detect `+0x204` changing.
    - `BoundPosA`'s `setFade(60)` is the game's own fade. Its captured
      picture is already left out of world frames.
13. **How the replay ends, and the skip: unchanged game code.**
    - The ring's end, `end_forced` or the shot button: `restore`, the exit
      choice, `cam+0x38 = cam+0x40`, `fade(30)`.
    - Our wraps (`h_vt3_set_mode` at 0x0808A6A7, `h_vt3_skip_winner` at
      0x0808A850 for Replays turned off mid-replay) keep working.
    - When the mode goes back to 1, `C` is dropped. The live broadcast view
      is the anchor or very near it (mode 1's routine did not run during the
      replay), so there is no jump. Check the first frame after (the cut
      log).
14. **The stadium's video board (not checked).**
    - It is fed by per-frame screen copies (33/34). In world mode those hold
      the eye image, not the replay camera's picture.
    - Under A the board shows what you see. This is the same as during
      rallies today, so no change.

### Steps (each leaves the game working)

Every step ships behind `LINDBERGH_VT3_REPLAY_VIEW` (see "Kill switches").
The default stays today's behaviour until the last step.

| # | Step | Behaviour change | Proof (unattended) |
|---|---|---|---|
| 0 | Log only: in mode 6, per frame, the replay type (`camera+0x1f0`), shot (`+0x1f4`), eye (`+0x50`), FOV (`+0x5c`) and lens `p[0]`, under `LINDBERGH_VT3_CAMMODE_LOG=2` | none | `LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_VT3_FLOWLOG=1 LINDBERGH_VT3_CAMMODE_LOG=2 LINDBERGH_VT3_CUTLOG=1 scripts/vt3-repro.sh replay quest 200`: lens numbers per replay and how often it crosses 8; replay lengths from the flow log |
| 1 | The mode in `Vt3Cam`; the GL side keeps `g_vt3_anchor_view` (frozen in 6); log `[world] frame N: replay anchor kept (eye x y z)` | none | the same run: one anchor line per ReplayLoop, the eye equal to the broadcast eye before it; Classic `prize` flow log identical |
| 2 | `REPLAY_VIEW=follow`: mode 6 drawn world (the flat rule, zoom count and `facts.zoom` off in mode 6), no correction. This is option B "following", for comparison | only with the switch | `LINDBERGH_REPLAY_VIEW=follow LINDBERGH_GAME_SHOT=<replay frames>,2 LINDBERGH_SHOT_BOTH=1 ... replay quest 200`: world frames, no `[mode] flat 1` in mode 6, no HUD-classed 3D |
| 3 | `REPLAY_VIEW=world`: `C` applied, anchor up for step back, painted sky from the anchor | only with the switch | the same shots: the stadium in the same pixels as the last rally frame (diff a shot 5 frames before ReplayLoop with one 20 frames in, stadium regions), players moving; `LINDBERGH_VT3_VIEW_TURN=90,0@<f>/180,0@<f+40>` for the sides and behind; `LINDBERGH_VT3_SKY=2` and `=1`; `[black]` log clean (`LINDBERGH_BLACK_LOG=1`) |
| 4 | Panel and vr.cfg: Immersive **Replays: Off / Flat screen / In the world** (`immersive.replays off|flat|world`; an old `on` reads as `flat`); Classic keeps On/Off | the setting exists; default stays Off | `python3 -m unittest tests.test_world_mode tests.test_xr_world_panel tests.test_xr_settings`; `LINDBERGH_XR_FAKE_MENU=1 LINDBERGH_XR_MENU_PAGE=2 LINDBERGH_XR_MENU_DUMP=1` panel picture; scripted clicks (`LINDBERGH_XR_MENU_CLICKS`) cycling the row and the vr.cfg value |
| 5 | Optional polish: a short dark dip at `reverseFrame` jumps; a frame hold or fade at replay start and end if the cut log shows a jump | with "world" | `replay` scene shots across a two-pass shot (types 0, 3, 6; force with `LINDBERGH_VT3_REPLAY_TYPE=<n>` if added in step 0) |
| 6 | Regression, then the owner's worn check | none new | `LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_REPLAYS=1 LINDBERGH_REPLAY_VIEW=world LINDBERGH_VT3_FLOWLOG=1 scripts/vt3-repro.sh prize quest 330`: ReplayLoop -> Gamesetmatch -> Stats 600 frames -> next round, two matches; the same with Replays off (no ReplayLoop) and `flat` (today's picture); Classic `prize` flow log unchanged; `LINDBERGH_GPU_TIME=1` replay frames within ~+0.5 ms of rally frames (more is drawn: no culling either way); macOS `LINDBERGH_VT3_IMMERSIVE=1` `replay` scene too |

**Skipping a replay mid-way** (test with the replay running):
`LINDBERGH_REPLAYS= LINDBERGH_XR_MENU_CLICKS=<window>` on the Replays row
must still end it two frames later, as now (`replay-paths.md`).

### Settings row and kill switches

- **Immersive page:** `Replays  Off | Flat screen | In the world`. The
  default is Off, as now. Later, the owner may choose In the world as the
  default.
- **Classic:** unchanged (On / Off; Classic is always flat).
- `LINDBERGH_REPLAYS=0|1` stays: 0 = off, 1 = on with the mode's view.
- `LINDBERGH_VT3_REPLAY_VIEW=flat|follow|world` picks the view for a run
  (env wins, never saved). `follow` is for tests only.
- `LINDBERGH_VT3_REPLAY_VIEW=flat` is the kill switch: today's behaviour
  exactly.
- `LINDBERGH_VT3_CUTFLAT=0`, `_CAM_QUEUE=0` and `_CAPTURE=1` keep their
  meanings.

### Comfort

- No forced motion, rotation or cut.
- The only visible discontinuities are the game's own: the rewind of a
  two-pass shot (a time jump) and the start/end fades, which we already
  turn into hard cuts in world frames.
- This is the most comfortable option.

## 3. The other options (short)

**B. Put the viewer at the replay camera (natural FOV).** Step 2 above is the
"following" version, almost free. But it carries you to a point high in the
stands (CameraData points), plus the dolly. The camera pans with physics
smoothing, so the world turns around you: uncomfortable. "Snapped per shot"
(eye fixed at the shot's eye, no rotation) fits the game well, because every
shot's **eye is fixed** and only the aim moves. With a 1:1 FOV, though, the
ball is a dot 40-60 m away (the long lens existed to magnify it). You would
also have to look for the action yourself. A fade at each cut (start, rewind)
would be needed. The cost is moderate, the comfort fair, and the view poor.

**C. Our own vantage points** (net post, behind the opponent, umpire's
chair). This is A with `V_a` replaced by a chosen view, plus a dark-dip
transition to it and back. It is a later add-on to A, not instead of it.
Moving the seat at all is the comfort cost, and a list of seats per venue is
the work. Once A works, it is cheap: a "Replay seat: Your seat / Umpire /
Net" row.

**D. A big virtual screen in the stadium.** Today's flat picture, placed as a
large screen above the far end (a quad layer or a `host_xr.c` screen draw
with a world pose). It shows the game's real broadcast replay, with long lens
and slow motion, while the stadium stays around you. The cost is low to
moderate. It needs the flat picture to be drawn into a texture while the eyes
show the world, which today is exclusive per frame (`g_flat`): that is the
real work. The comfort is good. It could also be combined with A later ("the
big screen shows the TV angle"). Not chosen.

## 4. Point cutaways

What they are (`replay-paths.md`, guide section 8):

- **Winlose** (camera 7, about 120 frames, a random close-up of the winner;
  split screen 1 in 10);
- **the big-point serve close-up** (camera 5 in `usrAcStartLoop`, about 150
  frames, zooming past lens 8);
- **game set and match** (camera 9, slow-motion celebration via
  `replay::startSlow`; always shown, it is not a "cutaway" row).

Can they be in the world with method A? Mechanically, yes: the same anchor,
`C`, and the flat rule off for modes 7 / 5 / 9. But:

- **Winlose (7):** worthwhile as an option. From the seat you would see the
  winner's celebration poses and the crowd, at rally distance. The
  **split-screen** variant draws the scene twice into two viewports (camera
  pairs). Under A both halves would land on top of each other, from the same
  anchor. Either suppress the split (`camera::initWinlose`'s first
  `getRandMT_U32() % 10`, the hook `LINDBERGH_VT3_SPLIT` already uses,
  answered non-zero) or leave out the second viewport's draws. Test with the
  `splitreplay` scene (with Immersive and cutaways on, and the split
  suppressed: no doubled players).
- **Serve close-up (5):** it adds nothing from the seat. The player only
  bounces the ball, which you see in a rally anyway, and the heat-up music
  and poses are already skipped with cutaways off. Keep it off.
- **Game set and match (9):** it is shown today (flat once the lens passes
  8), and it is a natural next candidate for A: the slow-motion celebration
  in the stadium around you. Same steps as replays, with mode 9 added to the
  set, behind the same switch. Its end leads to the result slate (mode 0xa,
  a flat menu) as now.

Recommendation: replays first (steps 0-6). Then "Point cutaways: Off / In
the world" for Winlose only (split suppressed). Then game set and match in
the world. The serve close-up stays off in Immersive.

## Verified versus inferred

**Verified (disassembly):**

- the replay loop's init, exec and end, and the camera mode 6 set in init;
- the REPLAY plate resource 0x7a;
- the replay types and their conditions;
- `initReplay`'s shot table (0x838688C) and `initReplayBall`'s fixed eye
  from `field` CameraData, its ball target and `rad2fov(25)` capped at 40
  deg;
- CameraPhysics tracking, slow motion scaling the camera, `reverseFrame(30)`
  two-pass shots, `end_forced`, the 0x78 ring;
- the world-mode eye math (`stereo.c` `eye_projection`) and the flat rule
  (`stereo_vt3_camera`, frame start).

**Verified earlier (other docs):** no culling calls, the stadium drawn whole,
the crowd cards static, the DOF composite left out in world frames.

**Inferred (to check in step 0 and in step 3's shots):**

- the replay lens values;
- camera vtable +0x10 being the reset that starts `initReplay`;
- what `captureFrame` does;
- camera-facing effects;
- the ground shadow staying aligned;
- the replay length in frames;
- the split-screen Winlose behaviour under A.
