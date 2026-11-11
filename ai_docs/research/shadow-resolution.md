# Shadow resolution in Immersive mode (research, 2026-11-11)

## Outcome (build worker, 2026-11-11)

**T1 - leads checked on the Quest** (installed build `77875a4`, `prize`,
Immersive, full-size game shots at frame 2300):
- **Which texture is the mask:** `LINDBERGH_COPY_LOG=1` + `LINDBERGH_FRAMEMAP=2300`.
  In a match the game copies the whole screen **three times per frame, all
  into game texture 45** (1360x768). The first copy comes right after the
  planar shadow draws (vp 0x8d/0x89 = 141/137, fp 0x72 = 114) and before
  the frame's first stadium draw - that is the ground mask; the later two
  (after the stadium) feed the depth-of-field / glare chain. Textures 33/34
  are copied only at cuts (the cross-fade capture, `fade::execCapture`);
  texture 40 in the menus.
- **`LINDBERGH_SHADOW_SCALE=1` vs `4`** (1024 vs 4096 map): the player's
  ground shadow is **identical** in sharpness and edge steps (3x crop, same
  pose). The low-res ground shadow is the screen-space mask, not the shadow
  map. Confirmed.

**T4 - per-eye mask: written, NOT run on the headset (uncommitted)** - the
headset was unplugged before it could be tried. Design as recommended in 2.1
+ 2.2: at the frame's first whole-screen copy from the eyes (world frames)
`stereo.c` `mask_copy` also copies both eye layers 1:1 (NEAREST blit) into a
runtime twin - a 2D texture of eye size whose gl4es array holds both views
(`gl4es_multiview_copy_layers`, new in `quest/gl4es.patch`); any later copy
into the game's texture that frame (the depth-of-field chain's) ends the
twin's use. A fragment program reading a screen copy (`u_scr` units) gets a
third branch: `u_scr.x < 0` -> `lg_mask(inv)`, 5 taps 1.3 eye pixels apart at
`gl_FragCoord` in `sl_<K>` at `gl4es_layer`, K the last texture unit gl4es
has (`vt3_mask_unit`, bound in `upload()` for that draw). The game's 1360x768
copy still happens (DOF chain, cross-fade, Classic). `LINDBERGH_VT3_MASK=0`:
the old path. Memory: 2 x 2064 x 2208 x 4 B = 36 MB. Expected GPU cost: one
2-layer 1:1 blit (~0.2-0.4 ms, to measure). Checks owed: HANDOFF 3.1.

T6 (self-shadow tile zoom, rec. 3): not started - the budget went to T2-T5
and the headset was away.

**Summary for the owner**
1. The low-res shadow you most likely see is the players' **ground shadow**. It is not the 2048 shadow map: it is a screen-space mask. The eye's image is squeezed into a 1360x768 texture with one bilinear blit, then stretched back over the court. Each mask texel covers about 1.5 x 2.9 eye pixels, so the edges come out jagged and crawl when you move your head.
2. The "Shadow quality High = 2048" setting only affects the players' **self-shadowing** (arm on shirt, and so on). Even there the game uses only a centred 128x128 or 256x256 tile of its 1024 map per player (256/512 texels at 2048).
3. Best fix for the ground shadow: make the mask copy eye-sized, ideally per eye. Then each eye reads its own pixels at its own screen position, which is pixel-exact. Add a small blur in the ground shader so the edges are soft like a real shadow.
4. Best fix for self-shadowing: draw each player's shadow tile larger inside the map, so it fills the map instead of 1/16 of it. Correct the lookup with one scale factor, and replace the 2x2 filter with a wider one. That gives 4-8x more texels at no extra memory.
5. The baked court and stand shadows are painted into the light-map textures (art, fixed). The net, umpire chair and crowd cast no runtime shadows.

## 1. Findings

### 1.1 Ground shadows = a screen-space mask (guide 8, "Player shadows in world mode")
The game clears the screen, draws the planar shadows (vp 141/137, fp 114, stencil once-per-pixel), and `glCopyTexSubImage2D`s the screen (0, 0, 1360, 768) into a game-allocated **1360x768 RGBA** texture. In Quest logs, textures 34/40/45 are "the screen copy is 1360x768 of 1360x768" (game texture ids). Which one is the mask is not yet pinned; on macOS it is tex 22, copied once at the frame's start.

Ground programs read the mask with `TXP` on unit 1. In world mode, `arbprog.c` (`vt3_screen_fix`, `u_scr`) swaps in a read at `lg_eye0` (the point's position in eye 0) mapped through `stereo_screen_copy_map`.

Where the copy's size is decided:
- The texture size is the game's own `glTexImage2D`, 1360x768. That is not one of `stereo.c`'s render targets: only textures attached to framebuffers go through `lg_stereo_target_scale` (stereo.c ~670), which is how texture 33 became 2064x2208.
- The copy itself is `copy_from_eyes` (stereo.c 1393-1450): `gl4es_multiview_copy(g_eye_tex[0], layer 0, 0, 0, eye_w, eye_h -> dst 0, 0, 1360, 768)` = `glBlitFramebuffer(..., GL_LINEAR)` (quest/gl4es.patch ~1083).
- The map is then `(GAME_W/tw, GAME_H/th, ...)`.

Effective resolution, eye 2064x2208 against mask 1360x768:
- One mask texel = 1.52 eye px across x 2.875 eye px down, about 4.4 eye pixels.
- A single-tap bilinear blit at 2.9x vertical minification samples 2 of every ~3 rows (aliasing). The ground shader then magnifies it again with bilinear filtering, giving stair-steps about 3 eye pixels tall.
- The right eye reads the left eye's mask, reprojected through `lg_eye0`: correct placement, but it doubles the resampling.
- On the ground: at the near player (~10.7 m away, view ~31 deg below horizontal, ~21 px/deg), a mask texel is ~1.3 cm wide by ~5 cm deep on the court. In Classic the same mask was 1:1 with its own 1360x768 screen.

Other users of the copy textures: the depth-of-field and glare chain uses screen copies too (game textures 34/40/45, render targets 29-33). Their lookups use normalised `TEXTURE_2D` coordinates, so resizing a copy texture keeps them working, except for any blur offsets given in texels (a narrower blur at most).

### 1.2 Self-shadow depth map (`LINDBERGH_SHADOW_SCALE`)
- Classic macOS frame map, `round0` frame 2600: the shadow FBO (depth tex 19, colour tex 20, 1024x1024) is used in **two passes per frame, one per player**. Viewports are 130 then 128 at offset 447/448, and 258 then 256 at offset 383/384. Each pass clears a centred tile plus a 1-pixel border, then draws that player depth-only (fp 202/166, vp 117/135). That player's body is then drawn reading tex 19 (vp 133/149/153/165/169/177...). Then the other player follows.
- So each player gets a **128 or 256 texel tile** of the 1024 map: probably the far player 128 and the near one 256, chosen by the game. In Immersive (`render target 41: 1024x1024 -> 2048x2048`) `note_fb_scale` doubles them to 256/512. The rest of the map is unused.
- `lg_pcf` (arbprog.c ~1344): one bilinear 2x2 compare at `u_shadow_size` (the full map size). The kernel is one texel of the map, so it shrinks with the map; it does not widen. Shadow bias: `LINDBERGH_SHADOW_BIAS` / profile `vr.shadow_bias`.
- **Not yet determined:** the light frustum's world width, which gives cm per texel. The next step is `LINDBERGH_MVP_DUMP=2600` on a Classic run (vp 135 locals in the shadow pass: width = 2/|row0.xyz| if the frustum is orthographic). If it is ~3 m (one player plus racket), the 512 tile is already ~0.6 cm per texel, and self-shadowing is not what looks low-res.

### 1.3 Other shadows
- Court, stand and wall shadows are baked into the light maps (uv1 of the 40-byte stadium vertices, fp 229/230, s2_2): art, fixed resolution.
- Net, net posts, umpire chair, bags, crowd: no runtime shadow draws in the frame map (only the two players, plus the vp 117 draws inside the passes, probably rackets and ball). The ball's shadow is planar, in the mask.

## 2. Recommended fixes (ranked)

### 1. Per-eye, eye-sized ground mask (biggest visible gain; GPU about +0.3 ms, an extra layer blit; ~36 MB for two layers)
Treat the mask copy as an "eye picture". On a full-screen copy into a texture the ground programs read, the runtime keeps its own 2-layer array of eye size (`gl4es_multiview_array`-style) and blits **both** layers 1:1 (no scaling). In the ground fragment shader, read the layer of the current view at the fragment's own screen position:
```glsl
// world draw, unit u holds the shadow mask copy
vec2 st = gl_FragCoord.xy / u_eye_size;          // this eye's screen 0..1
float m = texture(sr_mask, vec3(st, gl4es_layer)).a;   // same pixels the shadows were drawn to
```
Code points:
- `copy_from_eyes`: also copy layer 1, into the runtime's array, at eye size.
- `arbprog.c`: the `u_scr` branch reads `sr_` per view (the `g_tr_layered` mechanism already exists for "units holding the world's picture").
- `stereo_screen_copy_map` becomes the identity.

This needs no `lg_eye0` reprojection and is exact in both eyes. The game's own 1360x768 copy stays as it is for the DOF chain.

A simpler first step: keep `lg_eye0`, but make the copy target eye-sized for that one texture. Intercept the game's `glTexImage2D(1360x768)` for textures later used as the mask, or allocate a runtime twin and blit 1:1. That removes the 2.9x squeeze, but the right eye is still reprojected.

### 2. Soft edges in the ground lookup (cheap; 4-8 taps on ground pixels only)
The planar shadows are hard polygons. At eye resolution and without MSAA they alias. In the same lookup, take a 5-tap or rotated 8-tap disc of radius ~1.5 eye px (or a fixed ~3 cm on the ground, scaled by `fwidth(world)`) and average. Pair this with fix 1. Done alone on today's mask, it just blurs the stair-steps (still a visible gain, near-zero cost).

### 3. Self-shadow tile zoom (4-8x more texels, no extra memory)
In `note_fb_scale`/`apply_rect` (stereo.c), for viewports into a shadow-map target that are centred tiles smaller than the target, scale the viewport and its clear to fill the target, e.g. factor `z = target/tile` capped at 8. Then in `lg_pcf` remap first:
```glsl
c.xy = 0.5 + (c.xy - 0.5) * u_shadow_zoom[unit];   // the game baked tile/size into its texture matrix
```
`u_shadow_zoom` is the actual tile over the game's tile, set per pass. Each player's pass rewrites the tile before that player is drawn, so sharing the map between players still works. Cost: one 2048² depth clear per player pass instead of 512², plus depth-only player draws, well under 0.2 ms. Verify that the game's tile really is centred at 0.5 (offsets 448 = (1024-128)/2 and 384 = (1024-256)/2 say yes) and that no scissor is set in the pass.

### 4. Wider PCF
Replace the 2x2 with a 3x3 bilinear-weighted PCF (9 taps, each a 2x2) or 12 Poisson taps rotated per pixel. Give it a radius in texels that scales with the zoom, so the penumbra is ~1-2 cm in the world. Cost: player pixels only (~5-15% of the eye), 9-16 fetches each; about +0.1-0.3 ms. A 4096 map (the Shadow quality setting already allows it) adds 4x the memory and clear cost for less gain than fix 3.

### 5. Leave the baked shadows (art), or add anisotropic filtering for the court (see crowd doc 2.4)
This is not a resolution fix for the light maps.

## 3. Captures for the build worker (headset, Immersive, `prize` or `round0`)
- Crops of the near player's feet at a serve, both eyes (`LINDBERGH_VT3_SERVESHOT=1,3700 LINDBERGH_SHOT_BOTH=1 LINDBERGH_GAME_SHOT=99999,1`):
  - today;
  - `LINDBERGH_VT3_SCREENFIX=0` (expected wrong placement, the reference);
  - `LINDBERGH_SHADOW_SCALE=1` versus 2 versus 4 (if the ground shadow does not change, it is the mask that looks low-res: confirms 1.1);
  - `LINDBERGH_SHADOW_LIT=1` (self-shadow off: shows what the depth map contributes).
- `LINDBERGH_COPY_LOG=1` and `LINDBERGH_FRAMEMAP=<frame>`: which texture id is the mask copy (the one bound on unit 1 for the ground draws), and its size line.
- `LINDBERGH_MVP_DUMP=<frame>` (desktop is enough): the light frustum width for 1.2.
- After fixes 1-3: the same crops, plus `LINDBERGH_GPU_TIME=1` over a rally.

## 4. Verified vs inferred
- **Verified:**
  - Copy path and squeeze: code in stereo.c and gl4es.patch; sizes from Quest logs (screen copies 1360x768, target 41 1024 -> 2048, eye 2064x2208).
  - The two shadow passes per frame with centred 128/256 tiles, and the receivers reading tex 19: macOS Classic frame map.
  - The `lg_pcf` kernel: code.
- **Inferred:**
  - Which shadow the owner means (the ground mask; the reasoning is in the summary).
  - Near player = 256 tile.
  - The cm-per-texel numbers for the mask (a ~21 px/deg eye and a viewpoint about (0, 54, 216) assumed).
  - The GPU cost estimates.
- **Not determined:** the light frustum width; which of Quest textures 34/40/45 is the mask; whether the eye buffers would accept MSAA cheaply in this multiview path.
