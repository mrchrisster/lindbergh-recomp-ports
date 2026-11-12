# Virtua Tennis 3: can replays (and point cutaways) be in the world in Immersive?

Status: research in progress (2026-11-11). Read-only study; nothing built or run.

## Short answer (for the owner)

(being written - see the sections below as they fill in)

## Facts found so far

- In Immersive, a "world" frame is drawn from the **game camera's own pose**:
  `stereo.c` `eye_projection` takes the game's projection, swaps its lens for
  the eye's frustum, multiplies the head pose, and adds the dolly (200 units
  forward along the game camera's view) and step back (60 units, level). So the
  viewer is carried by whatever camera the game is using. In camera mode 1
  (broadcast) that is a slowly moving camera behind the near baseline.
- Flat vs world per frame: `stereo.c` (frame start, ~line 3839) `g_flat =
  flat_all || menu_state() || g_zoom_frames >= 6`, and at a camera mode change
  `stereo_vt3_camera(mode, lens)` decides at once: lens > `zoom_limit()` (8.0)
  = flat. The lens is `p[0]` of the world camera set through
  `_sRender::setProjectCameraMatrix` (`h_vt3_proj_cam`, hle_sega.c).
