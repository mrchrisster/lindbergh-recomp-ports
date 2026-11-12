# Work in progress - NOT VERIFIED / KNOWN BROKEN

Safety copies of uncommitted VT3 code (updated 2026-11-11 evening, on top of
submodule `8004564`, outer `c07bad8`). T5 (LOD bias) is committed and no
longer here; the gl4es side (`quest/gl4es.patch`, incl.
`gl4es_multiview_copy_layers`) is committed too.

- `t3-t4-lindberghrecomp.diff` - `git -C lindberghrecomp diff` against `8004564`:
  - **T4 per-eye ground shadow mask** (`arbprog.c` `vt3_mask_unit`, `lg_mask`;
    `stereo.c` `mask_copy`, `stereo_mask_twin`; `LINDBERGH_VT3_MASK=0` old
    path). **Fails on the Quest: the players' ground shadows disappear**
    (HANDOFF 3.1, `/tmp/vt3q/W/t4_near.png`). Needs debugging before use.
  - **T3 sky**: Painted / Off leave out fp 180 (`dome_left_out`) - but fp 180
    is **not** the visible dome (it is a sun-glow term; the front sky stays
    in Painted / Off). `dome_note` / `u_dome` (fill lit with fp 180's
    constants, `LINDBERGH_VT3_SKY_MATCH`, `_NSIGN`, `_CLOUDS`) gives a black
    fill - wrong, keep `LINDBERGH_VT3_SKY_MATCH=0` or remove it.
  - Test switches worth keeping: `LINDBERGH_XR_FIXED_HEAD=1` (host_xr.c: the
    head level at the anchor, facing ahead - comparable unattended shots and
    GPU ms), `LINDBERGH_VT3_VIEW_TURN=<yaw>,<pitch>@<frame>/...` (list over a
    run), `LINDBERGH_VT3_SKY_AT=<0|1|2>@<frame>/...`, `LINDBERGH_VT3_SKY_DEBUG=1`
    (fill drawn magenta).
  - TEMP code to delete before any commit: the two `LINDBERGH_DOMELOG_TMP`
    blocks in `stereo.c` (vert_dump and the desktop-only texture dump).

Restore: `git -C lindberghrecomp apply ../ai_docs/wip/t3-t4-lindberghrecomp.diff`.
