# Virtua Tennis 3 on Quest 3 – improvements and bugs

The working list for the Quest port's world ("immersive") mode and the
headset menu. Newest requests at the top of each section. Details of how each
fix works live in `VT3_PORTING_GUIDE.md` section 8.

## In progress

(nothing)

## To do

### Bugs
- [ ] **Match never ends with Replays off** – after 2 games won it keeps
      playing new games. Caused by the Replays switch (answers "no replay" even
      on the match's last point); plain mode too. Notes: `ai_docs/README.md`.
- [ ] **Serve strength meter not showing correctly in immersive mode** – sometimes
      fine, then glitches in the last second. Lead in `ai_docs/README.md`.
- [ ] **Some replays still play with Replays off.** The current switch
      answers `replay::isReplay_point`; some replays come through another path.
- [ ] **Blocky cloud patch near the top of the sky** (the cloud noise loses
      precision far out on its plane).
- [ ] One black frame at a camera change (older note).

### Features
- [ ] **Redesign the headset menu around two modes:**
      - **Classic mode** – the game as it is, all overlays, on a 2D screen.
      - **Immersive mode** – the world around you; replays **off** and arcade
        overlays **off** by default.
      - Each with its own *Advanced settings* page to customise (stand height,
        camera distance, replays, sky, shadow quality, ...).
- [ ] Tune the camera: forward move (`LINDBERGH_VT3_DOLLY`, 200) and step back
      (`LINDBERGH_VT3_BACK`, 60) – candidates for the advanced settings.
- [ ] Tune the stand height (`LINDBERGH_VT3_STAND_Y`, default 1.5).
- [ ] HUD scoreboards float in the scene at court level instead of a HUD
      panel (older note).
- [ ] Scene culling is off in world mode (~40 fps in places); widen it to the
      headset's view instead.

## Done (2026-11-10)

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
