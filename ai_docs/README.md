# AI working notes – Virtua Tennis 3 on Quest 3

Read this first. It records what is done, what is being worked on and how to
test, so nothing gets researched twice. The user-facing tracking list is
`docs/VT3_QUEST_BACKLOG.md`; how each fix works is in `docs/VT3_PORTING_GUIDE.md`
section 8. Add to this file whenever a session finds something.

## Ground rules

- Push only to the `fork` remote (mrchrisster/...), branch `vt3-quest`:
  the `lindberghrecomp` submodule first, then this repo. **No PRs or pushes to
  lialan's upstream repos** (origin push URLs are disabled on purpose).
- Never commit `games/*/generated`, game data or the APK. No decryption, no
  dongle circumvention.
- Don't turn Guardian off from adb; ask the user to confirm prompts in the
  headset ("Finding position in room" means the room is too dark).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## How to test

- Quest build: `JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ANDROID_NDK=$HOME/Library/Android/sdk/ndk/28.2.13676358 sh quest/build.sh vt3 > /tmp/qb.log; grep error: /tmp/qb.log; adb install -r quest/VirtuaTennis3VR.apk`
  ("1 errors" in the log is the old target-SDK lint notice; the APK is built.)
- macOS build: `ninja -C build-mac`. Game data: `~/code/quest_games/vt3`.
  **Immersive mode does not run on macOS** (the window closes right after start).
- Unattended runs: `scripts/vt3-repro.sh <scene> quest <secs>` or
  `... <scene> mac ~/code/quest_games/vt3 <secs>`. Extra `LINDBERGH_*` variables
  in the environment are passed through. The script **empties the headset's
  env.txt** at exit; restore with
  `adb shell "echo LINDBERGH_VT3_IMMERSIVE=1 > /sdcard/VirtuaTennis3/env.txt"`.
- Scenes: `round0` (normal first match), `forty` (every game starts 40-0 –
  **unsuitable for match-length tests**, see below), `prize` (1P wins every
  point from 40-0: the match is over in two points), `replay`, `splitreplay`.
- Useful switches: `LINDBERGH_VT3_WIN=1` (1P wins every point),
  `LINDBERGH_REPLAYS=0|1` (now works on macOS too), `LINDBERGH_VT3_FLOWLOG=1`
  (each arcade screen loop the game starts: `[flow] frame N: GameLoop` ...),
  `LINDBERGH_GAME_SHOT=<first>,<every>` (game picture), `LINDBERGH_XR_SHOT=...`
  (eye image without the compositor's layers).
- `adb exec-out screencap -p` captures the **composited** headset view
  (quad layers, system dialogs), 4128x2208 both eyes.
- Headset logs: `adb logcat -v time -s 'vt3:*'`, or `vt3.log` in
  `/sdcard/VirtuaTennis3/vt3_Lindbergh/`. Start logcat right before launching,
  because the Quest's log buffer rolls over within minutes.
- Callees/callers of a game function by name: a small script that scans
  `games/vt3/generated/recomp_funcs_*.c` for `call 0x...` and maps addresses
  with `recomp_symbols.h` (keep the longest body when a function appears in
  several files). Symbols are mangled, e.g. `_ZN3hud14drawServePowerEv`.

## Done (see the backlog's Done list for the full set)

- 2026-11-10 **Start-up screen** (`host_xr.c` splash section, art from
  `quest/tools/vt3_splash.py` -> `games/vt3/src/splash_art.c`). Verified in
  headset captures, both before the game's first frame (thread) and over the
  game's black boot. Startup timing: ~1.5 s to the XR session, ~8 s to the
  game's first frame, ~20 s of the board's own black boot, then the white logo.
  macOS still starts on black (not done).
- 2026-11-10 Start-of-match cameras, floating crowd, HUD on head movement, sky,
  shadow map, ad flicker, stands, blotches, shadows – all in the guide.

## In progress

### Match never ends with Replays off (bug, high priority)

User report: after one player wins 2 games the match keeps going endlessly.

**Root cause confirmed:** the headset menu's *Replays off* switch. Not immersive
mode – plain mode does the same.
- `prize` scene on the Quest, `LINDBERGH_REPLAYS=1`: game 2 ends, the match ends
  (closing replays play). With `LINDBERGH_REPLAYS=0`: new games forever
  (frames 2625, 3566, 5402, 7237, ...).
- `round0` + `LINDBERGH_VT3_WIN=1`, Replays off (from the user's saved vr.cfg):
  endless in immersive mode and in plain mode (6 games by frame 17557).

Mechanism: the switch wraps `replay::isReplay_point` and answers 0 always
(`h_vt3_is_replay`, `hle_sega.c`). Two callers:
- `usrAcPassLoop::exec` (0x808685a), between points. It sets one of three
  locals: `[ebp-0xd]` / `[ebp-0xe]` / `[ebp-0xf]`, then branches on them in that
  order. `ch_match::isFinished` (0x80c6c64) and a byte at
  `[ch + ch[+8] + 0x1b]` choose; at 0x8086ee7 `isReplay_point` false sets
  `[ebp-0xe]`. Manager global: `[0x85061A4]`, with +0x1c match, +0x20 ch_match,
  +0x90 replay, +0x94 vs, +0xf4 mtrLoopManager, +0xfc usrAdvLoop.
- `usrAcWinloseLoop::init` (the per-point win/lose animation; it runs after
  every point, not only at match end).
So the match-end path appears to need the real answer on the match's last point.

Planned fix (not written yet): with Replays off, still answer 0 on ordinary
points, but run the original `isReplay_point` when the point ends the match.
Candidates for "the match is over", read from the match object
`[[0x85061A4] + 0x1c]`:
- `match::isGame` (0x810c4b4) = `byte [match+0x1d] & 4` (a game ended).
- `match::isMatch` (0x810c4cc) = `byte [match+0xd6]` – **meaning unconfirmed**;
  it may be "this is a match (not a challenge)" rather than "match over".
- `match+0x18` event bits are tested in the pass loop (0x4, 0x8).
Check which one turns on only on the match-winning point (log them per point
in a `prize` run), then gate on it. Verify with `prize` + Replays off: the match
must end after game 2, and ordinary points must still skip replays.

Earlier dead end: the `forty` scene is endless with Replays on as well, because
forcing 3-0 at each game start keeps resetting the score when the AI wins. Use
`prize` or `round0` + `LINDBERGH_VT3_WIN=1` instead.

### Serve strength meter wrong in immersive mode (bug)

User: "sometimes works ok but then glitches last second".
- Drawn by `hud::drawServePower` (0x810f28e), called from `hud::draw`. It
  places itself with `hud::getScreenPosFrom3DPos` (projects the player's 3D
  position through the **game's** camera, `_sSceneManager::getProject`), then
  plays an AB animation (`TScene::AbHandle::setMatrix/setFrame/play`) as a 2D
  HUD sprite.
- Lead: in immersive mode the view is dollied/stepped back and follows the
  head, so a screen position from the game's camera does not match where the
  player is drawn. The "last second" glitch may be the end of the animation
  (branch changes, `finishBranch` x4) or the meter jumping as the camera moves.
- Not yet captured: the `forty` captures (`LINDBERGH_XR_SHOT=1950,15`) were too
  small to see it, and 1P may not serve there. Next: capture at full size
  (`LINDBERGH_XR_SHOT_FULL=1`) during a 1P serve, several frames apart through
  the toss, and compare with plain mode.

## Other open items

From `docs/VT3_QUEST_BACKLOG.md`: two-mode headset menu (Classic / Immersive,
advanced settings each; Immersive defaults replays and arcade overlays off),
blocky cloud patch near the top of the sky, one black frame at a camera change,
camera and stand-height tuning, HUD scoreboards in the scene, culling widened to
the headset's view, macOS start-up screen.

Note for the menu redesign: defaulting Immersive to Replays off depends on the
match-end fix above.
