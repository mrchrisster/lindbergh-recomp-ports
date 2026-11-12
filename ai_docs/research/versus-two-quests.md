# Virtua Tennis 3: versus with two Quest headsets

Read-only study, 2026-11-12. Nothing built, run or edited; no adb. Addresses
are from `vt3_Lindbergh_HD` (`~/code/quest_games/vt3/disk0/vt3_Lindbergh/`,
`objdump -d -C`; same layout as the original, guide 2.2). Runtime references
are to `lindberghrecomp/src/runtime/` at the time of writing. **[V]** =
verified in the disassembly or the code, **[I]** = inferred, **[M]** = only a
prototype run can tell.

## Short answer (for the owner)

**The arcade game has no cabinet link.** VT3's versus is two people on one
cabinet, side by side, one screen: player 2 puts in a coin and presses
Start, the game breaks into the match ("Here comes a new challenger") and
the two play each other, or team up for doubles against the computer.
The game has no network code at all (no socket calls; the only network
functions are Sega's standard board library, never called). So there is no
"native link protocol" to switch on - we have to build the connection
ourselves.

**What works best: both headsets run the game, and they swap only button
presses.** Each Quest runs its own copy of VT3. Every frame each sends the
other its controller's lever-and-button state (a few bytes). Both copies
feed both players' buttons into the game at the same frame, so both copies
play out the same match. Each headset then draws the court from its own
player's end. This is how fighting games and old LAN games do it
("lockstep"). It needs very little Wi-Fi, but it has one hard condition:
the two copies must compute exactly the same thing from the same buttons.
VT3 nearly does - it is a 60-frames-a-second arcade game with a fixed step -
but a few things must be fixed first: its random numbers are seeded from
the clock, the menus use the same random generator as the match, and the
Mac and the Quest compute some maths (sine, arctangent) slightly
differently. All fixable, and all testable on the Mac without a headset.

**What it will feel like:** about 2-3 frames (35-50 ms) of extra button
delay on a good home Wi-Fi, the same for both players - less than many TVs
add. If the Wi-Fi hiccups, the game freezes for a moment instead of
glitching. The other approaches (one headset running the game and streaming
video to the other; a PC host) cost much more and look or feel worse.

**Plan:** (1) make two-player versus work on one Mac (two pads), (2) prove
two copies stay identical, from a recording, on the Mac, (3) two copies on
one Mac talking over the network with fake delay and packet loss, (4) Mac
plus one Quest over the home Wi-Fi with a scripted "bot" opponent, so one
person can test alone, (5) the view from the far end in the headset, (6)
two Quests. Each step is useful on its own. Internet play could follow
later, with more delay.

## 1. How versus works in the arcade game

### 1a. Two players on one cabinet [V unless marked]

- **One cabinet, two sides, one screen.** The JVS I/O board reports two
  players' switches (`hle_sega.c` `jvs_switch_byte(buttons, player, byte)`,
  command 0x20 loops over `players`; coins command 0x21, two slots). 2P's
  lever and buttons are the same bits shifted (`cabinet_buttons.h`
  `CAB_P2_*`, `CAB_P2_JOY_SHIFT` 8, `CAB_P2_START`). On the desktop the
  second SDL pad is 2P (guide 3.4). **In the headset only 1P exists today:**
  `xr_controls.c` `lever_buttons()` maps both hands to `CAB_P1_*` when the
  profile sets `joystick` (the `dual` / `CAB_P2_START` path there is the gun
  games').
- **The `vs` object** (constructor 0x08180E4E; methods 0x0817FF06-0x081806xx):
  `+0x00` game master side (0/1, -1 none), `+0x04` challenger side, `+0x08`
  byte "start requested", `+0x09` byte "versus requested", `+0x0c` pointer
  to a per-side status array of **two** entries: 0 idle, 1 start requested,
  2 playing, 5 game over (`isPlaying`, `isGameplaying`, `isGameover`,
  `reqStart_game`). Two sides only: no 3P/4P humans.
- **Joining.** `credit::exec` calls `vs::reqStart_game(side)` (0x081802B0)
  when a side presses Start with credit. If no side is playing, that side
  becomes game master (`+0`, `+8 = 1`). If the other side is already
  playing, it becomes the challenger: `+4 = side`, **`+9 = 1`**, status 1.
  `vs::isReq_vs_game()` (0x0818043C) just returns `+9`. It is checked by
  `vs::exec`, `credit::exec`, `game::exec` and **every arcade loop's
  `exec()`** (Entrance, Start, Game, Pass, Judge, Winlose, Replay,
  Changeend, Gamesetmatch, Stats, Load, the menu/character/gear/name-entry
  loops, the challenge loops) - 46 call sites: the running match is
  interrupted. `sound::setBgm_new_challenger` is called from
  `usrAcLoop::exec` and `usrAcLoadLoop::draw` (the "new challenger" jingle).
- **Starting the versus.** `vs::setVs_forced()` (0x081804C8; called from
  `usrAcselectLoop::exec`, `usrMenuCharLoop::exec`, `usrMenuLoop::init`, the
  gear / colour / play-style / medal loops and `usrNameEntryLoop::exec`, i.e.
  wherever the challenger came in) sets `tennis::setGameType(1)`, moves the
  master's player data (`playerManager::move_player_data`), makes the
  challenger's player human (`playerManager::set_player(getPlno(side))`)
  and inits the AI learner. `vs::setStart_vs()` sets the challenger's
  status to 2 and charges the credit (`credit::execGame`). `vs::isBoth_seq()`
  (both statuses 2) makes the name entry, menus and gear screens run for
  both players.
- **Both at once: versus or doubles.** `usrVsselectLoop` (exec 0x08136400,
  `selectVersusOrDoubles` 0x0813694E, `setSelectStatusVersus` /
  `setSelectStatusDoubles`) is the "VS / Doubles" choice; `usrVspositionLoop`
  sets the game type too. Game type is `[g_pTennis+0x24]`: 0 vs computer, 1
  versus, 2 doubles, 3 a fourth (unknown) kind. `vs::getPlno(side)`:
  side 0 -> player 0; side 1 -> player 1 for types 1 and 3, **player 2 for
  type 2**. With the team rule `team = (plno + 1) mod 2` (`pov-camera.md`)
  type 2 puts both humans on the same team: **doubles is co-op, 1P + 2P
  against two computer players** [I: from getPlno and the team rule, not
  run]. Four players exist only in doubles (`playerManager::set_player` writes
  4 players when `+0x24 == 2`), and only two of them are human.
- **Records kept for versus:** `backup::addVs_win_player`, `getVs_play_time`,
  `player::addVs_lose`, `card::decrement_rest_versus` (a versus game costs a
  card play) - bookkeeping, not gameplay.
- **Camera on one cabinet.** One broadcast camera for both players. Its end
  follows the games' parity and `match::isCam_first_reverse()` (0x081090B4;
  `camera::initGameRoutine` 0x080A5692 mirrors x/z sign bytes `+0x4f` /
  `+0x5b`, flag `camera+0x1c8` bit 0) - so on one screen, after a change of
  ends, 1P plays from the far side (guide 8, T12 "The far end"). **There is
  no per-player view**: one screen, one camera.

### 1b. Cabinet-to-cabinet link: not in this game [V]

- **No socket API is imported.** The import list
  (`games/vt3/generated/recomp_imports.h`) has no `socket`, `bind`,
  `sendto`, `recvfrom`, `connect`, `listen`, `accept`, `setsockopt`. The
  disassembly has no `int 0x80` (no raw `socketcall`). The only network-ish
  imports are `inet_addr`, `inet_aton`, `ioctl`, `select`, `popen`,
  `system`, `sysctl`.
- **Where those are used:** `select` only in `CSerialRWUnix::acSciSend`
  (the IC card reader's serial port); `ioctl` in `JoystickOpen` and
  `amEepromInit`; `inet_aton` / `popen` / `system` in
  `amOsinfoGetNetworkPropertyEth0` / `amOsinfoGetDhcpStatusEth0` and
  `inet_addr` in `amSysData_InitNetwork0` - Sega's generic Lindbergh
  library (amLib), statically linked. **Nothing calls
  `amOsinfoGetNetworkPropertyEth0`, `amOsinfoGetDhcpStatusEth0` or
  `amSysData_InitNetwork0`.** `arcade::_sArcadeManager::initializeHardware`
  (0x08275B40) calls `amSysData_InitNetwork` / `_InitNetworkType`, which
  only fill a default backup record (`0x5555aaaa` magic, zeros) - the
  board's stored network settings, not a link.
- Strings: `/etc/dhcpc/dhcpcd-eth0.cache`, `255.255.255.0` (amLib's);
  `netUmpire` is the net-cord umpire model, `05_line_net` a court line.
- **The port's HLE** answers the board's network as absent:
  `hle_libc.c` "The network: the cabinet's link to its twin. Not present."
  (`inet_addr` -> 0xFFFFFFFF, `inet_aton` -> 0).
- So there is **no test-menu cabinet ID / link setting, no discovery and no
  sync protocol to reuse.** Architecture A below ("native link") does not
  exist for VT3; what remains of it is "build our own link", which is C.

## 2. Architectures for two Quests

Common facts used below:
- The game's logic runs on one thread per frame: `TScene::Framework::threadMain`
  (0x08198A08) calls `procUpdate` (-> `tennis::procMain`, which runs
  `padManager::exec` and the loops) and then `procDraw`, handing over to
  the main thread with `candy::Event`s; the main thread runs `_sSystem::execute`
  / `_sScene::execute` (the GL). Input from the JVS board is fetched by
  `_sInterface::execute` from `TScene::Framework::preSceneCallback` (main
  thread), `padManager::exec` reads it in the update [V for the calls; the
  exact hand-over order per frame I].
- The game steps by frames, not by time: `_sSystem::getFrameTime` is used
  only by camera physics (`TScene::CameraPhysics::calcDt/exec`), `uva::Animation`
  (fly-by cameras, menus' animations) and `tennis::procFix` (which only sets
  an LED from the FPS) [V]. Player, ball and AI code do not read the clock
  during play [I: no clock call found in them; `player::init` and
  `player_ai::player_ai` read it once for a seed, see C].
- The Quest's game thread costs ~13 ms a frame (gl_thread.c header), the
  game runs at 60 Hz on a 72/90/120 Hz display (`display_cadence.c`).

### A. Native cabinet link - does not exist

See 1b. A variant "make the HLE sockets real" has nothing to plug into. The
only reusable idea from A is "each headset runs its own game instance and
gets its own end and view", which is C.

### B. One game instance, two viewers

One Quest runs the match with both players (1P and 2P on one cabinet: the
guest's buttons arrive over the network and are fed into `CAB_P2_*`); the
second Quest only shows it.

- **B1, video stream of the guest's eyes.** The host would have to draw the
  world a second time from the guest's end (two more eye views: the host is
  already near the GPU's limit - sky fix brought Immersive to ~3.2 ms GPU but
  frame 60 fps only just, `LINDBERGH_GPU_TIME`), encode 2 x ~1.5k x 1.6k at
  60 fps with the Quest's hardware HEVC encoder (MediaCodec; Quest casting
  does this, at lower resolution), send ~30-60 Mbit/s, decode on the guest
  and reproject for head motion (rotation only; the image is ~50-80 ms old,
  position never matches). Costs: a second world pass in `stereo.c`,
  a MediaCodec pipeline in `host_xr.c` on both ends, heat and battery on the
  host. Feel for the guest: video-like image, compression artefacts on the
  crowd/net, ~2x the button delay of C (button to host, picture back), and
  head movement over an old picture (comfort risk). **Feasible but the
  worst result for the most work.** Only advantage: no determinism needed.
- **B2, a compact scene state redrawn locally.** In a recompiled game there
  is no "scene state" separate from the game's memory. The nearest thing is
  the GL command stream the port already queues (`gl_thread.c`: a 16 MB
  ring = "two busy frames", records point into guest memory - vertex data,
  textures, buffer maps). Shipping that per frame is megabytes per frame and
  every referenced buffer; re-creating the GL objects on the guest; answering
  synchronous calls. **Not feasible over Wi-Fi without deep work**; say no.
- **B3, a small state copy for a known set of objects.** Send per frame the
  ball, the four players' positions/poses (bone matrices: 31 x 48 bytes each),
  score and loop state, and have the guest run its own copy of the game with
  those overwritten. That is really C with "state correction" instead of
  determinism, and the guest's own copy still drives animation, sound, menus
  and flow - drift everywhere else. Not recommended as the base; possibly a
  repair tool for C (see desync recovery).

### C. Deterministic lockstep (recommended)

Both Quests run the same game. Each frame each sends its own side's 32-bit
cabinet word (lever + two shot buttons + Start + coin) for frame `N + D`;
both feed the agreed word pair into the JVS answer for frame N; both play
the same match. Each renders its own end.

**Is VT3 deterministic? Mostly; these must be fixed [V for the facts, fixes
I]:**
1. **Clock seeds.** `player::init(long)` seeds the player's own MT
   (`_sRandomObject::init_genrand`, 0x08260FE0) with `_sSystem::getTime() +
   plno` (0x0814FB4B); `player_ai::player_ai()` with `getTime()` (0x0806209B);
   `player::initFootPrintConstructor` reads the clock too. The AI tactics
   (`ai_tactics::desideAim`, `desideSwingWait`, `desideTossUpTime`, ...) and
   line umpires (`lineUmpireBack::execJudge*`) draw from such objects.
   Fix: wrap `init_genrand` (or `_sSystem::getTime` from those three return
   addresses) to use a seed the host sends at the handshake.
   `courtOfficial::init` seeds with 0 (deterministic already).
2. **One global generator shared by menus, effects and the match.**
   `_sRandom::getRandMT_U32/F32` (0x08260D6E / 0x08260D74; state at
   0x0850E7E0, index at 0x08463F08; `initRandMT` is never called, so it
   starts from the static default) is used 330 times: particles
   (`_abmParticleBillboard*::_CreateParticle`, `_abmLineEx::_create`),
   crowd (`CAudience2DManager::playKansei/execKansei`), voices
   (`sound::playVoice_audience`), the attract / menu loops every frame
   (`usrAdvTitleLoop::exec`, ...), **and** game logic: `match::init`,
   `match::decideFirstServer`, `match::setTournament`, `camera::initMatch`,
   `camera::initReplay*`, `camera::initWinlose*`, `player::calcNew_playstyle`,
   `player::playSe_racket`, the luck rolls (`player::calcEtc2_luckey`).
   Two copies that spent different numbers of frames in menus or loading
   enter the match with different states. Fixes: (a) at the versus match's
   start (e.g. `usrAcEntranceLoop::init`) the host sends its 2.5 KB MT state
   and the guest writes it in; (b) better, give the purely visual callers
   (particles, crowd, voices, racket sounds) their own per-copy generator
   by return address (the port already wraps by return address,
   `h_vt3_skip_winner` style), so view-dependent draws (a mirrored camera
   may spawn different effects) cannot move the match's stream.
   `match::getRandgen` (`RandGen(7)`, a fixed table) is deterministic.
3. **Flow settings that change the game's logic must be the same on both.**
   The port's Replays / Point cutaways switches skip or add loops
   (`h_vt3_set_mode`, `h_vt3_skip_winner`, `match::isHeatup` answered no),
   world mode skips fly-bys (`LINDBERGH_VT3_SKIP_UVA`: modes 4 and 8), the
   result slate waits on `camera::isUvaFinished`, and the camera init
   functions draw from the global MT. A copy with cutaways on would draw
   different numbers than one with them off. **The host's Replays, Point
   cutaways, Classic/VR flow rules and the arcade test-menu settings (match
   length, difficulty, free play - SRAM/EEPROM, `hle_sega.c` `g_sram` /
   `g_eeprom`) are sent at the handshake and locked during the match**;
   only view settings (height, sky, replay view Flat / World / Camera,
   shadow quality, overlays) stay per player.
4. **Card data.** Each player's IC-card record (612 bytes,
   `ic-card-save-emulation.md`, option C) changes the player (gear, play
   style). Each side sends its record at the handshake; both copies load
   1P's into side 0 and 2P's into side 1.
5. **Maths must give the same bits.** The lifted code emulates x87 with
   host `double`s and host libm: `fpatan` -> `atan2`, `fsqrt` -> `sqrt`
   (`games/vt3/generated/recomp_funcs_*.c`, e.g. 0x080655CC), and the
   imports `sin`, `cos`, `acos`, `pow`, `expf`, `logf`, `log10` go to host
   libm (`hle_libc.c` 1072-1121). Apple's libm and Android's Bionic can
   differ in the last bit; clang may fuse `a*b+c` into FMA differently per
   build. Quest-Quest (same APK) is safe; **Mac-Quest is not** until (a)
   lifted code and the runtime build with `-ffp-contract=off` on both and
   (b) the transcendental functions come from one bundled implementation
   (e.g. a small fdlibm/musl copy) on both. `sqrt` is exact (IEEE) and
   safe. Both machines here are arm64 (this Mac: `uname -m` = arm64).
6. **Input must be latched per game frame.** The JVS answer is built from
   `host_cabinet_input()` at the moment the game asks (`hle_sega.c` case
   0x20). In lockstep it must return "the agreed words for game frame N",
   with N counted at a fixed point (the port's `g_frame` at `host_swap`).
   If the game asks more than once a frame or on another thread, both
   copies must still see the same value per update [M: log JVS reads per
   frame, `LINDBERGH_JVS`].
7. **Loading and threads.** `TScene::Loader::exec` loads files on the
   framework thread between frames; ADX audio and the Cg/GL worker run on
   their own threads. Loading time changes how many frames a loop waits;
   that is fine for lockstep (both wait on the slower one each frame) as
   long as game logic does not branch on "is it loaded yet" differently -
   it does (the load loops poll). Both copies must therefore pass a
   **frame barrier**: a frame is simulated only when both have their inputs,
   and load-dependent decisions must be equal [M]. The worker-thread hazard
   in README (camera::gameRoutine on a worker; "anything queued for the GL
   thread must come from the game's main thread") is about GL, not logic,
   and does not by itself break lockstep [I].

**Delay, not rollback.** Rollback (GGPO) needs to save and restore the
whole game state many times a second; here that is the guest's memory plus
GL objects, audio voices and loader threads - not practical. So: a fixed
input delay D (2-3 frames at 60 Hz = 33-50 ms), and a stall (the frame
waits) when the other side's input is late.

- **Wi-Fi:** same LAN, both headsets on 5 GHz (or 6 GHz) to one router, or
  one Quest's hotspot. Traffic is tiny: one ~40-byte UDP packet each way
  per frame (frame number, the last ~8 frames' input words redundantly, an
  ack, a state hash) = ~20 kbit/s. Discovery: a UDP broadcast "VT3 versus
  here" on the LAN, or the host's IP typed in the panel (simplest first).
  The Quest APK needs `android.permission.INTERNET` (not in
  `quest/vt3/src/main/AndroidManifest.xml` today) and a Wi-Fi multicast
  lock for broadcast discovery.
- **Latency:** home Wi-Fi Quest -> router -> Quest RTT typically 3-10 ms
  with spikes to 50-150 ms (radio power save, channel scans, the other
  headset's traffic) [M]. With D = 3 a spike up to ~50 ms one way passes
  unnoticed; longer ones freeze the game briefly. VT3 is forgiving: shots
  are a button press timed to the ball, the player auto-runs toward the
  ball; 50 ms extra is similar to a slow TV. Both players get the same
  delay, so it is fair. Head tracking is always local: no added latency.
- **Desync detection:** every frame each copy hashes a small state block -
  ball position (`[g_pTennis+0x14]+0x1c`), each player's root `+0x18`,
  facing `+0x68`, the score/match struct, the current loop/camera mode,
  the global MT index (0x08463F08) and a few words of its state - and sends
  the hash for frame N-1. First mismatch: both log the frame and dump the
  block (and the last 120 frames of inputs) for debugging.
- **Desync recovery:** none in general (no state transfer). Policy: show
  "connection out of sync", finish the point on the host's view and return
  both to the attract mode, or end the match. A narrow repair (B3: overwrite
  the guest's ball/players from the host for one frame) may be tried later
  but will not fix diverged RNG or flow.
- **Pause / menu:** VT3 arcade has no pause. The port's panel blocks input
  (`f->blocked`) but the game runs: fine in lockstep (the blocked player's
  input is just "nothing"). A headset taken off / Android pause stops that
  copy's frames: the other stalls with a "waiting for the other player"
  plate; after ~30 s the session ends. Resume needs nothing (lockstep just
  continues).
- **Settings panels:** each player has their own panel; view settings
  local; match/flow settings shown as "set by host" on the guest.
- **Internet later:** the same protocol through a relay or with UDP hole
  punching; RTT 30-80 ms in-country means D = 4-6 frames (70-100 ms) -
  playable for casual tennis, noticeably laggy. A relay needs a server.
- **Cost:** medium. A UDP transport and lockstep core in the runtime
  (~600-1000 lines, host-independent C), hooks for seeds / MT / visual RNG
  (~10 wraps), a handshake (settings, cards, seeds, MT state), the panel's
  "Versus" page, the 2P-end view (section 3). Most can be developed and
  tested on the Mac.

### D. A Mac or PC as host, two headsets as viewers

- **D1 (PC streams both headsets).** The PC runs one copy with both players
  and renders four eye views, encodes two video streams (as Air Link /
  ALVR do, but for two headsets at once). Everything of B1 but on a strong
  GPU: much better image, still video latency (~40-70 ms for the picture,
  plus button round trip), needs a PC/Mac always on and two Air-Link-like
  clients we would have to write (or adapt ALVR, which supports one headset
  per server). The port's macOS build has no XR path for remote headsets.
  **High cost; the game no longer runs on the headsets** - against the
  point of the port.
- **D2 (PC as lockstep relay / referee).** Both headsets run C; the PC only
  relays packets and compares hashes. Useful for Internet play (a relay)
  and for debugging, not needed on a LAN.
- **D3 (Mac as one of the two players)** - the test stand, stage 4 below.

### Summary table

| | Work | Each player sees | Added button delay | Wi-Fi | Main risk |
|---|---|---|---|---|---|
| A native link | n/a | - | - | - | does not exist |
| B1 video | high | host: native; guest: video | guest ~2x C | 30-60 Mbit/s | encoder + 2nd world pass on a Quest at its limit; comfort |
| B2 scene | very high | - | - | MB/frame | not feasible |
| **C lockstep** | **medium** | **both native, own end** | **D frames (33-50 ms), both** | **~20 kbit/s** | **determinism (fixable, testable on Mac)** |
| D1 PC stream | high | video both | video | 2 x 30-60 Mbit/s | PC always on; two stream clients |

## 3. What the VR port needs whatever the architecture

- **A view from the 2P end.** Today the eyes follow the game camera
  (`stereo.c` `eye_projection`: `E * H * T * inv(P_game) * MVP`), and the
  game camera puts whoever's end it likes near. For each headset "my player
  is always at my end" is needed:
  - *Option V1 - flip the game camera itself* on each copy when its human
    is at the far end: set the camera's mirror (camera `+0x1c8` bit 0 / the
    sign bytes `+0x4f`, `+0x5b` that `camera::initGameRoutine` derives from
    the parity and `match::isCam_first_reverse`). The game then draws the
    court, the ground shadow mask (screen-space, `shadow-resolution.md`),
    LOD, crowd cards and the HUD anchors from the right end with no change
    to `stereo.c`. Risk: the camera might feed logic (it does draw from the
    global MT in its init functions - but the mirror does not change the
    number of draws [I]); any view-dependent RNG use must be moved off the
    match's stream (C fix 2b). The port already knows when the human is at
    the far end (`hle_sega.c` `vt3_far_end_note`, latched outside the
    rally, used today only to force Camera height High).
  - *Option V2 - turn the world 180 degrees in the reprojection* (the
    `C = V_pov * inv(V_g)` matrix of `pov-camera.md` / replays option A):
    no game change, but the game's screen-space effects (ground shadow
    mask, depth of field, the culling - unused in practice) are for the
    other end; the shadow mask would be wrong. V1 first, V2 as fallback.
  - The far-end height rule (T12: High when your player is far) becomes
    unnecessary in versus: each player is always near. Keep it for the
    single-player game.
  - Change of ends: with V1 the camera flips at the change of ends behind
    the game's own cut (ChangeendLoop; with cutaways off Pass -> Changeend ->
    Start, `h_vt3_set_mode`); add a short fade (pov-camera.md "Change of
    ends: turn the world 180 degrees behind a fade").
  - This is useful on its own: a single-player option "your player always
    near" (the owner chose High for the far end today).
- **HUD for the other side.** The HUD is the game's 2D layer; the score
  plate and names are the same for both players (it is one shared screen in
  the arcade) [I]. The serve meter is drawn at the server's position via
  `hud::getScreenPosFrom3DPos` (0x08110F2E) and the 1P/2P markers by
  `hud::setPlayerIcon` (0x08110C40); with V1 they follow the flipped camera
  and `stereo_vt3_hud_anchor` re-anchors per eye as now. Check the 2P
  meter at the near end (it is only ever seen at the far end today) [M].
  In-scene scoreboards (HANDOFF 5) are placed by "viewer's end at +z,
  mirror by camera z sign" - already end-agnostic.
- **Replays and cutaways per player.** Replay cameras are the game's
  (`camera::initReplay*`, global MT); both copies play the same replay.
  Camera view / In the world anchors on the viewer's last court view -
  works per copy. Whether replays are on is a match setting (C fix 3).
- **Controls for 2P.** Each headset sends its own Quest controller as
  *its side's* bits: host = side 0 (`CAB_P1_*`), guest = side 1
  (`CAB_P2_*`); `xr_controls.c` gets a "my side" parameter so
  `lever_buttons()` can shift into P2. Start and coin for the joiner:
  the guest's trigger at the attract/continue screens (auto-coin as the gun
  games' `auto_coins` do). Free play in the test menu avoids coins entirely.
  **Lever direction:** the lever is "up = toward the far end of the screen";
  with the camera flipped (V1) the game's mapping is already the screen's,
  so "up" stays "toward the net" for each player [I - check: VT3 might map
  the lever to court directions, then 2P's would be reversed when near; M].
- **Audio.** Each copy plays its own sound (identical events); nothing to
  send. Crowd and umpire are not positional in VT3 [I]. Voice chat: Meta's
  system party chat works across apps; nothing to build.
- **Settings panel:** a Versus page: Host / Join (IP or found on LAN),
  status (connected, RTT, delay frames, "in sync"), Leave.

## 4. Recommendation and staged plan

**Build C.** Each stage leaves something useful and has unattended tests.
All logging lines carry the game frame number, which is the common clock of
a lockstep session.

### Stage 1 - two-player versus on one machine (no network)

- Mac: second pad or keyboard keys as 2P already exist (guide 3.4); add
  scripted 2P keys to the repro script (`VT3_EXTRA_KEYS` for 2P: coin, 2P
  Start at frame X, lever/shots). Quest: a test switch
  `LINDBERGH_VT3_P2_HAND=left` (left controller = 2P, right = 1P) - two
  people on one headset is silly, but it tests the P2 mapping and the HUD.
- Test (unattended, macOS `round0`): 2P coin + Start at frame ~4000 ->
  flow log shows the match interrupted, `usrMenuCharLoop` / versus flow,
  game type 1 (`[g_pTennis+0x24]`), players with `+0x08` = 0 and 1, a
  versus match to game set and match. Also doubles via `usrVsselectLoop`
  (both Start at the attract screen) to confirm co-op doubles.
- Useful alone: local versus on the Mac with two pads.

### Stage 2 - determinism on the Mac, without a network

- Record mode: copy A logs each frame's two cabinet words to a file
  (`LINDBERGH_INPUT_RECORD=<file>`); copy B replays them
  (`LINDBERGH_INPUT_PLAY=<file>`), ignoring real input. Both log the per-frame
  state hash (`LINDBERGH_NET_HASHLOG=1`). Compare: first differing frame.
- Then add the fixes one by one: seeds (C1), MT state at match start / the
  visual-RNG split (C2), locked flow settings (C3), and see the first
  mismatch move later until there is none over several full matches.
- Same file replayed on the Quest (adb push) against the Mac's hash log =
  the cross-platform test of C5 (libm, FMA). Expect a mismatch until the
  bundled libm and `-ffp-contract=off` are in.
- Useful alone: input recordings are exact repro files for any bug
  ("replay this match").

### Stage 3 - two copies on one Mac over localhost

- The lockstep transport in the runtime (`net_lockstep.c`, host-neutral):
  UDP, a handshake (version/build hash, settings, seeds, cards, MT state),
  per-frame input packets with redundancy, input delay D, stall on missing
  input, hash exchange, a timeout.
- Two copies need **separate data folders** (each has its own
  `lindbergh_nvram.bin` SRAM/EEPROM and vr.cfg; same game files) and
  different ports. Flat mode, windowed or `LINDBERGH_HEADLESS`-style.
- **Impairment in the port's own socket layer** (no system tools, no
  password): `LINDBERGH_NET_DELAY_MS=<ms>`, `_JITTER_MS`, `_LOSS=<0..1>`,
  `_DUP`, `_REORDER`, `_BURST=<every s>,<ms>` (a stall like Wi-Fi power
  save). Implemented as a send queue with release times and a seeded
  random generator (its own, not the game's), applied on either end.
- Tests: full versus match with a bot on both sides (stage 4's bot), no
  desync, stall count and length vs the impairment; find the delay at which
  play freezes visibly (D = 2/3/4 vs 20/40/80 ms one way, 5% loss).

### Stage 4 - Mac + one Quest over the home Wi-Fi (the owner's stage)

The Mac stands in for the second headset.

- **Setup:** Quest = host, 1P (Immersive, worn or unattended); Mac = guest,
  2P, flat window or headless, **on Wi-Fi, not Ethernet** (so the path has
  two wireless legs like Quest-Quest; Ethernet as a second baseline). Host
  IP typed in env / panel first; broadcast discovery later. Both built
  with the C5 fixes (or the test only measures transport and expects a
  hash mismatch - say which in the log).
- **What to measure, and how:**
  - *Round-trip time and jitter:* every packet carries the sender's
    monotonic send time and echoes the last time it received from the peer
    plus how long it held it (NTP-style); RTT = now - echo - hold. Log
    per second: min / median / p95 / p99 / max RTT, jitter (mean deviation
    of one-way delay), packets lost, reordered, duplicated (from sequence
    numbers).
  - *Common clock:* the RTT exchange gives the clock offset (from the
    minimum-RTT samples); both logs print `[net] frame N t=<local ms>
    offset=<ms>`, so a script can merge the two logs on one time line. The
    game frame number is the primary key.
  - *Frame-of-input delay:* the configured D, plus measured "frames
    stalled waiting for input", and "input arrived k frames before needed"
    histogram (the slack) - tells how far D could drop.
  - *Desync:* the state hash per frame (C, "Desync detection"); the first
    mismatch dumps the state block and the last 120 input frames on both.
  - *Frame pacing:* each side's frame time histogram; the Quest is the slow
    side - its late frames stall the Mac too (lockstep runs at the slower
    one).
- **Artificial latency / jitter / loss** from the Mac side via the stage-3
  switches; sweep to find the game's tolerance (where stalls become
  visible, where play feels late - the owner judges worn).
- **A bot on the Mac** so one person can test alone:
  - *Scripted:* the stage-2 input file of a recorded human match, or a
    fixed pattern (serve on its own - the game auto-serves when no button
    is pressed, README "Scripting a serve").
  - *Reactive:* a small host-side bot that reads the ball position
    (`[g_pTennis+0x14]+0x1c`) and its player's root (`+0x18`) from guest
    memory each frame and sets lever bits toward the ball's x and a shot
    button when the ball is within ~1.5 m - inputs only, sent through the
    network like a human's. Its decisions must use only state both copies
    share (it runs on the Mac only, so it is just a source of input words).
  - The Mac also does the joining: auto-coin and 2P Start at the attract
    screen (`LINDBERGH_NET_AUTOJOIN=1`).
- **Unattended test:** Quest unworn (game paced at 60 by the clock; the
  session stops at state 6/1, README) + Mac bot: one versus match, logs
  pulled; pass = no desync, stalls < 1% of frames at no impairment, RTT
  stats logged. One worn smoke run by the owner (owner's rule: one short
  run per change).
- **What the Mac cannot stand in for:**
  - the Quest's CPU/GPU timing (game thread ~13 ms on the Quest, a fraction
    on the Mac): with two Quests both sides are slow, frames late on either
    stall both;
  - 72/90/120 Hz display pacing vs the game's 60 Hz (`display_cadence.c`)
    on *both* ends - two independent cadences beating against each other;
  - the headset's Wi-Fi radio: power save between packets, Guardian/system
    overlays, thermal throttling, two headsets contending for airtime in
    one room, the second headset's own Wi-Fi quality;
  - Android lifecycle on the guest (headset taken off pauses the app; the
    Mac never pauses) - test the stall/timeout path by hand once;
  - identical maths for free: Mac-Quest needs C5; Quest-Quest gets it from
    the same APK (so a Mac-Quest pass is stronger than needed, a Mac-Quest
    fail may be only C5).

### Stage 5 - the far-end view in the headset (no network needed)

- Option V1 (camera flip) behind a test switch, single-player first ("your
  player always near"): shots at both ends, serve meter / 1P marker at the
  near end for a far-end start, change-of-ends fade, ground shadow correct.
- Then 2P's view: with stage 1's local versus, the switch "view as side 1"
  shows 2P's end and 2P's serve meter near.
- Tests: `LINDBERGH_VT3_SERVESHOT` shots both ends, flow log through a
  change of ends, `LINDBERGH_BLACK_LOG` clean.

### Stage 6 - two Quests

- Same build on both; host / join from the panel; the stage-4 logs on both
  headsets. Owner and one other person, one short worn match; then the
  unattended pair (both unworn, bot input injected on the guest by switch).

### Stage 7 (later) - Internet

- Relay (a tiny UDP relay on any server or the Mac) or hole punching;
  D = 4-6; the panel shows the delay.

### Open questions only a prototype can answer

- Does a recorded input file replay to the same match on the same Mac
  (fixes C1-C3 enough)? On the Quest vs the Mac (C5)?
- Does the camera flip (V1) change any logic or the match's RNG stream?
- Does the lever map to screen or court directions for 2P at the near end?
- How often does the JVS get read per frame, and on which thread?
- Do the load loops branch on load completion (frame-count-dependent flow)?
- Real Quest-to-Quest Wi-Fi RTT spikes in a home; how big D must be.
- Is 33-50 ms of added delay acceptable to the owner worn?
- Is co-op doubles (type 2) worth offering, and what is game type 3?
