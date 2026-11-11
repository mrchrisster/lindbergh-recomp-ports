# Virtua Tennis 3: replay paths and the match end with Replays off

Static analysis of the original ELF
(`~/code/quest_games/vt3/disk0/vt3_Lindbergh/vt3_Lindbergh`, full symbols,
disassembled with `objdump -d -M intel -C`), done 2026-11-10. Addresses are guest
virtual addresses. Manager global: `mgr = [0x85061A4]`, with +0x1c the match,
+0x20 the challenge match (`ch_match`), +0x90 the replay object, +0x94 the vs
object, +0xf4 the top-level `mtrLoopManager`, +0xfc `usrAdvLoop`, +0x104
`usrAcLoop`, +0x108 `usrChLoop`.

## Outcome

- **Match end with Replays off: fixed** as recommended below.
  `h_vt3_set_mode` wraps `mtrLoopManager::setMode` (submodule commit 3227314).
  Verified on macOS and on the Quest.
- **"Some replays still play with Replays off": closed.** Two full matches
  with Replays off logged no `ReplayLoop` and no `initReplay`. In total: 0
  `ReplayLoop` in about 2.5 macOS arcade matches, two Quest Immersive matches
  and 5 minutes of attract. What the user saw was the per-point Winlose
  cutaway, which is not a replay.
- **Point cutaways switch:** `h_vt3_skip_winner` (commit e9f1be9). With Point
  cutaways off, the Winlose loop is now skipped entirely (submodule 1b1988b).
- **Replays switched off during a replay:** the replay ends through the
  game's own skip path (dca91c9). `h_vt3_skip_winner` answers yes for return
  address 0x0808A850 (the `check_skip_button_winner` call in
  `usrAcReplayLoop::exec`). On the Quest it ended 2 frames after the click.
  - `h_vt3_set_mode` is installed even with `LINDBERGH_FORCE_REPLAY=1`.
  - A log-only line `[vt3] ... replay requested with Replays off` exists. It
    has never fired.
  - WARNING lines are printed if the wraps fail to install.
- **Testing note:** replay frames vary between runs (3012, 3015 and 3540 were
  seen), so a single timed panel click misses. Toggle over a window of frames.

## Loop numbers

`mtrLoopManager` at `mgr+0xf4` picks the top-level mode:

| Check | Mode | Loop object | That loop's own manager |
|---|---|---|---|
| `checkMode(1)` | attract demo | `usrAdvLoop` at `mgr+0xfc` | `[[+0xfc]+0x18]->(+0x14 or +0x24)->+0x14` |
| `checkMode(4)` | challenge | `usrChLoop` at `mgr+0x108` | `[[mgr+0x108]+0x14]` |
| anything else | arcade | `usrAcLoop` at `mgr+0x104` | `[[mgr+0x104]+0x14]` |

Arcade (`usrAcLoop::init`, jump table 0x838292c):

| # | Loop | # | Loop |
|---|---|---|---|
| 0 | Load | 10 | Gamesetmatch |
| 1 | Gameinit | 11 | Stats |
| 2 | Entrance | 12 | Continue |
| 3 | Start | 13 | Gameover |
| 4 | Game | 14 | Ending |
| 5 | Judge | 15 | Staffroll |
| 6 | Pass | 16 | Nameentry |
| 7 | **Replay** | 17 | Ranking |
| 8 | **Winlose** | 18 | Tobecontinued |
| 9 | Changeend | 19 | EndingGameover |

Challenge (`usrChLoop::init`, table 0x8387d4c):

| # | Loop | # | Loop |
|---|---|---|---|
| 0 | Intro | 8 | Pass |
| 1 | MsSelect | 9 | **Replay** |
| 2 | Load | 10 | **Winlose** |
| 3 | Gameinit | 11 | Changeend |
| 4 | Entrance | 12 | Gamesetmatch |
| 5 | Start | 13 | Result |
| 6 | Game | 14 | TotalResult |
| 7 | Judge | 15 | Gameover |

Attract demo (`usrAdvDemoplayLoop::init`, table 0x8380f3c):

| # | Loop | # | Loop |
|---|---|---|---|
| 0 | Gameinit | 4 | Judge |
| 1 | Entrance | 5 | Pass |
| 2 | Start | 6 | **Replay** |
| 3 | Game | 7 | **Winlose** |

`usrAdvRankingLoop` builds the same Pass, Replay and Winlose loops.

**How a loop switch runs** (`mtrLoopManager::exec` 0x817a38e):

- `setMode` only queues the new loop.
- On the next frame the manager calls the old loop's `finish`, then the new
  loop's `init`, then its `exec`, all in that same frame.
- The vtable order is `[0]` init, `[1]` exec, `[2]` finish (vtable for
  `usrAcReplayLoop`).

## What the `replay` class decides

**`replay::isReplay_point` (0x810e18e)** answers 1 if any of these hold:

- `match::isMatch()` (byte `match+0xd6`);
- `+0x6f8` (smash);
- `+0x6f9` (high volley);
- `+0x700` (service ace);
- `+0x703`.

When `isMatch` is 0 there is one more rule. In arcade, if `[mgr+0x24]` is 0
or 2 and the point player is 0..3, the answer becomes 0 when that player's
type (`+8`) is 4. So **the match-winning point always earns a replay.**

**`match+0xd6`** is set only by `match::setEvent(12)` (0x810b0a6).

- `setEvent(12)` also sets bit 0x1000 in `match+0x1c`.
- `setEvent(n)` sets bit `1<<n` and calls `hud::setEvent`.
- `+0xd6` is cleared only in `match::init` and the constructor.
- So `isMatch` means "the match is over" and stays on until the next match.
- `match::isGame` is bit 0x400 (event 10, a game won).

**The replay flags** are filled by `calcReplay_point` (called from
`match::calcPoint`) and cleared by `resetReplay_point` (called from
`game::restart`).

**There is no other replay decision.** The symbol table has no
`isReplay_game`, `_set`, `_match`, highlight or challenge replay. The other
methods only record, play back or handle slow motion:

- recording: `rec`, `rec_key`, `rec_swing`, `rec_MoveFlag`;
- playback: `start`, `exec`, `restore`, `end_forced`, `reverseFrame`;
- slow motion: `startSlow`, `execSlow`, `isSlow*`, `getSlow_speed`.

**`replay::start` (0x810d4a4):**

1. Saves each active player (memcpy of 0x3158 bytes into `[+0x6f0][i]`).
2. Sets byte `[this]` = 1 (active) and `[this+2]` = 1.
3. Calls `camera::setReplayType`.
4. Calls `replay::exec` once.

**`replay::exec` (0x810d738):**

- Returns 1 at once when `byte [this]` == 0.
- Otherwise it plays recorded frames.
- After frame 0x78 it calls `restore` and returns 1.

**`replay::restore`** copies the saved players back, calls `resetSlow`, and
clears `[this]` and `[this+2]`.

**`usrAcReplayLoop::exec` has a skip path:** after `check_skip_button_winner`,
once more than `getCnt_skip_max` frames have passed, it calls `restore` and
treats the replay as done. The fix for a replay that is already playing when
Replays goes off uses this path.

## Replay entry paths

| Path | Address | Called by | When it fires | Covered by the switch? |
|---|---|---|---|---|
| `replay::start` | 0x810d4a4 | only `usrAcReplayLoop::init` (0x808a313) | when the Replay loop begins | yes, indirectly |
| `usrAcReplayLoop::init` / `exec` | 0x808a2fa / 0x808a538 | loop manager, after `setMode` to Replay (arcade 7, challenge 9, demo 6) | — | yes |
| `setMode(Replay)` | call 0x8086b12 (return 0x08086B17) | only `usrAcPassLoop::exec`, on the "no flag set" branch; no other `setMode(7/9/6)` targets a Replay loop | point decided and `isReplay_point` true | **yes**: the only gate |
| `replay::isReplay_point` | 0x810e18e | Pass 0x8086ee7, and `usrAcWinloseLoop::init` 0x808e401; both are `DISPATCH_TO` calls, so the override catches them | after each decided point; in Winlose it only chooses whether to show the center info board | yes, wrapped |
| Challenge mode | — | Pass never reaches the no-flag branch in mode 4 | never | n/a, no replays there |
| Attract demo | — | the same Pass decision | — | yes |
| `camera::initReplay` | 0x80b17d8 | camera mode 6, set only by `usrAcReplayLoop::init` | — | yes |
| `sound::playBgm_replay` | 0x816ffe2 | only Pass 0x8086e69, on the first Pass frame of the no-flag branch | — | yes |

## `usrAcPassLoop::exec` (0x808685a): the three flags

**Pass length:** 60 frames, or 30 in challenge mode (`cmove`). At frame 30 it
plays the audience cheer. The flags start at 0. `match+0x18` bit 0x4 / bit
0x8 behave like fault / double fault (my reading).

**Choosing a flag:**

1. If bit 0x4 is clear and `match::isLet()` is false, go to the decision (D).
2. Otherwise, if bit 0x8 is set, go to D.
3. Otherwise, outside challenge mode, set **d** (fault or let). In challenge
   mode, go to D if `ch_match::isFinished()` (byte `ch+0xac`) is true, else
   set d.

**The decision D:**

- **Challenge mode, finished:** set e when `[ch + ch[+8] + 0x1b]` == 1,
  else f.
- **Challenge mode, not finished:** set e when that byte == 1, else d.
- **Attract demo with `getAdvdemo()` == 3:** set d.
- **Everywhere else:** if `isReplay_point()` is false, set **e** (0x8086ef0).
  If it is true, set no flag.
- **No flag set:** on the first Pass frame (`[this+0x14]` == 1) it also calls
  `changeWipeResource(1.0)` and `playBgm_replay`.

**After the timer**, and once `vs::isReq_vs_game` / `isVs_stop` allow it:

| Flag | Next loop | Extras |
|---|---|---|
| **d** `[ebp-0xd]` | Start (arcade 3, challenge 5, demo 2) | `fade(30)`, `stopKansei` |
| **e** `[ebp-0xe]` | Winlose (arcade 8, challenge 0xa, demo 7); call at 0x8086c68, return **0x08086C6D** | `fade(30)`, `stopKansei` |
| **f** `[ebp-0xf]` | challenge only: clears match bit 0x1000, then challenge mode 0xd (or 0xe if `[ch+0xb4]->+4` > 3) | `hud::resetResult`, `fade(30)` |
| none | Replay (arcade 7, challenge 9, demo 6) | no fade, `stopKansei` |

## Why the match never ended with Replays off

**Winlose never ends a match.** `usrAcWinloseLoop::exec` runs 120 frames, or
fewer with the skip button. It never tests bit 0x1000:

- `isTiebreak_changeend`, or bit 0x400 set (it clears 0x400): go to
  Changeend (9);
- otherwise: go to Start (3).

**Only the Replay loop ends an arcade match.** `usrAcReplayLoop::exec` tests
`match+0x1d & 0x10` at 0x808a640. When the replay is done, it clears 0x1000
and picks the next loop:

| Condition | Next mode | Extras |
|---|---|---|
| `[mgr+0x24]` not 0 or 2 | 0xa (Gamesetmatch) | — |
| `[mgr+0x24]` is 0 or 2, and `match::isWinner(vs::getGame_master_plno())` | 0xa | — |
| `[mgr+0x24]` is 0 or 2, and not the winner | 0xb (Stats) | `sound::stopSoundAll` |

In every case it then restores the camera (`cam+0x38 = cam+0x40`), starts
`fade(30)` and calls `fadeoutBgm_replay`.

**Other modes:**

- Challenge mode with the match finished goes to challenge mode 0xc, but
  challenge mode ends its matches through flag f anyway.
- In the attract demo the Replay loop always goes to Winlose (7).

**What went wrong:** answering 0 on the last point sent it to Winlose (8).
Bit 0x1000 was never consumed, and new games started forever.

**What the fix does** (`h_vt3_set_mode`):

- **Condition:** `!g_replays`, return address 0x08086C6D, mode == 8,
  `self == [[mgr+0x104]+0x14]`, and `match+0x1c & 0x1000` set.
- **Action:** clear 0x1000, then use mode 0xa or 0xb chosen exactly as
  `usrAcReplayLoop::exec` chooses. After the original call, run
  `stopSoundAll` for 0xb.
- **Already the same as the original:** the e path supplies `fade(30)` and
  `stopKansei`.
- **Not needed:** the camera restore and `fadeoutBgm_replay`, because the
  camera never switched and the replay music never started.
- **Stack layout** (`dispatch.c`): an override runs after the return address
  is popped. `rd32(esp-4)` is the caller, and `A32(0)` / `A32(1)` are `this` /
  mode.

**Fallback that was not used:** off, answer `isReplay_point` =
`rd8(match+0xd6)`. The match ends through the game's own code, but the
closing replay plays.

- To hide it you would also make `replay::start` do nothing; `exec` then
  answers 1 at once.
- Even so, one frame of camera mode 6 plus the "replay" overlay (resource
  0x7a) would likely show.
- `playBgm_replay` would also sound for about 1 second.

## Cutaways that are not replays

None of these use recorded frames.

| Loop | Camera mode | When | Notes |
|---|---|---|---|
| `usrAcWinloseLoop` | 7 | after **every** decided point, Replays on or off | 120 frames, or shorter via `check_skip_button_winner` (return 0x0808E6CB) after `playerManager+0x78` frames; split-screen about 1 in 10 (`camera::initWinlose`) |
| `usrAcChangeendLoop` | 8 | change of ends | — |
| `usrAcGamesetmatchLoop` | 9 | match end | `camera::initMatch` calls `replay::startSlow`: a slow-motion celebration |
| `usrAcStatsLoop` | 10 | after the match | — |

`check_skip_button_winner` is also called by Start (0x8085a81), Gamesetmatch
(0x8088741) and Replay (0x808a84b). Any wrap of it must filter by return
address.

## Verified versus inferred

**Verified in the disassembly:**

- every address, branch, loop number table and caller list;
- the camera mode setters;
- the `isReplay_point` logic;
- `setEvent(12)` setting 0xd6 and bit 0x1000;
- the Replay loop as the only arcade match-end route;
- the init/exec/finish order within one frame;
- the stack layout of an override.

**Verified in runs:** the match-end fix (macOS and Quest), and no
`ReplayLoop` / `initReplay` with Replays off (see Outcome).

**Inferred:**

- the names for the mode values (1 = attract, 4 = challenge);
- the meaning of `match+0x18` bits 0x4 and 0x8, and of the challenge byte
  `[ch + ch[+8] + 0x1b]`;
- that bit 0x1000 is still set while Pass runs. The fix works, so in practice
  it holds.
