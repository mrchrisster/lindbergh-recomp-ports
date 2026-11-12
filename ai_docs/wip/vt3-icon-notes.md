# VT3 launcher icon (2026-11-12)

**Update 2026-11-12 ~14:40: the owner picked candidate 7 "VT3 orange" (court
blue, white-to-orange letters) "but kill the speckle highlight on the ball":
the specular spot is gone from the shared ball code (`glossy_ball`
gloss=0), so 5-7 stay consistent; 7 is the default and INSTALLED. Pictures:
`~/Desktop/Claude/vt3-icon/recommended.png` (= 7), `vt3_candidate_7_1024.png`,
`vt3_candidate_7_sheet.png` (192/96/48). Seen on the headset: OWED.**

**Update 2026-11-12 afternoon (build worker): the owner's brief - "simply VT3
with a tennis ball behind it, shaded in a similar way as the game" - is
candidate 5 "VT3 chrome", now the generator's default and INSTALLED (the
five drawable-*/ic_launcher.png). Original drawing: system font (Avenir
Next Condensed Heavy Italic), pearl "VT", deep-blue "3", black keyline,
white rim, bevel, gloss line, soft drop shadow, a glossy ball behind; no
Sega lettering traced or copied. Variants 6 "VT3 lime" and 7 "VT3 orange"
(court blue) selectable; 1-4 kept. Pictures: `~/Desktop/Claude/vt3-icon/`
`vt3_candidate_{5,6,7}_1024.png`, `vt3_contact_sheet.png` (192/96/48 px,
dark / light, square / rounded / circle), `recommended.png` (= 5).
Committed; seen on the headset: OWED (smoke run, HANDOFF 3.1).** The text
below is the earlier worker's (headset candidate), kept for the wiring facts.

Backlog item "Launcher icons are hotd4 placeholders". Done by an icon worker;
**not built, not committed, not checked on the headset yet**.

## How the icon is wired (unchanged)

- `quest/vt3/src/main/AndroidManifest.xml`: `android:icon="@drawable/ic_launcher"`.
  No `android:roundIcon`, no `android:banner`/`logo`, no `mipmap-*` folders, no
  adaptive-icon XML.
- The PNGs are **per-game** files in `quest/vt3/src/main/res/drawable-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png`
  (48/72/96/144/192 px). They were byte-for-byte copies of hotd4's, not shared
  or symlinked. `quest/build.sh` does nothing with resources; gradle takes
  them from `quest/vt3/src/main/res` as they are.
- So the fix is replacing those five files. No build.gradle, manifest or
  build.sh change is needed. hotd4/hotd4sp/lgj/ghostsquadevolution icons were
  not touched.

## Files written

- `quest/tools/vt3_icon.py` (new): the generator. Pillow + macOS system fonts
  (Avenir Next Condensed for candidate 1's "3"), deterministic, no network.
  Original artwork in the splash's palette (navy, ball yellow-green, court blue).
- `quest/vt3/src/main/res/drawable-*/ic_launcher.png` (5 files, replaced) =
  candidate 2.
- This note.
- Outside the repo, for the owner: `~/Desktop/Claude/vt3-icon/`
  (`candidate_1..4_1024.png`, `contact_sheet.png`, `recommended.png`).

## Candidates

1. ball 3 - tennis ball filling the tile, big navy italic "3" on it.
2. **headset (recommended, installed)** - a VR headset whose front plate is
   tennis-ball felt with the seam. Tennis + VR in one silhouette; reads at
   48 px; survives square / rounded / circle masks (only the strap stubs get
   cropped by a circle).
3. court - blue court in perspective, net, ball over the net (corners get
   cropped by a circle mask).
4. racket - racket and ball diagonal (generic sport icon, says nothing about VR).

## Switch to another candidate (one command, from the repo root)

    .venv/bin/python quest/tools/vt3_icon.py --candidate N --install

Other uses: `--out DIR` (master `icon_1024.png`, `drawable-*/ic_launcher.png`,
and adaptive layers `adaptive/ic_launcher_{foreground,background}.png`,
432 px = 108 dp at xxxhdpi, art body inside the 66 dp safe zone);
`--sheet PNG` (contact sheet of all four).

## Adaptive icon: deliberately not installed

minSdk is 29, so a `mipmap-anydpi-v26/ic_launcher.xml` would replace the
PNGs on every device, and it would also need the manifest moved to
`@mipmap/ic_launcher` (or the XML put in `drawable-anydpi-v26`). The Quest's
library does not mask icons the way phone launchers do, so the legacy
full-bleed PNGs are the simpler, safer choice. The generator still writes the
adaptive layers (`--out`) should that change later.

## For the build worker

1. Commit: `quest/tools/vt3_icon.py`,
   `quest/vt3/src/main/res/drawable-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png`,
   `ai_docs/wip/vt3-icon-notes.md`. (Don't add the untracked `.DS_Store` files.)
   Tick the backlog item in `docs/VT3_QUEST_BACKLOG.md` once seen on the headset.
2. Build and install as usual. Within the next smoke run anyway (no extra run
   needed): in the headset open Library, filter "Unknown Sources", check that
   "Virtua Tennis 3 VR" shows the yellow-green headset tile and not the
   hotd4 art. If the old icon persists, it is the launcher cache:
   uninstall/reinstall or reboot clears it.
3. Meta's library for sideloaded apps: there is no extra asset that can be
   shipped in the APK. Store/App Lab apps get their library tiles
   (landscape/square/portrait cover art) from the developer dashboard, not
   from the APK; sideloaded apps get the APK's `android:icon` (on some
   Horizon OS versions shown small on a generic tile, or a generic
   placeholder). `android:banner` is an Android TV attribute and is not used
   by the Quest. (From knowledge, not checked online in this session.)
