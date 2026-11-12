# The card reader's top bar ("1P/2P cannot use a card") - what it is and how to switch it off

Research only (2026-11-11/12). Nothing in the tree was changed. Addresses are
`vt3_Lindbergh_HD` (same layout as Rev. C). Scratch: disassembly and frame
crops in the session scratchpad `cardbar/`.

## The answer in plain words

1. The bar is the IC card reader's notice "ただ今、1P側/2P側はカードが使用できません" ("1P/2P cannot use Card at this time"): `CCardSlotWindowManager`'s two windows, opened ONCE at boot by `cardManager::startup()` because the port has no card reader, and never closed by the game afterwards - it stays up all session.
2. The Arcade overlays switch does hide it, but only if overlays are already Hidden when the game boots (checked: Quest Classic and macOS runs with overlays hidden show no bar; with overlays shown it is there). The switch only stops windows being OPENED; it never closes one that is open.
3. So it still shows whenever the run started with overlays Shown: a toggle to Hidden during the session (the panel says "applied live" - true for the credit text, not for this bar), a `LINDBERGH_ARCADE_OVERLAYS=1` pin left in the headset's env.txt by an interrupted test run (the row then reads "Shown (env.txt)"), or Classic before its own `overlays` key was set (Classic's default is Shown).
4. Recommended fix at the source: tell the game the cabinet's card reader/writer is switched OFF (its own test-menu setting, GAME ASSIGNMENT > CARD R/W 1P USE / 2P USE = OFF). With OFF the game never opens these windows at all, skips the 11 s "CARD R/W INITIALIZING..." boot screen and stops cycling the "insert your card" text at character select. In the port: a 2-line override of `backup::getCard_rw_1p_use` / `_2p_use` answering OFF (-1).
5. Optional, separately: the port's overlay switch should also close the bar when it is turned to Hidden (call the game's own `CCardSlotWindowManager::init()`), and the game can be switched to English (the card texts exist in English) - see section 5.

(Details, addresses and the verified/inferred split below.)

## 1. What draws the bar

### Objects

- `tennis` singleton: pointer at `0x085061A4`. `+0x70` = `cardManager*`, `+0xB4` = `backup*`, `+0xAC` = `CLanguageReplaceManager*`.
- `cardManager` (`+0xB4`) = `CCardSlotWindowManager*` (created in `cardManager::cardManager` `0x080B6CC4`, `new 0x3C`, ctor `0x080C1D50`). Siblings: `CCardInfoWindowManager` (`+0xB0`), `CCardAccessWindowManager`, `CCardResultWindowManager`, `CCardYesNoWindowManager` - the other card dialogs (only reached with a working card).
- `CCardSlotWindowManager` layout (from the ctor / `init` / window functions):
  - `+0x18` `AbHandle*` - ONE sprite-board handle for everything (resource `0xE2`, `ab_util::createResource` in `resource_create` `0x080C1FCC`), with 10 branches (sub-animations) 0..9.
  - `+0x1C` `AbResource*`.
  - `+0x20/+0x21` window open, 1P/2P. Branches 0+2 (1P) / 1+3 (2P): the bar's plate.
  - `+0x24/+0x25` slot icon started, 1P/2P. Branch 4 / 5: the "1P"/"2P" card-slot icon. Started by the FIRST `window_slot()` call for that side whatever its bool, and only ever finished by `init()`.
  - `+0x26/+0x27` branch 6 / 7 started: the cross over the slot icon (`window_slot(side, false)` starts it, `window_slot(side, true)` finishes it).
  - `+0x28/+0x29` branch 8 / 9: the "use card" icon (`window_slot_usecard(side, true)` starts, `false` finishes).
  - `+0x2A/+0x2B` **side in use**: set by `init()` when `backup::getCard_rw_Np_use() != -1`. Every window function returns at once when this is 0.
  - `+0x2C` resources created.
  - `+0x30` language keyword id: `0x1F` (Japanese, country 0) or `0x23` (English, any other country) - ctor `0x080C1DB7`. `+0x34/+0x38` the text variants (`CLanguageReplaceManager::getNbVariant/getVariantData`), set into the board with `AbHandle::setTextData`.
- Text: `set_message_mode(side, n)` (`0x080C223E`) stores the message number at `+0x10+4*side` and `setVariantData` puts it in the plate. The messages are `resource/language/repCRD_slot_JPN.bin` / `repCRD_slot_ENG.bin`; numbers 9 and 10 are "1P cannot use Card at this time." / "2P cannot use Card at this time." (the screenshot's text).

### Functions

| function | address | does |
| --- | --- | --- |
| `CCardSlotWindowManager::init()` | `0x080C1F16` | creates resources if needed, `AbHandle::play()`, `finishBranch(0..9)` (= closes EVERYTHING), clears `+0x20..+0x29`, sets `+0x2A/+0x2B` from the card R/W setting |
| `window_open(long side)` | `0x080C22B4` | if used and not open: `startBranch(0,2)` / `(1,3)`, `+0x20[side]=1` |
| `window_close(long side)` | `0x080C2350` | if open: `finishBranch(0,2)` / `(1,3)`, `+0x20[side]=0` (NOT hooked by the port) |
| `window_slot(long side, bool ok)` | `0x080C23EC` | first call: `startBranch(4/5)`; `ok` false: `startBranch(6/7)` (cross), true: `finishBranch(6/7)` |
| `window_slot_usecard(long side, bool on)` | `0x080C2516` | branch 8/9 on/off |
| `set_message_mode(long side, ulong msg)` | `0x080C223E` | the plate's text |
| `exec()` / `draw()` | `0x080C2218` / `0x080C221E` | empty stubs - the board is drawn by the generic AB (sprite board) manager |
| `finish()` / `resource_exit()` | `0x080C1FC2` / `0x080C215E` | destroys handle and resource |

### Who opens the bar, and when

- **Boot:** `usrStartupWarningLoop::exec` (`0x0817CA00`, call at `0x0817CC2A`) -> `cardManager::startup()` (`0x080B8B1C`). For each side: `init()` (first side only), `window_slot(side, true)` (starts the slot icon), then if `CSerialManagerCommon::iccd_check_system(side)` (`0x08111E1A`, a byte in the serial manager's table at `0x08504BC0`) is false, **or** the setting is OUT OF SERVICE: `window_open(side)`, `set_message_mode(side, 9+side)`, `window_slot(side, false)` (the cross). The port refuses every `/dev/*` open (`hle_libc.c` `host_device_refused`), so the reader never answers and both sides get the bar. That is the bar in the screenshot.
- Then `usrStartupCardLoop::exec` (`0x0817C5BE`) shows "CARD R/W INITIALIZING..." for 660 frames (`0x294`, ~11 s at 60 fps) unless both sides are OFF or OUT OF SERVICE (then it jumps to `0x295` and moves on at once).
- **Nothing closes it in normal play.** The bar survives attract, menus and matches; `CCardSlotWindowManager::init()` (which closes everything) runs again only from `usrAdvAdxLogoLoop::init` (`0x080558CB`), `usrAcStatsLoop::init` (`0x0808B108`, the stats after a match) and `cardManager::startup`; the attract (`cardManager::adv_exec` `0x080B8C7E`) and the stats screen (`cardManager::ac_stats_exec` `0x080B9022`, `usrChResultLoop::init`) re-open it through `window_open`/`window_slot`/`set_message_mode` while the reader is absent. `game::init` (`0x081080F9`) also calls `window_open` per side at match start. The card sequences (`exec_common_card_seq` `0x080B9498`, `disp_slot_window_*_message`, `set_eject*`) only run with a card.
- All opening goes through `window_open`, `window_slot`, `window_slot_usecard` (checked: every caller of the class in the binary, scratch `callers.txt`). There is no second draw path.

### Where it shows

macOS Classic with overlays Shown (`/tmp/vt3q/T8/mac_cls/f.01900.ppm`): the bar across the top, crossed "1P" icon and Japanese text at the left, mirrored 2P at the right, "CREDIT(S) 0 / INSERT COIN(S)" at the bottom. (Scratch `cardbar/cls1900.png`.)

## 2. Why the Arcade-overlays switch does not hide it for the owner

### What the switch does (hle_sega.c)

- `vt3_jumps()` (registration, before any game code runs): `world_mode_init()` reads vr.cfg (`xr_settings_load`, env > vr.cfg > the mode's default), then `g_arcade_overlays = world_mode_overlays()`, then wraps `window_open`, `window_slot`, `window_slot_usecard` (handlers return without calling the game while `g_arcade_overlays` is 0), `credit::draw` (skipped while 0) and `ab_card_info::init` (its texts swapped for "").
- `host_xr.c` `cfg_apply_live()` (at `xr_init` and on every panel click) sets `g_arcade_overlays` again from the stored settings for the running mode.

### The order at start-up is right

The flag is resolved from vr.cfg before the hooks are installed, i.e. before `cardManager::startup()` runs (boot, around frame 600-1000). The mode's key is the right one: Classic reads `overlays`, Immersive `immersive.overlays` (`world_mode_resolve`). Evidence:
- Quest run with the owner's settings unpinned (`/tmp/vt3q/V3_unpinned_r0`): log `[world] mode immersive (vr.cfg) ... overlays off (vr.cfg)`, `[sega] Virtua Tennis 3: arcade overlays hidden (5 draws hooked)`; frame 2600 in the match: no bar.
- Quest Classic, overlays hidden (`/tmp/vt3q/T8/C1`, frame 2000, the attract/menu screen where the macOS Shown run has the bar): no bar.
- macOS Classic, overlays hidden (`/tmp/vt3q/T8/M1`, frame 2149, a match): no bar. macOS Classic Shown (`mac_cls` f.01900): bar.
So with overlays Hidden at boot, the bar never appears, in either mode.

### The holes (why it can still show)

1. **Turning overlays to Hidden during a session does not remove it (the main hole).** The bar is opened once at boot and the game never closes it. Hidden only blocks NEW `window_open`/`window_slot` calls (it even blocks the game's own `window_slot(side, true)` close of the cross, and leaves `window_close` alone, which nothing calls for this bar). So: boot with Shown -> bar; switch to Hidden -> the credit text goes at once, the bar stays until the next start. The guide's "applied live" is only true for `credit::draw` and the card-info board. (The other direction is also only partly live: Shown again brings the bar back only when the game next opens it - attract or the next start.)
2. **An env pin wins over vr.cfg.** `scripts/vt3-repro.sh` writes `LINDBERGH_ARCADE_OVERLAYS=1` (its default pin) into `/sdcard/VirtuaTennis3/env.txt` and empties env.txt at exit; a run cut short (killed, cable pulled, usage limit) leaves the pin, and every later start of the owner's has overlays Shown regardless of vr.cfg. The panel then shows "Shown (env.txt)" and ignores clicks. HANDOFF already records env.txt being left full once.
3. **Classic's default is Shown** (`LG_XR_SETTINGS_DEFAULT`: `arcade_overlays 1`, `imm_overlays 0`). A vr.cfg without the `overlays` line (older file, "Restore Classic defaults") shows the bar in Classic only. The owner's backed-up vr.cfg (`/tmp/vt3q/T8/vr.cfg.owner`) does have `overlays off` and `immersive.overlays off`, so this is not their case today.
4. Mode switch / Restart now: not a hole. `restartGame` kills the process (`VirtuaTennis3VR.java`), the new process reads vr.cfg afresh, and the running mode's value is used.

Inferred: the owner's sighting is (1) or (2) (or a build installed before the hooks/world-mode refactor). How to tell on the headset: open the panel, Advanced settings for the running mode - "Hidden (env.txt)"/"Shown (env.txt)" means an env pin (check `adb shell cat /sdcard/VirtuaTennis3/env.txt`); otherwise the start's log line `[world] ... overlays off (vr.cfg)` plus a bar on screen means it was opened while Shown and survived a later toggle. A macOS repro of (1) was not run (another worker had the game running); the reasoning is from the code above.

## 3. Ways to switch the bar off for good (ranked)

### (a) At the source: the game's own CARD R/W setting = OFF (recommended)

The game has the setting a cabinet without card readers uses:
- Stored in the game's EEPROM backup record (user EEPROM, `0x36` bytes; `backup` object's data pointer at `backup+0`): byte `+0x12` = 1P, `+0x13` = 2P. Neighbours: `+0x10` advertise sound, `+0x11` event mode, `+0x14` MPH, `+0x15` doubles.
- Getters `backup::getCard_rw_1p_use()` `0x0809C0FE` (`_ZN6backup17getCard_rw_1p_useEv`) and `backup::getCard_rw_2p_use()` `0x0809C162` (`_ZN6backup17getCard_rw_2p_useEv`): byte 0 -> 0 **ON**, 1 -> -2 **OUT OF SERVICE**, 2 -> -1 **OFF** (labels from `usrTestmodeGameAssignmentLoop::draw` `0x080A20BA`: table ON / OFF / OUT OF SERVICE). Setters `0x0809C12E` / `0x0809C192`. `backup::clearEEPROM` (`0x0809B65C`) zeroes the record: default ON.
- The port's nvram today: card R/W ON (default), reader absent -> the bar.

What OFF (-1) changes, from every reader of the getters:
- `CCardSlotWindowManager::init` leaves `+0x2A/+0x2B` 0 -> every `window_*` returns at once: **no bar, no slot icons, ever** (boot, attract, match, stats).
- `cardManager::startup` still runs, but its `window_open`/`set_message_mode` are no-ops.
- `usrStartupCardLoop::exec`: **the "CARD R/W INITIALIZING..." screen is skipped** (660 frames, ~11 s at 60 fps; the owner's "~20 s" boot wait includes it).
- `usrMenuCharLoop::draw` (`0x0812BA58`): `changeExplanationText()` (cycling the explanation line every 240 frames, the "insert your card" variant) only runs while a side is ON -> **the character-select card prompt stops** (inferred: the line stays on its first variant).
- `CCardAccessWindowManager::init`, `CCardInfoWindowManager::init`: the other card dialogs disabled the same way.
- `cardManager::isLockCard`, `player::calcScore`, `padManager::init` (`0x0817B30A`: with a side ON it checks the JVS board has the card-lock outputs; OFF asks less, and `tennis::setError` is stubbed to return 1 in this binary anyway).
- **Game-flow side effects** (the intended non-card cabinet behaviour): `match::getKing_level` (`0x08109F98`) - with both sides OFF the arcade "King" level comes from the cabinet's backup (`backup::getKing_level`) instead of the players' cards (with ON and no card it appears to stay 0 - inferred from the branch structure, not traced through `player::isUse_card`); `usrAdvLoop::isShowBossLv` (`0x080556E0`) - with both OFF the attract shows the cabinet's boss level. So OFF gives a cabinet-wide progression that persists in lindbergh_nvram.bin; ON-without-card always plays level 0. Owner's call whether that is wanted (it is what a real card-less cabinet does). No screen is skipped other than the card init wait; the point/match loops' "card being written" wait (`hle_sega.c` setMode wrap) never triggers either way.
- OUT OF SERVICE (-2) is NOT the answer: it keeps the side "in use" and `cardManager::startup` opens the "cannot use" bar explicitly for it.

How the port can set it:
1. **Override the two getters to answer -1 (recommended).** Pure, two lines, no nvram editing, reversible, independent of overlays:
   ```c
   /* Virtua Tennis 3's card reader/writer, per side: 0 on, -2 out of service,
    * -1 off. The port has no card reader (every /dev open is refused), so the
    * game is told the cabinet has its readers switched off: no "cannot use a
    * card" bar, no CARD R/W INITIALIZING wait, no card prompt at character
    * select. LINDBERGH_VT3_CARD_RW=1 keeps the game's own setting. */
   static void h_vt3_card_rw_off(CPU *c) { RET(0xFFFFFFFFu); }
   ...in vt3_jumps(), next to the overlay hooks:
   { const char *v = getenv("LINDBERGH_VT3_CARD_RW");
     if (!(v && *v == '1') &&
         guest_override("_ZN6backup17getCard_rw_1p_useEv", h_vt3_card_rw_off) &&
         guest_override("_ZN6backup17getCard_rw_2p_useEv", h_vt3_card_rw_off))
         fprintf(stderr, "[sega] Virtua Tennis 3: card readers off\n"); }
   ```
   (Override handlers take no args here: the `this` at `esp+0` is not needed.) It must be installed at registration (vt3_jumps), before `cardManager::startup` at boot - it is. Side effect: the test menu shows OFF and its Test presses do not stick (they write the byte; the getter ignores it). All readers of bytes `+0x12/+0x13` go through these two out-of-line getters (every caller listed in scratch `callers.txt`; they live in `backup.cpp` and are called across translation units).
2. Write OFF into the saved setting once (a wrap of `backup::init` `0x0809A028` calling `setCard_rw_1p_use(-1)`, `setCard_rw_2p_use(-1)` and `backup::updateBackup_eeprom_data()` `0x0809B980` when the byte is 0). Keeps the test menu working, but changes the owner's save file and needs a "done once" marker; more code than 1 for no visible gain.
3. A default in the nvram image: the record has a duplicate and a CRC (`amBackupRecordWriteDup` layer) - not worth hand-editing.
4. An HLE answer for the card reader: does not help. "Not present" is today's answer (that is what opens the bar); "present and working" would make the game wait for and prompt for cards.
5. **The owner can do it today without a build** (if the panel's Test button reaches the game's test mode in this port - not verified): headset panel > "Arcade Test button (select)" opens GAME TEST MODE; "Arcade Service button (next)" moves the arrow, Test chooses. GAME TEST MODE > GAME ASSIGNMENT (third item) > Service down to "CARD R/W 1P USE [ ON ]" > Test once -> `[ OFF ]` (each Test cycles ON -> OFF -> OUT OF SERVICE -> ON); Service to "CARD R/W 2P USE" > Test once -> `[ OFF ]`; Service to EXIT > Test; exit the test menu. It is saved in `vt3_Lindbergh/lindbergh_nvram.bin` and holds from the next start. If the Test button does not enter the test menu, use option 1. (The panel row holds `CAB_TEST` for 12 frames, sent as the JVS test switch, `hle_sega.c` line ~215; on macOS the `T` key is the same switch, `hle_window.c`, so a build worker can check the menu path on the desktop first.)

Verify (build worker):
- macOS: `LINDBERGH_ARCADE_OVERLAYS=1` (overlays SHOWN, to prove the fix does not depend on the switch) `OUT=<dir> LINDBERGH_GAME_SHOT=1800,20 scripts/vt3-repro.sh round0 mac ~/code/quest_games/vt3 120`: log has `card readers off`; no "CARD R/W INITIALIZING..." text in early frames (and the menu script's timing moves ~660 frames earlier - check the scripted keys still land; the repro key script may need its frames shifted); no bar in attract (frame ~1900 where `mac_cls` has it) or in the match; "CREDIT(S) 0" still at the bottom (that is credit::draw, overlays). Same with `LINDBERGH_VT3_CARD_RW=1`: bar back.
- Quest: same scene with `quest`; also one unpinned start with the owner's vr.cfg (`LINDBERGH_VT3_IMMERSIVE= LINDBERGH_ARCADE_OVERLAYS=` ...): no bar, boot reaches the title ~11 s sooner (`[flow]`/log timestamps).
- Character select: shot every 60 frames for ~600 frames on that screen, explanation line no longer alternating.

### (b) In the port's overlay switch: close what is open (do this too if the bar should follow the switch)

Not needed for the bar once (a) is in, but it fixes the "applied live" lie for anything the slot manager shows (and is the fix if the owner wants card R/W left ON).

- On the change to Hidden, call the game's own close-everything: `CCardSlotWindowManager::init()` (`0x080C1F16`, `_ZN22CCardSlotWindowManager4initEv`) on the manager, game thread. It `finishBranch`es 0..9 and clears the open flags - exactly what the game does between screens - and is safe to call any time after `resource_create` (`+0x2C == 1`; it creates resources itself otherwise). Do it in `vt3_card_apply()` (already called every frame from `credit::draw` on the game thread, on change only):
  ```c
  /* overlays hidden: close the card reader's windows the game already opened
   * (it opens them once at boot and never closes them) */
  static void vt3_slot_close_all(CPU *c)
  {
      uint32_t t = rd32(0x085061A4u), cm = t ? rd32(t + 0x70) : 0, sw = cm ? rd32(cm + 0xB4) : 0;
      static uint32_t init_fn;
      if (!init_fn) init_fn = guest_symbol("_ZN22CCardSlotWindowManager4initEv");
      if (sw && init_fn && rd8(sw + 0x2C) == 1) guest_call(c, init_fn, &sw, 1);
  }
  /* in vt3_card_apply (give it the CPU): when g_arcade_overlays went 1 -> 0 */
  ```
  `h_vt3_credit_draw(CPU *c)` has the CPU to pass. Note `credit::draw` must actually run every frame in all screens for this (it is the credit layer; it is called while hidden - the hook returns before the original, `vt3_card_apply` runs first). Alternatively hook `_ZN11cardManager8adv_execEv`-level exec functions - not needed.
- Turning Shown again: the bar returns when the game next opens it (attract `adv_exec`, stats, next boot) - acceptable, or call `_ZN11cardManager7startupEv` (`0x080B8B1C`) once to reopen at once (it re-runs `init()` then reopens; harmless).
- Avoid: `CCardSlotWindowManager::draw` (empty stub), scaling the board (guide 7.5: no effect / crash), `finish()`/`resource_exit()` (destroys the handle the game keeps using -> crash risk).
- Verify: macOS has no live panel, so test with a run that flips the flag: e.g. a temporary env `LINDBERGH_VT3_OVERLAYS_AT=<frame>:0` is not in the tree; on the Quest use `LINDBERGH_XR_MENU_CLICKS=<frame>:<Arcade overlays row>` (`LINDBERGH_XR_MENU_PAGE` for the page) with overlays starting Shown, game shots before/after: bar gone within a frame of the click.

### (c) Fix the env.txt pin (process)

`vt3-repro.sh` should not leave `LINDBERGH_ARCADE_OVERLAYS` (or any pin) behind: an EXIT trap already empties env.txt; also have the app log `[world] ... (env)` sources prominently and consider ignoring env.txt pins older than N hours. Cheapest guard: the build/install script empties env.txt.

## 4. Same mechanism elsewhere?

- **CREDIT(S) / INSERT COIN(S) / PRESS START BUTTON**: drawn by `credit::draw` every frame; the hook skips the draw, so it follows the switch live and reliably. Not the same problem.
- **Card information board** (`ab_card_info`, "CREDIT 0" / "INSERT COIN(S)" on the board): texts swapped every change, live. Fine.
- **"Insert your card" at character select**: not a window of this manager - `usrMenuCharLoop::changeExplanationText` cycles the explanation line while a card side is ON. Not touched by the overlay switch; goes away with (a).
- **"CARD R/W INITIALIZING..."** boot text: `TScene::Fix::put` debug-font text in `usrStartupCardLoop::exec`; goes away with (a).
- Anything else opened once and kept open while Hidden would have the same live-toggle hole; among the overlay hooks only the card slot windows are "open once" objects.

## 5. Language (Japanese -> English)

### How the game picks its language

- `tennis::slCountry_` (`0x0850C8A0`, `tennis::getCountry()` `0x08177400`): 0 = Japan, 1 = export, 2 = USA (debug range 0..6).
- Set in `tennis::initializeSystem` (`0x08175B23`): `backup::getRegion()` (`0x0809FFA4`) returns byte `+0x4E` of `arcade::_sArcadeManager::_arcadeContext` (`0x085344E0`) = byte 14 of the AM system-data static record (`_arcadeContext+0x40` = `0x08534520`). Mapping: region 0 -> country 0, region 1 (USA) -> country 2, region 2 (export) -> country 1. A debug command-line switch `-c<n>` overrides it (`0x0817615C`).
- The record: `arcade::_sArcadeManager::initializeHardware` reads it with `amBackupRecordReadDup` (record `0x083EE4A0` = EEPROM offset 0, size 0x20); on failure `amSysData_InitStatic` (`0x083224A5`) fills defaults: region 0 (Japan), serial "AAGX-01A00009999".
- **The port today:** VT3's game profile (`games/vt3/src/host.c`) does not set `.sysdata_region`, and the EEPROM part of `lindbergh_nvram.bin` (file offset `0x40000`) is all zero at offset 0..0x9F (checked) -> the record's CRC fails -> region 0 -> **Japan**. That is why the card bar (and the rest) is Japanese. The game ID (SBKX -> SBJJ in these binaries) plays no part in the language: `backup::isGameId_registered` only decides whether the save is wiped.
- The port's existing switches for other games: `get_arcade_region_country` / `CConfigMgr::GetRegion` overrides (not in VT3), and `sega_sysdata_region()` -> `sysdata_apply_region()` (hle_sega.c, used by hotd4sp/hotdex: writes `region_value()` into EEPROM byte 14 with the record's CRC; `region_value()` = `LINDBERGH_REGION`, else `g_country ? 1 : 0`, `g_country` = host settings `country`, default 1 = English, `LINDBERGH_COUNTRY` overrides). Not touching security: it is the cabinet's region byte the game reads from its own EEPROM.

### What changes with the country (from every reader of `slCountry_`)

- Card windows: `CCardSlotWindowManager` (+ Info, Result, YesNo managers) pick keyword `0x1F` (JPN) vs `0x23` (ENG): `repCRD_slot/_info/_message/_result_ENG.bin` exist - **the bar has an English version**: "1P cannot use Card at this time." (the crossed slot icons are pictures, same in both).
- Title: `usrAdvTitleLoop::init` - AB resource `0x16` (Japan) vs `0x18` (other): the Japanese "Power Smash 3" title vs "Virtua Tennis 3" (inferred from the two resources; not looked at).
- Movies: `movie::play` - `sj_00000.sfd`/`Lj_0000.sfd` (Japan) vs `sa_00000.sfd`/`La_0000.sfd` (abroad); all four are in `resource/movie/`.
- Title music: `sound::setBgm_title` - Japan honours the advertise-sound setting; others take another path.
- Start-up warning screen (`usrStartupWarningLoop::init`), SEGA logo (`usrAdvSegaLogoLoop::init`), name entry (`nameEntry::*`: kana/hiragana boards vs alphabet), item / medal / play-style / challenge / ranking / how-to-play / player-intro / result texts (`*_txtDB.bin` vs `*_txtDB_US.bin`, all present), game-over screens, tournament table, stats fonts.
- USA only (country 2): `usrAdvRatingLoop` (a rating screen in the attract), `credit::draw` (a country-2 branch around checkMode 3/4), and `backup::clearEEPROM` defaults speed to MPH (`+0x14 = 1`) for region 1 on a fresh save.
- **Not changed by country:** the card system itself. No card code reads the country; an export cabinet still has the card readers (ON by default) and would show the bar in English. So switching language is not a fix for the bar - (a) is.
- Japanese-only data: `ExtendCardMessageJPN.bin` (no ENG twin; card-related, only reached with a card), `nameEntry_hiragana/kana.bin` (Japan's name entry only), `ReplaceCredit_dummy.bin`. Everything a player sees has an English file.

### Cleanest way for the port

- Add `.sysdata_region = 1` to VT3's `k_profile` (games/vt3/src/host.c). Then the region follows the existing country setting (`LINDBERGH_COUNTRY` / host settings `country`, default English) or `LINDBERGH_REGION`. Note the mapping: the port's "English" is region 1 = **USA** (country 2: rating screen, MPH on a fresh save); region 2 = export (country 1: English without the US extras). For VT3 export (2) is probably the better "English"; a VT3-specific `region_value` mapping (English -> 2) or `LINDBERGH_REGION=2` would do it.
- It applies from the next start (the region is read once in `initializeSystem`; the card windows pick their keyword in their constructors) - like Mode.
- Effect on saves: the region byte lives in the system record (EEPROM 0..0x1F), separate from the game's own records; switching does not wipe the save. A fresh save under region 1 starts in MPH.
- Player-facing: a "Language: English / Japanese" row in the headset panel's main page and a desktop setting (`country` already exists in host_settings on desktop), "(on restart)" like Mode, saved in vr.cfg (new key, e.g. `language english|japanese`) and fed to `region_value()` before `nvram_load()` (it runs lazily at the first EEPROM access, after registration, so reading vr.cfg in `world_mode_init` is early enough). Default: English (the owner reads English; the Japanese "Power Smash 3" title and texts remain one click away).
- Verify: macOS `LINDBERGH_REGION=2` (with the profile flag): log `[sega] system data region 2`; title shows "Virtua Tennis 3"; with overlays Shown and card R/W ON the bar reads "1P cannot use Card at this time."; name entry offers letters. Quest: same, then switch back to Japanese and check the save survives.

## Verified vs inferred

Verified (disassembly / data / existing captures):
- The bar = `CCardSlotWindowManager` windows opened by `cardManager::startup` at boot when `iccd_check_system` fails; message numbers 9/10; English text exists in `repCRD_slot_ENG.bin`.
- The card R/W setting's encoding (0 ON, 1 OUT OF SERVICE, 2 OFF; getter -1 = OFF), its readers, and that OFF disables every window function and skips the 660-frame init screen.
- Overlay hooks hide the bar when Hidden at boot: Quest (V3_unpinned_r0, C1) and macOS (M1) frames; bar present when Shown (mac_cls). Flag resolved before the hooks and before boot.
- Region/country logic and that the port runs VT3 as Japan (blank EEPROM system record).

Inferred (not run):
- That the owner's case is the live toggle or an env.txt pin (no owner log available; a macOS repro was not run because another worker was using the game).
- That OFF also stops the character-select card prompt (from `usrMenuCharLoop::draw`); the title resources 0x16/0x18 being the two logos; the exact screen of `usrAdvRatingLoop`.
- That the panel's Arcade Test button reaches GAME TEST MODE in this port.
- That `guest_call` of `CCardSlotWindowManager::init()` from `credit::draw`'s hook is safe at any frame (it is what the game itself does between screens).
