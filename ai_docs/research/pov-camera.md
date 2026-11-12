# Virtua Tennis 3: a POV ("player's eyes") camera in Immersive

Read-only study, 2026-11-11. Nothing built, run or edited. Addresses are from
the original ELF (`~/code/quest_games/vt3/disk0/vt3_Lindbergh/vt3_Lindbergh`,
`objdump -d --x86-asm-syntax=intel -C`); the HD executable the port runs
(`vt3_Lindbergh_HD`) has the same symbol addresses (checked for
`player::getEyePosition`, `player::calcFacePosition`, `player::draw`,
`camera::gameRoutine`, `replay::isReplay_point`). Code references are to
`lindberghrecomp/src/runtime/` at the time of writing. **[V]** = verified in
the disassembly or the code, **[I]** = inferred, **[M]** = to be measured.

## Short answer (for the owner)

Yes, a "player's eyes" view can be added, and the game makes it easier than
expected. Every frame it works out exactly where your player's eyes are (the
midpoint of two eye bones in the model), where the player stands, which way
the player faces, and where the hand and racket are. We can draw the stadium
from there using the same one-matrix trick planned for replays.

- **Scale.** Today the headset treats 1 m as 10 cm of the game world. From a
  seat 20 m away nobody notices. Standing on the court, it must be life size
  (10x), so the POV modes change it. Then the net is knee-high and the
  opponent is 24 m away and small, as in real tennis.
- **Three views to try:**
  - **Player's eyes:** you move with the player. Head bob and swings are
    taken out, the movement is smoothed, and a dark vignette shows while
    running. The view never turns on its own; only your head turns it.
  - **Behind player:** 1.5 m behind and above, following. Probably the most
    comfortable that still feels like playing.
  - **Snap:** you stay put and jump to the player behind a short blink.
- **Change of ends.** When your player changes ends, the screen fades to
  black, the world turns 180 degrees, and it fades back in. "Forward" in your
  room is always toward the net.
- **Your own head is hidden; the rest stays.** Anything within ~20 cm of the
  player's head is left out of the picture. Your arms, racket and shadow stay.
  Hiding the whole body is possible too. The serve meter moves to in front of
  you, at chest height.
- **Controls, honestly:**
  - **Realistic:** the stick moves you relative to where you look. The game
    has a hidden analog-stick path we can feed, so you get full 360-degree
    movement. Aiming by looking is also realistic.
  - **Possible:** swinging the controller instead of pressing a button.
    Underneath it is still Virtua Tennis's timing: the game decides the hit,
    not your racket meeting the ball.
  - **Cosmetic only:** a racket that follows your hand. The ball would still
    fly off from where the game's racket is.
  - **Fights the game:** walking around your room to move the player.
- **Comfort** is the big unknown. Only you can judge it worn. Each view is a
  setting (Immersive page, **View: Seat / Behind player / Player's eyes /
  Snap**). "Seat" stays exactly today's view.

## 1. Where the player lives in the game

### Units: one game unit is 10 cm [V]

The court constants in `.rodata` are exact decimetres: 41.15 (0x8381374, half
the singles width, 4.115 m), 118.85 (0x838134c, half the court's length,
11.885 m), and the start positions table at 0x838aea0 (12-byte vectors read by
`match::getPlayerPosition`) holds (±10, 0, ±124.85), (±31.15, 0, ±128.85),
(±27.425, 0, ±124.85), (±27.425, 0, ±44): baseline +1 m, and so on. The court
is centred on the origin, y up, the net along x at z = 0.

**Important for a POV:** the headset profile has `vr.scale = 1`
(`games/vt3/src/host.c`), and `lg_stereo_pose_view` multiplies the head's
position in metres by that scale. So today **1 m of head movement is 1 game
unit = 10 cm**, and the eyes are 0.64 units apart (6.4 mm in the game's
world). From a seat 20-30 m away this does not show (the serve-meter study
measured the parallax as negligible). Standing in the player's place it is
everything: life size needs **scale 10** (1 m = 10 units). The switch
exists: `LINDBERGH_XR_SCALE` / vr.cfg `scale` (`xr_settings.c`). The POV
modes must set it (or multiply by 10 inside the POV path only, so that the
seat view stays as it is).

### The player list [V]

- `g_pTennis` = `[0x085061a4]` (`VT3_G_PTENNIS` in `hle_sega.c`).
  `[g_pTennis+0]` = number of players (2 singles, 4 doubles:
  `playerManager::set_player` 0x08165DBC writes 2, or 4 when
  `[g_pTennis+0x24]` == 2), `[g_pTennis+4]` = array of `player*`.
- `playerManager::draw` (0x08165D24) and the other loops walk indices 0..3
  and use only players whose byte `+0x04` is 1 (active).
- **Which player is human:** `player+0x08`. `player::init_base` (0x0814FD8E)
  sets it to 4; `playerManager::set_player(n)` calls `player::set_player(n)`
  (0x0814FE8C), which writes `n` there for the chosen player.
  `player::keyScan` (0x081507FC) reads the pad when `+0x08 <= 3`
  (`cmp [ebx+8],3; jg` -> `player_ai::setKey`): **`+0x08 <= 3` is a human
  (its value is the pad index), 4 is the computer.** 1P is player 0 in
  practice (the serve-meter tools read `[[g_pTennis+4]+0]` as 1P).
- `player+0x00` = player number (`set_plno`), `+0x0c` = team ((plno+1) mod 2),
  `+0x10` = partner index in doubles.
- `player+0x05` = "put" (drawn) byte; `playerManager::setPut_off`
  (0x081684E2) clears it, turns the player's cloth and hair off and calls
  `sm_down` (its shadow-map entry).

### Position, facing, head [V unless marked]

| Field | What | Evidence |
|---|---|---|
| `player+0x18` (x, y, z) | **root position on the ground** (y ~ 0) | `player::setPosition` (0x0815031C) writes it from `match::getPlayerPosition`; the HUD anchors the serve meter and the 1P marker to it (`hle_sega.c` `h_vt3_screen_pos` compares the point with `player+0x18`) |
| `player+0x68` (x, 0, z) | facing direction, (0, 0, -1) at the +z end, (0, 0, +1) at the -z end at a point's start | `setPosition`: `z >= 0` -> (0, 0, -1) |
| `player+0x28` | yaw angle, atan2(dir.x, dir.z) | `setPosition` (`fpatan` of +0x68 / +0x70) |
| `player+0x38..0x64` | 3x4 rotation (about y) built from that yaw | `setPosition` |
| `player+0x14a4` | the player's `TScene::SceneObj` (the model) | `player::initMotionPerLoad` (0x081371F8) creates it; `player::draw` adds it to the scene |
| `player+0x14b0 + 4*i` | 31 bone nodes found by name (`_sTree::getNodeByName`, names at 0x841e420) | see the list below |
| node`+0x88` | the bone's world matrix, 3x4 row-major, translation at +0x0c/+0x1c/+0x2c | `calcFacePosition` and `getEyePosition` read it as world positions |
| `player+0x1574` (x, y, z) | **"face position": the midpoint of the eye_L and eye_R bones**, world | `player::calcFacePosition` (0x0813E712): `0.5 * (eye_L.t + eye_R.t)`; zero when the bone is missing. Called from `assignMotionMatrix` and `updateBoneTranslation` each frame. The replay camera aims at it (`immersive-replay-cameras.md`) |
| head forward | **minus column 1** of the `Head` bone's world matrix | `player::getEyePosition` (0x0814647E) case 1: look target = `+0x1574 - 100 * (m[1], m[5], m[9])` of `[player+0x14ec]+0x88` |

Bone slots (`player+0x14b0 + 4*i`): 0 bobobone (root), 1-5 left leg, 6-10
right leg, 11 spine, 12 Spine1, 13 Spine2, 14 Neck, **15 Head (+0x14ec)**,
**16 eye_L (+0x14f0)**, **17 eye_R (+0x14f4)**, 18-23 left arm to Hand_L, 24-29
right arm to **Hand_R (+0x1524)**, **30 racket_model (+0x1528)**.

So the game gives us, every frame, the exact eye point (`+0x1574`), the head's
orientation (the `Head` bone), the root on the ground (`+0x18`) and the hand
and racket bones. Eye height: not measured; a ~1.8 m model puts it at ~16.5
units **[M]** (log `+0x1574.y` in step 0).

### Per frame, and which end [V / I]

- `player::exec` (0x0815002A) calls, in order, `keyScan` (input), `execMotion`
  (animation; the bone matrices and `calcFacePosition` come from
  `assignMotionMatrix` / `updateBoneTranslation` under it), `moveTarget`,
  `playerServe`, `playerSwing`, `playerMove` [V, call order]. So `+0x1574`
  is from this frame's pose and `+0x18` is updated just after it (one step
  apart, negligible). The camera is set (`_sRender::setProjectCameraMatrix`)
  after the update, as the camera feed already relies on [I].
- The game turns the player's head itself: `calcEyeTarget` / `getEyePosition`
  pick a look target (case 6 is the ball, `[g_pTennis+0x14]+0x1c`) and
  `calcHeadIK` turns the `Head` bone to it [V for the targets]. **The head
  bone's orientation must never drive the view** (it would turn the
  viewer's head to follow the ball).
- **The broadcast camera does not keep the human at the near end.** Its own
  side flag is `camera+0x1c8` bit 0: `camera::initGameRoutine` (0x080A5692)
  mirrors the camera's x and z (sign bytes +0x4f, +0x5b) from the games'
  parity and `match::isCam_first_reverse` (`match+0x28` bit 0x40). In runs the
  human (1P) plays from the far end after a change of ends (README: "game 2
  at ~7300 ... 1P then at the far end"; the serve-meter study measured the
  meter at both ends). So the human's end is simply the sign of
  `player+0x18.z` (or the facing `+0x68`).
- Doubles: four players, the human's partner is the computer (`+0x08` = 4),
  the same fields apply. Each team's two players stand side by side, so the
  partner can come within a metre of the POV eye.

## 2. Design: the view from the player

### The tool: the same correction matrix as replays [V for the plumbing]

`stereo.c` `eye_projection` builds each eye as `E * H * T * inv(P_game) *
MVP`, i.e. the viewer's body is the game camera's eye space `V_g`, moved by
the dolly/step-back `T`. For a POV the body is a view we choose:

```
eye = E * H * C * inv(P_game) * MVP,     C = V_pov * inv(V_g)
```

- `V_g` is the broadcast view the draw was made with (`g_game_view`, from the
  camera feed).
- `V_pov` is a look-from matrix with **position** from the player and
  **orientation fixed**: yaw toward the net from the human's end, horizon
  level, no pitch or roll. Every rotation comes from the head (`H`). `T`
  (dolly / step back / height) is not used in POV modes.
- Scale: `H`'s translation must be in game units at 10 per metre (see units).
  Simplest: in POV modes `eye_projection` uses `g_view` with its translation
  times 10 (the IPD comes with it), so Seat mode is unchanged.
- One place, as for replay option A: everything that goes through the deep
  branch (court, players, stadium, sky dome, shadow-mask draws) follows. The
  painted sky (`sky_draw`) must use `V_pov` the same way. The HUD anchors
  (`stereo_vt3_hud_anchor`) call `eye_projection`, so the serve meter and the
  1P marker follow automatically (but see 3.3).
- Data path: the game thread reads the human's `+0x18`, `+0x1574`, `+0x68`
  in `h_vt3_proj_cam` and posts them with the camera through the GL queue
  (`Vt3Cam` in `hle_sega.c`, `vt3_cam_job`), never read from the GL thread
  (the match-start-hang rule).

### The four variants

**(a) Player's eyes, fully attached.** `V_pov` position = `+0x1574` every
frame. Most "real", worst comfort: the face bone bobs with every step, every
bend for a low ball and every swing (the body rotates through ~180 degrees in
a serve; we take only the position, but the head moves ~0.5 m in a swing).
That is forced motion of the view the viewer did not make. Keep it as an
experiment switch only.

**(b) Player's eyes, with comfort (recommended first).**
- Position = root `+0x18` (x, z) plus a fixed eye height (the face bone's
  standing height, measured once per match, or the owner's own eye height:
  LOCAL space puts the real head at y 0 at recentre, so the real crouch still
  lowers the view). No bob, no swing lurch.
- Smoothed with a critically damped spring (time constant ~0.12 s) so
  direction changes are not instant jerks.
- No rotation ever: yaw fixed to the end's direction (toward the net), the
  head alone turns the view.
- A comfort vignette (a dark ring drawn over the eyes, strength by the
  anchor's speed: 0 below ~1 m/s, full at the player's sprint ~6 m/s) -
  the usual VR answer to smooth locomotion.
- The player runs a lot (a baseline rally covers ~8 m sideways); this is
  still smooth locomotion. Some people tolerate it, many do not.

**(c) Behind the player ("over the shoulder").** Eye = root + 15 units behind
(away from the net) + up to ~22 units (2.2 m), following x with the same
spring, z with a slower one; yaw fixed. You see your player from behind and
above, life size, ~1.5 m away: the classic third-person VR camera. It moves as
much as (b) but the motion is mostly sideways and the own body is in front of
you, which most people find easier. No model hiding needed (the own player is
1.5 m ahead, outside the near plane). Good second step, maybe the best
default.

**(d) Snap ("teleport") steps.** The eye stays put; it jumps to the player
(variant b's point) with a short blink (6-8 frames dark) only when the player
is more than ~1.5 m (15 units) from it, and always at the start of each point
(StartLoop / serve position). No smooth motion at all: the best comfort, but
during a rally you see your player run away from you between snaps. A hybrid
(snaps between points, (c) during the rally) is worth a try.

### Change of ends: turn the world 180 degrees behind a fade

When the human's end changes (`sign(player+0x18.z)` flips, which happens in
the Changeend loop or between points), `V_pov`'s yaw flips by 180 degrees.
The viewer would see the stadium spin. Do it only behind black:

- trigger: the sign flip, or `usrAcChangeendLoop::init` (mode 9; with Point
  cutaways off the game goes Pass -> Changeend -> Start, `h_vt3_set_mode`);
- fade the eyes to black over ~10 frames (a full-screen dark quad after the
  world, or the existing frame hold), switch the yaw and position, fade in
  over ~15 frames;
- in POV modes the game's own between-point fades already happen as hard cuts
  (`screen_copy_stale`), so this is the only fade we add.
- The viewer's physical direction does not change: "forward" in the room is
  "toward the net" at either end. A recentre is not needed.

### What the other camera modes do while POV is on

POV applies only while the game's camera mode is 1 (the rally). Point
cutaways stay off in Immersive (as now). A point replay with "Replays: In the
world" (`immersive-replay-cameras.md`, option A) works unchanged: its anchor
`V_a` is simply the last POV view, so the replay plays around the viewer
where they stood. The serve camera (5), game set and match (9) and the result
slate behave as today (flat once the lens passes 8). Menus are flat as now.

## 3. What must be hidden or changed

### 3.1 The own player's model

**The draw path [V].** `playerManager::draw` (0x08165D24) loops over the four
player slots and, for a player with `+0x04 == 1` (active), `isPut_all()`
(`playerManager+0x75`) and `+0x05 == 1` (put), calls `player::draw`
(0x081500E4), which is only `TScene::SceneObj::addScene([player+0x14a4])`
(plus a debug draw). The model, its racket (`racket_model` is a node of the
same tree) and, inferred, its planar ground-shadow and shadow-map entries all
come from that one scene object. The actual GL draws happen later, sorted,
on the main thread (`_sScene::execute`), as the HUD study found for the HUD.

Three ways to hide, in rising order of reach:

1. **Head bubble on the GL side (recommended).** In the eye passes only
   (`stereo_draw_world()`; not the shadow-map pass, which draws into its own
   depth target without `u_reproj`, and not the screen copies), discard the
   fragments of player draws that lie within ~20 cm of the human's head
   point (`+0x1574`, sent with the camera). The translated programs already
   have the game's clip position (`gl4es_mvPre`); one uniform `inv(P_g*V_g)`
   gives the world point, a `vec4 u_bubble` (centre, r^2) the test. Limit it
   to the skinned (player) programs, found once with `LINDBERGH_FRAMEMAP`
   (the shadow ones are vertex 141/137, fragment 114 - they must be left
   alone or the head's ground shadow goes too). `discard` costs early-Z only
   on those small draws. Result: no head, no hair or cap brim in the eyes;
   arms, body, racket and every shadow stay. A per-vertex collapse (vertices
   in the bubble pushed behind the near plane) is the cheaper fallback but
   leaves torn triangles at the neck.
2. **Hide the body but keep the racket.** The same test with a vertical
   cylinder (radius ~60 cm, from 30 cm above the ground up) around the
   human's root, still skinned programs only, still not the shadow programs.
   The racket is kept if its program is a rigid one (to check in the frame
   map); if it shares the skinned program, keep it by excluding fragments
   near the `Hand_R` / `racket_model` bones (a second sphere that wins).
3. **No own player at all (simplest, loses the shadows).** Wrap
   `player::draw` and return for the human. Shadows go with it (inferred:
   same scene object; `setPut_off` also calls `sm_down`). Useful only as a
   quick experiment (`LINDBERGH_VT3_POV_HIDE=all`).

Option 1 is enough for variant (b); (c) needs nothing (the player is 1.5 m
ahead). Seeing one's own body move without moving is a known oddity in VR;
the owner should judge head-only versus body hidden.

### 3.2 Near clip plane

The eyes' near plane is `LINDBERGH_VT3_NEAR` x the game's (`stereo.c`
`eye_projection`: `n2 = nk * n`, the broadcast camera's n = 1 unit), i.e.
10 cm today, which is right for a life-size view: the own hands and racket
are 30-70 cm away, the ball only comes closer when it hits you. Do not lower
it (the decal / polygon-offset blotches came from a 20x closer plane). With
the head bubble the inside of the head is not a near-plane problem.

### 3.3 Serve meter, 1P marker and the HUD

- **The HUD panel** (score box, plates; pixel-camera draws) is placed with the
  head pose (`hud_view`: `g_view`, or head-locked with
  `LINDBERGH_XR_HUD_LOCK`), in the room, not in the game world. It does not
  turn when the world turns 180 degrees at a change of ends: good. With the
  scale change the HUD must stay where it is in metres (it does if the POV
  path scales the head translation itself instead of `cfg.scale`, or if
  `screen * scale` keeps it in metres as `host_xr.c` does) [I, check].
  The in-scene scoreboards (HANDOFF section 5) suit POV better later.
- **The serve meter** is anchored at the serving player's root (`+0x18`, the
  feet) and re-solved through `eye_projection` (`stereo_vt3_hud_anchor`),
  so under POV it lands at your own feet, below the view. In POV modes,
  `h_vt3_screen_pos` should swap the human's own root for a point ahead:
  root + facing x 6 + right x 3 + up 12 units (about chest height, 60 cm
  ahead, 30 cm to the right). The opponent's meter stays at the opponent.
- **The 1P marker** sits above the own head: behind or at the eye, so the
  solver would place it wildly. Hide it in POV (answer a far-off-screen
  position when the point is within ~1 m of the eye or behind it).

### 3.4 Ball

- The ball's radius is `0.35` units = 3.5 cm (`ball::getBall_rad`, stored at
  0x84e7cb4 by `ball::init`: 0x3eb33333) [V] - life size. At the far
  baseline (~24 m) it is ~0.17 degrees, ~4 headset pixels; a serve at
  50 m/s crosses the court in ~0.5 s. Real players manage, but a **Ball size
  x1 / x1.5 / x2** option (visual only: scale the 3x3 of the ball's world
  matrix in a `ball::draw` wrap, put it back after) is cheap insurance [I].
- `ball::isBlur` (`ball+0x9070`, `kBLUR_SPEED`) draws a blur/trail for fast
  balls; whether it is built to face the broadcast camera is not checked. If
  it looks edge-on from the court, leave its program out in POV frames (as
  `LINDBERGH_SKIP_FP` does).
- The ball's ground shadow is a game draw like the players'; it follows.

### 3.5 Net, far opponent, scale

At scale 10 everything is life size: the net 0.91 m at the centre, the
opponent ~24 m away and small, the stands tall around you. That is the point
of the mode. The seat mode keeps scale 1 (a giant-scale stadium, stereo
almost flat), which is why nobody noticed the scale before.

### 3.6 Level of detail, culling, depth of field, ground shadow mask

- **Culling:** `_sCamera::isVisible` is never called in arcade runs, and
  `h_vt3_field_draw` draws the whole stadium (both ends, `GAME_NO`) in
  Immersive [V, earlier studies]. From court level the end behind you is
  drawn already.
- **Level of detail:** no LOD switch found (only texture LOD bias fields);
  the players' `*_M1..M4` model files are morph targets (faces), not LODs
  [I]. Player meshes up close are the same meshes the close-up cameras use.
  Watch the textures: up close the players' and court textures will look
  softer than from the seat (they were made for TV distance). Nothing to fix.
- **Depth of field / blur / glare:** the whole-screen composite is left out
  of world frames already [V].
- **Ground shadow mask:** drawn by world draws, reprojected per eye, so it
  follows `C` like everything else (the per-eye mask in the working tree, or
  the `lg_eye0` lookup in the committed one). Check the feet's shadows in
  both eyes in step 2's shots. The self-shadow map is a light camera,
  unaffected.
- **The painted sky** (`sky_draw`) builds directions from `g_game_view`: use
  `V_pov` in POV, as for replay option A. Sega's dome needs nothing.

## 4. Controls: what a "real VR game" would need

Today: the cabinet's 8-way lever (JVS, `pad::exec` 0x0817AFD4 sets
`pad+0x10` bits 1/2/4/8 from the lever) plus two shot buttons; on the Quest
the stick is the lever, trigger = top spin, A/X = slice, B/Y = lob (both
buttons). The game moves the player and times the swing itself.

**How the game reads the lever [V].** `player::keyScan` (0x081507FC), for a
human (`+0x08 <= 3`), reads its pad (`[g_pTennis+0x110][player+0x294]`, a
`pad`):
- lever bits set: the vector (x, 0, z) from the bits;
- **no lever bit: an analog stick**, `x = pad+0x1c / 32767`,
  `z = -(pad+0x20) / 32767` (`cvtsi2ss`, the constant 32767.0 at
  0x839ba1c). `pad::exec` zeroes `+0x1c/+0x20` every frame and nothing fills
  them on the cabinet: a leftover console/dev path (the camera class still
  has `DXPCAction`, `XBOXAction`, `DOLPHINAction`, `PXAction`);
- then the vector is **turned by the inverse of the scene camera's view**
  (`_sSceneManager::get(5)->getAttachedCamera()`, `_sMatrix34::getInverse`),
  flattened (y = 0) and renormalised: the lever is screen-relative to the
  broadcast camera. It lands in `player+0x298` (x, y, z), with the button
  bytes at `+0x2a4..+0x2ad` and a 10-frame command history at `+0x2b8`
  (`setCommand`; `getCommand_release_frame`, drop volley and other
  commands read it).

In rising order of cost:

1. **Stick relative to the view (realistic, low-moderate).** Wrap
   `pad::exec`; after the original, for the human's pad in POV modes, clear
   the direction bits 1/2/4/8 and write `+0x1c/+0x20` from the stick turned
   by (head yaw relative to the POV facing) and then into the broadcast
   camera's screen axes (the inverse of what `keyScan` does; the camera view
   is known on the game thread). Bonus: full 360-degree analog movement
   instead of 8 directions (whether the game uses the magnitude for speed is
   not checked; `kLEVER_ON` suggests a threshold [I]). Also fixes "up" at the
   far end, where today's screen-relative lever is reversed for a viewer
   facing the near end.
2. **Head-relative aiming (realistic, moderate).** In Virtua Tennis the aim
   is the lever held at the hit (`playerSwing` reads the button bytes; the
   aim targets `setTarget_swing_x/z` are worked out from the lever and the
   "neutral" targets [I]). While a shot button is held, the analog vector
   from (1) can come from the gaze instead of the stick: left/right of the
   court centre from head yaw, deep/short from head pitch. A switch, so the
   stick can still aim.
3. **Swing the controller to shoot (feasible as a gesture "button", but the
   game's timing stays).** Detect a swing from the controller's linear and
   angular velocity (OpenXR action poses are already read in `host_xr.c` for
   the panel's aim). Map: an upward brush = top spin, a downward chop =
   slice, a high upward swing = lob; the swing's sideways direction feeds
   the aim of (2). **The catch:** VT3 wants the button pressed well before the
   ball arrives (the press starts the auto-run to the ball and the
   swing/charge; `getCommand_release_frame` shows the release is read too).
   A real swing happens at contact, too late. So the gesture must be the
   **take-back** (racket drawn back = press, forward swing = release), or the
   game must press for you when the ball comes and the swing only picks the
   shot. Either way hit or miss is still decided by the game's timing, not by
   your racket meeting the ball. Worth one experiment; it will feel like
   "swinging to press a button".
4. **The racket in your hand following the controller (visual only:
   possible; real: not realistic).** The `racket_model` bone (`+0x1528`) has a
   world matrix (`+0x88`) the draw uses; overwriting it after the animation
   with the controller pose (in game units) would draw the racket in your
   hand, best with the own body hidden (3.1 option 2 without the racket
   exception). The arm would not follow (the game's arm/wrist IK,
   `calcArmIK`, `calcWristIK`, `execBindRHand`, serves its own animations),
   and the ball still bounces off where the game's racket is - a visible
   mismatch at every hit. Replacing the swing animation with the controller
   is not realistic in a recompiled game.
5. **Room-scale movement moving the player (experimental at best).**
   Writing `+0x18` from the headset fights the game: its movement, the
   auto-run after a shot press and the swing search all set and read it. A
   gentler version: a "follow me" stick - the analog vector of (1) points
   from the player to your physical position (scaled ~2-3x, since half a
   court is ~12 x 8 m and a room ~3 x 3 m), the view is your real head
   (world-locked, no vection). The player then chases you, the game's
   auto-run still takes over after a press, and the translation gain itself
   is a comfort question. Last, and only if (1)-(3) are liked.

Honest summary: 1 and 2 are solid work in this game; 3 is an experiment that
keeps the game's button timing underneath; 4 is cosmetic; 5 fights the game.
A "real" racket game (hit where your racket is) would need the game's ball
contact replaced by ours - out of reach here.

## 5. Steps (each leaves the game working)

Switches (env wins, never saved; vr.cfg keys as the other Immersive ones):

- `LINDBERGH_VT3_VIEW=seat|behind|eyes|snap|eyes_raw` (vr.cfg
  `immersive.view`, panel row **View: Seat / Behind player / Player's eyes /
  Snap**; `eyes_raw` = variant (a), env only). **`seat` is the kill switch:
  today's behaviour exactly.** Default `seat` until the owner picks.
- `LINDBERGH_VT3_POV_SCALE` (default 10; 1 = today's scale in POV, for
  comparison), `LINDBERGH_VT3_POV_EYE` (eye height, units; default the
  measured standing face height), `LINDBERGH_VT3_POV_SMOOTH` (seconds,
  default 0.12; 0 off), `LINDBERGH_VT3_POV_VIGNETTE=0|1`,
  `LINDBERGH_VT3_POV_HIDE=none|head|body|all`, `LINDBERGH_VT3_POV_FADE=0|1`
  (the change-of-ends fade), `LINDBERGH_VT3_POV_STICK=0|1` (view-relative
  analog stick), `LINDBERGH_VT3_POV_LOG=1`.
- Test only: `LINDBERGH_VT3_POV_FAKE_STICK=<frame>:<deg>,...` (a stick held
  at that angle relative to the view, for unattended movement tests).
- Existing helpers for proof: `LINDBERGH_XR_FIXED_HEAD=1` (head level, ahead,
  on the unworn headset), `LINDBERGH_VT3_VIEW_TURN=<yaw>,<pitch>@<frame>/...`
  (look down, sideways, behind), `LINDBERGH_GAME_SHOT=<f>,<every>[,..,<last>]`
  with `LINDBERGH_SHOT_BOTH=1`, `LINDBERGH_BLACK_LOG=1`, `LINDBERGH_GPU_TIME=1`,
  `LINDBERGH_VT3_FLOWLOG=1`, `LINDBERGH_VT3_SERVELOG=1` /
  `LINDBERGH_VT3_SERVESHOT`, `LINDBERGH_FRAMEMAP=<frame>`, scenes `round0`
  (a long rally match; 1P at the far end from game 2, ~frame 7300),
  `prize`, `replay`.

| # | Step | Change | Unattended proof |
|---|---|---|---|
| 0 | **Log only.** `LINDBERGH_VT3_POV_LOG=1`: once a second, the human's index (`+0x08 <= 3`), root `+0x18`, face `+0x1574`, facing `+0x68`, end sign, camera mode; a line at each end change | none | `LINDBERGH_VT3_IMMERSIVE=1 LINDBERGH_VT3_POV_LOG=1 LINDBERGH_VT3_FLOWLOG=1 scripts/vt3-repro.sh round0 quest 200`: face height while standing (sets the eye default), the end flip near ChangeendLoop, root speed in rallies (sets the vignette ramp); macOS the same (`... round0 mac ~/code/quest_games/vt3 200`) |
| 1 | **Data path.** `Vt3Cam` carries the POV point, facing and a valid bit; GL side keeps `g_vt3_pov`; nothing uses it | none | the same run: `[pov]` GL-side lines equal the game-side ones, one frame later at most; Classic `prize` flow log identical |
| 2 | **`eyes` raw view, no hiding:** `C = V_pov * inv(V_g)` in `eye_projection` (deep branch, camera mode 1 only), POV scale, painted sky from `V_pov`, `T` off | only with `VIEW=eyes` | `LINDBERGH_VT3_VIEW=eyes LINDBERGH_XR_FIXED_HEAD=1 LINDBERGH_GAME_SHOT=2400,30 LINDBERGH_SHOT_BOTH=1 ... round0 quest 160`: the far court ahead from eye height, net 0.9 m; `VIEW_TURN=0,-60@<f>/90,0@<f2>/180,0@<f3>` (down: own body/feet and shadows in both eyes; side; behind: the near stand); far end after ~7300 faces the other way; `[black]` clean; GPU within ~+0.5 ms of seat |
| 3 | **Comfort basics:** root + eye height instead of the face bone, spring smoothing, the change-of-ends fade (black over ~10 frames, flip, ~15 in) | with `eyes` | shots every frame across the end change (`GAME_SHOT=<f-20>,1,0,<f+40>`): dark frames then the turned view, never a half-turned frame; log shows no jump > 1 unit per frame in rallies |
| 4 | **Head hidden** (bubble, skinned programs only; shadow programs kept) | with `HIDE=head` (default in `eyes`) | `FRAMEMAP` once to list the player programs; shots looking ahead and down (`VIEW_TURN=0,-50`): no hair/cap/face pieces; head's ground shadow still there; the opponent whole (shots at the far player); `LINDBERGH_FRAMEMAP` draw count unchanged |
| 5 | **Serve meter and 1P marker in POV** (meter point ahead at chest height, own marker hidden) | with `eyes` | `LINDBERGH_VT3_SERVELOG=1 LINDBERGH_VT3_SERVESHOT=2,3700 LINDBERGH_SHOT_BOTH=1 LINDBERGH_GAME_SHOT=99999,1 ... round0 quest 165`: the meter ~60 cm ahead-right in both eyes through the fill; at the far end (~6800+) too |
| 6 | **`behind` variant** (c), and **`snap`** (d) with a 6-frame blink | with those values | shots as step 2 (own player ~1.5 m ahead, whole); `snap`: log the snaps (one per point start, plus distance snaps), shots across one: dark, then the new place |
| 7 | **Vignette** (alpha ring by anchor speed, drawn last in the eyes) | `VIGNETTE=1` | shots mid-sprint vs standing; GPU cost |
| 8 | **Panel row and vr.cfg** (`immersive.view seat|behind|eyes|snap`; `xr_world_panel` row on the Immersive page; `world_mode` key `WM_VIEW`) | the setting exists, default `seat` | `python3 -m unittest tests.test_world_mode tests.test_xr_world_panel tests.test_xr_settings`; `LINDBERGH_XR_FAKE_MENU=1 LINDBERGH_XR_MENU_PAGE=2 LINDBERGH_XR_MENU_DUMP=1` picture; `LINDBERGH_XR_MENU_CLICKS` cycling the row (live: it is a view value like dolly) |
| 9 | **View-relative analog stick** (`pad::exec` wrap; human pad only; POV modes only) | `POV_STICK=1` (default on in POV) | `LINDBERGH_VT3_POV_FAKE_STICK=3000:0,3100:90,3200:180,3300:270` with `POV_LOG`: the root moves toward the net, then right, back, left in the view's terms, at both ends; Seat mode unchanged (the lever path) |
| 10 | **Experiments, each its own switch:** gaze aim while a shot button is held; swing gestures (take-back = press); visual racket at the controller with the body hidden; follow-me room-scale | off by default | aim: `FAKE_YAW` held through a rally and the ball's landing x in the log; gestures: a recorded controller trace replayed (`LINDBERGH_XR_...` replay switch to be added) and the button bytes `+0x2a4..` logged |
| 11 | **Regression** | none new | `prize` Immersive with `VIEW=eyes` and `seat` (flow, slates 600, next round), Classic `prize` unchanged, replays `world` with POV (anchor = last POV view), `[black]` only boot/load, GPU log |

**Only the owner can judge, worn:**

- comfort of each variant in a real rally (b vs c vs d), the smoothing time,
  the vignette strength, the fade at a change of ends;
- whether life size (scale 10) feels right, and the eye height;
- head-only versus whole body hidden; whether seeing your own arms swing on
  their own is fun or disturbing;
- whether the ball is readable at life size, and the ball size option;
- the stick direction feel (view-relative vs. the old screen-relative);
- the serve meter's place in POV;
- any experiment in step 10.

## Verified versus inferred

**Verified (disassembly / code):** units = 0.1 m (court constants, start
table 0x838aea0); `vr.scale = 1` and the head-position scaling
(`lg_stereo_pose_view`); the player list at `g_pTennis` and the human test
(`+0x08 <= 3`, `keyScan`); `+0x18` root (`setPosition`), `+0x68` facing,
`+0x28` yaw; the bone list at `+0x14b0` (names at 0x841e420) with Head /
eye_L / eye_R / Hand_R / racket_model; node `+0x88` world matrices;
`+0x1574` = eye midpoint (`calcFacePosition`); head forward = -column 1 of
the Head bone (`getEyePosition`); `player::exec` call order; the draw path
(`playerManager::draw` -> `player::draw` -> `SceneObj::addScene`) and the
put byte `+0x05`; the camera's mirror flag `camera+0x1c8` bit 0; the
lever: `pad::exec` bits, the unused analog `+0x1c/+0x20` / 32767 path,
the turn by the camera's inverse view in `keyScan`; ball radius 0.35;
`eye_projection`'s structure and the near plane.

**Inferred (to check in the steps):** that the players' shadows come from the
same scene object (hiding by `player::draw` loses them); which GL programs
are the players' (skinned) colour passes and whether the racket's is rigid;
the face height (~16.5 units); the camera set after the player update for
the same frame; the analog magnitude's meaning; how the aim is taken at the
hit; the ball blur's orientation; no player LOD; the HUD keeping its place
in metres with the POV scale.
