# Crowd and upper stands in Immersive mode (research, 2026-11-11)

## Outcome (build worker, 2026-11-11)

**T1 - leads checked on the Quest** (installed build `77875a4`, `prize`,
Immersive, replays and cutaways off, full-size game shots both eyes at frame
2300/2600; `LINDBERGH_GAME_SHOT=2300,300,1,2600 LINDBERGH_SHOT_BOTH=1`):
- `LINDBERGH_SKIP_FP=158`: **every spectator gone** (seated and standing),
  the stadium untouched - fp 158 is the crowd cards. Confirmed.
- `LINDBERGH_SKIP_FP=229,230`: **the stadium shell gone** (stands, walls, ad
  boards, umpire chair, net), the court surface, people and every crowd card
  left floating over an empty plane - fp 229/230 are the light-mapped stadium
  meshes. The guide's "158 seating, 230 crowd cards" was reversed (corrected in
  the guide).
- The crowd cut (`LINDBERGH_VT3_CROWD_CUT`, applied to fp 230) therefore cut
  **stadium geometry**, not cards: with it off (`=0`) the far end's light masts
  above y 55 come back (they are missing in the default shot); the floating
  cards are the same with it on or off.
- Round 0 (Ita3F) shows the floaters exactly as described: the upper-tier
  cards (2F) and the standing spectators hang above the side stands' tops and
  the far stand.
Raw images (not committed, game content): scratchpad `runs/A_base`,
`B_skip158`, `C_skip229`, `D_nocut`.

**Summary for the owner**
1. Yes, the upper bleachers exist. Every venue ships full 2nd and 3rd tiers, plus roof, walls, ducts, upper scoreboards and a sky dome, in its stadium model. They are loaded every match.
2. The game hides them on purpose. `field::draw` skips the model's `GAME_NO` group (and the stand behind the camera) while the camera is the court camera (modes 1 and 2). The broadcast camera never frames them; replays and close-ups do draw them.
3. The audience manager does not follow that rule. In later rounds it draws the upper-tier crowd cards, and on every court it draws the "standing" spectators (some up to 19 m high). Those cards sit on seats that are not being drawn, so they float.
4. Recommended fix: in Immersive, draw `GAME_NO` and both end stands (a small hook on `field::draw`). Then drop the stand stretch (x1 instead of x1.5) and delete the crowd cut. The people then stand on real seats and keep their real proportions.
5. "Low resolution": the crowd art is 512x512 DXT5 atlases, ~43x128 texels per spectator. On the Quest the game's sharpening (LOD bias -1) is thrown away by gl4es, so the crowd shows one mip level blurrier than Sega intended. The x1.5 stretch and the aliased alpha-test edges (no MSAA) add to it. Putting the LOD bias back in the shader is a cheap, honest fix.

## 1. Findings

### 1.1 Stadium model structure (all 8 venues)
Files: `resource/model/field/S_<court>{S,D}_B_stage_TQ_NY.efo` (YABX serial format, self-describing schema; data strings are u16-length-prefixed). Top-level trees: `DHPTH`, `GAME_NO`, `GAME_NORTH`, `GAME_SHOW`, `GAME_SOUTH`. Shape and geometry names carry the group prefix (`GAME_NO_polymsh45_..._seat01_..._cls_Shape`).

`field::createTree` (0x080FFF8E) gives each tree a type byte in `[field+0x3c][i]`: `GAME_NORTH` 2, `GAME_SOUTH` 1, `GAME_NO` 3, anything else 0. The strings are at 0x0838ACDA/E5/F0.

`field::draw` (0x080FFB86):
- `flag = (camera mode [[g_pTennis(0x85061a4)]+0x38]+0x38) in {1,2}`.
- `dz = (target - eye).z` of the game camera (`+0x84` minus `+0x78`).
- When `flag` is set: type 3 is never drawn; type 1 (SOUTH) is drawn only when the camera looks +z, and type 2 (NORTH) only when it looks -z (the end behind the camera is dropped); type 0 is always drawn.
- In any other camera mode (replay, close-ups, intro) every tree is drawn.
- A rare second path (`[ebp-0x2a]`, from `[g+0xf4]`/`[g+0xfc]` checkMode 2) drops NORTH only.

The only reads of `field+0x3c` are in `field::draw` (the entrance tree has its own).

### 1.2 What is in each group (vertex ranges per sub-mesh, unstretched game units of ~0.1 m)
Extracted by parsing vertex arrays (stride 40: pos, normal, uv0, uv1) and the primitive lists (vertex start/count per sub-geometry). Scripts: `scratchpad/crowdshadow/{varrays,prims,shapes,court,allcourts}.py` (scratchpad path of this session).

| Court | Drawn in court camera: SHOW top y | NORTH/SOUTH top y | GAME_NO (hidden) extent | Seat-like meshes in GAME_NO | Crowd tiers (card bases..tops) |
|---|---|---|---|---|---|
| Aus1F | 52 (x±193, z±245) | 48 | x±525 y8..325 z±610 | seat01 y36..80 (x±281 z±333); step01/03 y63..116 (x±376 z±420); step04/passageStep03 y132..192 (x±496 z±548) | 1F 4..47; 2F_A 32..87 (x±280 z±332); 2F_B 72..127 (x±376 z±420); 3F 131..203 (x±496 z±548) |
| Eng1F | 86 | 89 | x±592 y13..264 | seat01 y52..85; step01 y41..218 (x±361 z±477) | 1F 0..59; 2F_A 42..93; 2F_B 104..155; 3F 144..195 |
| Fin0E | (see note) | 65 | x±870 y0..507 | stand01 y12..40, seat01 y16..45 (x±250 z±258) | 1F 0..51 |
| Fra1F | 55 | 55 | x±569 y-13..338 | step01/stepSeat02 y57..238 (x±504..522 z-617..598); step02 y57..117 | 1F 2..45; 2F 57..128 (x±351 z±446); 3F 148..247 (x±502 z±609) |
| Ger3M | 55 | 157 (far town, buildings) | x-693..1060 y0..429 | step01/stepSeat01/step02 y40..80 (x-140..342 z-200..402) | 1F 10..51; 2F 40..91 (x-130..342 z-190..402) |
| Ita3F | 62 | 84 (SOUTH) | x-345..636 y0..215 | seat02 y28..77 (x±266 z-160..308) | 1F 0..51; 2F 24..83 (x±264 z-160..306) |
| Spa3E | (see note) | 49 | x-1752..769 y2..572 | seat01/02 y17..82 (x±345 z±345) | 1F 3..32; 2F 37..88 (x±343 z±343) |
| Usa1N | 42 | 44 | x±658 y26..570 | seat02 y30..61 (x±266 z±320); step01/02 y116..360 (x±634) | 1F 12..49; box 48..67 (x±264 z±318); 2F 116..191 (x±402 z±456); 3F 216..369 (x±634 z±660) |

On every court, every tier above the lower bowl (2F, 3F, the boxes) matches a `GAME_NO` seat/step mesh in x, y and z, often to the unit (Aus 2F_B = step01/03 exactly; 3F = step04 exactly; Ger3M 2F = stepSeat01). Sega modelled the upper stands for the cut-scene cameras and switched them off for the court camera, because it never frames them.

`GAME_NO` also holds `GAME_NO_SKY_Polygon` (a sky dome ~±400 m), the `SUN` sprite, and `SP_SCORE_2F_NORTH/SOUTH` (big scoreboards at y 216..232, z ±491 on Aus).

Note on the table: a few cells are polluted by my vertex-array assignment heuristic: Fin0E/Spa3E SHOW, Spa3E SOUTH x-1500 and Ger3M SOUTH whitechair. Sub-meshes share 65 535-vertex buffers, and I placed each one by the "fits in the parent bbox" rule. The seat/step rows were checked by hand.

### 1.3 Crowd cards
- Files: `resource/model/audience2D/A_<court>_All_<tier>_<half>.efo` (01_01 = 1F south half, 01_02 = 1F north half, 02_xx = 2F, 03_xx = 3F; Ita3F, Ger3M and Spa3E use fewer files), plus `A_<court>_All_stand.efo` (the "stand" file: standing spectators), `audienceAnim.efo` (21 animation frames of the atlas) and `audience_common_texture.efo`. The `_apd.bin` files are hex-text appendix data (texture-anim reference indices, `CAudience2DAppendixDataLoad`).
- The cards are static world-space quads baked in the files. There is no procedural grid and no billboarding. Vertex = 52 bytes: pos(3f), normal(3f), tangent(3f)+sign(f), colour BGRA8 (always 0xFFFFFFFF), uv(2f). They are drawn with **vp 121 / fp 158**: normal-mapped (`audience_NM_xx` in s2_0, colour `audience_CM_xx` in s2_1), alpha test GREATER 0.5. The cheer animation swaps the texture (`setTextureAnim`).
- Measured over all 168 648 seated cards on all courts: height **always 15.0** (1.5 m), width 5 (sometimes 6 / 6.67 / 7.5 / 10), vertex order **always top, bottom, bottom, top** in 4-aligned groups. Atlas cell 1/12 x 1/4, top v smaller (64 exceptions). Bases lie on integer steps of 2, 4 or 6.
- Standing spectators (`_stand.efo`): 26 to 96 quads, **height 20**, vertex order **bottom, bottom, top, top**. Bases go up to 72 (Ita3F), 91 (Ger3M), 192 (Aus1F) and 416 (Usa1N), i.e. on the hidden tiers. They are drawn always.
- How many tiers are drawn: `CAudience2DManager::draw` (0x08090096) draws trees `0 .. min([this+0xac], [this+0x8c])-1`, then the stand tree `[this+0xb0]`. `[this+0xac]` is the crowd level from `make(bool, level)` (0x08090022), adjusted per court through a jump table (1 → 2, 2 → 4, 3 → 6). So attendance grows through the tournament: the first round draws only the 1F, the final draws all tiers.
- **Round 0 = Ita3F** (inferred: the 4 crowd draws at frame 2600 of a Classic `round0` run were 2799 + 72 quads = `A_Ita3F_All_01` 11 196 verts / 4 and the Ita3F stand file). So in round 0 the floaters are the Ita standing spectators (bases 54..72) on the hidden `GAME_NO` seat02 tier. In later rounds the whole 2F/3F crowd floats as well.

### 1.4 Program ids: the guide's labels are wrong
Frame map of a Classic `round0` frame (`LINDBERGH_FRAMEMAP=2600`, `LINDBERGH_ARB_DUMP=1`):
- **fp 158 / vp 121 = all crowd cards** (stride 52, triangles), seated and standing.
- **fp 230 and fp 229 / vp 228 = the light-mapped stadium meshes** (stride 40, two UV sets, cube env map), drawn as triangle strips.

So the guide's "158 = seating, 230 = crowd cards" is reversed. The existing crowd cut (`LINDBERGH_VT3_CROWD_CUT`, applied to fp 230) therefore discards stadium geometry at the far end above y 55, not cards. That is harmless on Aus1F (NORTH tops at 48) but cuts the top of the far stand on Eng1F (to 89) and Ita3F (62), and the far-end town on Ger3M (to 157). This needs a check on the headset: `LINDBERGH_SKIP_FP=158` must remove every spectator, and `LINDBERGH_SKIP_FP=229,230` the stadium shell.

The stand stretch list (158, 229, 230) does stretch crowd and stadium together, as intended.

### 1.5 Textures and sampling ("low resolution")
- `audience_CM_00..20.dds`: 512x512 DXT5, 10 mips. `audience_NM_xx`: 256x256 DXT5, 9 mips. `audienceStand_CM00/NM00`: 512x512 DXT5. Per spectator cell: 42.7 x 128 texels for 0.5 x 1.5 m, i.e. ~85 texels/m (57 texels/m vertically with the x1.5 stretch).
- The material record (`_sTexture` in the efo) for the crowd: min/mag/mip filter linear, mipmaps on, `anisoNumber` 1, **`lodBias` -1.0** (CM and NM alike).
- `_sRender::loadTexture` (0x0826E022): `glTexParameteri(MAX_ANISOTROPY 0x84FE, min(aniso, max))` if the global flag 0x88D4958 is set; `glTexParameterf(GL_TEXTURE_LOD_BIAS 0x8501, [0x8534048] + lodBias)` at 0x0826E206; `MAX_LEVEL` = levels-1.
- **gl4es drops `GL_TEXTURE_LOD_BIAS`** (`deps/gl4es/src/gl/texture_params.c`: `case GL_TEXTURE_LOD_BIAS: return; // not on GLES`). On the Quest the crowd and every other biased texture is sampled one mip blurrier than designed. macOS keeps the bias, so mac captures look sharper than the headset.
- DXT on the Quest goes to the driver natively (quest/gl4es.patch `native_dxt`, Adreno has s3tc). All mip levels are uploaded, and `MAX_LEVEL` is set to the given levels, so the mips are complete and used (trilinear). There is no downscale on upload. Anisotropy works in gl4es (`hardext.aniso`), but the crowd asks for 1.
- No MSAA on the eye buffers (no sample count anywhere in host_xr/stereo), so the alpha-tested card edges alias and shimmer with head motion. Alpha-to-coverage needs MSAA.
- Texels per degree (Immersive viewpoint about (0, 54, 216), eye ~20-22 px/deg):

  | Spectator | Distance | Texels/deg | Mip level without / with bias |
  |---|---|---|---|
  | Far-end 1F (z -200) | ~42 m | 62 | ~1.5 / ~0.5 |
  | Side 1F | ~23 m | 34 | ~0.6 / 0 |
  | Upper 3F | ~60 m | ~87 | ~2 / ~1 |

  Broadcast camera (Classic, lens 3.2, 1360 px wide: ~39 px/deg, spectators ~55-60 m away): about 19 px per spectator width, versus ~15 px in the headset at the far end.
- So the art itself is adequate for the headset. What looks "low res" is the lost bias (half the texture detail), the vertical stretch, and edge aliasing.

## 2. Recommended implementation

### 2.1 Draw the real stands (fixes the floating; all courts)
Wrap `field::draw` (0x080FFB86) in `hle_sega.c`. In world mode (gate per frame, so Phase B's live switch works), zero the type bytes for the duration of the call:
```c
// field = [[0x85061a4]+0x64]; n = number of trees (the same scene-db count createTree uses,
// 0x81a7718(scene db at field+0x2c)); types = (uint8_t*)[field+0x3c]
static void h_vt3_field_draw(CPU *c) {
    if (!world_mode_immersive() || !stands_on) { call_original(c); return; }
    uint8_t save[64]; int n = min(ntrees(field), 64);
    memcpy(save, types, n); memset(types, 0, n);   // 0 = drawn in every camera
    call_original(c);
    memcpy(types, save, n);
}
```
Optional finer control (env `LINDBERGH_VT3_STANDS=0|1|2`): 1 = draw `GAME_NO` + both ends, 2 = also keep the end behind the camera off.

Watch for:
- `GAME_NO` brings Sega's sky dome (radius ~400 m, beyond the far plane of 3000 units at its corners). Either keep the procedural sky and leave out the `SKY_Polygon` draw, or turn the procedural sky off when the dome shows. A test run will tell which looks better.
- The upper scoreboards `SP_SCORE_2F_*` appear. They are fed by `ScoreBoard` and could serve the scoreboard feature.
- GPU cost: Aus `GAME_NO` is ~62k vertices and ~35 draws; it replaces sky pixels in the upper half of the view. Expect about +0.5-1.5 ms GPU (not measured). Measure with `LINDBERGH_GPU_TIME=1`.
- The `DHPTH` depth-only tree (`VT3_C_depth`, y to 325) is drawn already. My guess is that it explains the "gaps in the far upper stands" (crowd cards failing the depth test against invisible geometry). With the real stands drawn the two coincide. Unverified.

### 2.2 Stretch: go back to k = 1, or lift the cards rigidly
Recommended default with the real stands drawn: **k = 1** (`immersive.stand_y 1`). The geometry is real scale, so stereo gives true size, and people are not stretched. The camera height stays as it is (about 5 m up, 6 m behind the baseline). If the owner still wants taller stands, lift the cards rigidly instead of stretching them.

The vertex shader can find a card's base: seated cards are 15 tall with the quad order T, B, B, T; standing cards are 20 tall with B, B, T, T.

Option A (Quest only; the shaders are GLSL ES 3.00 after gl4es multiview): in the stand block for fp 158 use `gl_VertexID & 3`, with a per-draw uniform for the quad order (the runtime reads the first non-degenerate quad of the bound VBO once). The desktop GLSL 1.20 has no `gl_VertexID`.

Option B (recommended, works on both): patch the crowd VBO once, at the first fp 158 draw from that buffer. For each group of 4 vertices write `alpha = round((y - ymin) * 8)`, so 0 = bottom and 120/160 = top (colour alpha is always 255 today). In vp 121's stand block decode it and restore the alpha:
```glsl
float h = gl_Color.w * 255.0 / 8.0;          // height above the card's base
vec3 w = lg_world;                            // the unstretched world point
float base = w.y - h;
float nb = base > u_stand.y ? u_stand.y + u_stand.x * (base - u_stand.y) : base;
w.y = nb + h;                                 // rigid: people keep 1.5 m / 2 m
gl_Position = u_sP * (u_sV * vec4(w, 1.0));
gl_FrontColor.w = 1.0;                        // the art's alpha was 255 everywhere
```
The stadium programs (229/230) keep the plain mapping, so seats and card bases stay together.

### 2.3 Hiding spectators with no stand under them
With 2.1 every card has a stand under it, so **remove the crowd cut** (it currently cuts stadium geometry, see 1.4).

If 2.1 is refused for cost, the correct rule for every court is: hide a card whose base is above the top of the drawn seating at its (x, z). The seating comes from what is actually drawn.
```
at the first world frame of a court (and after each createTree):
  heightmap H[64x64] over x,z in [-1000,1000] = -inf
  for each world draw of the stadium programs (229, 230, ...) from a VBO:  // read the buffer once per VBO
      for v in vertices: cell(v.x, v.z) = max(cell, v.y)
  upload H as an R16F texture
crowd VS (fp 158 draws): base = card base (2.2 B); if (base > texture(H, xz).r + 4.0) discard the card
```
(Move the card behind the near plane in the VS, or pass a varying and discard in the FS.) A constant table per court is not needed: the vertex data gives it.

### 2.4 Sharper crowd, honestly
1. **Restore the LOD bias on GLES.** Intercept `glTexParameterf/i(GL_TEXTURE_LOD_BIAS)` in the runtime's GL layer (before gl4es) and store it per texture name. Then emit `texture2D(s, uv, u_bias[unit])` in translated fragment programs that sample 2D textures, uploading `u_bias` per unit at draw time. Only fragment stages can take a bias in GLSL ES. Cost is nil. Gain: one mip sharper crowd, ads and court textures, exactly as Sega shipped.
2. **Anisotropic filtering** (`LINDBERGH_ANISO=4`, applied on every mipmapped 2D texture in world mode): this helps the court surface and lines at grazing angles far more than the face-on cards. Cost on Adreno 740: small to moderate.
3. Alpha-test edges: real improvement needs MSAA on the eye buffers (`GL_EXT_multisampled_render_to_texture` / `OVR_multiview_multisampled_render_to_texture`, 4x, cheap on tiled GPUs), then alpha-to-coverage for fp 158. This is a large change to the multiview path (screen copies and blits read the eye arrays). It is an option, not a quick fix.

### 2.5 Building upper stands procedurally (an alternative the owner can choose)
Not needed: the real ones exist (2.1). If it were wanted anyway, it is feasible. Generate stepped boxes per tier from the crowd cards' bases (row riser = base step, tread ~8 units), textured with `S_<court>_B_ch_seat01`, and draw them in `stereo.c` after the stadium with the game camera and the eye reprojection, the way the sky is drawn. That takes about a day of work and would look worse than Sega's own geometry.

## 3. Captures for the build worker (headset)
1. `round0` and the last round, Immersive, game shots both eyes (`LINDBERGH_GAME_SHOT`, `LINDBERGH_SHOT_BOTH=1`), each of: today; `LINDBERGH_SKIP_FP=158` (all spectators gone? confirms 1.4); `LINDBERGH_SKIP_FP=229,230`; `LINDBERGH_VT3_CROWD_CUT=0` (what the cut removes).
2. After 2.1: the same frames, plus `LINDBERGH_GPU_TIME=1` over a rally, plus `LINDBERGH_XR_FAKE_YAW=180` worn (the end behind the viewer).
3. LOD bias: crop the far-end 1F before and after, same frame.

## 4. Verified vs inferred
- **Verified (static, from data and code):** the tree types and `field::draw` logic (disassembly); per-court group extents and tier/seat matches (vertex data, all 8 venues); card geometry statistics; texture sizes, formats, mips and the lodBias -1; gl4es dropping `LOD_BIAS`; native DXT mips on the Quest; `CAudience2DManager::draw` level logic.
- **Verified (one Classic macOS run):** fp 158 = 52-byte crowd quads, fp 229/230 = 40-byte light-mapped stadium; the round-0 crowd draw counts.
- **Inferred:** round 0 = Ita3F (from the quad counts); the crowd cut removes stadium parts on Eng/Ita/Ger courts; `DHPTH` causes the "gaps"; the GPU cost of `GAME_NO`; the sky-dome clipping; that k = 1 looks right worn.
- **Not determined:** the round → venue mapping for rounds 1 and up; the per-round crowd level values (`make` callers); program ids on the Quest (expected identical, since arbprog emulates the ids); what `0x817a452` / checkMode 2 is in `field::draw`.
