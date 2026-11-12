# Work in progress - NOT VERIFIED / KNOWN BROKEN

Safety copies of uncommitted VT3 code (updated 2026-11-11 night, on top of
submodule `9d68719` = the sky dome fix, outer: the commit that adds this file).
The T3 sky work is committed (`9d68719`); its wrong fp-180 "dome" code was
dropped. T5 (LOD bias) is committed.

- `t4-on-sky-lindberghrecomp.diff` - T4, the per-eye ground shadow mask
  (`arbprog.c` `vt3_mask_unit`, `lg_mask`, `k_mask_fn`; `stereo.c`
  `mask_copy`, `stereo_mask_twin`; plus the unused helper `arb_fp_local`).
  **Fails on the Quest: the players' ground shadows disappear** (HANDOFF
  3.1). In this copy it is **opt-in** (`LINDBERGH_VT3_MASK=1`). Needs a
  debug run (e.g. output `lg_mask` as colour) before use.
  Restore: `git -C lindberghrecomp apply ../ai_docs/wip/t4-on-sky-lindberghrecomp.diff`.
- `t8-flat-and-fade-lindberghrecomp.diff` - T8 (owner's worn reports): VT3
  Classic always flat (stereo.c `flat_all`), Immersive cross-fade quad left
  out of world frames (stereo.c, arbprog.c `arb_fp_units`). Works in
  test runs (HANDOFF 3.1), regression not yet run.
- `glq-second-writer-fix.diff` - historical (committed as `373c5ae`).
