# Virtua Tennis 3 on Quest 3 – improvements and bugs

The working list for the Quest port's world ("immersive") mode and the
headset menu. Newest requests at the top of each section. Details of how each
fix works live in `VT3_PORTING_GUIDE.md` section 8.

## In progress

(nothing)

## To do

### Bugs
- [ ] **Some replays still play with Replays off.** The current switch
      answers `replay::isReplay_point`; some replays come through another path.

### Features
- [ ] **Switch Classic / Immersive without a restart** (Phase B of the
      menu): world-mode hooks installed always and gated per frame, the
      shader link key's world bit, flat frames forced in Classic. Today the
      Mode row applies on the next start ("Restart now").
- [ ] Pick the defaults for the camera's forward move (Camera closer, 20 m)
      and step back (6 m) and the stand height (x1.5) - all adjustable now
      in Immersive's advanced settings.
- [ ] HUD scoreboards float in the scene at court level instead of a HUD
      panel (older note).

## Done (2026-11-11)

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
- [x] Floating crowd behind the far baseline hidden: crowd cards with no seating
      under them (end away from the camera, beyond the side stands, above the
      far tier's top, ~5.5 m) are left out (`LINDBERGH_VT3_CROWD_CUT`).
- [x] HUD (score, speed, 1P marker) and the startup logo screen no longer
      vanish when the head moves.
- [x] Sky: a procedural blue sky with light clouds, fixed to the world.
- [x] Shadow map at 2048x2048 in world mode.
- [x] Ad boards (CITIZEN, Düsseldorf Open, IBM) no longer flicker.
- [x] Stands raised (stretched up above ~1 m).
- [x] Blotches on shirts, crowd and banners gone.
- [x] Player shadows attached to the feet in world mode (both eyes).
- [x] Replays switch in the headset menu (most replays).
- [x] World mode: camera moved closer and stepped back out of the court.
