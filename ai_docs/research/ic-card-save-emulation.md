# VT3's IC card as a save game - research and design (option C chosen)

Research only (2026-11-12). Nothing in the tree was changed, nothing was run.
Binary: `vt3_Lindbergh_HD` (`~/code/quest_games/vt3/disk0/vt3_Lindbergh/`),
addresses from `objdump`/`nm` of it. Scratch (disassembly dumps): session
scratchpad `ic/` (`all.s`, `cardmgr.s`, `card.s`, `player.s`, `serial.s`).
Builds on `card-reader-top-bar.md` (the bar, the CARD R/W setting, tennis
singleton offsets) - not repeated here.

**Owner's decision (2026-11-12): option C** - no card screens at all; the
port loads and saves the card's data itself. No profile picker: always the
same player, one save, 1P side only. A and B are kept short below for the
record.

## Plain answer for the owner

Yes - the card is a save game for one player. On the real cabinet you bought
a card, put it in before a game, and it remembered *your* player: which
character you play, the outfits/rackets and colours you have won, your play
style, medals, singles/doubles/challenge progress, win/lose records and
streak, world ranking and the "King" level, plus how many plays are left on
the card (a new card starts at 199). Without a card you still play the full
arcade game, but nothing about you is remembered between credits (no new
gear, medals or ranking that carry over).

We can give the port the same thing without a card reader. The game keeps
your card's contents, unscrambled, in one fixed-size record per player
(612 bytes). The plan: when you pick your character at the start of a game,
the port puts your saved record into that player and marks "this player is
using a card" - exactly what the game does after a real card has been read.
The game then counts your points, medals and gear as it would for a card
player. After each match result (and at the end of the session) the port
copies the updated record into a small save file. The card reader itself
stays "switched off" as it is today, so you never see the "insert card"
messages, the 11-second card start-up screen or any card dialog.

What is solid: where the record lives, its size, when the game updates it
and when it would write it (all read from the code). What still needs a test
run: whether the game shows the card-only extras (new gear, medal and ranking
screens) with the reader switched off, how a brand-new save gets its name
(the real game's name entry is part of the card flow), and one small
progression (the King level) that the game ties to the reader setting
rather than to the player. The steps below each leave the game working and
can be switched off with one panel row ("Save progress: On / Off").

Not involved: the game's security dongle. The card's contents *are*
encrypted on the physical card (by the game itself, keyed by the card's
serial number), but option C works only on the game's already-decrypted
copy, so the port never touches keys or ciphers.

## 1. What the card is in this game

### Classes and globals (verified, symbols + disassembly)

| what | where |
| --- | --- |
| `tennis` singleton | `0x085061A4`; `+0x04` player* table (4 players, `player+0x4` = active), `+0x18` **card* table, one `card` per cabinet side** (index 0 = 1P, 1 = 2P), `+0x70` cardManager*, `+0xB4` backup*, `+0x94` vs*, `+0xF4` mtrLoopManager* |
| `card` (per side, size >= 0x1660) | ctor `0x080B580C`; methods `swap_row_card_data` `0x080B59F8`, `get_current_card_no` `0x080B5AB2`, `isNew_current_card` `0x080B5ADE`, `decode_card_data_tag(int)` `0x080B5B46`, `encode_card_data_tag(int,bool)` `0x080B619A`, `reset_card_data` `0x080B6CA6`, `set_used_card_flag`/`isUsedCard`, `decrement_rest_versus` |
| `CARD_DATA` (the save record) | **0x264 bytes (612)** - `player::reset_card_data(CARD_DATA&)` `0x08169B54` resets one; copies are `rep movsl` of 0x99 dwords everywhere |
| player's copies | `player+0x490` (the working CARD_DATA) and `player+0x6F4` (a second one; both reset by `player::reset_card_data()` `0x08169D36`); `player+0x958` = cabinet side; `player+0x14` = character |
| player flags | `player+0x6F0` (= CARD_DATA+0x260): bit0 **use card** (`isUse_card` `0x0816A196`, `setUse_card` `0x0816A1B6`, `resetUse_card` `0x0816A1E8`), bit4 new medal, bit5 new gear, bit6 renewed gear (set in `player::calcCard_data`) |
| cardManager statics | `m_r_req_` `0x084E8120`, `m_w_req_` `0x084E8160`, `m_r_result_` `0x084EA120`, `m_backup_data_` `0x084EC0E0`, `m_previous_data_` `0x084EE0E0` (4 x 0x800: side x row) |

### The `card` object layout (verified offsets, meanings partly inferred)

- `card+0x000` 0x264: a working CARD_DATA.
- `card+0x264 + row*0x264` (row 0/1): **two rows of CARD_DATA read from the
  card** - the card holds two copies (A/B), and the game keeps track of which
  is current: `+0x1638[row]` = each row's id/generation value, `+0x164C` =
  the current one (`get_current_card_no` returns the row whose id equals
  `+0x164C`), `+0x1648` used by `swap_row_card_data` (copy the newer row
  over the older). Inferred: classic double-buffered write - a pulled card
  mid-write still has the other row.
- `+0x1640`: 1 or 2 (setRealCardData: 2 -> use the current row, else row 0;
  inferred = number of valid rows).
- `+0x72C[row]` (int): **plays left on the card**. A blank card gets `0xC7`
  = 199 (`read_judge_card_data` `0x080B8899`); `cardManager::decrement`
  `0x080B82EC` / `ask_decrement` `0x080B81FA` count it down. Read result by
  value: 0 -> 5, 1..10 -> 2 ("few plays left", inferred), >10 -> 3, negative
  (-16..-1) -> 4 (inferred: expired/error codes).
- `+0x734[row]`, `+0x736[row]` bytes: `+0x736` = "blank (new) card" flag.
- `+0x738 + row*0x780`: the row's **tag stream**, 0x778 bytes, plain text
  after decryption: byte `0x32`, then (tag, length, value) items for 53 tags
  `0x01..0x35` from the table at `0x084151C0` (8 bytes per entry: tag,
  length; e.g. `0x06` 32 bytes, `0x1F` 20, `0x20` 156, `0x2E` 196 ...),
  `0xFF` ends it. `decode_card_data_tag(row)` parses it into the row's
  CARD_DATA; `encode_card_data_tag(row, bool)` builds it. (The tag format
  makes the card self-describing; field names are not in the binary.)

### What CARD_DATA holds (offsets into the record; verified from getters)

| field | offset | from |
| --- | --- | --- |
| character | +0x000 | `requestUnitSlotCue_ask_update` copies `player+0x490` to `player+0x14` then `decide_chartype`, `setPlayerData` |
| world ranking | +0x024 | `player::getWorld_ranking_card` `0x0816AC1A` |
| gear (wear/racket/colours) | ~+0x030.. | `player::setGears_default` writes `+0x4C0..` of the player (= record +0x30..), `getNew_gear_card(signed char&, CARD_DATA::gear&)` |
| play style | +0x04C (s8) | `getPlaystyle_card` |
| straight wins | +0x05C | `getVs_straightwin_card` |
| versus played / won / lost | +0x100 / +0x104 / +0x108 | `getVs_num_card`, `getVs_win_num_card`, `getVs_lose_num_card` |
| last play time (time_t) | +0x258 | `player::calcCard_data` `0x0816A6A5` stores `time(NULL)` at `player+0x6E8` |
| flags (use card, new medal/gear) | +0x260 | above |
| validity check | row +0x25C | `read_judge_card_data`: a row with this > 1 -> result 6 (inferred: format version/bad card) |

Also in the record (from the functions that update it, offsets not traced):
medals (`isNew_medal`, `isNew_medal_card`), singles/doubles counts and clears
incl. "clear special" (`addSingles_num/clear/clearsp`, `addDoubles_*`),
King count (`player::getKing_num` `0x0816BF70`, compared with 100),
per-point and per-swing stats (`addCard_point`, `addCard_swing`), rest-versus
counter, name (inferred: name entry `isName_entry_finish` and the 20-byte tag
`0x1F` - not traced).

**So: yes, it is a per-player save, and a complete one for that player** -
one character with everything that player earned. It is not a whole-game
save (cabinet settings, cabinet-wide high scores, and, with the reader OFF,
the King/boss level live in the cabinet's nvram, already saved today).

### When the game reads and writes it (verified call sites)

- **Read**: at insert, before/at character select. `cardManager::
  exec_common_card_seq` `0x080B9498` -> `iccd_request_search` -> on success
  `read_judge_card_data(side,row)` `0x080B85AE`: copy the 0x780 raw block,
  derive a key from the card serial (`serial_to_key` `0x080B7620`), decrypt
  (`CSerialDataConvert::decode` `0x080BFE6C`, a DES: `CSerialDataConvert::des`
  `0x080BE76C`, `makekey`), `card::decode_card_data_tag`, judge rest count.
  At character select `usrMenuCharLoop::exec_ask_use_card` `0x0812AAAC`
  ("use the card?") then `setRealCardData` `0x0812BB92` copies the current
  row into `player+0x490`, `setReal_ulFlag` sets bit0 of `+0x6F0`.
- **New card**: an all-blank block (<= 9 non-zero bytes) -> rest 199,
  `+0x736` = 1, result 1. Character select's new-card branch
  (`usrMenuCharLoop::exec` `0x08129FE3..0x0812A09E`): `backup::addNew_card_buf`,
  `addCard_play_buf`, `player::setUse_card()`, plus name entry / gear colour
  (`isName_entry_finish`, `isGear_color_finish`). So the game formats a blank
  card itself - no external issuing tool. (Card vending is the operator's
  business; nothing in the code dispenses cards.)
- **Updated during play**: `usrAcGameLoop::exec` -> `playerManager::
  addCard_update` (only players with `isUse_card`). After each match:
  `usrAcJudgeLoop::init` `0x0808624A` -> `playerManager::calcCard_data`
  `0x08168978` (ranking, medals, gear, play style; skipped in event mode) ->
  `setCard_write` -> `set_card_cue(write)`. Challenge mode:
  `ch_match::calcResult_score` -> `calcCard_data`.
- **Write**: the write cue -> `decrement` copies `player+0x490` into the
  card's current row -> `write_judge_card_data` `0x080B88DE`: encode tags,
  encrypt, into `m_w_req_` -> `iccd_request_write`. The write cues come up in
  judge, pass, win/lose, game-set-match, replay, continue, game over, ending,
  stats and challenge result loops (callers of `set_card_cue`).
  The cabinet also keeps a copy of the last card data in its SRAM
  (`backup::setBackup_card_data/serial_id/value_data`, `cardManager::
  set_backup_data` `0x080B784C`) to restore a card after a failed write.
- **End of session**: `usrAcStatsLoop::exec` -> `playerManager::resetUse_card`.

### Game features tied to the card

With `isUse_card`: card statistics (`addCard_*`), new gear and colours,
medals, play style evolution, world ranking (`calcWorld_ranking_for_solo/
_vs/_doubles`), versus records, the card pages of continue / game over /
ending / stats (`usrAcContinueLoop::draw_card`, `usrAcGameoverLoop::
draw_card`, `usrAcEndingLoop::initRecordUseCard` vs `initRecordUseNoCard`,
`usrAcStatsLoop::draw_card`, `usrChGameoverLoop::draw_card`), the King level
of the player (when the reader is not OFF: `match::getKing_level`
`0x08109F98`, `player::calcScore`). Card-less player: plays everything,
earns nothing that carries over; King level comes from the cabinet (reader
OFF) or stays 0 (reader ON, no card - inferred).

## 2. How the game talks to the reader (verified unless marked)

- Vendor: **Toppan** IC card R/W (`CSerialManagerToppan`,
  `CSerialRequestToppan`). Layers: game -> `cardManager` cues ->
  `CSerialManagerCommon::iccd_*` (`iccd_init` `0x08111D44`,
  `iccd_check_system` `0x08111E1A`, `iccd_request_search` `0x08111E42`,
  `iccd_response_search`, `iccd_request_write` `0x08111F20`,
  `iccd_response_write`, `iccd_check_request`; state table
  `m_iccd_info` `0x08504BC0`) -> `CSerialManagerToppan::iccd_ctrl_*`
  (reset / search / write / all) -> `CSerialRequestCommon::ic_request_stack_*`
  (packet build, `ic_request_calc_bcc` checksum) -> `CSerialRWUnix`.
- Device: **`/dev/tts/0` (1P) and `/dev/tts/1` (2P)** (strings `0x08390477`,
  `0x0839046C`; `CSerialRWUnix::ser_ic_init` `0x08116006`), opened
  `O_RDWR|O_NOCTTY|O_NONBLOCK` (0x902). **9600 baud, 8 data bits, even
  parity, 1 stop, CLOCAL|CREAD** (`ser_ic_port_init` `0x0811616E`: c_cflag
  0x9B0, `cfsetspeed(9600)`), switchable to 38400 (`ser_ic_change_baudrate`
  `0x081160F6`). The port refuses every `/dev/*` open (`hle_libc.c`
  `host_device_refused`), so `iccd_check_system` stays false.
- cardManager: cue bitmask (`set_card_cue(kCardRWCueType)` `0x080BCE70`,
  `isFinishedCue`, `reset_card_cue`, values 0x1..0x400 seen), per-side
  sequences `exec_automatic_slot/unit_slot/pair_slot` (unit = 1 player per
  side, pair = doubles, inferred), `exec_common_card_seq`,
  `init/exec_write_card_seq`, `init/exec_eject_card_seq`, `set_eject`,
  `set_eject_not_samecard` (a different card re-inserted), `isLockCard`
  (JVS card-lock output), slot window messages (access / success / failed /
  pulled). Boot: `cardManager::startup` + `usrStartupCardLoop` 660-frame
  "CARD R/W INITIALIZING". Test mode has a card test and a card editor
  (`usrCardTestLoop`, `usrCardEditLoop` with its own encode/decode).

## 3. Options

### A. Emulate the Toppan reader on the serial port (not chosen)

A device behind `/dev/tts/0`/`1` in the open/read/write hooks, like
`hle_rideboard.c` does for HOTD4SP's ride board. Most faithful (all card
screens, insert/eject on a panel button), most work: the Toppan command set,
framing and BCC have to be read out of `CSerialManagerToppan::iccd_ctrl_*` /
`CSerialRequestToppan` (no protocol notes in the repo; only the rideboard
precedent). Card images could stay opaque (the game encrypts with its own
key; a blank image is a valid new card), so no cipher work, but timing,
error and baud-switch behaviour must be right or the game shows card errors.
Weeks; player sees every card prompt.

### B. Replace the iccd_* layer (not chosen)

Override `iccd_check_system` (true), `iccd_request_search`/
`iccd_response_search` (card present + the stored 0x780 blocks + header
`IccdCardHeader`), `iccd_request_write`/`iccd_response_write` (store
`m_w_req_` blocks), `iccd_check_request` (done). The game still does its own
DES - the port stores the bytes it is given, and a first card is just zeros,
so no keys in the port. Less work than A, still all card dialogs ("use
card?", writing, eject, "card pulled") and the R/W setting must be ON, so
the notice/boot wait come back unless hidden separately. Days.

### C. Load/save the record directly, no card UI (CHOSEN)

#### Principle

Leave the reader **OFF** (today's default `h_vt3_card_rw_off`,
`hle_sega.c` ~1063/1874) - that is what keeps every card screen, prompt,
eject message, boot wait and notice away, and it stays the reason the notice
is gone (the "card R/W OFF by default" decision stands; C builds on it, it
does not reverse it). Then do by hand the three things a successful card
read leaves behind, and catch the record at the moments the game would
write it:

1. the player's record `player+0x490` (0x264 bytes) filled,
2. the player's use-card bit (`player+0x6F0` bit0) set - via the game's own
   `player::setUse_card()` (`_ZN6player10setUse_cardEv`, also resets play
   style through `set_playstyle`),
3. the side's `card` object (`tennis+0x18`[0]) made to look like a read
   card, because the `*_card` getters read it rather than the player:
   row 0 (`card+0x264`) = the record, `+0x1638[0]` = `+0x164C` = `+0x1648` =
   a fixed id (e.g. 1), `+0x1640` = 1, `+0x72C[0]` = 199 (topped up on every
   load, so "plays left" / expiry never comes up), `+0x736[0]` = 0.

Nothing in `cardManager`, `CSerialManager*` or `CSerialDataConvert` is
called, hooked or answered: with the reader OFF the cardManager never
starts a sequence, so there is no cue to fake (verified for the boot path
and the slot windows in the earlier doc; inferred for the write cues - with
OFF `set_card_cue` has no reader to drive, and `isCard_writing` is cleared
by `resetCard_write`; this is step 3's proof).

#### When to load (1P only)

At character select, at the moment 1P's character is decided in the no-card
path - candidate hooks (pick in step 1 by logging): wrap
`usrMenuCharLoop::changeCharacterDataNotUsingCard(int)` `0x0812C9CE` /
`selectCharacterNoUsingCard(int,int)` `0x0812C93E` (return), or the
existing `mtrLoopManager::setMode` wrap in `hle_sega.c` when the menu loop
leaves character select. Load *after* the game set the player up for the
chosen character, so its own defaults are in place, then overlay the saved
record and call `setUse_card`. Side -> player: `vs::getPlno(side)`
(`0x0818018C`, `this` = `tennis+0x94`), player* = `tennis+0x4`[plno].

**One player, but the card is tied to one character** (record +0 is the
character; with a real card the character is fixed). Recommendation: the
save file holds one record **per character**, and picking a character loads
that character's record (or starts a fresh one). That keeps "always the
same player" with no picker and never forces a character on the owner.
(Alternative: one record, character locked like a real card - simpler file,
worse to play.)

The file is read once at boot (or at first use) into host memory; a bad
file is reported and ignored (game plays card-less, file untouched).

#### Fresh save (first run, or a character not yet in the file)

`player::reset_card_data(CARD_DATA&)` `0x08169B54` on `player+0x490` (the
game's own blank record) + character at +0 + `setUse_card` + the card
object as above. This is what the game's new-card branch does
(`usrMenuCharLoop::exec` `0x08129FE3`: `addNew_card_buf`, `addCard_play_buf`,
`setUse_card`). Name: the real new-card flow runs name entry and gear colour
(`isName_entry_finish`, `isGear_color_finish`, `cardManager::
set_nameentry_flag`). Whether the game offers name entry with the reader
OFF is **unknown** (step 5); fallback: a fixed default name written into the
record (needs the name field's offset - trace `nameEntry::*`), or leave the
game's default.

#### When to save

- After `playerManager::calcCard_data` `0x08168978` returns (wrap): judge of
  every arcade match (`usrAcJudgeLoop::init`) and challenge results
  (`ch_match::calcResult_score`). Write 1P's `player+0x490` if its use-card
  bit is set.
- Before `playerManager::resetUse_card` `0x08168C28` (wrap, call original
  after): end of session in the stats screen - the final state.
- Only these two; nothing per frame. (`addCard_update` runs per point; no
  need to save that often - a match lost to a crash costs one match.)

#### File, location, safety

- Name `vt3_save.bin`, next to `lindbergh_nvram.bin` (the game directory,
  the runtime's cwd): macOS `~/code/quest_games/vt3/disk0/vt3_Lindbergh/`
  (a `lindbergh_nvram.bin` is there today; `extracted/disk0/...` has one
  too - whichever game directory the run uses); Quest `/sdcard/VirtuaTennis3/vt3_Lindbergh/`
  (survives app reinstall, like the nvram). Override `LINDBERGH_VT3_SAVE_FILE`
  (like `LINDBERGH_NVRAM`) for test runs, so unattended runs never touch the
  owner's save.
- Format (ours): magic `VT3SAVE1`, version, record size (0x264, refuse
  others), binary id (`vt3_Lindbergh_HD`), count, then per record:
  character id, saved time, CRC-32 of the 0x264 bytes, the bytes.
- Write: whole file to `vt3_save.bin.tmp`, fflush+fsync, rename the old
  file to `vt3_save.bin.bak`, rename tmp into place. On load: bad magic/CRC
  -> try `.bak` -> else card-less with a log line; never overwrite a file we
  could not read (write to `vt3_save.bin.unreadable-<time>` first).
  (The runtime's own `nvram_save` writes in place; do not copy that.)
- "Reset save": rename to `vt3_save.reset-<date>.bin` (recoverable), not
  delete.
- 2P: **no card** (as today) - the second player plays card-less and
  nothing of theirs is saved. Later, if wanted: the same code with
  `vt3_save_2p.bin` and side 1; nothing in the design blocks it.

#### Panel and switches

- Panel (Classic and Immersive, both - it is not a display setting): one
  row "Save progress: On / Off" (on restart is fine; applying it live at the
  next character select is also safe), and "Reset save..." with a
  confirm ("Erase saved progress? Yes / No"). vr.cfg key `save on|off`
  (`xr_settings.c`, `world_mode.c` like `classic.card_notice`); env
  `LINDBERGH_VT3_SAVE=1|0` wins, shown "(env.txt)" like the others.
  Desktop: the same key in host settings.
- Default: On once steps 1-5 are proven; Off until then.
- Interaction with the existing "Card reader notice" row: keep both
  independent. Notice On (reader ON, real hardware path) + save On is
  pointless: make save On force the reader OFF for that run and log it.

#### What is still uncertain (the steps prove or settle each)

- That the card-only screens/awards (new gear, medal, ranking pages) appear
  with the reader OFF: they key on `isUse_card`, but some draw paths may
  also test the R/W setting or `cardManager` state (`cm+0x28/+0x29`,
  inferred per-side "card present" bytes - `usrMenuCharLoop::exec` tests
  them at `0x08129FB8`/`0x0812A0BA`).
- King level: with both sides OFF the game uses the cabinet's King level
  (`backup::getKing_level`/`addKing_level` in `getKing_level`/`calcScore`)
  instead of the player's. That still persists (nvram) and for one player
  it is nearly the same thing; if the owner wants it per save, wrap
  `match::getKing_level` to return the 1P player's `getKing_num` when the
  save is active (small).
- "Update card?" prompt at character select (`requestUnitSlotCue_ask_update`
  when `isNew_medal_card`/`isNew_gear_card` differ between player and card
  row): keeping the card row equal to the player's record after each save
  should keep it quiet (inferred).
- Doubles with 1P using a card (pair slot) - not traced.


## Outcome (2026-11-12, T16 build worker - option C built, macOS-verified, Quest smoke run owed)

Built as designed, with these choices (code: `vt3_save.c/.h`, `hle_sega.c`
"Save progress (T16)"):
- **Load hook:** `player::reset_card_data()` when it returns to
  `usrMenuCharLoop::exec_no_card`'s decision (0x0812A8DD; after
  `decideUsePlayer`, before `decide_chartype` / `setPlayerData`, i.e. where a
  card's record would already be in place), side 0 (`player+0x958`). Saved
  record -> `player+0x490`, flags `| 1`, bits 4-6 ("new" marks) cleared - what
  `setRealCardData` + `setReal_ulFlag` do; fresh: the game's own blank record +
  character at +0 + `player::setUse_card()`. Card object row 0 = the record
  (ids 1, `+0x1640` 1, plays left 199, not new), then
  `usrMenuCharLoop::setRealPlayerName(0, plno)` (without it the result slate
  shows "(null)" under the player's name).
- **Save hooks:** after `playerManager::calcCard_data` (once per match, at the
  match's last JudgeLoop) and before `playerManager::resetUse_card` (not seen
  in prize runs: the StatsLoop after a won match continues the session).
- **File:** `vt3_save.bin` in the game directory (`LINDBERGH_VT3_SAVE_FILE`
  overrides), format as planned (header + CRC per record + CRC of all);
  missing file -> `.bak` if good, else fresh; unreadable -> moved to
  `.unreadable-<time>`, `.bak` tried, else fresh; never written over.
  Unit tests `tests/test_vt3_save.py`.
- **Setting:** `save on|off` (vr.cfg), `LINDBERGH_VT3_SAVE=1|0`, row "Save
  progress" on both Advanced pages (one value, on restart, kept by Restore
  defaults), macOS menu Game > Save Progress. Save on keeps the card readers
  off even if Classic's Card reader notice is On. **Default Off** - see below.

Open points, as far as macOS settles them:
- **Name entry:** not offered - `exec_no_card` has no name-entry step; a fresh
  save is named "noname" (the game's blank record), shown under the
  character's name on the result slate. A name would need the record's 32
  bytes at +0x04 written (e.g. a panel text field) - not done.
- **Card-only pages with the reader off:** none appeared in prize runs
  (result slate, total money, next round); the continue / game over / ending
  card pages are reached only by losing - not exercised (prize always wins).
- **King level:** follows the save, as with a real card: with Save progress
  on, round 0 is Milan (King level 0 of a fresh save) instead of Dusseldorf
  (the cabinet's level, used card-less since T15).
- **"Update card?" prompt:** never (the card path is never entered).
- Also seen: rallies run longer with a save (first point's judge at frame
  2442-3004 vs 2575 Off; match end 3260-3798 vs 3353) - a card player plays
  with the record's own play style; not investigated. `+0x258` (last play
  time) stays 0 in our records; `+0x25C` becomes 2.
- Carry-over (character 0, one prize match per session): `+0xA8` 1/2/3,
  `+0xB0` and `+0xB4` 2/4/6, `+0x118` and `+0x128` 1/2/3 after sessions
  1/2/3 (`~/Desktop/Claude/vt3-save/record_bytes.txt`).

**Default Off**, because: the lose path (continue / game over / ending, where
the card pages and card-write waits are) is untested; a save changes the
game (King level / venue order, play style) - the owner should choose it;
and the Quest file location is unchecked. Flip `save` in
`LG_XR_SETTINGS_DEFAULT` (xr_settings.h) once the owner has judged it.

## 4. Legality / safety

- The card is the player's own save medium, not copy protection: without
  it the game is complete. Its contents are DES-encrypted on the card by the
  game (`CSerialDataConvert::des/makekey`, key from the card serial via
  `cardManager::serial_to_key`) - anti-tamper / anti-cloning of card data.
  **Option C stops above that boundary**: it reads and writes only the
  decrypted `CARD_DATA` in game memory; the port contains no key, no cipher,
  no call into `CSerialDataConvert`, and does not decrypt any card image.
  (B/A could likewise store only bytes the game encrypted itself.)
- The **security dongle** is a separate path that happens to sit in the same
  character-select function: `usrMenuCharLoop::exec` calls `amDongleUpdate`
  `0x0812A17C`, `amDongleSetSeedSend/Recv`, `amDongleSetIv`,
  `amDongleDecryptEx` `0x0812A251` then `tennis::setError`. It is not part
  of the card system and the save work must not hook, move or depend on it
  (the runtime's existing amDongle handling in `hle_sega.c` ~2026-2038 is
  out of scope). Hook points chosen above are other functions.

## 5. Recommendation and steps (C)

Each step is behind `LINDBERGH_VT3_SAVE` (default off until step 6), leaves
the game playable, and is proven by unattended macOS runs with
`LINDBERGH_VT3_SAVE_FILE=<scratch>` (never the owner's file) using the usual
`scripts/vt3-repro.sh` round scripts (log + `LINDBERGH_GAME_SHOT` frames).

1. **Observe only.** Wrap the char-select decision candidates,
   `playerManager::calcCard_data`, `playerManager::resetUse_card`,
   `player::setUse_card`; log frame, side, plno, character, `+0x6F0`.
   No behaviour change. Proof: a credit-start-to-stats run logs one decision
   for 1P, calcCard_data at each judge, resetUse_card at stats; frames
   identical to a run without the switch.
2. **Fresh record in memory, no file.** At 1P's decision: reset record,
   character, `setUse_card`, card object (row 0, ids, rest 199). Proof: run
   completes a match and reaches stats without hang/crash; log shows
   use-card 1 and, after the judge, changed counters (+0x100 versus played,
   +0x258 time) in `player+0x490`; shots of continue/game over/stats -
   look for card pages (first answer on the "card-only screens" question).
   Also check the match-end waits do not stall (isCard_writing).
3. **Save.** After calcCard_data / before resetUse_card write the file
   (tmp+fsync+rename, .bak). Proof: file exists, CRC ok, two runs leave
   `.bak` = previous; a run killed mid-match leaves a readable file.
4. **Load.** At decision, load the character's record if present. Proof:
   run 1 then run 2 with the same scripted character: run 2's log shows
   loaded counters = run 1's saved; after its judge they increase. Corrupt
   the file (scratch copy) -> run falls back to `.bak`, then card-less, no
   crash.
5. **Name and extras.** Settle name entry for a fresh record (log/shots of
   the new-save path; else default name), King level choice, "update card?"
   prompt never shown (shots every 60 frames through char select).
6. **Panel + settings.** "Save progress: On/Off", "Reset save..." with
   confirm; vr.cfg `save`; env pin shows "(env.txt)". Default On. macOS proof:
   env/vr.cfg combinations logged at boot; reset renames the file.
7. **Quest (only there):** the file lands in
   `/sdcard/VirtuaTennis3/vt3_Lindbergh/` and survives an app reinstall;
   panel rows and the confirm work with the controller; one short owner
   smoke run (play a match, quit, restart, see the progress). Per the
   minimal-headset-test rule: one run per change, owner judges.

Rough size: steps 1-4 are a few hundred lines in `hle_sega.c` (or a new
`vt3_save.c` next to it) with the existing `vt3_wrap`/`guest_call`/`rd32`
helpers; step 6 follows the `classic.card_notice` row's pattern.
