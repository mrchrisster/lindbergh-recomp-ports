# Two-mode headset menu (Classic / Immersive) – design

Line references are as of submodule **6513cd3** (before the work below).
Paths are relative to `lindberghrecomp/src/runtime/` unless they start with
`games/`, `scripts/`, `tests/` or `quest/`.

**`ai_docs/HANDOFF.md` section 4 (live-switch plan and groundwork, submodule
3a713ff) supersedes the Phase B steps below where they differ.** Keep this
file's code map and switch inventory as the reference.

## Outcome

- **Phase A (A1–A4) is implemented** in submodule commit **b711cde**:
  `world_mode.c/.h`, `xr_world_panel.c/.h`, new `vr.cfg` keys, env
  overrides no longer saved to `vr.cfg`, and the repro script pins the mode.
- **B1** (live camera distance, step back, stand height, sky) was done in the
  same commit.
- A **Point cutaways** row was added to each mode's Advanced page.
- Decisions taken:
  - switch modes by restart first, live switching later;
  - two camera rows (Camera closer, Step back);
  - one shared frame-rate counter;
  - fresh installs start in Classic;
  - `env.txt` left empty on the headset.
- **Phase B2–B5 (live Classic <-> Immersive switch) is NOT done.** This file
  is its plan, as amended by HANDOFF.md section 4.

---

## Four findings that shape the design

1. **A setting saved in `vr.cfg` loads too late for most immersive switches.**
   - `hle_register_sega()` → `vt3_jumps()` decides at registration which
     immersive hooks to install. It runs from `hle_register_all()` in
     `games/vt3/src/host.c`, after `chdir` and `load_env` in
     `games/vt3/src/android_main.c` (~199–204).
   - `vr.cfg` is only read later: `xr_init()` → `cfg_load()`
     (`host_xr.c:799`), called from `host_gl_context()` (`host_sdl.c:960`).
   - So a mode stored in `vr.cfg` must be read early, by an init call at the
     top of `vt3_jumps()`.
2. **Saving silently deleted unknown `vr.cfg` keys.** `xr_settings_save`
   reopens the file for writing and prints a fixed key list. New keys must
   live in `LgXrSettings` and in the save function.
3. **Test overrides leaked into `vr.cfg`.** `cfg_load` copied
   `LINDBERGH_REPLAYS`, `LINDBERGH_ARCADE_OVERLAYS` and `LINDBERGH_XR_SET`
   into `cfg`, and the next menu click saved them. This is likely how the
   user's `vr.cfg` got Replays off. Fixed in b711cde.
4. **Classic's 2D screen probably comes from a heuristic, not a choice.**
   - `stereo_frame_begin` sets
     `g_flat = flat_all || menu_state() || g_zoom_frames >= 6`
     (`stereo.c:3474`).
   - Without immersive, `keep_shape` is off (`arbprog.c:3156`), so crowd and
     banner draws read as a lens over 8. The code comment says this made
     "every match frame a scope's zoom".
   - **Not verified.** Run a Classic match with `LINDBERGH_MODE_LOG=1` and
     check that `flat 1` holds throughout.

---

## 1. How the menu worked (at 6513cd3)

### `xr_menu.h/.c` – paints the panel image
- `XM_W 768`, `XM_H 860`, `XM_ROWS 21` (the guide's "20" is stale);
  `TITLE_H 64`, `ROW_H 36`.
- `XmItem {label; value[40]}`. An empty value is an action row, drawn gold.
- `xm_paint(img, title, items, n, hover, hint)` (line 93).
- `xm_row_at(u, v, n)` (line 113): panel coordinates to a row.

### `xr_panel.h/.c` – rows and click behaviour, shared with the Vulkan host
- Item enum (line 8): `XP_SIGHT, LASER, CROSSHAIR, GUN, HAND, DUAL, STATS,
  OVERLAYS, REPLAYS, SCREEN, HUD, RATE, RES, FOVEATION, COINS, COIN, RECENTRE,
  TEST, SERVICE, RESET, CLOSE`; `XP_COUNT` = 21.
- Effect flags (line 9): `XP_SAVE` … `XP_OVERLAYS_CHANGED` = 512,
  `XP_REPLAYS_CHANGED` = 1024.
- `XpPanel {open, hover, dirty, c, right, up, n, hw, hh, test_frames,
  service_frames, coin, reset_armed}`.
- `xp_items()` (line 7) fills every item's label and value.
- `xp_choose()` (line 43): one `switch` case per item; a click moves to the
  next value and wraps.
  - Preset lists: screen distance `{2, 2.5, 3, 4, 5}`, HUD pitch
    `{0, -10, -20, -30, 10}`, plus the refresh-rate and resolution tables.
  - Reset game needs two pulls (`reset_armed`).
- `xp_place()`: panel 0.95 m out at yaw +0.55 rad (player's left), 0.12 m
  below the head.
- `xp_hit()`: ray against the panel plane.
- `xp_menu_button()` and `xp_hold_button()` (other hand's upper button held
  1 s) open and close the panel.

### `xr_settings.h/.c` – `LgXrSettings`, defaults, `vr.cfg`
- `LG_XR_SETTINGS_DEFAULT` is **positional** (`xr_settings.h:29`) and is
  also used by `vulkan_guest.cpp:353`. Append new fields at the end only.
- Defaults include `show_stats` 1, `arcade_overlays` 1, `replays` 1.
- Load (line 22):
  - reads `vr.cfg` in the working directory, else `../vr.cfg`;
  - parses `%31s %31s` pairs, so values cannot contain spaces;
  - ignores unknown keys;
  - applies `LINDBERGH_XR_SET="k=v,..."` afterwards.
- Save (line 9): rewrites a fixed key list to `vr.cfg` in the working
  directory (`/sdcard/VirtuaTennis3/vt3_Lindbergh/` on the Quest).

### `host_xr.c` – the GL host's panel
- `static XpPanel menu` (line 306).
- `menu_rows()` (line 323) builds `menu_ids[]`:
  - on a lever cabinet (`game_profile()->joystick`) it drops sight, laser,
    crosshair, gun, hand and dual wield;
  - it drops `XP_OVERLAYS` unless `g_arcade_overlay_hooks`, and `XP_REPLAYS`
    unless `g_replay_hook`;
  - VT3 therefore showed 15 rows.
- `menu_items()` (334).
- `menu_paint()` (383): title "`<LINDBERGH_XR_TITLE>` - settings", then
  `xo_panel_upload`.
- `menu_place()` (396).
- `menu_choose(row)` (440): row → item → `xp_choose`, then applies the
  effect flags:
  - overlays → `g_arcade_overlays`; replays → `g_replays`;
  - screen distance and HUD → `stereo_*`; display rate → `request_rate`;
  - recentre → `anchor_pending`;
  - `cfg_save()`;
  - restart → `reset_game()`.
- `reset_game()` (346) calls the Java `restartGame`; `VirtuaTennis3VR.java`
  has it.
- Input runs every frame in `xr_frame_begin`, on the GL thread when there is
  one:
  - while the panel is open, the controller ray hits it (`menu_hit`, ~576),
    `xm_row_at` sets the hover row, and a trigger edge calls `menu_choose`
    (~586);
  - `LINDBERGH_XR_FAKE_MENU=1` opens the panel but blocks clicks (629–630);
  - on a lever cabinet the beam and dot are hidden unless the panel is open
    (641).
- The panel is drawn into each eye by `xo_draw_panel` (~1683), so
  `LINDBERGH_XR_SHOT` captures it.
- `cfg_load()` (150): `xr_settings_load`, then the env overrides for
  overlays and replays, then copies them into the globals.

### `hle_sega.c` – the two switches the panel drives
- `g_arcade_overlays` / `g_arcade_overlay_hooks` (973). Live:
  `credit::draw`, the card windows and the `ab_card_info` texts check the
  flag on every call.
- `g_replays` / `g_replay_hook` (1220). Live: the `h_vt3_is_replay` wrap.
- Both hooks are always installed for VT3 (1238–1250, 1316–1319).
- `LINDBERGH_FORCE_REPLAY=1` replaces the replay hook, so `g_replay_hook`
  stays 0 and the Replays row disappears.

### Other relevant code
- `host_settings.c` (`lindbergh.ini`) is desktop-only (bindings, aim,
  volume). Its rules are worth copying: env wins over the file, and nothing
  is saved when `LINDBERGH_EXIT_AFTER` is set.
- The Vulkan host (`src/renderer/vulkan/settings_panel.cpp:32, 61–62`) shows
  **all `XP_COUNT` items** unfiltered, and `tests/test_xr_panel.py` asserts
  `XP_COUNT==XM_ROWS`. **Do not add VT3 rows to the `XP_` enum.**

---

## 2. Every VT3 immersive switch (at 6513cd3)

"S" means read once and cached in a `static`, or decided at install time.
"L" means it already takes effect live.

| Env var | Read at | Default | Now | Cost to make live |
|---|---|---|---|---|
| `LINDBERGH_VT3_IMMERSIVE` | hle_sega 1114, 1271, 1273, 1277–1282; stereo 362, 677, 2081; arbprog 1115, 1122, 1163, 2432, 3157 | off | S everywhere | High overall; split out in the rows below |
| — culling (`_sCamera::isVisible` → `h_true`) | hle_sega 1279 | off in immersive (`LINDBERGH_VT3_CULL=1` keeps it) | S, replaced at install | Medium: always install a wrap that calls the original, returning 1 only while immersive. Calling the original here is new: check for hangs and fps |
| — camera read (`_sRender::setProjectCameraMatrix` wrap → `arb_note_projection`) | hle_sega 1281, 1010–1027 | immersive only | S | Low–medium: always install; skip the note in Classic. On leaving immersive, clear `g_game_world_ok=0` and `g_game_world_real_frame=~0u` (arbprog 3233–3235), or the exact-lens path (arbprog 3110) and the world uniforms stay on |
| `LINDBERGH_VT3_FEEDCAM` | hle_sega 1114 | on in immersive | S; hook only installed in immersive | Low once the gameRoutine wrap is always installed: gate on the live flag |
| `LINDBERGH_VT3_SKIP_UVA` | hle_sega 1273 | = immersive | S; `h_vt3_init_uva` never calls the original | Low–medium: always install; call the original (`push32` + `g_vt3_init_uva`) when not immersive |
| `LINDBERGH_VT3_DOLLY` | stereo 404 (`effective_projection`) | 200 units (~20 m) | S | Trivial: read a live float (done, B1) |
| `LINDBERGH_VT3_BACK` | stereo 409 | 60 (~6 m) | S | Trivial (done, B1) |
| `LINDBERGH_VT3_NEAR` | stereo 388 | 1.0 | S | Trivial; keep env-only |
| `LINDBERGH_VT3_SKY` | stereo 2081 `sky_on()` | on in immersive | S | Trivial: the program is built on first use, and the draw is already gated on `!g_flat && g_game_world_ok` (done, B1) |
| `LINDBERGH_SHADOW_SCALE` | stereo 677, when a depth target is created | 2 in immersive, else 0 (1024) | S | High: the target is sized when the game creates it, so a live change means reallocating it and rescaling `g_scaled_k`. **Applies on restart** |
| `LINDBERGH_VT3_STAND_Y` / `_STAND_FROM` / `_STAND_FP` | arbprog 2015 `upload()` | 1.5 / 10 / "158,229,230" | S (the uniform is set every draw) | Trivial for Y and FROM (done, B1); the program list stays env-only. The stand code is only compiled in when the screen fix is on, so a live mode switch needs the link-key change |
| `LINDBERGH_VT3_CROWD_CUT` / `_CROWD_FP` | arbprog 2044 (uniform), 1163 (compiled into the shader) | 190,55 / 230 | S | Uniform trivial; shader part needs the link key. Env-only |
| `LINDBERGH_VT3_DECAL_OFFSET` | arbprog 2432 | 32 in immersive | S | Trivial; env-only |
| `LINDBERGH_VT3_SCREENFIX` | arbprog 1122; `translate()` 1377–1428 (`lg_eye0`, stand code); link key `scr` (1680–1693) | on in immersive | S, compiled into the GLSL | Medium: see note A below the table |
| — `keep_shape` | arbprog 3156 | = immersive | S | Trivial |
| `LINDBERGH_VT3_GROUND` / `_GROUND_Y` | arbprog 1115, 2080 | off / 0.08 | S | Leave env-only (test) |
| `LINDBERGH_REPLAYS` | hle_sega 1318, host_xr 155 | on | L | Already live |
| `LINDBERGH_ARCADE_OVERLAYS` | hle_sega 1239, host_xr 152 | shown | L | Already live; card windows return with the next window the game opens |
| Tests and logs: `_GAME_CAM`, `_SAMECAM`, `_W1`, `_CAMLOG`, `_FLOWLOG`, `_CAMFIELDS(_ALL)`, `_CAMROUTINES`, `_ATTACHLOG`, `_OVERLAY_HOOK`, `_ROUND`, `_POINTS`, `_LOG`, `_WIN`, `_SPLIT`, `_PRIZE_TRACE` | various | off | S | Not in the menu; env only |

**Note A – making the screen fix switch live.**
- Add a `world` bit to `Linked` and to the cache-match line (1694), and make
  `vt3_screen_fix()` / `vt3_crowd_prog()` read it.
- The first switch of each kind compiles programs, which is one hitch. The
  disk cache (`../shadercache`, 1567–1640) covers later switches.
- Watch `MAX_LINKED` (1024, line 1513): it flushes everything when full.
  Raise it to 2048 if needed.
- Alternative: always build the world programs for VT3. They are
  uniform-gated by `stereo_draw_world()`, so this avoids hitches, but it
  changes Classic's shaders.

**Where code runs.**
- `host_xr.c` reads no `LINDBERGH_VT3_*` variable, only REPLAYS and
  ARCADE_OVERLAYS.
- On the GL side, the natural point to apply a mode change is
  `stereo_frame_begin()` (`stereo.c:3394`).
- `menu_choose` also runs on the GL thread, at the frame boundary in
  `frame_gl` → `xr_frame_begin`.

---

## 3. Menu design

### Structure
- Keep `XP_*` and the Vulkan host untouched. A separate module
  `xr_world_panel.c/.h` holds its own `XW_*` items, `xw_items()` and
  `xw_choose()`. `host_xr.c`'s `menu_ids[]` encodes them as
  `XP_COUNT + XW_x`.
- A `page` variable in `host_xr.c`; changing page resets hover to -1 and
  repaints.
- The pages only appear when `g_world_capable` (set by `hle_sega` when the
  VT3 camera symbols resolve).
- Rows pinned by an env var show "(env.txt)" and ignore clicks.
- Rows that need a restart show "(on restart)", like the Resolution row.
- A click moves to the next value and wraps. Optional: a pull on the left
  half of the row steps back.

### Main page (VT3), 14 rows
1. Mode: `Classic (2D screen)` | `Immersive (3D world)`
2. `Advanced settings >` (opens the current mode's page)
3. Screen distance 2 / 2.5 / 3 / 4 / 5 m (default 3). Still matters in
   Immersive, because menus are flat in both modes.
4. HUD position
5. Display rate
6. Resolution per eye
7. Foveation
8. Coins
9. Insert a coin
10. Recentre view
11. Arcade Test
12. Arcade Service
13. Reset game
14. Close

`XP_STATS`, `XP_OVERLAYS` and `XP_REPLAYS` are hidden on Main when
`g_world_capable`.

### Classic advanced
- `< Back`
- Replays On/Off (default On)
- Arcade overlays Shown/Hidden (default Shown)
- Shadow quality Standard 1024 / High 2048 / Very high 4096 (default
  Standard; on restart)
- Frame rate counter (shared between modes)
- Restore Classic defaults (two pulls)
- Close

As built in b711cde, this page also has a Point cutaways row.

### Immersive advanced
- `< Back`
- Stand height ×1.0 (off) / 1.25 / 1.5 / 1.75 / 2.0 (default 1.5) –
  `STAND_Y`
- Camera closer 0 / 5 / 10 / 15 / 20 / 25 / 30 m (default 20 m). This is
  DOLLY 0–300 game units in steps of 50; 20 m = 200. Capped below the
  camera's ~345-unit distance.
- Step back 0 / 3 / 6 / 9 / 12 m (default 6 m). This is BACK 0–120 in
  steps of 30; 6 m = 60.
- Replays (default Off; see the dependency in section 4)
- Arcade overlays (default Hidden)
- Sky On/Off (default On)
- Shadow quality (default High; on restart)
- Frame rate counter (shared)
- Restore Immersive defaults
- Close

As built in b711cde, this page also has a Point cutaways row.

Everything else stays env-only: near plane, decal offset, crowd cut, program
lists, feedcam, skip-intro, culling, screen fix, ground.

### `vr.cfg` format
Classic keeps the existing keys (`replays`, `overlays`, `stats`), so other
games and the Vulkan host are unchanged. New keys, as designed (see b711cde
for the exact set written, including the cutaways keys):

```
mode classic|immersive
classic.shadow 1
immersive.replays off
immersive.overlays off
immersive.stand_y 1.5
immersive.dolly 200
immersive.back 60
immersive.sky on
immersive.shadow 2
```

New fields are appended to `LgXrSettings`, with the default macro extended at
its end. A file without the new keys keeps today's behaviour.

### Precedence: env > `vr.cfg` > mode default, per value
- `LINDBERGH_VT3_IMMERSIVE=1` pins Immersive; `=0` pins Classic. Unset or
  empty falls through to `vr.cfg` `mode`, then the built-in default (Classic
  for fresh installs).
- The tunable variables (`DOLLY`, `BACK`, `STAND_Y`, `SKY`, `SHADOW_SCALE`,
  `REPLAYS`, `ARCADE_OVERLAYS`) pin their value in whichever mode they apply
  to.
- Stored settings and env overrides are kept in separate structs; only the
  stored ones are saved.
- `world_mode.c/.h` is compiled in every build:
  - `world_mode_init()` is called first in `vt3_jumps()`.
  - On XR builds it reuses the `xr_settings` parser
    (`#ifdef LINDBERGH_OPENXR`). Desktop builds use env only; immersive does
    not run on macOS.
  - It logs one `[world] mode X (env|vr.cfg|default) …` line.
  - It holds the `volatile` requested values the menu writes. The GL side
    copies them at `stereo_frame_begin`; game-thread hooks read the
    requested mode directly. A one-frame lag is fine.

---

## 4. Implementation plan

Phase A ships the feature with a restart to switch mode, at low risk.
Phase B makes the switch live. **For B2–B5, HANDOFF.md section 4 supersedes
this plan where they differ.**

| # | Commit | Unattended check |
|---|---|---|
| A1 (done) | `world_mode.c/h` and `world_mode_init()`. Replace the 12 `getenv("LINDBERGH_VT3_IMMERSIVE")` reads with `world_mode_immersive()`, still decided at start. No behaviour change. | `tests/test_world_mode.py` (cc harness) for precedence. On the Quest, a run with `env.txt IMMERSIVE=1` and a run with empty `env.txt` plus pushed `vr.cfg` `mode immersive` must print the same `[sega] … immersive` / `[world]` lines and give matching `LINDBERGH_XR_SHOT` frames. |
| A2 (done) | `xr_settings`: new fields and keys, old files load unchanged, env kept out of the saved file. | `tests/test_xr_settings.py`: round trip, old file, unknown keys, `XR_SET` not saved. `tests/test_xr_panel.py` still passes (`XP_COUNT` unchanged). |
| A3 (done) | `xr_world_panel.c` and pages in `host_xr.c`. The Mode row saves, shows "(on restart)" and adds `Restart now` (`reset_game()`). Replays and overlays per mode, applied at start and on change. | Unit test for `xw_items` / `xw_choose`. Test switches `LINDBERGH_XR_MENU_PAGE` (with `FAKE_MENU`) and `LINDBERGH_XR_MENU_CLICKS=<frame>:<row>,...`. Check `adb exec-out screencap -p` or `XR_SHOT` of the panel, pull `vr.cfg`, grep `[xr] mode` in the log. |
| A4 (done) | `scripts/vt3-repro.sh` pins `LINDBERGH_VT3_IMMERSIVE` (default 0) and `LINDBERGH_REPLAYS` (default 1), so `vr.cfg` cannot change test runs. Update the docs. | A repro run's log shows the mode coming from env. |
| B1 (done) | Camera closer, step back, stand height and sky read the copied live state; those rows dropped "(on restart)". | `LINDBERGH_WORLD_SET_AT=<frame>:dolly=100,...`; compare `XR_SHOT` before and after with a run started with the same values from env. |
| B2 **(risky)** | Always install the VT3 world hooks (cull wrap that calls the original, camera-read wrap, gameRoutine wrap, initUva calling the original), all gated on the requested mode. | Classic: `GAME_SHOT` unchanged (mac `vt3-repro.sh round0 mac` and Quest); same fps in the frame-rate log; a full `prize` match with `LINDBERGH_REPLAYS=1` ends with no hang. Immersive: same shots as after A1. |
| B3 **(risky)** | arbprog: a `world` bit in `Linked` and the cache match; `vt3_screen_fix`, `vt3_crowd_prog` and `keep_shape` read the live flag. | Starting in Immersive gives identical shots; build stats show no extra builds until a switch; `g_nlinked` stays below `MAX_LINKED`. |
| B4 **(risky)** | stereo: copy the mode at `stereo_frame_begin`. Classic forces `g_flat` for world-capable games (only if `MODE_LOG` confirms today's Classic is flat throughout; otherwise keep the heuristic). Gate `deep` on the live flag. Leaving Immersive clears `g_game_world_ok` / `g_game_world_real_frame`; entering sets `anchor_pending=1`. | `LINDBERGH_WORLD_TOGGLE_AT=f1,f2,...` in `round0`, mid-match and in a menu. `XR_SHOT` ±5 frames around each switch: sky present or absent, shadows at the feet (screen-copy path), HUD shown. fps recovers, no crash. `MODE_LOG` shows `flat` following the mode. |
| B5 | The Mode row switches live (remove `Restart now`). Shadow quality stays "(on restart)". | `MENU_CLICKS` on the Mode row during a match, then screencap. |

### Risks
- **B2:** new wraps of `isVisible` and `initUva` that call the original. The
  guide records that generic wraps of `camera::procMain` and similar
  functions hung the game.
- **B3:** more shader variants, and compile hitches on a switch.
- **B4:** Classic's look may depend on the zoom heuristic (finding 4).
- **Dependency:** Immersive defaulting to Replays off depends on the
  match-end fix and on the "some replays still play" bug.

### Fallback
If a Phase B piece cannot be made clean, keep "on restart" plus
`Restart now`, as A3 already does. Nothing else is needed.

---

## 5. Open questions

All five now have decisions; recorded here for reference.

1. **Restart to switch first, live later?** Decided: yes.
2. **What to do about `env.txt` `LINDBERGH_VT3_IMMERSIVE=1`, which locks
   the Mode row, and where fresh installs start.** Decided: `env.txt` left
   empty on the headset; fresh installs start in Classic.
3. **Immersive Replays default before the match-end fix lands.**
   Recommended: On until the fix is merged, then Off. Check the current
   default in b711cde.
4. **Two camera rows or one Near/Mid/Far preset?** Decided: two rows.
5. **Frame rate counter shared or per mode?** Decided: shared. Replays,
   overlays and cutaways are per mode.
