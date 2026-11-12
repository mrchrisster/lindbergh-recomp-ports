# Virtua Tennis 3 on Quest 3 – improvements and bugs

The working list for the Quest port's world ("immersive") mode and the
headset menu. Newest requests at the top of each section. Details of how each
fix works live in `VT3_PORTING_GUIDE.md` section 8.

## In progress

- [ ] **Switch Classic / Immersive without a restart** - groundwork in
      (2026-11-11), not switched on: the mode now has a target / game /
      drawing latch and a per-frame switch point (`world_mode_frame`), a
      kill switch `LINDBERGH_VT3_LIVE_SWITCH=0` and a test switch
      `LINDBERGH_VT3_MODE_AT=<frame>:<0|1>,...`; the panel can show Mode
      without "Restart now". Nothing changes for the player yet - the Mode
      row still applies on the next start. Left: the game and drawing side
      (hooks gated per frame, shader world bit, flat frames in Classic),
      which needs headset runs.

## To do

### Bugs
- [ ] **T14: a short glitch at the start of every point (VR)** (owner,
      2026-11-12, build 9dd8505, his vr.cfg: replays off, cutaways off):
      "the little glitch at every start of a point - not sure if it's still
      a top-down shot, it disappears too quickly". T8 left the StartLoop
      cross-fade out and holds the frame after a match's EntranceLoop only.
      Being traced (HANDOFF 3.1): every-frame shots of both eyes round two
      point starts in the T13 smoke run, `LINDBERGH_VT3_CAMMODE_LOG=3`
      (every world camera note) on macOS.
Reported by the owner after a full match worn on 2026-11-11 (build before
`1b1988b`); the owner also said "we are getting close to a first release"
and asked that all progress and research be written to the docs.
- [ ] **Music plays skipping / not clean** (2026-11-11, Quest) - skipping
      **fixed, owner to confirm by ear** (see Done). Left open for the
      "not clean" half: in loud moments the effects drive the mix up to 4x
      full scale into the limiter (measured, not changed - tell us if loud
      rallies sound distorted).
- [ ] **Audience looks low resolution** (2026-11-11, Immersive) - the
      stretched / floating half is fixed (see Done). The crowd textures are
      sampled one mip level blurrier on the Quest than Sega set (the
      headset's graphics layer dropped the game's sharpening, LOD bias -1);
      a fix is written but not yet tried on the headset.
- [ ] **Shadows still look low resolution** (2026-11-11, Immersive, Shadow
      quality High 2048). Found: it is the players' ground shadow, a
      screen-sized mask copied from one eye at 1360x768 (it looks the same
      with the shadow map at 1024 or 4096). A per-eye, full-resolution mask
      with soft edges is written but not yet tried on the headset.
- [ ] gl4es multiview patch (`quest/gl4es.patch`, `multiview.c`): `mv_copy[64]`
      keeps a `gltexture_t*` after `glDeleteTextures` frees it - a dangling
      read in `mv_framebuffer_left`, the texture's two-layer array leaked, the
      slot never freed (found 2026-11-11 reading the code; no symptom tied to
      it yet).
- [ ] GPU page faults on the Quest (`kgsl-3d0: GPU PAGE FAULT ... FAULTING
      BLOCK: UCHE: BR_SP` in logcat, ~900 a second, rate-limited) in every VT3
      run, from the boot screens (frame ~1070, right after `fragment program
      21/22 ... units 0x8000 compare depth`) on, Classic and Immersive: a shader
      reading outside its memory. Nothing visibly wrong; not looked into.
- [ ] Confirm worn (fixed in `1b1988b`, not yet tried by the owner):
      "button A is slice and button B is not mapped" -> now trigger top
      spin, A / X slice, B / Y lob; "quick 1 s camera changes after every
      point" -> now one steady camera with Point cutaways off.

### Features
- [ ] **Switch Classic / Immersive without a restart** (Phase B of the
      menu): world-mode hooks installed always and gated per frame, the
      shader link key's world bit, flat frames forced in Classic. Today the
      Mode row applies on the next start ("Restart now"). Groundwork: see
      In progress.
- [ ] Sky (owner to judge worn): Immersive's Sky row - Stadium (default) is
      now Sega's own sky all round and overhead (each court's full sky dome,
      which the headset used to cut down to a cone in front - the "two
      different skies" seam), Painted (ours only), Off (none). Pictures:
      `~/Desktop/Claude/vt3-sky/`.
- [ ] Stadium checks still owed on the later venues (seen in unattended
      shots of rounds 0-2, 2026-11-11): floating cards, z-fighting and roofs
      at the far plane not seen in the shots but not looked for closely;
      rounds 3+ not looked at. (Missing near-end crowd: parked, below.)
- [ ] HUD scoreboards float in the scene at court level instead of a HUD
      panel (older note).

## Later / parked
- [ ] **Spectators missing near the viewer in Immersive** (parked by the
      owner 2026-11-11: "probably a game setting and can be ignored for
      now"). The stands at the viewer's own end and the near side stands
      have seats but no crowd cards, the far end is full (rounds 0-2:
      Ger3M, Aus1F, Fra1F). Picture:
      `~/Desktop/Claude/vt3-sky/round0_Ger3M-Duesseldorf_stadium_10_directions.png`
      (panels 90,0 / 120,0 / 180,0 / -90,0). Research lead
      (`ai_docs/research/crowd-and-upper-stands.md` 1.3):
      `CAudience2DManager::draw` (0x08090096) draws crowd trees
      `0 .. min(level, count)-1` plus the standing tree, the level set by
      `make(bool, level)` per round (attendance grows through the
      tournament); no camera-end rule was found in it, so the empty sections
      may simply have no cards at that crowd level. Not investigated further.

## Done (2026-11-12)
- [x] **Settings panel: Classic / VR buttons on top** (owner, T12). Two big
      buttons above everything, the chosen one highlighted, a line under them
      saying which runs and whether a restart is needed (Restart now right
      below). "Immersive" is called "VR" on the panel (vr.cfg and env names
      unchanged). Picture: `~/Desktop/Claude/vt3-view/panel_T12.png`.
- [x] **VR viewpoint fixed: 20 m closer, 5 m back** (owner, T12) - the
      Camera closer and Step back rows are gone; old vr.cfg values ignored.
      **Camera height** is Low / Medium / High (camera's own, +1 m, +2 m);
      when your player is at the far end (after a change of ends) it is
      always High.
- [x] **Replays and point cutaways in the world** (T10): Off / Flat screen /
      In the world / Camera view in VR's advanced settings (default Off).
      Owner to judge worn. Strips: `~/Desktop/Claude/vt3-replay/`.

## Done (2026-11-11)
- [x] **Sky in Immersive: one sky.** The court's own sky (Sega's 360-degree
      dome) now fills the whole sky in the headset; before, only a cone in
      front showed, with our painted sky round it in a different colour.
      The Sky setting acts on it: Stadium / Painted / Off, no stray wedge.

- [x] **Audience and ad boards blurrier than on the PC** (Quest, both modes).
      The game asks its crowd, boards and other textures for one mip level
      sharper (texture LOD bias -1); GLES has no such setting, so the Quest
      showed them a level blurrier. The bias is now applied in the shaders
      (Virtua Tennis 3 only; `LINDBERGH_LOD_BIAS=0` off). Unattended: crowd
      and boards visibly sharper, board text steady frame to frame. Owner to
      judge worn.

- [x] **Immersive froze or crashed at the start of a match** (the owner hit
      it worn; unattended 2 of 2, later 1 of 3). The game updates its camera on
      one of its own worker threads, and Immersive's camera feed queued its
      camera for the GL thread from there, at the same moment as the game
      thread queued its draws: the queue got scrambled. Jobs from other threads
      are now handed to the game thread. 5 of 5 match starts clean on the
      Quest, full matches in both modes.

- [x] **Upper bleachers missing, audience floating in mid air, stands
      stretched** (owner's report, 2026-11-11, Immersive). The upper stands
      exist on every court: Sega built 2nd and 3rd tiers, roofs, light
      towers, buildings around the stadium and a sky, and the game hides
      them while the TV camera is on the court because that camera never
      shows them - but the spectators on those tiers were still drawn, so
      they floated. Immersive now draws the whole stadium, including the
      stand behind you. Our stand-height stretch (and its "Stand height"
      menu row) and the crowd cut are gone: everything is at Sega's own size.
      Your saved settings need no change. Checked on the first court
      unattended; other courts, the frame rate cost and how it looks worn
      still to check.

- [x] **Music skipping** (owner's report, 2026-11-11): the music lost about
      a third of a second about three times a second, on every platform. At
      the end of each lap of the game's 0.34 s music ring, our sound code
      reported "end of ring" instead of "start of ring". The game then
      rewrote the whole ring over music still waiting to play. Fixed:
      macOS and Quest now play exactly what the decoder writes (1.01x / 1.02x,
      was 2.38x / 2.19x). Effects at 22/44 kHz are now interpolated (less
      grainy). No device underruns or stream starvation were found
      (unattended runs; not yet heard worn at 120 Hz).
      Details: `ai_docs/research/audio-music-skipping.md`.

- [x] "Some replays still play with Replays off" - not replays. The game
      has a single way into a replay (the point's end asks
      `replay::isReplay_point`, which the Replays switch answers), and with
      Replays off no replay played in long runs (macOS and Quest, two whole
      matches each, attract demo). What looked like replays were the point
      close-ups: the winner's close-up after each point and the server's
      close-up on big points - those are the **Point cutaways** row (both
      off by default in Immersive). Also: a replay already playing when
      Replays is switched off now ends at once (as a shot button skips
      it), and the desktop Controls menu / start-up screen labels are
      up to date (button 2 slice, button 3 no shot; "mode, replays,
      cutaways").

- [x] Quest controls match the cabinet's two shot buttons: trigger = top
      spin, A / X = slice, B / Y = lob (on the cabinet: both buttons
      together); before, A gave a slice and B did nothing. Start-up screen's
      controller map redrawn to match. Holding Y no longer opens the
      settings panel in VT3 (Y is the lob) - use the left Menu button.

- [x] No camera changes between points in Immersive (with Point cutaways
      off, the default): no winner close-up, no big-point serve close-up -
      a whole game plays from the court camera; only game set and match and
      the result slate cut. With cutaways (or replays) on, each cut goes
      straight from the court to the flat close-up and back - no distorted
      frames, no small floating picture of the old view.

- [x] Blocky cloud patch near the top of the sky gone (smooth clouds).
- [x] Black frames at camera changes in Immersive (two at each cut: point
      close-up, change of ends, serve camera, game set and match, match
      start) gone.
- [x] Immersive frame rate: the dips were the sky's shader, not the scene
      culling (which the game hardly uses). The sky is now cheap (same look);
      in unattended tests a match holds 60 fps where it dropped to ~53.
      Culling is widened to the headset's view anyway. Not yet checked worn
      at 72/90 Hz.
- [x] Result slate after a match (RESULT, prize money, TOTAL MONEY) shown for
      its full ~10 s in Immersive mode too (it ended after a few frames: the
      intro fly-by skip also cut the slate's camera, which times the slate).
      A shot button still skips it.
- [x] Headset menu around two modes. Main page: **Mode** Classic (2D screen)
      / Immersive (3D world) - applies on the next start, with a **Restart
      now** row until then - and **Advanced settings** for the chosen mode.
      Classic: Replays, Point cutaways, Arcade overlays (all on), Shadow
      quality (Standard 1024). Immersive: Stand height (x1.5), Camera closer
      (20 m), Step back (6 m), Replays, Point cutaways, Arcade overlays (all
      off), Sky (on), Shadow quality (High 2048). Both: Frame rate counter,
      Restore defaults (pull twice). Everything but the mode and shadow
      quality changes at once. A setting fixed by env.txt shows "(env.txt)".
      Test runs no longer save their own replays/overlays choice into vr.cfg.

- [x] Point cutaways switch: the ~2 s close-up of the winner after every
      point (taken for a replay) can be skipped - it then lasts ~0.3 s (the
      game's own minimum before a skip), the POINT plate flashes and the score
      box shows the new score; change of ends and the match's end unchanged.
      `LINDBERGH_VT3_CUTAWAYS=0|1` for a run.

## Done (2026-11-11)

- [x] Court seen from above for a split second at each match's start (both
      modes), Classic's wrong wide 3D view and black frames at the match's
      start, and Immersive's "image within an image" before every serve -
      fixed (owner confirmed worn).

## Done (2026-11-10)

- [x] Serve strength meter in immersive mode: the bar no longer jumps to full
      height below its frame in the last second before full (85-100%) and on
      the fall back, and the meter and the 1P marker sit beside the player
      (they were drawn below the feet, further off at the far end), both
      eyes. `LINDBERGH_VT3_PIXCAM=0` / `LINDBERGH_VT3_HUD_ANCHOR=0` turn the
      two parts off.

- [x] Match ends with Replays off: after the last point the game goes
      straight to GAME SET AND MATCH and the result slate, without the closing
      replay (before, it kept playing new games). Plain and immersive mode.
- [x] Start-up screen: instead of ~30 s of black, a panel 2 m ahead with the
      title "Virtua Tennis 3 (VR edition)" (original artwork), the controller
      map and a countdown with a bar. It shows from the headset session's start
      (~1 s after launch) until the game's first bright screen; the countdown
      is the last start's time (`startup_seconds` beside the game).
      `LINDBERGH_SPLASH=0` turns it off. The macOS build still starts on black.
- [x] Start of a match goes straight to the normal camera: the fly-by intro is
      skipped (`LINDBERGH_VT3_SKIP_UVA=0` keeps it), and the "overview" and
      "top-down" views were world mode's own fault - for the first ~3 s the game
      draws through the broadcast camera without setting it the way world mode
      reads it, so world mode guessed. It is now built from the game's camera
      routine until the game sets it (`LINDBERGH_VT3_FEEDCAM=0` turns it off).
- [x] Floating crowd behind the far baseline hidden (`LINDBERGH_VT3_CROWD_CUT`) -
      replaced 2026-11-11 by drawing the real upper stands (the cut turned
      out to remove stadium parts, not spectators).
- [x] HUD (score, speed, 1P marker) and the startup logo screen no longer
      vanish when the head moves.
- [x] Sky: a procedural blue sky with light clouds, fixed to the world.
- [x] Shadow map at 2048x2048 in world mode.
- [x] Ad boards (CITIZEN, Düsseldorf Open, IBM) no longer flicker.
- [x] Stands raised (stretched up above ~1 m) - removed 2026-11-11: they
      looked low because the upper tiers were not drawn.
- [x] Blotches on shirts, crowd and banners gone.
- [x] Player shadows attached to the feet in world mode (both eyes).
- [x] Replays switch in the headset menu (most replays).
- [x] World mode: camera moved closer and stepped back out of the court.
