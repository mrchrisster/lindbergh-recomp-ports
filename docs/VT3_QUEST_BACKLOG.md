# Virtua Tennis 3 on Quest 3 – improvements and bugs

The working list for the Quest port's world ("immersive") mode and the
headset menu. Newest requests at the top of each section. Details of how each
fix works live in `VT3_PORTING_GUIDE.md` section 8.

## In progress

- [ ] Extra cameras at the start of a match (see Bugs).

## To do

### Bugs
- [ ] **Serve strength meter not showing correctly in immersive mode.**
- [ ] **Extra cameras at the start of a match.** Three cameras before the
      normal broadcast one; the first serve is on a different camera than the
      rest. Found so far (`LINDBERGH_VT3_CAMLOG=1`): the first is the fly-by
      intro, `camera::initUva` (also between games) - `LINDBERGH_VT3_SKIP_UVA=1`
      skips it cleanly (opt-in for now). Two remain: a high overhead view, then
      a high camera for the first serve, both inside `camera::gameRoutine`,
      before the game switches to the broadcast camera ~3 s in. Next: find what
      gameRoutine keys those on (first point of the match) and skip to the
      broadcast camera.
- [ ] **Some replays still play with Replays off.** The current switch
      answers `replay::isReplay_point`; some replays come through another path.
- [ ] **Blocky cloud patch near the top of the sky** (the cloud noise loses
      precision far out on its plane).
- [ ] One black frame at a camera change (older note).

### Features
- [ ] **Startup screen:** on black, a countdown with the title
      "Virtua Tennis 3 (VR edition)" (original artwork – not Sega's logo) and
      a picture of the Quest controllers showing the button mapping, while the
      game loads (~30 s of black today before the first screen).
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
