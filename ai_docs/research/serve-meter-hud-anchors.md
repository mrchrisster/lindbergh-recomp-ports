# Serve meter and 3D-anchored HUD in immersive (world) mode

Research for the backlog bug "Serve strength meter not showing correctly in
immersive mode – sometimes fine, then glitches in the last second". The
analysis is static: the disassembly of the unstripped ELF
(`~/code/quest_games/vt3/disk0/vt3_Lindbergh/vt3_Lindbergh_HD`), the game data
and the runtime source.

Tags: **[V]** checked in the disassembly, data or runtime source;
**[I]** inferred (geometry or a reading of the data); **[M]** measured on the
headset after the research.

## Outcome

- Implemented as **Part 1 + candidate (a)** (see "Fix designs") in submodule
  commit `19c451a`:
  - `arbprog.c`: an exact pixel-camera match (`cam_exact`). A draw made through
    the pixel camera's own projection gets that projection, whatever its model
    matrix's scale. `LINDBERGH_VT3_PIXCAM=0` turns it off.
  - `stereo.c` `stereo_vt3_hud_anchor` plus a `hle_sega.c` wrap of
    `hud::getScreenPosFrom3DPos` (`h_vt3_screen_pos`). In world mode the 3D
    anchor is projected through the eyes' real matrices onto the HUD plane.
    `LINDBERGH_VT3_HUD_ANCHOR=0` turns it off.
- The measurements **[M]** confirmed both mechanisms:
  - **Glitch:** worse than predicted. The wrong lens stayed in `good` on the
    way down from max, and HUD sprites scaled uniformly were drawn unscaled.
  - **Misplacement:** near end ~140 HUD units low, far end ~1.6x too far out.
- Part 2b (re-anchoring the latched serve meter every frame) was **not
  needed**.
- `G` at 0x850e280 is the **identity** at run time.
- The esp off-by-one aside (end of "Fix designs") was confirmed, and fixed for
  the log hooks.

## 1. What the game does

### `hud::getScreenPosFrom3DPos(_sSerial::_sVector3d const&)`, 0x8110f2e [V]

- **ABI:** returns a `_sVector4d` through a hidden pointer and pops it itself
  (`retl $4`). Stack at entry: `[esp+4]` = return pointer, `[esp+8]` = hud
  `this`, `[esp+12]` = `const _sVector3d*`.
- **Camera:** the game camera object at `g_pTennis` (0x85061a4) `->+0x38`. Its
  virtual `+8` returns the `_sCamera`.
- **Matrix:** `M = proj44(cam+0x34) * view34(cam+4)`, built with
  `_sSerial::_sMatrix44::setMul(44, 34)` (0x8111aaa). This is the broadcast
  (match) camera.
- **Maths:** `x = M.row0·(p,1)`, `y = M.row1·(p,1)`, `w = M.row3·(p,1)`, then
  output `(x/w * 480, y/w * 360, 0, 1)`. If `tennis::bWide_` (0x850c890) is set,
  x is also multiplied by 4/3. Constants: 0x8380cbc = 1.0, 0x838b930 = 480,
  0x8384cec = 360, 0x838b934 = 1.3333.
- **Result:** the game camera's NDC scaled to a centred HUD space of
  ±640 x ±360 (wide), y up.

### `hud::drawServePower()`, 0x810f28e (called from `hud::draw`) [V]

**Handles.** `res = g_pTennis->+0x7c` (`ab_game_info`).
- `A = res+0x14`: the gauge, model 0 of resource slot 1.
- `B = res+0x18`: the frame and effects, model 1 of the same resource.
- `ab_game_info::add_all` (0x80501bc) loads slots 0, 1 and 2 from resource ids
  0x74, 0x76 and 0x78. The file-name table `ab_util::createResource` reads is
  at 0x84194a0:
  - 0x74 `I_GME_pointer_KB.abd`: the 1P/2P markers.
  - 0x76 `I_GME_serveGauge_TR.abd/.abr`: the serve gauge.
  - 0x78 `testPrimitive.abd`.

**Which player.** It loops over all players (`g_pTennis[0]` is the count,
`g_pTennis[1][i]` the player). A player counts as serving when state `+0x265`
is not 0 or 4 and `+0x258 != 0xF`. Nothing filters out CPU players.

**First frame, while `hud+0x60 == 0`:**
1. `B.play()`, `A.play()`, `B.finishBranch(9)`, `B.finishBranch(10)`.
2. `s = getScreenPosFrom3DPos(player+0x18)`, the player's root position.
3. Quadrant offset:

   | Quadrant | Offset |
   |---|---|
   | sx < 0, sy ≥ 0 | +(50, 0) |
   | sx ≥ 0, sy ≥ 0 | +(−50, 0) |
   | sx < 0, sy < 0 | +(80, 70) |
   | otherwise | +(−60, 70) |

   Constants 0x8380804 = 50, 0x838b920 = −50, 0x83817e8 = 80,
   0x83892b4 = 70, 0x838a14c = −60.
4. `Mtx = G(0x850e280, a 3x4 in bss) * T(sx+ox, sy+oy, 0)`. `G` is the
   identity at run time **[M]**.
5. `TScene::AbHandle::setMatrix(_sMatrix34 const&)` (0x818f54c) on B, then A.
6. `hud+0x60 = 1`.

**The position is latched once per serve and never updated.**

**Every frame:**
- `A.setFrame(power*100)` (0x818f3a0), with power at `player+0x244`.
- When `power*100 ≥ 100` and the static flag `max` (0x8500840) is clear:
  `B.startBranch(9)`, `B.startBranch(10)` (0x818f6e6), `max = 1`.
- When it drops back below 100 with `max` set: `B.finishBranch(9)`,
  `B.finishBranch(10)` (0x818f7fc), `max = 0`.
- A `_sSceneManager::getProject` call on `(pos.x ∓ 10, 10, pos.z)` writes a
  result that is never read: dead code.

**No serving player:** the visibility bytes `+0x14/+0x15` of both handles are
cleared, and `hud+0x60` and `max` are reset.

### Serve power states, `player::calcServePower(long)` at 0x81596a0 [V]

| `+0x265` | Meaning |
|---|---|
| 0 | idle |
| 1 | charging: power += `getAddServePower()` each frame |
| 2 | maxed: reaching 1.0 sets this, then `setRegist(&power, 0, 0.1)` makes power fall away |
| 3 | swung (`adjustServePower`) |
| 4 | done |

The meter shows in states 1 to 3. So the "last second" is the stretch from
about 85% up to max, the fall-back from max and the hit.

### The gauge's fill is a Y scale [I, data; consistent with the measurements]

`I_GME_serveGauge_TR.abd`, file offsets 0x324–0x368, holds a 3-vector key
`(1, 0, 1)` at t = 0 going to `(1, 1.01, 1)` at t = 101.0. So the gauge bar is
a **Y scale from 0 to 1.01 driven by `setFrame(power*100)`**: its model matrix
is non-uniform, with sx = sz = 1 and sy ≈ power. Other keys in the file
(values 0.2–1.0 and 0.95 at times 24–25) look like the pulses and alpha of the
max branches 9 and 10. The `.abr` also carries Acrobata cameras
(`CAM03_1609` for 16:9, `CAM03_0403` for 4:3).

### The matrix that reaches the draw [I; confirm with `[envp]`]

The gauge sprites go through the pixel camera: lens 1.45455 / 2.57576,
n 800, f 1050, level, 989.092 back.

    MVP = P_pix * V_pix * G * T(sx+ox, sy+oy, 0) * AB node (S(1, sy_fill, 1) for the bar)

By rows, with tz ≈ −989:
- r0 = (P0·sx, 0, 0, P0·tx)
- r1 = (0, P5·sy, 0, P5·ty)
- r2 = (0, 0, A·sz, A·tz + B)
- r3 = (0, 0, −sz, −tz)

The HUD programs build position by columns (MUL/MAD, pos_kind 1), so
`program.local[0..3]` holds the columns.

## 2. Other HUD items anchored to 3D [V]

All callers of `getScreenPosFrom3DPos`:

| Caller | Call site | What it anchors |
|---|---|---|
| `hud::drawServePower` (0x810f28e) | 0x810f4f1 | serve meter, latched once per serve |
| `hud::setPlayerIcon(int)` (0x8110c40), from `hud::drawPlayerTag` (0x810f8f0) | 0x8110c7d | 1P/2P markers, re-anchored every frame through `AbHandle::setMatrix` |
| `ab_game_info::initPlayerIcon(int, bool)` (0x80521d2) | 0x8052229 | marker set-up; re-runs when the marker changes quadrant |
| `hud::drawChallenge_result_ball` (0x8110548) | 0x81105ad | challenge result marker, on the player from `vs::getGame_master` |
| `hud::drawGameInfoPlate` (0x81106fe) | 0x8110827 | players' screen positions, used only to keep the plate from overlapping them |

Not HUD anchors:
- `hud::drawSpeed_meter` (0x810f8ea) is an empty stub.
- `mtrMath::vecToScr*` serves the camera logic (`camera::player_scr_in_all`,
  `camera::gameRoutine_kawa`) and 3D sound (`sound::playSe_3D_cam`).
- `HyScreen::CalculateProjection` serves Acrobata effects (`_abmBlurBelt`,
  `_abmBillboardTail`, `_abmTexScreen`).
- `drawPlayerTag` also calls `_sSceneManager::getProject` and
  `mtrMath::vecToScr_check`, for its on-screen check.

## 3. How the runtime treats these draws in world mode [V]

- **Class.** Pixel-camera sprites are perspective draws, so
  `lg_stereo_classify_draw` gives them **`LG_STEREO_WORLD`**. See the comment in
  `stereo.c` `stereo_draw_not_screen`, which tells them apart only by an exact
  lens match against `g_game_layer_x`.
- **Projection P.** `arbprog.c` `arb_env_projection` takes the MVP apart: lens
  = `lx/s`, `ly/s`, depth from `c[3]`. Before the fix, only the broadcast camera
  had an exact match (the shadow fix's `same` test).
- **Eye matrix.** `stereo.c` `effective_projection` takes its deep branch:
  - near is 0.05x, because the pixel camera's near is above 10;
  - `lg_stereo_eye_projection` applies the eye's frustum, then `g_view[eye]`
    (head pose, `vr.scale = 1` for VT3);
  - then the dolly and step-back `out*T(t)`, with t ≈ (0, ~−20, 200 − ~56).
- **Result.** `u_reproj = eff * inv(P)`. The HUD plane (z ≈ −989 in pixel-camera
  space) is treated as broadcast-camera space and becomes a world plane about
  845 units ahead. It is tied to the game camera, not to the head.

### Misplacement mechanism (always present) [I, then M]

- Angle from the dollied eye of a HUD point at game NDC n:
  `n·0.6875·989/845 ≈ 0.80·n`.
- Angle of the player: `n·0.312·|Zp|/(|Zp| − 144)`.
  - Near-end player (|Zp| ≈ 260): ≈ 0.70·n.
  - Far-end player (|Zp| ≈ 450): ≈ 0.46·n.
- So the meter lands about 1.15x (near) to 1.75x (far) farther out from the
  view centre than the player, plus a vertical offset from t_y. That fits
  "sometimes fine", since players change ends.
- **[M]** near end ~140 HUD units low; far end ~1.6x too far out.
- Stereo and head translation hardly matter at `vr.scale = 1`: the parallax
  between the ~845 and ~200 depths is under 0.1° for a 0.3 m lean.

### "Last second" glitch mechanism [I, then M: confirmed, worse than predicted]

`arb_env_projection` assumes the model matrix is rigid. With the bar's
`S(1, sy, 1)` it reads `ly/s = P5·sy`:

| sy | What happens |
|---|---|
| < 0.019 | the `ly/s < 0.05` test fails, so it uses `good` |
| 0.019 to 0.85 | the immersive-only `keep_shape` aspect test (more than 15% off 1.771) fails, so it uses `good` |
| **0.85 to 1** | it accepts `P' = P_pix·diag(1, sy)` and writes `P'` into `good` |

`good` is the last P that passed. Usually it is the previous HUD sprite's exact
pixel P, so the bar looks right. If the previous draw went through the
broadcast camera, the bar lands about 2 units from the eye.

In the 0.85–1 band, `inv(P')` gives `y_eye/sy`. The bar is therefore drawn at
full height and shifted vertically by 1/sy, up to 18% of its distance from the
HUD centre. Because `P'` is also written into `good`, later fallback draws
inherit the wrong lens. That includes the bar itself on the way down from max
below 0.85, and it lasts until some ordinary sprite resets `good`. At exactly
sy = 1 (power 1.0) the bar is right again.

A sprite scaled uniformly (sx = sy = s, sz = 1), such as the max-branch pulses
on B or the markers, reads lens·s and is placed at t/s, unscaled. **[M]**
uniformly scaled HUD sprites were indeed drawn unscaled.

Flat mode is unaffected: there `eff = p`, so `u_reproj = I` and misreads
cancel. Side effect: scaled sprites miss the exact-lens test in
`stereo_draw_not_screen`, so they also got the decal polygon offset.

## 4. Fix designs

### Part 1 (required, fixes the glitch): exact pixel-camera projection — implemented

- In `arb_note_projection`'s pixel branch, keep the pixel camera's projection
  (transposed like the world one).
- In `arb_env_projection`, test a draw against it with the same two-way
  "row 3 + A x row 4 = (0 0 0 kB)" test used for the broadcast camera. The
  test is unaffected by model scale and rotation. The pixel camera has
  A = −7.4, B = −6720, far from the world camera's −1.0007 / −2.0007.
- On a match, use the pixel P and leave `good` alone.
- Unscaled sprites read exactly as before.
- `LINDBERGH_VT3_PIXCAM=0` turns it off.

### Candidate (a), placement: wrap `getScreenPosFrom3DPos` — chosen, implemented

`stereo_vt3_hud_anchor(world[3], ndc[2])` works as follows:

    for eye v in 0, 1:
      Ew = effective_projection(world P, LG_STEREO_WORLD)
      Eh = effective_projection(pixel P, LG_STEREO_WORLD)
      (save and restore g_eye and g_last_persp, which effective_projection writes)
      pe   = g_game_view * world
      clip = Ew * pe;  n = clip.xy / clip.w      (fail if clip.w <= 0)
      solve (row_i(Eh) - n_i * row_3(Eh)) · (hx, hy, -d, 1) = 0  for i = 0, 1
                                                 (d = 989.092, the HUD plane)
      ndc_v = (hx * Pp0 / d, hy * Pp5 / d)
    ndc = average of ndc_0 and ndc_1

The wrap (`h_vt3_screen_pos`) calls the original, then overwrites the result
with `(ndc.x * 480 * k, ndc.y * 360)`, k = 4/3 when `bWide_`. It is skipped
when the world camera is not known yet, and in flat mode.

Why this one:
- One hook covers every caller: serve meter, markers, challenge marker, info
  plate.
- It uses the runtime's own dolly, step-back and head pose, so both eyes line
  up and head turns keep it on the player.
- It is a leaf hud function, not one of the camera routines that hang under the
  generic wrap (`camera::procMain`, `ab`, `calcParameter`, `setLook_down`).

`LINDBERGH_VT3_HUD_ANCHOR=0` turns it off.

### Part 2b: re-anchor the latched serve meter every frame — not needed

The idea was a wrap of `hud::drawServePower` that recomputes the position with
the stored quadrant offset and calls `AbHandle::setMatrix` on both handles
every frame, so the meter follows the camera and head during the toss. **[M]**
the meter did not visibly drift once (a) was in.

### Candidate (b): draw the meter as a world-space billboard at the player — rejected

Acrobata drawing is deferred: `AbHandle::draw` (0x818f2fc) calls
`AbkTrunk::ServerDraw`, which goes through `HyEnv::AddCallback` to
`_sSceneManager::addCallBack`. The GL draws happen later, in the scene render,
so wrapping `drawServePower` or `AbHandle::draw` does not bracket them. Doing
(b) would mean finding the meter's draws one by one (by texture, or by the MVP
translation near a captured anchor) and swapping in a custom `u_reproj`. That
is fragile, and the real depth it buys is negligible at `vr.scale = 1`.

### Candidate (c): pin the meter to a fixed HUD position — rejected, fallback only

Trivial and robust, but it loses the meter's link to the player. Part 1 would
still be needed for the scale glitch.

### Aside: ABI of override handlers [V, then M]

An override handler is entered with esp pointing at the first argument:
`dispatch.c` pops the return slot (`dispatch_slow`, `dcache_run`). A wrapper
calls the original with `push32(c, 0xDEADBEEF); orig(c);`. For this sret,
callee-pop function, the original's `retl $4` pops the dummy and the sret slot,
which leaves esp where the caller expects it.

The existing `h_vt3_game_routine` read `self` at `esp+4`, and `CAM_DEF` read
its argument at `esp+8`: one slot off. **[M]** confirmed, and fixed for the
log hooks.

## 5. How to verify (headset)

1. **Scene:** `scripts/vt3-repro.sh forty quest` (`LINDBERGH_VT3_POINTS=3,0`).
   Games are short and the server alternates, so 1P serves every other game.
   Check both ends. Someone has to wear the headset and serve, because
   `AUTOPRESS` is SDL/mac only. The meter loop doesn't filter CPU players, so
   note whether CPU serves show it.
2. **Per-serve log:** log `frame, player, state +0x265, power +0x244,
   hud+0x60, max 0x8500840`, plus the original and corrected positions. Trigger
   an `[envp]` dump (`LINDBERGH_MVP_DUMP`) once at power ≈ 0.5 and once at the
   first frame with power ≥ 0.85.
3. **Before the fix:** for the gauge draws, expect `same 0`, x lens 1.455 and a
   y lens (|row1| / |row3|) of 2.576·sy. `LINDBERGH_DRAW_LOG=<f>` shows them as
   `hud 0` (world).
4. **Pictures:** `LINDBERGH_XR_SHOT=<F0>,3` with `LINDBERGH_XR_SHOT_FULL=1` and
   `LINDBERGH_SHOT_BOTH=1`, or `LINDBERGH_GAME_SHOT=<F0>,3,1` for unattended
   runs, through the toss. Take the same frames with `LINDBERGH_VT3_IMMERSIVE=0`
   as the flat reference.
5. **After the fix:**
   - no jump or full-height flash from 85% to max or on the way down;
   - the meter and the 1P marker at the player at both ends, in both eyes;
   - re-test with `LINDBERGH_XR_FAKE_YAW=25`;
   - turn each part off on its own with `LINDBERGH_VT3_PIXCAM=0` and
     `LINDBERGH_VT3_HUD_ANCHOR=0`.
6. **Regression checks:** scoreboard, speed readout and logo screens
   unchanged; no blacked-out layers (as `LINDBERGH_VT3_GAME_CAM=1` caused);
   flat mode identical.
