# Work in progress - UNVERIFIED (never run on the headset)

Safety copies of uncommitted VT3 code (2026-11-11), so it cannot be lost.
**Not verified work: do not treat as tested.** macOS build, unit tests, a macOS
Classic `prize` run and a Quest APK build pass with it; it has never run on
the Quest. The checks owed are in `ai_docs/HANDOFF.md` 3.1 (run list).

- `t3-t5-lindberghrecomp.diff` - `git -C lindberghrecomp diff` against
  submodule `fade8ac` (`src/runtime/stereo.c`, `src/runtime/arbprog.c`):
  - T3 sky modes: Painted / Off leave out the stadium dome's draw
    (`dome_left_out`, fragment program `LINDBERGH_VT3_DOME_FP`, default 180;
    `=0` keeps the dome as in `fade8ac`); Stadium draws the painted sky behind
    the dome (as `fade8ac` already did).
  - T4 per-eye ground shadow mask (`mask_copy`, `stereo_mask_twin`,
    `vt3_mask_unit`, `lg_mask`; `LINDBERGH_VT3_MASK=0` = the old 1360x768 path).
    Immersive only.
  - T5 GLES texture LOD bias (`lod_bias_on`, `u_lodb[16]`;
    `LINDBERGH_LOD_BIAS=0` = as before). Default on for Virtua Tennis 3 only
    (`world_mode_capable()`), both modes; other games unchanged unless
    `LINDBERGH_LOD_BIAS=1`.
- `t3-t5-gl4es-patch.diff` - `git diff quest/gl4es.patch`: the gl4es side
  (`gl4es_multiview_copy_layers`, `gl4es_texture_lod_bias`,
  `gltexture_t.lg_lod_bias` kept by `glTexParameterfv(GL_TEXTURE_LOD_BIAS)`).
  The working tree's `quest/gl4es.patch` equals `git -C ../deps/gl4es diff`
  and applies cleanly to gl4es `1891af3` (checked).

Restore: `git -C lindberghrecomp apply ../ai_docs/wip/t3-t5-lindberghrecomp.diff`
and `git apply ai_docs/wip/t3-t5-gl4es-patch.diff` (then re-apply the patch to
`../deps/gl4es` and rebuild it, guide 7.1).
