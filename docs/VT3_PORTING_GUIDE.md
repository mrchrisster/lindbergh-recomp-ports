# Virtua Tennis 3 (Sega Lindbergh -> macOS & Meta Quest 3) Porting & Research Guide

This document contains the complete technical findings, workspace layout, binary reverse-engineering analysis, and step-by-step implementation guide for porting **Virtua Tennis 3** (*Power Smash 3*, Lindbergh Yellow, ID: `SBKX` / `DVP-0005`) to **macOS** and **Meta Quest 3** using [`lialan/lindbergh-recomp-ports`](https://github.com/lialan/lindbergh-recomp-ports) and its `lindberghrecomp` static recompilation toolkit.

---

## 1. Current Workspace & Extracted Files Layout

All archives, extracted game files, and the recompilation repository are placed under `<workspace>/`:

| Path | Description |
| :--- | :--- |
| `<workspace>/lindbergh-recomp-ports/` | Cloned `lialan/lindbergh-recomp-ports` repository with initialized submodules (`lindberghrecomp` and `lindberghrecomp/pcrecomp`). |
| `<workspace>/Virtua Tennis 3.7z` | Original archive containing `vt3.bin` (1.97 GB Linux rev 1.0 ext2 filesystem image). |
| `<workspace>/vt3/vt3.bin` | Unpacked raw ext2 filesystem image for *Virtua Tennis 3*. |
| `<workspace>/vt3/extracted/disk0/` | Extracted game root directory (`TEA_DIR`). Contains `vt3_Lindbergh/`, `shader/`, `lib/`, `game`, and `vt3rc`. |
| `<workspace>/House of the Dead 4.7z` | Original archive for *The House of the Dead 4* (reference game already supported by `lindbergh-recomp-ports`). |
| `<workspace>/hotd4/extracted/disk0/` | Extracted reference game root directory (`elf/`, `fs/`, `drv/`) ready to test `build-macos.sh hotd4`. |

### ⚠️ `vt3.bin` (the old base) is truncated: Blake and Ancic are missing
**Resolved with Rev. C's data:** `Virtua Tennis 3 (SBKX) (Rev. C).zip` is a clean extracted `disk0/` tree with all of these files at full size. The working copy is that tree plus `vt3_Lindbergh_HD/_VGA/_FULLHD` from the old dump (`<workspace>/vt3/disk0`, archived as `<workspace>/Virtua Tennis 3 (SBKX) (merged).zip`; `game.conf`'s `find_game` picks it for `<workspace>/vt3`). Rev. C also replaces an 11th file the old dump had wrong: Ancic's base model `P_M_ANC_game_all01_base_AN.efo` was full-size but its contents differed. What follows is kept for anyone with the old dump.

**The build checks for this.** `games/vt3/game.conf` defines `check_game`. It looks for any 0-byte file in the tree, and for the 12 Blake/Ancic player models it compares sha256 against a complete Rev. C copy (Ancic's base model was full-size but wrong in the old dump). `scripts/build-macos.sh`, `quest/build.sh --with-game` and `quest/install.sh` call it when a game defines it. **They stop** with the list of bad files and a pointer to Rev. C, because otherwise the game crashes partway through a tournament, depending on who the player picks and the draw. `LINDBERGH_ALLOW_DAMAGED_GAME=1` builds anyway.
**10 player animation `.efo` files** under `disk0/vt3_Lindbergh/resource/model/player/` are 0 bytes: `P_M_BLA_game_all01_base_II` and `P_M_BLA_game_all_M1/M2/M3/M4SP_II` (James Blake), and `P_M_ANC_game_all01_M1/M1SP/M2/M3/M4_AN` (Mario Ancic).

This is not a 7-Zip bug, and `debugfs` cannot recover them (checked 2026-11-09). The image in `Virtua Tennis 3.7z` is **2,069,479,424 bytes**, but its ext2 superblock declares 512,000 blocks of 4 KB = **2,097,152,000 bytes**. The last ~27.7 MB are missing, and those files' blocks (e.g. 506186+) lie past the end. `debugfs dump` reports "short read". A complete dump of the game is needed. To check one:
```bash
/opt/homebrew/opt/e2fsprogs/sbin/dumpe2fs -h vt3.bin | grep -E 'Block (count|size)'   # count x size must equal the file size
find disk0 -size 0 -type f                                                                # must print nothing
```
The Redump disc image (`DVP-0005A ... [REDUMP].iso`, 1,811,709,952 bytes) does not help here. It is the encrypted install disc (no ISO9660 header, ~8 bits/byte entropy throughout), and this project does not decrypt game media. What's needed is a complete decrypted dump of an installed game.

With the truncated copy, **any match against James Blake crashes** (Section 4, the "third tournament" crash). Ancic's base model is intact, but his match animations are not.

---

## 2. Virtua Tennis 3 Binary & Launch Architecture Analysis

### 2.1 How the Cabinet Boots VT3
From `<workspace>/vt3/extracted/disk0/game` and `vt3rc`:
1. Working directory at launch: **`disk0/vt3_Lindbergh/`** (the game opens `resource/...` relative to `vt3_Lindbergh/`).
2. Environment variables set by `game`:
   - `TEA_DIR=/home/disk0/` (relative to `vt3_Lindbergh/`, this is **`..`** — where `../shader` and `../lib` sit!).
   - `LD_LIBRARY_PATH` includes `../lib` (`libCg.so`, `libCgGL.so`, `libCgFX.so`, `libCgFXGL.so`).
   - `GLIBCPP_FORCE_NEW=1`

### 2.2 ELF Executables Comparison (`with debug_info, not stripped`)
Inside `disk0/vt3_Lindbergh/`, there are four main game executables (all **6,543,267 bytes**, 32-bit x86 SYSV ELF, dynamically linked, **not stripped**, with full C++ symbols and DWARF debug info!):

| Executable | SHA-256 | Exact Binary Differences |
| :--- | :--- | :--- |
| `vt3_Lindbergh_VGA` | `c10d3a572be39996516fa513ab51a810266bcdd284c55d244094997bcebb3b5d` | Original unmodified binary. Defaults to **640x480** unless DIP switch bits (`0xE0`) are set; skips the widescreen override via `jmp 0x8175b23` at `0x08175b03`. |
| `vt3_Lindbergh_HD` | `4bc1ff1735b382f9dd6246656cdeaa3260193283aa494d3e745ad83655d3c9aa` | Patched at 2 locations:<br>1. `0x08175b03` (`tennis::initializeSystem`): `eb 1e` -> `90 90` (NOPs out the jump so it unconditionally writes width `0x550` = **1360**, height `0x300` = **768**, mode `2` to `0x088bbe68`/`0x088bbe6c`).<br>2. `0x0831c63c` (`amDipswGetData`): forces DIP switch return byte to `0xE0`. |
| `vt3_Lindbergh_FULLHD` / `vt3_Lindbergh` | `556729756c9160c4a5b1c6ed0c2674d7363a936b4ca91f5e2661494a55eb66a2` | Same as `vt3_Lindbergh_HD`, except the immediate constants at `0x08175b0b` and `0x08175b15` are patched from `1360x768` (`0x550 x 0x300`) to `1920x1080` (`0x780 x 0x438`). |

> **Note (2026-11-09):** the three binaries above are not Sega's originals. Rev. C's `vt3_Lindbergh` (sha256 `0afba27d...`, from `Virtua Tennis 3 (SBKX) (Rev. C).zip`) is the original. Even "`_VGA`" differs from it in 13 bytes:
> - game ID `SBKX` -> `SBJJ`
> - `tennis::setError(long)` replaced by `mov eax,1; ret`
> - the widescreen test at `0x08175b03` changed from `je` to `jmp`
> - the serial ports changed from `/dev/ttyS*` to `/dev/tts/*`
>
> The original raises "Game Program Not Found" (`setError(-3)`) when the security dongle's challenge-response fails (`usrAdvSegaLogoLoop::exec`: `amDongleDecryptEx` on a table of encrypted blocks, compared with the expected plaintext). The runtime does not answer that challenge, so the port builds from `vt3_Lindbergh_HD` as before. The code layout is identical, so every address in this guide holds for both.

### 2.3 Dynamic Library Dependencies (`DT_NEEDED`)
Running `objdump -p` on `vt3_Lindbergh_HD` shows:
- `libGLU.so.1`, `libGL.so.1` (handled by `lindberghrecomp` `hle_gl.c` / `gen_gl_thunks.py` / `vulkan_guest.cpp`)
- `libCg.so`, `libCgGL.so` (lifted via `solib.py` and HLE in `hle_cg.c`, detailed below)
- `libpthread.so.0`, `libc.so.6`, `libm.so.6`, `libstdc++.so.5`, `libgcc_s.so.1` (handled by `hle_pthread.c`, `hle_libc.c`, `hle_cxx.c`)
- `libX11.so.6`, `libXext.so.6` (handled by `hle_window.c`, `hle_glx_posix.c`, `hle_vidmode.c`)
- `libsegaapi.so`, `libkswapapi.so` (handled by `hle_segaapi.c`, `hle_sega.c`)

---

## 3. Critical Architectural Discoveries & Solutions

### 3.1 VT3's Use of NVIDIA Cg & Why `libCgGL.so` Must NOT Be Lifted

VT3 imports only **15 `cg*` functions** total (`games/vt3/generated/recomp_imports.h` lines 136-150):
- **12 from `libCg.so`:** `cgCompileProgram`, `cgCreateContext`, `cgCreateProgram`, `cgDestroyContext`, `cgDestroyProgram`, `cgGetError`, `cgGetErrorString`, `cgGetProfileString`, `cgGetProgramString`, `cgIsContext`, `cgIsProgramCompiled`, `cgSetErrorCallback`.
- **3 from `libCgGL.so`:** `cgGLGetLatestProfile`, `cgGLIsProfileSupported`, `cgGLSetOptimalOptions`.

#### VT3's In-Memory Shader Compilation Pipeline:
VT3 does **NOT** use `libCgGL.so` to load or bind shaders (`cgGLLoadProgram`, `cgGLBindProgram`, etc. are not imported). Instead, VT3 uses `libCg.so` purely as an **in-memory text-to-text compiler**:
1. Calls `cgCreateProgram(ctx, CG_SOURCE, src, profile, entry, args)`
2. Calls `cgGetProgramString(prog, CG_COMPILED_PROGRAM)` (`0x100a`) to get the compiled `!!ARBvp1.0` / `!!ARBfp1.0` (`OPTION NV_vertex_program3` / `OPTION NV_fragment_program2`) assembly string
3. Parses the `#var` comments in that compiled assembly string (via `_sShaderConstantTable::parseAsm` at `0x082dfae6` and `TScene::Shader::getParameter` at `0x081ae740`) to map Cg uniform names to `program.local[N]` / `program.env[N]` registers and texture sampler units!
4. Uploads the compiled assembly string to OpenGL via `glProgramStringARB`, which `lindberghrecomp/src/runtime/arbprog.c` translates to GLSL!

#### Why `libCgGL.so` must be answered by HLE:
`libCgGL.so`'s `cgGLGetLatestProfile` (`0xb401da4c`) and `cgGLIsProfileSupported` (`0xb401f968`) query the host's `glGetString(GL_EXTENSIONS)` for `GL_NV_vertex_program3` and `GL_NV_fragment_program2`. Because macOS OpenGL 2.1 Compatibility mode does not advertise NVIDIA-proprietary extensions (even though `arbprog.c` translates them in software), `libCgGL.so` would return `0` (unsupported) on macOS!

**Solution:**
- Keep `SOLIBS="lib/libCg.so"` in `games/vt3/game.conf` (excluding `libCgGL.so`).
- Implement the 3 `cgGL*` functions in `lindberghrecomp/src/runtime/hle_cg.c`, always registered even when `libCg.so` is loaded via `solib`:
  - `cgGLIsProfileSupported(profile)` -> returns `1`
  - `cgGLGetLatestProfile(type)` -> returns `0x1b59` (`7001`, `CG_PROFILE_VP40`) when `type == 8` (`CG_GL_VERTEX`), and `0x1807` (`6151`, `CG_PROFILE_FP40`) when `type == 9` (`CG_GL_FRAGMENT`)
  - `cgGLSetOptimalOptions(profile)` -> no-op, returns `0`

---

### 3.2 Lifting `libCg.so` via `solib.py` & Disassembler Speedup

1. `disk0/lib/libCg.so` has no `.symtab` (only `.dynsym` with 282 exported symbols), while it actually contains **13,221 functions** in `.text`.
2. In `libCg.so`, `.init` is at `0x32840..0x32858`, `.plt` is at `0x32858..0x33008`, `.text` is at `0x33010..0x18f400`, and `.fini` is at `0x18f400..0x18f41e`.
3. In `lindberghrecomp/pcrecomp/tools/disasm/disasm32.py`:
   - Added GCC prologue `b'\x55\x89\xE5'` alongside MSVC `b'\x55\x8B\xEC'`.
   - Chunked `disassemble_at` into 128-byte windows, avoiding decoding 8,192 bytes per basic block. This sped up function discovery by ~50x (13,221 functions discovered in ~25 seconds!).
4. In `lindberghrecomp/tools/recomp/solib.py`:
   - Updated `Lib.functions()` to run `Disassembler.find_functions` over `.text` (`[self.base + text.addr, self.base + text.addr + text.size)`), seeded with `.dynsym` functions, `.ctors`/`.dtors` entries, and call targets from `.init`/`.fini`.
   - Relocated and lifted 13,153 functions across 33 C translation units (`recomp_solib_funcs_0000.c` .. `recomp_solib_funcs_0032.c`)!

---

### 3.3 GCC 3.3 `libstdc++.so.5` Struct Layouts in Lifted Code

From VT3's lifted code in `recomp_funcs_0037.c` (`L_082DFAE6`: `_sShaderConstantTable::parseAsm`), VT3 constructs a stack-allocated `std::istringstream` at `[ebp - 0x108]`:
- `base + 0x00`: `istringstream` vptr (`0x84E795Cu`, virtual base offset to `basic_ios` at `vptr - 0xc` is `0x5c`).
- `base + 0x04`: `streamsize _M_gcount` (`0`).
- `base + 0x08`: `std::basic_stringbuf` subobject (`size = 0x54`):
  - `+0x00`: `basic_streambuf` vptr
  - `+0x04`: `char* _M_buf`
  - `+0x08`: `size_t _M_buf_size`
  - `+0x14`: `char* _M_in_beg` (`eback()`)
  - `+0x18`: `char* _M_in_cur` (`gptr()`)
  - `+0x1c`: `char* _M_in_end` (`egptr()`)
  - `+0x20`: `char* _M_out_beg` (`pbase()`)
  - `+0x24`: `char* _M_out_cur` (`pptr()`)
  - `+0x28`: `char* _M_out_end` (`epptr()`)
  - `+0x2c`: `ios_base::openmode _M_mode`
  - `+0x50` (`base + 0x58`): `std::string _M_string` (pointer to guest string data).
- `base + 0x5c`: `std::basic_ios` virtual base subobject:
  - `+0x00`: `basic_ios` vptr
  - `+0x14`: `_M_streambuf_state` (`_Ios_Iostate`: `goodbit = 0`, `badbit = 1`, `eofbit = 2`, `failbit = 4`)
  - `+0x18`: `basic_streambuf* _M_streambuf`

All HLE stream and string implementations in `lindberghrecomp/src/runtime/hle_cxx.c` match these exact offsets.

---

### 3.4 JVS Input Mapping (8-Way Lever + 2 Shot Buttons) — DONE

`hle_sega.c` (`jvs_switch_byte`) reports VT3's switches:

| Byte | Bit | Meaning | Cabinet bit (`cabinet_buttons.h`) |
| --- | --- | --- | --- |
| 0 | `0x80` | Start | `CAB_P1_START` |
| 0 | `0x40` | Service | `CAB_SERVICE` |
| 0 | `0x20` / `0x10` / `0x08` / `0x04` | Up / Down / Left / Right | `CAB_P1_UP/DOWN/LEFT/RIGHT` (bits 12-15) |
| 0 | `0x02` | Button 1 (left: top spin) | `CAB_P1_TRIGGER` |
| 0 | `0x01` | Button 2 (right: slice / backspin) | `CAB_P1_BUTTON2` (bit 16) |
| 1 | `0x80` | Button 3 (no shot - see below) | `CAB_P1_BUTTON3` (bit 17) |
| 1 | `0x40` | Button 4 | `CAB_P1_FIREMODE` |

**The cabinet has two shot buttons (corrected 2026-11-11).** The game's How
to Play text (`language/I_ADV_HowToPlay_TK_txtDB_US.bin`): "Press Left button
for top spin", "Press Right button for backspin", "Press Left and right
buttons together to lob". `pad::init` reads only switches 0x02000000 (button 1)
and 0x01000000 (button 2) for its button bits (0x2000 / 0x4000, both also
0x400 "decide"); switch byte 1 0x80 becomes pad bit 0x80000, which no shot
code reads. So a lob is buttons 1 and 2 at once; the old "button 2 = lob,
button 3 = slice" was wrong (on the Quest A gave a slice and B nothing).

Player 2's lever and buttons 2-3 are the same bits shifted by `CAB_P2_JOY_SHIFT` (8).

- **Keyboard** (defaults in `host_settings.c`, rebindable from the Controls menu): arrows = lever, Z / X / C = buttons 1-3, i.e. top spin / slice / nothing (Z + X together = lob; the Controls menu's own labels, "Button 2 (lob)" / "Button 3 (slice)", are still the old, wrong ones), 5 = coin, 1 = start, M = mute (starts muted), Esc = quit.
- **Game controllers** (`host_sdl.c`): the first pad is P1, the second P2. D-pad or left stick = lever (8 sectors), A/B/X = buttons 1-3, Y = button 4, Start, Back = coin.
- **Quest** (`xr_controls.c` `lever_buttons`, when the profile sets `joystick`): either thumbstick = lever; trigger = top spin (button 1), A / X = slice (button 2), B / Y = lob (buttons 1 and 2 together), the same on both hands. On a lever cabinet holding Y no longer opens the settings panel (it is the lob); the left Menu button does.
- Keyboard and pads on the desktop still send button 3 for keyboard C / pad X: that is no shot there either (not changed; press Z and X, or pad A and B, together for a lob).
- `game_profile.h` `joystick = 1` (VT3's `host.c`) also stops "pointer left the window" from pressing reload (which is button 2 here).

Menus: on the player-select and tournament screens press **Z**; on court select press **Enter**. Waiting for the timers costs about a minute per screen.

---

## 4. Current Status (2026-11-08, macOS and Quest 3)

### Works on macOS (OpenGL renderer, `--opengl`)

- Boots through `CARD R/W INITIALIZING`, the SEGA logo, attract mode (video plays), menus, and into a match at a steady 60 fps.
- All of VT3's shaders compile through the **lifted libCg.so** (no precompiled `.asm_gl` exists for VT3, so `hle_cg.c`'s disc lookup cannot be used).
- Logos, courts, crowd, umpire, ball kids, and **skinned players** (arms, shirts, hands) render correctly.

### Fixes made this session (all pushed, see Section 6)

pcrecomp (lifter/disassembler):
- `push ax` / `pop ax` (0x66 prefix) move esp by 2 (libCg passes shorts with `sub esp,2; push ax`).
- x87 rounding control: `fldcw` is honoured; `frndint` and `fist(p)` round by the RC bits (GCC's `(int)` casts; libCg's `ceil(log2 n)` array growth).
- Disassembler: straight runs longer than 4 KB continue as new leaders; GCC PIC switch tables (`sub r,[ebx+i*4+d]; jmp r`) recognised, bounded by the last live `cmp r, imm`.

lindberghrecomp `solib.py` (lifting libCg):
- Drop candidate function starts that fall inside another instruction; size discovered functions by their own control-flow reach (bodies may overlap).
- Switch arms, out-of-body branch targets and `lea r,[ebx+f@GOTOFF]` callbacks become entries; the lifter gets NOPs over inline switch tables.
- Data imports emitted (`SOLIB_DATA`) and filled at load (`__ctype_b/tolower/toupper`).

lindberghrecomp runtime:
- `arbprog.c` (ARB -> GLSL): classic vertex names (`vertex.color`, `vertex.texcoord[n]`, `vertex.weight`, ...) alias generic attributes as on NVIDIA; `fragment.facing`; register-relative constant reads clamped to the array; **program locals raised from 96 to 1024** (VT3's bone palette reaches `c[225]` — this was the missing-arms bug).
- `hle_cxx.c`: istream `basic_ios` found when the copied libstdc++ vtable reads 0 (shader parser spun forever); `hle_libc.c`: relative `fopen` retried under `TEA_DIR` (scene shaders `shader/*.fx`).
- `hle_glx_posix.c`: `GLX_SGIX_fbconfig/pbuffer` as framebuffer objects, behind profile flag `glx_sgix_pbuffer`.

### Open issues

1. ~~Replay camera / pre-match intro flat colour~~ — fixed, see Section 5.
2. ~~Audio~~ — works (confirmed by ear). SEGAAPI is answered by `hle_segaapi.c`; it starts muted, M toggles (or `LINDBERGH_MUTE=0`). `LINDBERGH_SEGA_METER=1` logs the mix peak and voice count every two seconds. **Music skipping fixed 2026-11-11:** VT3's music comes from CRI ADX through `lbrna` into a 341 ms SEGAAPI ring (16384 frames, refilled up to the play position by ADX's own 16.67 ms thread, not the game loop). The mixer left a looping voice's position on its loop end when a 1024-frame block ended exactly there (every lap for this ring). `lbrna` then read "ring size", took the ring for empty and overwrote the queued lap. So 341 ms of music was lost every lap (written / played 2.38 on macOS, 2.19 on the Quest). Now wrapped at once (`LINDBERGH_SEGA_POS_WRAP=0` gives the old behaviour). Diagnostics: the `[sega-api] health:` line, `LINDBERGH_AUDIO_DUMP=<wav>` (`_STREAMS=1`, `_WRITES=1`), `[io] slow read`, `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1` (unattended Quest runs), `scripts/wav_glitches.py`. Full write-up: `ai_docs/research/audio-music-skipping.md`.
3. **Quest 3 (gl4es + OpenXR)** — playable: boots, menus and matches run at a steady **60 fps** with textured 3D, controls work. See Section 7 for what was fixed and how to test without a person. Still open on the headset:
   - **The match is shown on a flat panel**, not as a 3D world (see Section 8).
   - The menu-to-court transition shows one tilted frame (world mode starting a frame early).
   - ~~**Crash at the start of the third tournament**~~: **game data, not code.** Road to the Championship round 2 (the third tournament) is against **James Blake**, whose base model is one of the empty files from the truncated image (Section 1). The game opens it at boot (`fopen ... -> ok`, 0 bytes read), and his scene entry is NULL when the match loads: guest `0x18` in `TScene::SceneDatabase::executeManager()` <- `Framework::execute()`. It reproduces on **macOS too**, in ~30 s with `scripts/vt3-repro.sh tournament3 mac <disk0>`. Round 0 (Henman) and round 1 (Hewitt) jumped to the same way play normally. **Fixed with Rev. C's data** (Section 1): on the merged tree, round 2 loads Blake at the French Cup (Stage 3) and plays (macOS, 2026-11-09).
   - ~~**Prize money counter is empty**~~ — **fixed 2026-11-09** (`quest/gl4es.patch`). On the result slate, each digit is a 32x512 strip scrolled by `program.local[7]` (`va_8 * local[6] + local[7]`, offsets -0.1 to -1), so the texture coordinate goes below 0 and relies on `GL_REPEAT`. VT3 sets its textures' wrap inside display lists with `glTexParameteri`. gl4es turns that into `glTexParameterfv` with a pointer to a float on its own stack, and **recorded the pointer, not the value, into the list**: every replay read a dead stack slot, mostly 0 (about 1,500 wraps of 0 per session). The repeat never arrived, so the rolled digits sampled the strip's empty edge. gl4es now copies the values into the list, and refuses a wrap that is no wrap mode, as a desktop driver does. Any texture parameter VT3 sets in a list was affected, so other textures may look different now. Reach the slate with `scripts/vt3-repro.sh prize` (1P wins every point from 40-0).
   - ~~**The two-player camera after a point: black background, players squashed**~~ — **fixed 2026-11-09** (`stereo.c`). After a point, `camera::initWinlose()` picks the split-screen camera when its first `getRandMT_U32() % 10` is 0 (singles), so about 1 point in 10. Each frame, the game clears **depth only** with a half-screen viewport (`0,0 680x768`, then `680,0 680x768`) and draws that player in the half. In the headset the pbuffer is the eyes, and `stereo.c` took any part-screen clear for the start of a "side pass" (another game's colour-cleared reflection passes). Both halves went into an offscreen buffer that's never shown. Now only a clear that includes colour starts a side pass, and a whole-screen clear still ends one. Reach the shot on every point with `LINDBERGH_VT3_SPLIT=1` (`scripts/vt3-repro.sh splitreplay`). **Still open:** the right pane shows a reddish, see-through band of crowd over part of the court near the middle, which macOS does not have (probably the screen blur/composite pass).
   - The end-of-game split ("GAME 1P 1-0") renders correctly on the Quest.
   - **The court logo shown in replays has a white pane behind it that does not rotate with the logo** - a quad drawn with a different transform than the logo (likely a 2D/HUD-classified pass beside a 3D one, `LINDBERGH_DRAW_LOG` on a replay frame shows which).
   - **The match is shown as a flat screen** in front of the player, not as a 3D world: `stereo.c` judges VT3's camera "zoomed" (lens ~29, from the combined MVP in program locals) and falls back to the flat picture. See Section 8 for where this should go.
   - **Opening frames of a match glitch** (play-testing 2026-11-09): for a few frames as the game begins, the camera showing the court glitches. Possibly the known tilted frame at the menu-to-court handover (above), or the court flyover (`usrAcEntranceLoop`) switching from flat to world. Capture with `LINDBERGH_GAME_SHOT=<first>,1` around the hand-over and `LINDBERGH_DRAW_LOG` on the bad frames.
   - **Split-screen point camera: the left pane's player shows as a shadow in the right pane** (2026-11-09, after the side-pass fix). Likely related to the reddish see-through band already noted there: the right pane draws over something left from the left pane (a shadow map, or the screen copy the composite reads). Reach it on every point with `scripts/vt3-repro.sh splitreplay`.
   - **Sky texture glitches when the camera looks from down the court up towards the sky** (2026-11-09). Not yet captured. Candidates: the sky dome drawn with the game's far plane against the headset's projection, or a wrap/clamp on the sky texture (texture parameters set in display lists only reach the driver since the gl4es list fix, so this may be new or old).
   - The last runs with the shadow variant averaged ~50 fps in some stretches; not yet profiled (`LINDBERGH_XR_PROF=1`, `LINDBERGH_FRAMEMAP=<frame>`).
   - Launcher icons are hotd4 placeholders.
4. **Vulkan renderer** — untested for VT3 (needs a shader pack via `quest/build_vulkan.py`).
5. **Other games** (hotd4, lgj, gse) have not been rebuilt against the toolkit changes above. The lifter changes (16-bit push, x87 rounding) affect every game and should be regression-checked.
6. `lindbergh_nvram.bin` is written beside the executable; the card-reader message is Japanese-only (cabinet language setting).

---

## 5. Replay Camera / Pre-Match Intro — RESOLVED

### Symptom
After a point, the replay ("LIVE" logo) and the pre-match intro right after court selection showed one flat colour behind the 2D overlays, though the 3D scene was drawn correctly underneath.

### The pipeline (traced)
1. The scene is drawn to the window, then copied into texture 17 (`glCopyTexSubImage2D`).
2. A post-process chain runs through the game's FBOs: fb 1 / fb 2 (1360x768 textures 12 / 13) at several viewport sizes; **fb 3** (texture 14, 680x384) via `v32/f33` (4-tap blur); **fb 4** (texture 15) via `v26/f27` (glare).
3. One full-screen `v59/f60` draw composites: `(lerp(scene, blurred, saturate(|depth*c1.x + c1.y|)) + glare) * f_loc0.x + transition * f_loc0.y`. The DOF factor saturates for most pixels, so the screen is mostly texture 14.

### Cause
Texture 14 was always black. The blur quad is plain immediate mode (`glBegin`, `glTexCoord2f`, `glVertex3f`) with correct coordinates, but the translated shader picks texcoord 0 as `u_gen[8] > 0.5 ? va_8 : gl_MultiTexCoord0`, and `u_gen` came from the runtime's own record of `glEnable/DisableVertexAttribArrayARB`. That record went stale: `glPopClientAttrib` (called every pass) and entry points fetched through `glXGetProcAddress` change array state without passing the hook. With `u_gen[8]` stuck at 1 the shader read a stale generic array, every pixel sampled one texel, and the frame went flat.

### Fix
`arbprog.c` `upload()`: `u_gen` is filled from `glGetVertexAttribiv(i, GL_VERTEX_ATTRIB_ARRAY_ENABLED)` at each draw instead of the remembered state. Verified on the intro: texture 14 fills (261,120 pixels) and the close-up of the opponent fades in with the "LIVE" logo.

### A wrong turn worth knowing about
I first concluded the quads lived in display lists and sent texcoords with immediate `glVertexAttrib2fARB(8, ...)`. Both were wrong. The "display list" idea came from probes that called `glGetIntegerv` between `glBegin` and `glEnd`, which GL forbids, so they silently saw nothing. `LINDBERGH_LIST_LOG=1` showed VT3's lists hold only texture state, and `LINDBERGH_VA_LOG=1` showed the game never calls `glVertexAttrib*ARB`. The routing written for that theory (`va_alias` in `hle_gl_posix.c`: immediate generic attributes go to their classic twins, as on NVIDIA) is correct NVIDIA behaviour and harmless, so it stays, but nothing in VT3 exercises it.

---

## 6. Working Notes for the Next Agent

### Repos and branches
- `lindbergh-recomp-ports` (outer), submodule `lindberghrecomp`, nested `lindberghrecomp/pcrecomp`. Work is on branch **`vt3-port`** in all three (Quest work continues on **`vt3-quest`** in lindberghrecomp and the outer repo), pushed to forks under `mrchrisster` (remote `fork`); upstream is `lialan`. Submodule URLs in `.gitmodules` are relative, so a clone of either owner resolves to that owner's submodules. PRs go inner-first: pcrecomp, lindberghrecomp, then the outer repo.
- Never commit `games/*/generated/` (lifted game code; gitignored) or any game data.

### Build and run
```bash
cd <workspace>/lindbergh-recomp-ports
./scripts/build-macos.sh --opengl vt3 <workspace>/vt3/extracted/disk0   # full re-lift + build (~5 min)
cd build-mac && ninja vt3                                                  # runtime-only changes
./scripts/run-macos.sh --opengl vt3 <workspace>/vt3/extracted/disk0
```
Run long tests in the background and stop them by PID; never `killall`.

### Driving the game without a person
- `LINDBERGH_AUTOSTART=1`: coin at frame 300, start every 2 s.
- `LINDBERGH_KEYS="frame:key,..."`: scripted key taps (`\r` = Enter). Reaching the pre-match intro (~frame 2500):
  ```bash
  K=""; for f in $(seq 1500 90 3300); do K="$K$f:z,"; done
  for f in 2000 2400 2800 3200; do K="$K$((f+45)):"$'\r'","; done
  LINDBERGH_AUTOSTART=1 LINDBERGH_KEYS="$K" ./scripts/run-macos.sh --opengl vt3 ...
  ```
  Without keys the first replay lands around frame 7800 (it drifts between runs).
- `LINDBERGH_SHOT=<path> LINDBERGH_SHOT_EVERY=N LINDBERGH_SHOT_FROM=F`: saves PPM frames.

### Jumping to a broken section (`scripts/vt3-repro.sh`)
Not save states: a full snapshot would have to restore the GL driver's objects, the GL thread's queue and the sound voices, which live outside the guest. Instead the runtime sets the game's own state at the right moment (`hle_sega.c`, `vt3_jumps`). The match object is `g_pTennis` (`0x085061a4`) + `0x1c`. Its round is at `+0x0c` (setMatching picks that round's opponent from `+0xac`), and the current game's points are at `+0x06` / `+0x07` (0-3 = 0/15/30/40, zeroed by `match::init` and `calcGame`; `match::initGame` is dead code).

| Switch | Effect |
| --- | --- |
| `LINDBERGH_VT3_ROUND=N` | The run's first match is round N (0-based; written before the first `match::setMatching`). Round 0 Henman, 1 Hewitt, 2 Blake |
| `LINDBERGH_VT3_POINTS=a,b` | Every game starts at those points (`3,0` = 40-0) |
| `LINDBERGH_VT3_LOG=1` | Each matching, next round and new game, with the frame |
| `LINDBERGH_VT3_SPLIT=1` | Every point ends on the split-screen camera (normally 1 point in 10): the first `getRandMT_U32()` inside `camera::initWinlose` returns 0 |
| `LINDBERGH_VT3_WIN=1` | 1P wins every point (`match+0x61`, the point's winner, set to 0 before `match::calcPoint`). With `LINDBERGH_VT3_POINTS=3,0`, a match is won in two points |
| `LINDBERGH_VT3_PRIZE_TRACE=<frames>` | `LINDBERGH_TRACE_VP` starts that many frames after the result slate's first prize coin sound (`sound::playSe_prize_coin`) |

```bash
./scripts/vt3-repro.sh tournament3 mac <disk0>     # Blake crash, ~30 s
./scripts/vt3-repro.sh splitreplay quest           # the split-pane replay on the headset, frames pulled back
./scripts/vt3-repro.sh round1 mac <disk0> 90       # any round; any LINDBERGH_* in the environment rides along
```
The script drives the menus, runs for a set time, and leaves the log and frames in `$OUT` (default `/tmp/vt3-repro-<scene>`). On the Quest it writes `env.txt`, does the proximity override and wake, and afterwards force-stops the app, undoes the override and **empties `env.txt`**. It pins Classic mode with replays, point cutaways and arcade overlays on (`LINDBERGH_VT3_IMMERSIVE=0`, `LINDBERGH_REPLAYS=1`, `LINDBERGH_VT3_CUTAWAYS=1`, `LINDBERGH_ARCADE_OVERLAYS=1`) unless the caller sets them, so the headset's saved settings cannot change a run; an empty value (`LINDBERGH_VT3_IMMERSIVE=`) leaves it to vr.cfg.

### Diagnostic switches (all off by default)
| Switch | What it shows |
| --- | --- |
| `LINDBERGH_SOLIB_TRACE=1` | Calls into lifted libCg, args, and the Cg compiler listing on failure |
| `LINDBERGH_CXX_TRACE=1` | iostream open / read / getline |
| `LINDBERGH_ARB_DUMP=1` (+ `ARB_NOCACHE=1`) | The GLSL every ARB program translates to |
| `LINDBERGH_GL_TRACE=<frame>` | Every GL call of that frame, plus a `[draw]` block per draw: programs, target FBO status/attachments, scissor/stencil/cull/draw buffer, textures on units 0-4 with content readback, constants, attributes, and `[skin]` decoding of bone weights/indices |
| `LINDBERGH_TRACE_VP=26,51 LINDBERGH_TRACE_FROM=<frame>` | The same `[draw]` block for the first 60 draws using those vertex programs, plus that draw's `glTexCoord2f`/`glVertex3f` arguments up to its `glEnd`. Prefer this to frame numbers: scenes drift a few hundred frames between runs |
| `LINDBERGH_TEX_WATCH=<texture>` | That texture's content at every traced draw |
| `LINDBERGH_FB_PROBE=<fbo>` | Readback/vertices while that FBO is bound. Caveat: it queries GL inside `glBegin`/`glEnd`, where queries fail silently, so it misses immediate-mode quads |
| `LINDBERGH_FP_SOLID=1/2/3/4` (+ `FP_ONLY=<id>`) | Replace fragment programs: solid green / raw unit 0 / texcoord as colour / vertex colour |
| `LINDBERGH_ARB_NOCLAMP=1` | Turns off the relative-index clamp (comparison only) |
| `LINDBERGH_LIST_LOG=1` | The calls recorded into each display list |
| `LINDBERGH_VA_LOG=1` | Immediate `glVertexAttrib*ARB` calls and where they are routed |
| `LINDBERGH_FORCE_SHADOW=1` (desktop) | Depth textures read as 2D become `sampler2DShadow` (the driver compares): the reference for the Quest's in-shader compare |
| `LINDBERGH_XR_SHOT=<first>,<every>` (+ `XR_SHOT_FULL=1`) | Quest: the left eye as handed to the headset, `xrshot_<frame>.ppm` beside the game (quarter size unless FULL) |
| `LINDBERGH_XR_PROF=1` | Quest: per 60 frames, the game's GPU work (a `glFinish` on entry to the frame's end), the eye copies, `xrEndFrame` |
| `LINDBERGH_FRAMEMAP=<frame>` | Quest: every draw of that frame with its GPU time (a finish after each), target, viewport and program pair |
| `LINDBERGH_SKIP_DRAWS=offscreen\|main\|all` | Quest: whole groups of draws left out, to find where GPU time goes |
| `LINDBERGH_DRAW_LOG=<frame>[-<last>]` | Quest: each draw's classification (`persp`, `hud`, target), colour mask and stencil state in `stereo.c`, and each clear with its viewport and side-pass state (`[units] ... clear`) |
| `LINDBERGH_CLEAR_LOG=1` | Quest: colour clears of the eyes while a world is drawn |
| `LINDBERGH_GLPROF=1` (+ `GLPROF_SLOW=<ms>`) | Quest: CPU time per GL call and the slowest frames |
| `LINDBERGH_SHADOW_BIAS=<depth>` | Quest: bias off the reference depth in the in-shader shadow compare (default: profile `vr.shadow_bias`, 0) |
| `LINDBERGH_GAME_SHOT=<first>,<every>[,1]` | Quest: the left eye as the game drew it, read from the eye array at the frame's end, as `game_<frame>.ppm` (quarter size unless `,1`). Works while the headset sleeps or sits at a Guardian prompt - use this, not `XR_SHOT`, for unattended runs |
| `LINDBERGH_FORCE_REPLAY=1` | Every point earns a replay (`replay::isReplay_point()` overridden): the replay camera ~a minute into a match |
| `LINDBERGH_INPUT_LOG=1` | Quest: each change of the cabinet buttons, with the controllers' raw state |
| `LINDBERGH_CUBE_LOG=1` | Cube maps: face uploads, what each cube unit holds at a draw, each cube's face contents and its state in gl4es and the driver |
| `LINDBERGH_CUBE_BIND_LOG=1` | Quest: draws where the driver's cube binding differs from gl4es' |
| `LINDBERGH_CUBE_GREY=1` / `LINDBERGH_SHADOW_LIT=1` | Every cube lookup a flat grey / every shadow lookup lit: which term darkens a model |
| `LINDBERGH_SHADOW_LOG=1`, `LINDBERGH_CMP_LOG=1` | Which texture each shadow lookup reads; each fragment program's link and its depth-compare unit mask |
| `LINDBERGH_SHADOW_PCF=0/1` | The in-shader shadow compare filtered over 2x2 texels (default on with `vr.depth_tex_shadow`) |
| `LINDBERGH_FORCE_SHADOW=1 LINDBERGH_SHADER_COMPARE=1` (desktop) | The Quest's in-shader shadow compare on macOS, to check it against the driver's |
| `LINDBERGH_COPY_LOG=1` | Each distinct copy from the framebuffer into a texture |
| `LINDBERGH_AUDIO_DUMP=<wav>` (+ `LINDBERGH_AUDIO_DUMP_STREAMS=1`, `_WRITES=1`) | The final mix as a 48 kHz WAV (after the limiter, before mute); the streamed rings alone; what the decoder wrote into each ring. `[sega-api] health:` (starvation, lead, late device blocks, limiter load) is always on, logged when something went wrong |
| `LINDBERGH_IO_SLOW_MS=<ms>`, `LINDBERGH_IO_DELAY=<ms>[,<every>]`, `LINDBERGH_IO_LOG=1` | `[io] slow read` threshold (default 50); a simulated slow disk; reads of 4 KB+ logged |
| `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1` | Quest: SDL keeps the audio device running while the Activity is paused (an unworn headset), so unattended runs have a mixer |
| `LINDBERGH_VT3_SERVELOG=1` | VT3: every frame a serve meter shows (player, state, power, latched, game vs re-anchored screen position), each `getScreenPosFrom3DPos` answer, each pixel-camera draw whose lens read is off the camera's |
| `LINDBERGH_VT3_SERVESHOT=<n>[,<from>]` | Quest, VT3: full-size game shots through 1P's next n serves (from that frame): power 0.3...0.95, then every 3rd frame for 45 |
| `LINDBERGH_SHOT_BOTH=1` | Quest: `GAME_SHOT` / `XR_SHOT` also save the right eye (`game_<frame>_r.ppm`, `xrshot_<frame>_r.ppm`) |
| `LINDBERGH_ARB_LOCAL_LOG=<index>[:<program>]` | Each write of that program local (frame, thread, program, value), and what each draw of the program uploads for it, while a trace window is open |
| `LINDBERGH_TRACE_VP` (additions) | Also prints `local[6]`/`local[7]` and the draw's texture coordinate sources: generic attribute 8 (enabled, buffer, stride, first four values) and unit 0's classic texcoord array |

### Method that has worked
Capture frames, then binary-search the pipeline with readbacks: which draw, which target, which texture, which constants, which inputs. Never query GL state between `glBegin` and `glEnd`: the query fails silently and misleads. Each bug so far was a one-line semantic gap between NVIDIA's 2006 GL and Apple's (attribute aliasing, out-of-range reads, local-parameter limits, rounding mode, 16-bit pushes), found by measuring rather than guessing.

---

## 7. Meta Quest 3 Port (2026-11-08)

### 7.1 Build
- `quest/deps.sh` with `ANDROID_NDK=~/Library/Android/sdk/ndk/28.2.13676358` (NDK 28.2 works). It applies `quest/gl4es.patch` (multiview, texture targets, shader conversion, and now `gl4es_compare_units` / `gl4es_mark_shadow`) and builds `deps/gl4es-android`. After editing `deps/gl4es`, `cmake --build ../deps/gl4es-android` and regenerate the patch (`git -C ../deps/gl4es add -N src/gl/multiview.[ch] && git -C ../deps/gl4es diff > quest/gl4es.patch`).
- `JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ANDROID_NDK=... sh quest/build.sh vt3`, then `adb install -r quest/VirtuaTennis3VR.apk`. Game data: `quest/install.sh vt3 <disk0>` (to `/sdcard/VirtuaTennis3`).
- GL thunks against gl4es: `llvm-nm` the exports of `../deps/gl4es/lib/libGL.a`, then `gen_gl_thunks.py --exports ... > games/vt3/generated/recomp_gl_thunks_android.c`. Redo after every re-lift.
- The APK holds translated game code: keep it private.

### 7.2 Controls (lever cabinet)
Right trigger = confirm / top spin, A = slice, B = lob (top spin + slice together, as on the cabinet), the left hand's trigger / X / Y the same, either stick = 8-way lever, stick click = start. Lever mode turns off the gun, laser, sight and recoil rumble (`xr_controls.c` `lever_buttons`, profile `.joystick = 1`).

### 7.3 Testing without a person
The headset sleeps and will not show an app when nobody wears it. What works over adb (USB debugging authorised):
```bash
adb shell am broadcast -a com.oculus.vrpowermanager.prox_close   # proximity sensor reads "worn"
adb shell input keyevent KEYCODE_WAKEUP                           # repeat until dumpsys power says Awake
adb shell am start -n org.lindbergh.vt3.vr/org.lindbergh.vt3.VirtuaTennis3VR
# ... wait, pull /sdcard/VirtuaTennis3/vt3.log and vt3_Lindbergh/xrshot_*.ppm ...
adb shell am broadcast -a com.oculus.vrpowermanager.automation_disable   # undo the override
```
Runtime options go in `/sdcard/VirtuaTennis3/env.txt` (one `NAME=value` per line). **Empty it afterwards**: a leftover `LINDBERGH_KEYS` keeps pressing Enter at court selection and looks like the game auto-advancing. Menu script used for the Quest (frame:key):
```bash
K=""; for f in $(seq 700 120 1500); do K="$K$f:1,"; done; for f in $(seq 1550 90 3600); do K="$K$f:z,"; done
for f in 2100 2500 2900 3300; do K="$K$((f+45)):"$'\r'","; done
```
**Unattended runs: use `LINDBERGH_GAME_SHOT`.** It reads the game's own picture on the GPU, so it works even when the session never gets past READY. Add `LINDBERGH_FORCE_REPLAY=1` to reach the replay camera in about a minute. The helper script used for this (scratch, not in the repo) pushes `env.txt`, does the proximity override and wake retries, launches, waits, pulls `vt3.log` and `game_*/xrshot_*` files, then force-stops, undoes the override and empties `env.txt`. One menu-to-replay run takes ~2.5 minutes.

`scripts/vt3-repro.sh <scene> quest` does all of this, and repeats the proximity override and wake every 15 s while the run lasts (an unworn headset dozes off within a minute or two). It also checks that the game really started (its log appears within 40 s) and tries the launch up to 3 times: a launch into a sleeping or just-woken headset sometimes comes to nothing. Nobody has to wear the headset. `XR_SHOT` frames do need the session shown; `GAME_SHOT` does not.

Blockers seen: the **Guardian boundary dialog** (logcat `GuardianDialogActivity`) keeps the session at READY (states `1 2` in the log) until someone confirms the boundary; don't turn Guardian off from adb, ask the person. A launch sometimes fails silently: check that `vt3.log` is new before reading it.

### 7.4 What was fixed, in order
1. **GL thread stalls (3-6 fps in menus).** ~640 synchronous waits per frame on `glCallList` and `glPush/PopClientAttrib`; queued as values in `gl_thread.c` (0 waits).
2. **Black 3D, only text visible.** `stereo.c` decides per draw whether it is world (stereo, perspective) or HUD, from the projection that `arb_env_projection()` reads out of `program.env[0..3]`. VT3's Cg programs keep `g_transform_mat` in **`program.local[0..3]`**, so every draw looked 2D. Profile switch `vr.camera_in_locals` reads the bound vertex program's locals instead (`DRAW_LOG` went from `persp 0` to `persp 1` on all 262 match draws).
3. **3 fps in a match, GPU-bound (~340 ms/frame).** `XR_PROF` put the time in the game's GPU work; `FRAMEMAP` showed single draws into a 128x128 target taking 36 ms (vertex program 135). The ARB translator copied Cg's 216-entry bone palette (`PARAM c[] = { program.local[0..3], {literal}, program.local[5..215] }`) into a **per-vertex local array** before indexing it with A0; Adreno spills that to scratch memory. Lists that are program.local (or program.env) at their own indices plus a few literals now index the uniform array directly, the literals written into that program's uploaded copy. 60 fps since; macOS unchanged.
4. **Black players.** Their fragment programs read a 1024x1024 depth texture (`DEPTH_COMPONENT32`, unit 0 or 1) through a plain `2D` target with `texture2DProj`, four taps summed as a soft shadow factor that multiplies all lighting. NVIDIA (and Apple) compare depth there; GLES leaves it undefined and the Quest returned 0. With profile `vr.depth_tex_shadow`, units whose bound 2D texture has a depth format (gl4es state, `gl4es_compare_units`) get a program variant (linked programs are keyed by that unit mask) that compares in the shader, as Let's Go Jungle's `SHADOW2D` path already did; `gl4es_mark_shadow` keeps the texture a shadow map after the runtime turns its own compare off. Only projective reads (`TXP`) of such a unit are shadow lookups: the depth of field reads the screen's depth texture with plain `TEX` and wants the depth itself (treating it as a shadow map blacked out the replay's world). The compare is filtered over 2x2 texels (`lg_pcf`, as a driver does with linear filtering) and the sampler is declared `highp` (a GLES sampler defaults to `lowp`).
5. **Close-ups and replays: players as silhouettes.** Not the shadows (`LINDBERGH_SHADOW_LIT=1` left them dark) but the **cube maps** - the players' ambient/environment light (`LINDBERGH_CUBE_GREY=1` lit them). Three gl4es bugs, all in `quest/gl4es.patch`:
   - `realize_textures` pushes a unit's sampler state (filters, wrap) to the driver only for the target enabled with `glEnable`; shaders never enable `GL_TEXTURE_CUBE_MAP`, so the driver kept the default mipmapped min filter on one-level cubes: incomplete. `gl4es_realize_cubes(units)` (called before each translated draw for the program's cube units) applies them and clamps `GL_TEXTURE_MAX_LEVEL` to the levels present.
   - Native DXT uploads set `GL_TEXTURE_MAX_LEVEL` on the face target (invalid) instead of `GL_TEXTURE_CUBE_MAP`.
   - **The driver's cube binding was 0 by draw time** while gl4es believed the cube bound (`LINDBERGH_CUBE_BIND_LOG`): gl4es binds a cube map "immediately" and never re-checks. `gl4es_realize_cubes` binds it again before the draw. This was the one that made the close-ups black.
   Dead ends, for the record: shadow bias (0.05 changed nothing), reprojection of the shadow pass (framebuffer 21 is already drawn with the game's own projection), 16-bit depth (gl4es stores multiview depth as `DEPTH24_STENCIL8`).
6. `stereo.c`: after a whole-screen copy of a drawn world, the colour bit of the next eye clear is dropped (VT3 clears before compositing its depth-of-field copy, and that composite is left out in stereo). In the working build, but not tested on its own.
7. **Court select looked skipped; menus as a tilted card.** VT3's menu panels are 3D, and `stereo.c` knew no VT3 menu states (`0 menu states of 0 found`: its list is House of the Dead 4's `Game<Name>` functions), so menus were drawn as world - a small tilted card, or black. VT3's screens are `usr...Loop` objects whose `exec()` runs once a frame (found with `LINDBERGH_HUD_LOG=1` against captures: `usrMenuCharLoop` character select, `usrAcselectLoop` mode select, `usrAcLoadLoop` Road to the Championship + versus card, `usrAcEntranceLoop` the court flyover, `usrAcGameLoop` play...). The profile now lists them (`vr.menu_states` / `vr.play_states`, full symbols; parents like `usrAcLoop` in neither), and `watch_states` takes a game's own list. Two more pieces were needed:
   - `menu_state()` allows 8 frames since a menu loop last ran (was 1): the GL thread asks a frame or two behind the game, and the frame flipped between flat and world every few frames. A play state still ends it at once.
   - Road to the Championship draws its panels, clears the colour, then copies the screen for a composite that stereo leaves out: on a flat frame, a colour clear of the screen after anything was drawn is dropped (`g_eye_draws`), so the panels stay. Menus lose the composite's depth-of-field blur; drawing the composite on flat frames gave black (the blur chain through the offscreen targets has never been checked on the Quest).

---

## 7.5 The headset settings panel on a lever cabinet (2026-11-09)

The left controller's menu button (or the other hand's upper button held for a second) opens the settings panel. On a lever cabinet (`game_profile.joystick`, VT3) it now:
- **Can be used:** while it is open, the right controller points at it with a beam (no gun model, sight or flash) and the trigger chooses. Before, lever mode skipped the aiming code, so the panel opened but nothing could be clicked.
- **Shows only rows that apply:** no sight, laser, crosshair, gun model, gun hand or dual wield.
- **Frame rate counter** (was "Show stats"): the frame rate readout, as before.
- **Arcade overlays: Shown / Hidden** (only for games that can hide them, `g_arcade_overlay_hooks`), saved as `overlays on|off` with the other settings and applied live. `LINDBERGH_ARCADE_OVERLAYS=0` hides them for a run (also on macOS). For VT3 (`hle_sega.c`):
  - `credit::draw` skipped: CREDIT(S), INSERT COIN(S), PRESS START BUTTON, TO START / TO CONTINUE.
  - `CCardSlotWindowManager::window_open`, `window_slot`, `window_slot_usecard` not called: the card reader's "card cannot be used" messages and icons at the top. Turning overlays back on brings these back with the next window the game opens.
  - The card information board (`ab_card_info`, a table of 3 `{font, text}` at `+0x14`): its texts ("CREDIT 0", "INSERT COIN(S)") pointed at an empty string, the originals put back when shown.
  - Not hidden: the character select's "insert your card into the slot" prompt (part of that screen).
  - Dead ends: `CCardSlotWindowManager::draw` is a stub; scaling the card board to zero with `AbHandle::setMatrix` did not hide it, and doing it every frame crashed.

The panel is now 20 rows (`XM_ROWS`, `XM_H` 824).

### 7.5.1 Pages for a game with a world mode (2026-11-11)

For Virtua Tennis 3 (`g_world_capable`: `hle_sega.c` sets it when `_sRender::setProjectCameraMatrix` and `camera::gameRoutine` resolve) the panel has three pages; other games' panels are unchanged.
- **Main:** Mode (Classic (2D screen) / Immersive (3D world); "(on restart)" while it differs from the running mode), Restart now (only then; `reset_game`, the activity's `restartGame`), Advanced settings (Classic) / (Immersive) > (the saved mode's page), then the shared rows without Frame rate counter, Arcade overlays and Replays.
- **Classic advanced:** < Back, Replays, Point cutaways, Arcade overlays, Shadow quality (Standard 1024 / High 2048 / Very high 4096, on restart), Frame rate counter, Restore Classic defaults (two pulls), Close.
- **Immersive advanced:** < Back, Camera closer (0-30 m = `dolly` 0-300 game units in 50s), Step back (5 / 6 / 7 / 8 m = `back` 50-80, default 6 m; since 2026-11-11 late, was 0-12 m in 3s - an older vr.cfg value is read as the nearest choice), Camera height (2 m lower / 1 m lower / Standard / 1 m higher / 2 m higher = `immersive.height` -20..20, default 0; `LINDBERGH_VT3_HEIGHT`), Replays, Point cutaways, Arcade overlays, Sky (Stadium / Painted / Off, 2026-11-11; the Stand height row is gone), Shadow quality, Frame rate counter, Restore Immersive defaults, Close.
- On the running mode's page every row but Shadow quality applies at once (`world_mode_update`, then `g_replays` / `g_arcade_overlays` / `g_cutaways`; dolly, back and sky are read per draw); the other mode's page is saved for its next run (hint "Applies when ... mode runs."). A row whose env variable is set (`LINDBERGH_REPLAYS`, `_ARCADE_OVERLAYS`, `_VT3_CUTAWAYS`, `_SHADOW_SCALE`, `_VT3_DOLLY`, `_VT3_BACK`, `_VT3_SKY`, `_VT3_IMMERSIVE` for Mode) shows the run's value with "(env.txt)" and ignores clicks.
- Code: `xr_world_panel.c` (pure, like `xr_panel.c`: `xw_page_rows`, `xw_items`, `xw_choose`, `XW_*` items; tested by `tests/test_xr_world_panel.py`). `host_xr.c` keeps the page in `XwState wpanel` and lists rows in `menu_ids[]` as `XP_` ids or `XP_COUNT + XW_x`; the `XP_` enum stays the shared list the Vulkan host shows (`XP_COUNT == XM_ROWS`). The panel opens on the main page.
- `cfg` in `host_xr.c` holds only the stored settings; env overrides live in `world_mode.c`. Before, `cfg_load` copied `LINDBERGH_REPLAYS` / `LINDBERGH_ARCADE_OVERLAYS` into `cfg`, and the next click saved them - how a test's `replays off` got into the player's vr.cfg. `LINDBERGH_XR_SET` keys are likewise saved as the file had them.
- The hint line is now "Point and pull the trigger. Menu: close." - the old one was 47 characters and the panel fits 42 (it was cut off at "cl").
- Test switches: `LINDBERGH_XR_FAKE_MENU=1`, `LINDBERGH_XR_MENU_PAGE`, `LINDBERGH_XR_MENU_HOVER`, `LINDBERGH_XR_MENU_DUMP=1` (the painted panel as a PPM beside the game), `LINDBERGH_XR_MENU_CLICKS=<frame>:<row>,...` (see `ai_docs/README.md`).

## 8. Immersive Mode (world mode working, 2026-11-09)

**Status:** Immersive mode draws the match as a 3D stadium in front of the player at the broadcast camera's angle, pushed back in depth (HOTD4-style world mode). Confirmed in the headset. Chosen with the panel's Mode row (vr.cfg `mode immersive`, from the next start) or `LINDBERGH_VT3_IMMERSIVE=1|0` in `env.txt` for a run. Default Classic (the flat screen).

**Mode and its values (`world_mode.c`, 2026-11-11).** Which hooks to install is decided at registration (`hle_register_sega` -> `vt3_jumps`), before the headset host loads vr.cfg (`xr_init` -> `cfg_load`), so `world_mode_init(g_world_capable)` is the first call in `vt3_jumps`: on headset builds it reads vr.cfg itself (the `xr_settings` parser on a scratch copy; desktop: env only) and resolves every value env > vr.cfg > the mode's default, logged once as `[world] mode immersive (vr.cfg) dolly 200 (default) back 60 ... replays off (vr.cfg) overlays off ... cutaways off ...`. `LINDBERGH_VT3_IMMERSIVE=1` pins Immersive, `=0` Classic, unset or empty leaves it to vr.cfg `mode`; a game without the camera symbols is always Classic unless env says otherwise. Classic keeps the old keys (`replays`, `overlays`) plus `classic.cutaways`, `classic.shadow`; Immersive has `immersive.replays/.overlays/.cutaways/.dolly/.back/.sky/.shadow` (defaults off/off/off/200/60/stadium/2048; `.sky stadium|painted|off`, an old `on` reads as stadium; the old `immersive.stand_y` is ignored and no longer written, 2026-11-11). Every former `getenv("LINDBERGH_VT3_IMMERSIVE")` (hle_sega.c, stereo.c, arbprog.c) is `world_mode_immersive()`; `effective_projection`'s dolly and back and `sky_on` read live getters, the shadow-map scale is read once at the depth target's creation (1024 = 0, as the game makes it). The mode itself stays as started; switching live is Phase B (backlog).

**Camera view reframed, In the world off the panel, point-start snap (T13 / T14, 2026-11-12, owner).** Rows Replays / Point cutaways are Off / Flat screen / Camera view (a stored `world` reads as camera; env `world` stays for tests). Camera height defaults to Medium (+1 m; stored values kept). **Camera view** (`stereo.c` `rv_frame_shot`): the view looks along the game camera's own aim, pitch included, from a point moved forward toward its target (`camera+0x44`, passed with the camera from the main thread with the players' roots): the target at depth d, the eye at d - k (d - d tan(game half fov)/tan(eye half fov)), k = `LINDBERGH_VT3_REPLAY_CLOSE` (default 0.6), at least 2 m from the target, not below 0.5 m, not through the net, not within 0.8 m of a player (backed off, or past a player right at the camera); the close-up 2.8 m from its target. Fixed per shot (default: no motion at all inside a shot) or `LINDBERGH_VT3_REPLAY_FOLLOW=1` (re-placed every frame); `LINDBERGH_VT3_REPLAY_LEVEL=1`: standing height 1.7 m, level gaze. A replay's start dip holds black 16 frames (covers the game's intro wipe). `LINDBERGH_VT3_REPLAY_PAN` is gone. Per-shot log: camera, aim, lens, target depth, eye, distance, players in view, the target's player in view. macOS (`LINDBERGH_VT3_REPLAY_TYPE=cycle`, new test switch on `camera::setReplayType`): all seven replay types and the close-ups, 17 shots, the target's player in view every time (eye 2.5-16 m from the target). The washed-white near ground was seen only from the seat (In the world), not in Camera view - left. **T14, the glitch at each point's start:** `usrAcStartLoop` puts the court camera 9-11.5 m nearer and ~3 m lower (eye (0, 80, 253) from ~(0, 110, 330-360), the same aim) two frames into the loop, then it glides back over ~1.5 s (`LINDBERGH_VT3_CAMMODE_LOG=3` logs every world camera note); on TV the start's cross-fade hid it, in VR it was a jump toward the court and a glide back. Now the drawn eye is eased from where it was to the camera over 60 frames (smoothstep; `[vt3] frame N: court camera snapped 11.5 m (point start) - eased over 60 frames`; only a pure move of 2-20 m with the aim unchanged; `LINDBERGH_VT3_START_GLIDE=0` off); a far-end height change is eased over 60 frames too.

**Panel and viewpoint, T12 (2026-11-12, owner).** The panel (`xr_world_panel.c`, `xr_menu.c` `xm_paint_modes`) starts every page with two big buttons, **Classic** and **VR** (VR = Immersive; vr.cfg `mode immersive` and the env names stay), the chosen one filled green and ringed, hover ringed gold; under them one line: "Classic runs now - VR after a restart" (or "... runs now", or "(set by env.txt)") and Restart now as the first row. They are the pages' first two rows (`XW_MODE_CLASSIC`, `XW_MODE_VR`), so scripted clicks count them as rows 0 and 1; `xm_row_at_modes` maps the pointer. Choosing a mode on an Advanced page shows that mode's page. VR's viewpoint is fixed: 200 units closer and 50 back (5 m) - no Camera closer / Step back rows, `immersive.dolly` / `.back` are no longer read or written (`LINDBERGH_VT3_DOLLY` / `_BACK` for tests). **Camera height** is Low / Medium / High (`immersive.height 0|10|20`; an older negative value reads as Low). **The far end:** the court camera does not keep the human near - after a change of ends 1P plays from the far side (macOS `round0`: change of ends at 6815, player z -129 with the camera at +253). `hle_sega.c` `vt3_far_end_note` compares the human player's root z (`player+0x18`+8, the player with `+0x08 <= 3` in `[g_pTennis+4]`) with the court camera's eye z on each mode-1/2 camera, latches only outside the rally (the arcade loop not GameLoop) after 10 notes - measured: at frame 6818, in the StartLoop after ChangeendLoop - and hands it with the camera to `stereo_vt3_far_end`; the height is then High whatever the row says (`LINDBERGH_VT3_FAR_HIGH=0` off; an env height wins). Log: `[vt3] frame N: your player at the far end ... - VR camera height High`.

**Replays and point cutaways in the world (T10, 2026-11-12; design `ai_docs/research/immersive-replay-cameras.md`).** Immersive's Replays and Point cutaways rows are **Off / Flat screen / In the world / Camera view** (vr.cfg `immersive.replays|.cutaways off|flat|world|camera`, an old `on` = flat; defaults stay off; Classic keeps On / Off, always flat). For a run: `LINDBERGH_VT3_REPLAY_VIEW` / `LINDBERGH_VT3_CUTAWAY_VIEW=flat|world|follow` (`camera` = `follow`; a view variable alone turns it on; `LINDBERGH_REPLAYS` / `_VT3_CUTAWAYS` alone pin on/off with the flat view, so test runs do not depend on vr.cfg; `flat` is the kill switch - today's behaviour). How: `vt3_cam_job` (GL thread, in order with the draws) hands each world camera with its mode to `stereo_vt3_view`. The last court-camera view (mode 1/2, not the first frame of a mode - **the game's first frame in a new camera mode still carries the old view**) is the anchor. In camera mode 6 (replay) / 7 (winner close-up) with a world view, `eye_projection` appends `C` to every world draw's eye matrix (not the pixel camera's, near > 10): **In the world** `C = V_anchor inv(V_cam)` - the stadium stays where it was, the players and ball replay in front of you, dolly / step back / height along the anchor's up; **Camera view** `C = L inv(V_cam)`, `L` a level view at the game camera's eye along the shot's heading (taken at each shot's first frame; `LINDBERGH_VT3_REPLAY_PAN=1` heading every frame, `=2` the camera's own view), no dolly / back / height, and a dip to black (3 frames, clearing over `LINDBERGH_VT3_REPLAY_FADE`=12 frames; `rv_fade_draw` at the frame's end, over the HUD too) at the start, at each new shot (the camera jumps >10 m or >20 deg in a frame, or `replay::reverseFrame` - counted on the worker thread, handed on by the main thread's next camera) and at the end. While corrected, the long lens makes nothing flat (`stereo_vt3_camera`, the cut's first-draw rule, `g_zoom_frames`, the per-draw zoom class) and the HUD screen keeps the court camera's lens. The painted sky follows by itself (its matrix is the eye's times the game view). The close-up's 1-in-10 split screen (`camera::initWinlose`'s first `getRandMT_U32() % 10 == 0`) is moved off 0 while cutaways are in the world (thread-local flag; also wins over `LINDBERGH_VT3_SPLIT=1`; log `split-screen close-up left out`), and the big-point serve close-up stays left out (`match::isHeatup` answered no as with cutaways off). With cutaways Off the win/lose loop is still skipped by the `setMode` wrap. Test switch `LINDBERGH_VT3_VIEW_AT=<frame>:<replay view>,<cutaway view>` (both views from that frame). Quest (S1/S2, 2026-11-12): A keeps the stadium exactly in place; B's dips and level corner views work; the game's replay intro wipe shows as a translucent plate in the world, and the near ground is washed white in replay frames (glare) - not fixed. Logs: `[rview]` (start / shot / back), `LINDBERGH_VT3_CAMMODE_LOG=2` per frame (replay type, shot, fov, lens, eye, dips). Measured (macOS logs): replay lens 3.0-3.2 for type 4 (a low camera ~1 m high behind a baseline), others from points ~8 m high at the corners; close-up lens 2.8-9.6, three world camera notes a frame. **The macOS desktop stereo (`LINDBERGH_STEREO=1`) is no picture test for VT3**: left eye small, right eye without world in every view, baseline included - use the headset's `LINDBERGH_GAME_SHOT`.

### 8.0 What the camera turned out to be
- **Two cameras per frame**, read with a wrap of `_sRender::setProjectCameraMatrix` (`hle_sega.c`, immersive only), which leaves the current scene manager's projection at `+0x5c` (4x4, row-major) and view at `+0x2c` (3x4):
  - **Broadcast camera** (set 3x a frame, first): lens 3.20261 / 5.67128, near 1, far 3000, pitched ~19 deg, ~345 units back; its view moves every frame. **Every match draw** goes through it with a rigid model matrix at real court positions (court at the origin, net posts x +-60, players z ~+-117) or a flattened one (ground shadows).
  - **Pixel camera** (set ~9x a frame): lens 1.45455 / 2.57576, near 800, far 1050, no turn, 989.092 back - exactly 1360x768 at its screen plane. HUD, scoreboards, sprites.
  - The "n 800 / f 1050 slab" seen earlier was the pixel camera, never the court.
- **Root cause of the misplaced court:** the match shaders build the position by rows (`DP4 result.position.x, R0, c[0]` - `program.local[0..3]` are the matrix's **rows**), the HUD ones by columns (MUL/MAD). `arb_env_projection` read every draw by columns, so match draws were taken apart transposed. Fix: `position_by_rows()` marks such programs (`pos_kind` 3) and their locals are read transposed (only for `vr.camera_in_locals`, i.e. VT3).
- Tried and **turned off** (`LINDBERGH_VT3_GAME_CAM`, test only): handing every draw the broadcast camera's exact projection (=2), and sending pixel-camera draws to the HUD (=1). Both blacked out the whole picture on the Quest (render targets and full-screen layers took them too).
- Also under immersive: scene culling widened to the eyes (below), a wider eye depth range in `stereo.c`, and the stereoscopic-screen experiment (`LINDBERGH_STEREO_DEPTH`, `u_eyex`).
- **Culling and frame rate (2026-11-11).** `_sCamera::isVisible(sphere)` tests a bounding sphere against the camera's six planes (`this+0xb8`, 16 bytes each, inward). Its only caller is `_sTree::addScene`, for trees with their culling flag (`+0x40` bit 0), from `uva::SceneObject::addScene`: in whole arcade runs it is never called (`LINDBERGH_VT3_CULLLOG=1`), and `LINDBERGH_FRAMEMAP` shows the same 283 draws with it off, the game's or widened - the "~37 fps with culling off" was the sky, which arrived at the same time. Now: `h_vt3_is_visible` (default, `LINDBERGH_VT3_CULL=2`) tests the world camera's spheres (the camera with a plane facing the game camera's forward) against both eyes' frusta (`stereo_vt3_cull_planes`: `eye_projection` x the game view, each side pushed out `LINDBERGH_VT3_CULL_MARGIN` degrees, default 20), other cameras keep the game's test; `=0` all visible, `=1` the game's. The cost was the sky's fragment shader: 5 octaves of value noise with 4 sine hashes each at 2064x2208 per eye. It now reads a 256x256 random texture (one filtered fetch per octave at the smoothstepped position, lattice wrapped at 256) and skips the clouds below the horizon. Unattended (`LINDBERGH_GPU_TIME=1`: timer queries from frame end to frame end, logged every 300 frames, frames over 20 ms listed): GPU 4.6 -> 3.2 ms a frame in a match (sky off 2.8), frames over 25 ms per 5 s 44 -> 3, 53.7 -> 57.6 fps, rallies at 60.0. The unworn headset does not present, so these are 60 Hz-paced, uncomposited numbers.
- Diagnostics: `LINDBERGH_MVP_DUMP=<frame>` logs every draw's `program.local[0..3]` (`[mvp]`) and every camera set (`[cam]`) around that frame; solve `M = inv(P*V) * MVP` offline to see which camera a draw used.

- **Closer camera:** the world-mode viewpoint is moved in along the broadcast camera's view by `LINDBERGH_VT3_DOLLY` game units (default 200 of its ~345 from the court; a unit is ~0.1 m), `stereo.c` `effective_projection` (`out * T(0,0,+d)`). The narrow lens (~20 deg down) made the stadium a small model far off.
- **Shadows in world mode:** ground shadows are drawn with a flattened model matrix, which the lens read takes apart wrong (their depth off, so the eyes and the dolly put them metres from the feet). A draw made through the broadcast projection exactly - row 3 + A x row 4 of its matrix = (0 0 0 B) - now gets that projection, shadows included (`arbprog.c`; `LINDBERGH_VT3_GAME_CAM=3` turns it off).
- **Replays switch:** headset menu **Replays On/Off** (`vr.cfg` `replays on|off`, `LINDBERGH_REPLAYS=0` for a run). Off, a wrap of `replay::isReplay_point` answers no; the match goes straight on (checked on the Quest, `forty` scene).
  - **The match's end with Replays off (2026-11-10).** At first the match never ended: after the last point it went on into new games. Between points `usrAcPassLoop::exec` picks the next screen through `mtrLoopManager::setMode` on `[[g_pTennis]+0x104]+0x14`: mode 7 (replay) when `isReplay_point` says so, else mode 8 (win/lose animation, then the next point). `isReplay_point` always answers yes once the match is over (`match::isMatch`, `match+0xd6`, set with event bit 0x1000 of `match+0x1c` by `match::setEvent(12)`), and in arcade mode **only the replay loop's end** (`usrAcReplayLoop::exec`) carries a finished match on: it clears bit 0x1000 and sets mode 0xa (game set and match) - or, when `[g_pTennis+0x24]` is 0 or 2 and `match::isWinner(vs::getGame_master_plno())` is false, 0xb (stats) with `sound::stopSoundAll`. The win/lose loop never looks at the bit. Fix: with the switch off, a wrap of `mtrLoopManager::setMode` (`h_vt3_set_mode`) catches the pass loop's mode 8 (return address 0x08086C6D) while bit 0x1000 is up and makes the replay loop's choice instead. The closing replay is skipped, the match ends at once. `LINDBERGH_VT3_FLOWLOG=1` also logs each `setMode` of the arcade screen loops.
  - **The only way into a replay (2026-11-11).** Replay playback (`usrAcReplayLoop`, `replay::start` / `exec`, camera mode 6) is entered only from `usrAcPassLoop::exec`'s `mtrLoopManager::setMode` at return address **0x08086B17**, and only when `replay::isReplay_point` (0x0810E18E) says yes. The mode depends on the loop manager: arcade (`[g_pTennis+0x104]+0x14`) mode **7**, attract demo (`[[g_pTennis+0xfc]+0x18]+0x14` or `+0x24`, `checkMode(1)`) mode **6**, challenge (`[g_pTennis+0x108]+0x14`, `checkMode(4)`) mode **9** (unreachable in practice per the static analysis: challenge mode does not come this way). Other `setMode` sites of note: the pass loop's mode 8 / win-lose (0x08086C6D), the replay loop's own exit (0x0808A6A7). Long runs with Replays off (macOS `round0` + `LINDBERGH_VT3_WIN=1` 400 s, two matches; Quest Immersive `round0` 330 s, two matches; macOS attract demo 5 min) had no `ReplayLoop` and, in Immersive with cutaways off, camera mode 1 from the first serve to game set and match. The "replays" still seen with Replays off were the point close-ups (camera 7 win/lose, camera 5 big-point serve) - the **Point cutaways** switch. Since then, in `h_vt3_set_mode`, a replay requested from 0x08086B17 with Replays off is logged (`[vt3] ... replay requested with Replays off`, not redirected), and a failed `isReplay_point` override or `setMode` wrap is logged as a WARNING. The `setMode` wrap is installed with `LINDBERGH_FORCE_REPLAY=1` too (the `replay` scene gets the cutaways-off and match-end logic).
  - **Replays switched off during a replay.** `usrAcReplayLoop::exec` (0x0808A538) asks `playerManager::check_skip_button_winner()` each frame of a replay (return 0x0808A850); yes and the count (`this+0x1c`) past `getCnt_skip_max()` (15) - and no card being written (`isCard_writing`, else `cardManager::isFinishedCue(1)`) - calls `replay::restore()` (0x0810DE7C, on `[g_pTennis+0x90]`) and the loop takes its usual exit. `h_vt3_skip_winner` answers yes for that caller while `g_replays` is 0 (log `[vt3] frame N: replay playing with Replays off - skipped`). Quest, `prize` Immersive, scripted panel click on the Immersive page's Replays row: replay started 3015, click 3030, replay ended 3032, game set and match -> stats -> next round as usual.

- **Point cutaways switch (2026-11-11).** After each point the arcade loop runs `usrAcWinloseLoop` (mode 8, camera 7 `camera::winlose`, split screen ~1 in 10): its `exec` counts `this+0x20` and leaves at 121 - or earlier when `playerManager::check_skip_button_winner()` (a player's shot button, 0x81682e6) is true and the count is past `playerManager::getCnt_skip_max()` (`+0x78`, 15, set in the constructor), and then only when no card is being written (`isCard_writing` / `cardManager::isFinishedCue`) and not in challenge mode (`checkMode(4)`). Both ways take the same exit (next point mode 3, change of ends 9, game set and match / stats, `hud::resetResult`). `usrAcWinloseLoop::init` starts the centre board (the "POINT 1P / 15-0" plate, `ab_game_info::startCenterInfoBoard`) and `finish` erases it. With `g_cutaways` 0 a wrap answers the skip check yes when called from the win/lose loop (return address 0x0808E6CB; the start, game-set-and-match and replay loops ask it too and are left alone): the loop lasts 17 frames instead of ~121, the plate flashes for that time, the score box has the new score. `LINDBERGH_VT3_CUTAWAYS=0|1` for a run; the mode settings set it (Classic on, Immersive off).

- **Step back:** after the dolly the viewpoint steps back level with the ground (`LINDBERGH_VT3_BACK`, default 60 game units), along the camera's forward with the world's up taken out (up read from the game's view in the hook), so the player stands behind the court at the same height. **Camera height** then moves the viewpoint along the world's up (`LINDBERGH_VT3_HEIGHT` game units, panel row, live; default 0 = the camera's own - estimated, not measured, at ~5 m above the court after the dolly: the broadcast camera sits at ~(0, 112, -340) and the dolly runs down its view). The HUD anchors re-solve through the same eye matrices, so the serve meter follows.
- **Player shadows in world mode: fixed (2026-11-10).** The ground shadows are a **screen-space mask**. Each frame the game clears the screen to black (alpha 0), draws the planar shadows into it (vertex 141 / 137, fragment 114: GPU-skinned, flattened along the light, stencil NOTEQUAL 1 / REPLACE so each pixel is darkened once), copies the screen into a texture (`glCopyTexSubImage2D`, 1360x768), clears depth and draws the stadium and court. The ground programs read the mask back projectively (`TXP` on unit 1) at a coordinate built in the vertex program from the **game camera's clip position** (`texcoord[6]` = clip.xy offset by w/2, scaled). In world mode the copy holds the first eye's image (`gl4es_multiview_copy` of layer 0, squeezed to the game's 1360x768), so the lookup missed: the shadow lay where the eye's picture had it at the game camera's screen position - metres off, and moving with the head. With the eyes on the game camera (`LINDBERGH_VT3_SAMECAM=1`) the two screens agree, which is why that test was right.
  - Fix (`arbprog.c`, world mode only, `LINDBERGH_VT3_SCREENFIX=0` turns it off): every translated vertex program passes `lg_eye0`, its point's clip position in the first eye (`u_reproj[0] * clip`); a fragment program whose unit holds a whole-screen copy at link time (`stereo_screen_copy_map`, recorded at each copy in `stereo.c`: the eye's screen 0..1 -> the copy's texture coordinates; part of the link key) reads it at `lg_eye0`'s screen position instead of the game's coordinate. Right for both eyes: the copy is the first eye's picture and `lg_eye0` is where the first eye drew that point.
  - How it was found, for the record: `LINDBERGH_STOP_AFTER=<n>` (each frame, the screen's draws after the n-th left out: the eyes as they stood then) showed the shadows drawn at the feet on black and gone once the court was drawn; `LINDBERGH_FRAMEMAP=<frame>` (every call of one frame) showed the screen copy right after them. Earlier notes here that "no screen copies happen during play" were wrong - the copy-log check missed it - and the vertex-placement theories (points at infinity, camera nudge) were wrong too: the CPU emulation (`LINDBERGH_EMU_VP`) showed the planar shadows are correct world geometry.
  - Diagnostics kept (all off by default): `LINDBERGH_VERT_DUMP=<a>[-<b>]` (`[vert]`/`[vmat]`: positions back to the world, matrices, raster state, class, reprojection), `LINDBERGH_EMU_VP=<vp>`, `LINDBERGH_STOP_AFTER`, `LINDBERGH_SKIP_FP`, `LINDBERGH_NO_STENCIL`, `LINDBERGH_NOBLEND_FP`, `LINDBERGH_VT3_SAMECAM=1|2`, `LINDBERGH_VT3_CULL=1`, `LINDBERGH_VT3_NEAR`, `LINDBERGH_VT3_GROUND=1`, `LINDBERGH_NO_CLEAR_INJECT=1`, `LINDBERGH_LIST_LOG=1`. Reading locals: a literal the program declares in a slot overrides the stored value (`arb_vp_local` checks `lit_loc`).
- **Blotches on shirts, crowd and banners in world mode: fixed (2026-11-10).** The eyes' near plane was 0.05 x the camera's (`stereo.c` `effective_projection`, deep branch). The game layers decals and multi-pass surfaces with polygon offsets of up to ~2800 depth steps (`glPolygonOffset(-0, -70 ... -2816)`); a depth step's size in the world grows as the near plane shrinks, so at a 20x closer near plane every offset reached 20x further and passes bled through each other in patches. The game's own near plane (`LINDBERGH_VT3_NEAR`, default now 1; ~10 cm) is clean. Found by elimination: the eye's lens alone (`LINDBERGH_VT3_SAMECAM=2`, which keeps the game's near plane) was clean, the shadow map only coloured the patches (skipped, they showed stale content in the same shapes).

- **Stands raised (2026-11-10) - removed 2026-11-11.** The stands looked squashed because the upper tiers were not drawn at all (next item); the x1.5 stretch of the stand programs (`LINDBERGH_VT3_STAND_Y/_FROM/_FP`, `immersive.stand_y`, the Stand height row) is gone. Program ids for the record: fragment 158 = **the crowd cards** (vertex 121), 229 / 230 = **the light-mapped stadium meshes** (vertex 228) - checked on the Quest with `LINDBERGH_SKIP_FP` (158: every spectator gone; 229,230: the stadium shell gone). They were first read as 158 seating / 230 crowd with `LINDBERGH_FP_SOLID=9`.
- **Sega's whole stadium in Immersive (2026-11-11).** Every venue's stadium model (`resource/model/field/S_<court>..._stage_TQ_NY.efo`) has the trees `DHPTH`, `GAME_NO`, `GAME_NORTH`, `GAME_SHOW`, `GAME_SOUTH`; `field::createTree` (0x080FFF8E) gives each a type byte in `[field+0x3c][i]` (SOUTH 1, NORTH 2, NO 3, else 0) and `field::draw` (0x080FFB86) leaves out type 3 - the upper tiers, roof, walls, light towers, town, upper scoreboards, the sky dome and the sun - and the end stand behind the camera while the camera mode (`[[g_pTennis]+0x38]+0x38`) is 1 or 2, the court camera; every other camera draws all. The crowd cards (`CAudience2DManager`) do not follow that rule, so they floated over seats that were not drawn. `h_vt3_field_draw` (hle_sega.c) zeroes the type bytes (count: the scene database's tree count, `0x081A7718(field+0x2c)`) for the length of the call and puts them back, in Immersive only, checked per call (`LINDBERGH_VT3_STANDS=0` keeps the game's cut); installed whenever the game is world-capable. On the Quest (`prize`, round 0, Ita): no floating spectator, light towers and the town behind the far end, the stand behind the viewer drawn (`LINDBERGH_VT3_VIEW_TURN=180`), the same in both eyes; 103 more draws in the frame (fp 230 +86, 229 +11, the dome vp 129 / fp 180 one). **Not yet measured** (headset unplugged): GPU cost, other venues, a full match. Test switch `LINDBERGH_VT3_VIEW_TURN=<yaw>[,<pitch>]` (degrees): the eyes turned about the viewpoint (yaw left about the world's up, then pitch up) - what an unworn headset cannot look at.
- **Flickering ads on the boards: fixed.** The ad artwork is a decal at the board's depth; from the game camera the two round alike, through the headset's reprojection not, and the board won about half the frames (CITIZEN's letters, the far board's Düsseldorf Open and IBM logos). In world mode a blended or alpha-tested, depth-tested draw without an offset of the game's own gets `glPolygonOffset(-1, -32)` (`LINDBERGH_VT3_DECAL_OFFSET`, default 32 depth steps, ~2 cm at the far boards; 2 was not enough there). The game sets its offset before every draw, so nothing leaks. Checked on six consecutive frames (`LINDBERGH_GAME_SHOT=<f>,1,1`).
- **Shadow map 2048x2048** in world mode (`LINDBERGH_SHADOW_SCALE`, default 2 there; depth-only targets of their own size only). The shadow pass's tile viewports scale with the target; the soft compare reads the size it has. The players' ground shadow is the screen-space mask (eye resolution already); this sharpens the self-shadowing.
- **Sky:** the game draws none (the broadcast camera never looks up). World mode draws its own (`stereo.c` `sky_draw`, original: a blue gradient and fair-weather clouds from value noise) at the frame's first depth-only clear of the eyes, after the shadow mask is copied and before the stadium; each pixel's direction goes back to the world through the inverse of that eye's projection and the game camera's view, so it stays put as the head turns. `LINDBERGH_VT3_SKY=0` turns it off.
- **Gaps in the far upper stands - explained 2026-11-11.** The far upper tier was not drawn (`GAME_NO`, above); its crowd showed through gaps of the invisible depth-only tree `DHPTH`. With the stadium drawn the seats are there.

- **HUD vanishing on head movement: fixed.** The near-plane fix above (the game's own, 1x) also hit the pixel camera, whose near plane is 800 with its screen at ~989; with the viewpoint moved in 200 units, a turn of the head took the HUD sprites (and the startup logo screen) behind it. Cameras with a near plane over 10 units keep the old 0.05x (`stereo.c`). While at it, the world-mode tweaks are kept off 2D screens: the decal offset skips the flat picture, HUD draws and the pixel camera's sprites (`stereo_draw_not_screen`; the far board's logos still get it), the stand stretch and the screen-copy lookup apply to world draws only (`stereo_draw_world`; the lookup falls back to the game's own coordinate otherwise). Checked with `LINDBERGH_XR_FAKE_YAW=25` in a match: score, speed and 1P panels all there.
- **Sky's blocky patch: fixed (2026-11-11).** The hash `fract(sin(dot(p, (127.1, 311.7))) * 43758.5)` lost all precision once p reached the hundreds (fifth octave; mediump floats in a GLES fragment shader): hard rectangles high in the sky. The noise is now a 256x256 random texture read once per octave (see "Culling and frame rate"), coordinates wrapped, `highp`. `LINDBERGH_VT3_SKY_PITCH=<deg>` (test) turns the sky down by that much about the game camera's right, so a game shot shows the zenith.

- **The sky in Immersive: Sega's own dome, all round (2026-11-11 night).** Each venue's sky is `GAME_NO_SKY_Polygon` (in the `GAME_NO` tree, drawn since the whole-stadium change): **one draw, a whole hemisphere of radius ~4000 game units** round the court origin (32 segments x 8 rings, apex at y 4000; Ger3M's reaches down to y -780), drawn with vertex program 111 (plain matrix: locals 0-3) and a texture-times-colour fragment program (118 on round 0, 122 on rounds 1 and 2 - the fragment ids are not stable across venues), unit 0 the stadium's atlas (4096x1024 or 4096x512) with uv 0..0.5 x 0..0.5: the 2048x512 panorama (`S_<court>_B_sk_sky_NY_tga`) wrapped **once round the full 360 degrees** (u 0 at azimuth -125 deg, v 0.499 at the horizon to 0.001 at the apex). Depth test LEQUAL, no depth write. Fragment program 180 (vp 129) is the **SUN** sprite, a small quad at ~(860, 350, -1740), not the sky. The game draws the dome at its far plane (3000): on rounds 1/2 with the projection's depth row equal to w (z = w), on round 0 at its true depth (~4000, beyond the far plane - the broadcast camera, pitched down 19 deg with a 10 deg half-height, never sees the sky at all). The eyes are reprojected from the game's clip space (`u_reproj`), so only a cone in front survived: the "lavender sky in front, deep blue painted sky round it" the owner saw (the lavender is the panorama's own colour). Fix (`arbprog.c` `vt3_sky_fix`, uniform `u_sky`; Immersive only, every plain-matrix vertex program): a vertex more than 3000 from its model's origin (no other model reaches that; the stadium ~2000) gets its true clip depth back before `u_reproj` (`z = B - A w`, A and B the game projection's depth terms `g_game_world_P[10]`, `[14]`), so the reprojection finds the real point on the dome, and after it is pinned to the eye's far plane (`z = 0.99999 w`), never clipped; with Sky Painted or Off (`u_sky.w < 0`) the dome's vertices are collapsed (no wedge, no band). Stadium no longer draws the painted sky behind it (`LINDBERGH_VT3_SKY_FILL=1` puts it back, test only); Painted draws ours alone; Off leaves the game's clear colour. `LINDBERGH_VT3_DOME=0`: as the game draws it (the old cone). Found with a vertex dump of the draw's own indices (the generic `LINDBERGH_VERT_DUMP` reads the whole vertex buffer and its world transform cannot invert a z = w projection - it prints inf). Checked on the Quest with `LINDBERGH_XR_FIXED_HEAD=1` and `LINDBERGH_VT3_VIEW_TURN` lists on rounds 0 (Ger3M Duesseldorf - not Ita3F as inferred before), 1 (Aus1F, under the roof opening) and 2 (Fra1F Paris): one continuous sky at yaw 0/60/90/120/180/-90 and pitch 0/40/70/89; both eyes identical in the sky (0 px disparity at pitch 70: 400 m away); Off black above the stands, Painted ours only. Pictures for the owner: `~/Desktop/Claude/vt3-sky/`.
- **Floating crowd: hidden (2026-11-10) - superseded 2026-11-11.** The crowd cut (`LINDBERGH_VT3_CROWD_CUT`, `_CROWD_FP`, `lg_world`) acted on fragment 230, which is the stadium, not the cards: it discarded the far end's light masts and stand tops above y 55 and left every floating card in place (Quest, `LINDBERGH_VT3_CROWD_CUT=0` vs default). Removed: with the whole stadium drawn every card stands on a real seat.

- **Start-up screen (Quest).** The ~30 s of black at launch is ~8 s of loading with no game frame at all, then ~20 s of the board's own boot drawn black (macOS shows the same). `host_xr.c` now shows quad layers 2 m ahead in `local_base` from a static swapchain holding the picture (`games/vt3/src/splash_art.c`, deflated RGBA, drawn by `quest/tools/vt3_splash.py`; the runtime reads it through weak symbols, so other games have none): the panel, two digit cells and a stretched cell for the bar. Until the game's first frame a thread of its own runs `xrWaitFrame`/`xrBeginFrame`/`xrEndFrame` with only those layers (the first `xr_frame_begin` starts it, the second joins it); after that `xr_frame_end` adds them over the game's projection layer, sampling the left eye every 8 frames (16x16 blit + read) until its mean passes 40 twice. The countdown is the last start's time in `startup_seconds` (cwd, the game folder; first start 35 s). `LINDBERGH_SPLASH=0` turns it off. `adb exec-out screencap -p` shows the composited view (quad layers included), unlike `LINDBERGH_XR_SHOT`.
- **Start-of-match cameras: fixed.** Three views before the broadcast camera: the fly-by intro (`camera::initUva`, also between games; skipped in world mode, `LINDBERGH_VT3_SKIP_UVA=0` keeps it), then an "overview" and a "top-down" view that were world mode's own: `camera::gameRoutine` (the only camera routine running then, `LINDBERGH_VT3_CAMROUTINES=1`) writes the broadcast pose into the scene camera from the first frame (eye +0x78, target +0x84 of `[camera+8]`; `[camview]` with `LINDBERGH_VT3_CAMFIELDS`), but for ~3 s the game sets no world camera through `_sRender::setProjectCameraMatrix` (only the pixel camera; `[cam]` with `LINDBERGH_MVP_DUMP`), so `g_game_world_*` was unset and the per-draw lens guess produced those views. Now, when the game has not set the world camera for 3 frames, a gameRoutine hook builds one (look-at from that eye and target, the broadcast lens 3.20261 / 5.67128, n 1, f 3000) and passes it to `arb_note_projection` (`LINDBERGH_VT3_FEEDCAM=0` turns it off). **The skip only for modes 4 and 8 (2026-11-11):** `camera::reset` starts a fly-by (`initUva(-1)`, the animation at `camera+0x228`) for camera modes 4 (`usrAcEntranceLoop`), 8 (`usrAcChangeendLoop`), 0xa (`usrAcStatsLoop`, `usrChResultLoop`, `usrChTotalResultLoop`), 0xe (`usrAcEndingLoop`) and 0x10 (`usrPlayerintroLoop`), and the result slate's `exec()` ends when `camera::isUvaFinished()` - true with no animation at `+0x224`. Skipping every `initUva` ended the slate after ~4 frames (600 in Classic); the hook now reads the mode at `camera+0x38` and calls through for all but 4 and 8. Dead ends: the routine's frame counter (+0x1e8, resets every point), the global block at 0x850e280 (constant), camera attaches (none then). Hooking `camera::procMain`, `ab`, `calcParameter` or `setLook_down` with the generic wrap hangs or stalls the game.

- **HUD items at 3D points: serve meter and 1P marker (2026-11-10).** Two faults, both world mode only.
  - *The meter's last second.* `hud::drawServePower` (0x810f28e) draws an AB gauge (`ab_game_info` +0x14, frame and effects +0x18) through the pixel camera; `setFrame(power*100)` fills it by a **scale along y** of its model matrix. `arb_env_projection` took the matrix apart as a rigid camera: the y lens came out as the pixel camera's times the scale. Below ~0.85 the shape test rejected it (last good lens - looked right); from 0.85 to 1.0 it was **taken**: the reprojection undid the scale, so the bar was drawn full height and shifted down out of its frame, and that lens was stored as the "good" one, so later fallback draws (the fall back after full) were wrong too. Measured with `LINDBERGH_VT3_SERVELOG=1` (`[servelog] ... pixel-camera draw ... lens read ... TAKEN`) and full-size frames through a serve. Uniform scale pops of other HUD sprites (x1.1, x0.5, x2) were likewise drawn unscaled. Fix (`arbprog.c`): `arb_note_projection` keeps the whole pixel camera (`g_game_pixel_P`, `g_game_pixel_view`), and `arb_env_projection` tests each draw for an exact match against it (`cam_exact`, the test the match camera already used: row 3 + A x row 4 = (0 0 0 kB), A -7.4, B -6720) before the match camera; a match gets the pixel projection and leaves the last good lens alone. `LINDBERGH_VT3_PIXCAM=0` turns it off.
  - *Placement.* `hud::getScreenPosFrom3DPos` (0x8110f2e; hidden return pointer at argument 0, popped by it - `retl $4`; this, then the point) projects a point through the game camera (`[g_pTennis+0x38]`, virtual +8: projection at +0x34, view at +4) to the HUD's units (x/w*480 (x4/3 when `tennis::bWide_`), y/w*360); the HUD item's matrix is G (0x850e280, identity in practice) x T(x, y, 0), drawn through the pixel camera, whose plane is ~989 ahead. The eyes see that plane from the dollied, stepped-back viewpoint, so the meter (latched once per serve, `hud+0x60`) and the 1P marker (`hud::setPlayerIcon`, every frame) sat below the feet at the near end and ~1.6x too far from the middle at the far end. A wrap (`hle_sega.c` `h_vt3_screen_pos`, immersive only, `LINDBERGH_VT3_HUD_ANCHOR=0` off) calls the original, then `stereo_vt3_hud_anchor` (`stereo.c`): per eye, where the eye sees the point (`eye_projection` of the game camera - `effective_projection`'s world part, now a state-free function so the game thread can ask), and the HUD (x, y) whose point on the pixel plane the same eye sees there (two linear equations through G, the pixel view and `eye_projection` of the pixel camera); the eyes' answers averaged. Also used by `ab_game_info::initPlayerIcon`, `hud::drawChallenge_result_ball` and `hud::drawGameInfoPlate` (overlap avoidance), which now get the same eye-correct positions. The meter is not re-anchored per frame: no drift seen during the toss.
  - Tools: `LINDBERGH_VT3_SERVELOG=1` (per frame of a meter: player, state, power, latch, game vs anchored position; each pixel-camera draw whose lens read is off), `LINDBERGH_VT3_SERVESHOT=<n>[,<from>]` (full-size game shots through n serves of 1P, see `ai_docs/README.md`), `VT3_EXTRA_KEYS` in `scripts/vt3-repro.sh`.

- **Black frames at camera cuts: fixed (2026-11-11).** At a cut (win/lose close-up, change of ends, serve camera, game set and match, match intro) the game blends the screen it captured (`fade::execCapture`: a whole-screen 2D draw of a screen copy into fb 0). `stereo.c` classed it HUD, and a HUD draw makes its target `g_hud_fb` for the next frame; with fb 0 as "the HUD's target" none of the next frame's world counted (`g_scene_draws` 0, the draws classed HUD), so no sky was drawn and the colour clear before the depth-of-field composite was kept (it is dropped only after scene draws and a screen copy): two fully black frames, HUD included. In world mode fb 0 never becomes the HUD's target. Found with `LINDBERGH_BLACK_LOG=1` (each frame's left eye averaged from the eye array; a black frame gives the next one the draw log, now with the facts `target/menu/zoom/flat/offscreen`, and a game shot) and `LINDBERGH_CLEAR_LOG=2`.

- **Between points, one steady camera; clean cuts where cuts remain (2026-11-11).** With **Point cutaways off** (Immersive's default) nothing between points changes the camera any more. Before, the win/lose loop still ran ~17 frames (camera 7, the winner's close-up, plus the cross-fade) and on every big point (game / break / set / match point) `usrAcStartLoop::init` put the camera on the server (camera mode 5, ~150 frames, a flat close-up in Immersive). Now (`hle_sega.c`): the `mtrLoopManager::setMode` wrap turns the pass loop's mode 8 (return 0x08086C6D) - and a point replay's end (0x0808A6A7) - into what `usrAcWinloseLoop::exec` picks at its end in the arcade path: change of ends (9) on `match::isTiebreak_changeend()` or the match's change-ends bit (0x400 of match+0x1c, cleared as it does), else the next point (3); a card being written, a versus game asked for (`vs::isReq_vs_game`), the attract demo (`checkMode(1)`) and a decided match (0xa/0xb, handled first) are left to the game. The win/lose loop's init/exit only serve the close-up (camera mode 7 saved at +0x40 and restored, celebration poses, the centre "POINT" plate, the crowd's cheer animation, glare); the score box has the new score. A wrap of `match::isHeatup` answers no for the start loop's questions (0x080856D3, 0x08085775, 0x08085AB2), so a big point starts like any other (`restartPlusAb`, camera 1; no heat-up poses or music). Flow and camera log over a `round0` + `LINDBERGH_VT3_WIN=1` run: Pass -> Start (or Changeend -> Start) at every point, camera mode 1 from the match's start to game set and match, no flat frame. Cutaways on: the original sequence.
  For the cuts that remain (cutaways or replays on, game set and match, the result slate) three faults made the in-between frames: (1) the world camera was handed to `arb_note_projection` straight from the game thread, which sets it after a frame's draws for the next frame while the GL thread may still be drawing the frame before - the last frame before a cut was taken apart with the new camera (a turned, distorted frame); it now goes through the GL queue (`vt3_note_projection`, `glq_job`; `LINDBERGH_VT3_CAM_QUEUE=0` the old way). (2) Flat or world followed the zoom rule (lens > 8 held 6 frames): ~6 distorted world frames into each close-up, the first court frame after one flat. The game thread now also sends each world camera's mode (camera+0x38) and lens in the queue (`stereo_vt3_camera`): in the two frames after a camera mode change the frame's first draw into the eyes decides (long lens: flat from that draw; short: world), and a lens crossing the limit within a mode (the serve camera zooming in) sets the next frame (`LINDBERGH_VT3_CUTFLAT=0` off, `LINDBERGH_VT3_CUTLOG=1` logs). (3) The cut's cross-fade (`fade::execCapture`: the captured screen drawn back over ~30 frames) hung as a small flat picture in the world; on world frames a 2D draw into the eyes of a whole-screen copy taken in an earlier frame is left out (`screen_copy_stale`; `LINDBERGH_VT3_CAPTURE=1` keeps it), so world cuts are hard cuts. Camera modes in Immersive: see `ai_docs/README.md`.
- **The fade before every serve, the court from above at a match's start, Classic's stray 3D frames (2026-11-11, owner's worn reports on `9d68719`).** Captured every frame both eyes (`LINDBERGH_GAME_SHOT=<f>,1,0,<last>`, `LINDBERGH_SHOT_BOTH=1`), strips in `~/Desktop/Claude/vt3-bugs/`. (1) **Immersive, "an image within an image" before every point:** with Point cutaways off the game goes Pass -> (Changeend ->) Start without a camera mode change, and `usrAcStartLoop` (~30 frames) cross-fades from its picture of the last frame with a whole-screen 2D quad, fragment program 54, reading screen copies 34 and 40 on units 0 and 1 - both copied again every frame of the fade, and neither on the active unit. The stale-copy check above missed it, so the old picture hung small in the middle of the court, fading. Now any 2D draw into the eyes that is classed HUD (or fill) on a world frame and reads a whole-screen copy on any unit its fragment program reads (`arb_fp_units`: the `texture[n]` in the program's source; fixed function: unit 0) is left out (`stereo.c`, after the draw log; `LINDBERGH_VT3_CAPTURE=1` keeps it; `LINDBERGH_VT3_CUTLOG=1` logs each multi-unit HUD draw and its units). Quest `prize`: left out exactly over each StartLoop (1950-1978, 2467-2496, ...) plus the single fade-start frame at a point's end and at the slate; nothing else. (2) **Both modes, the court from above at each match's start:** the frame after `usrAcEntranceLoop::init` draws the stadium through the menus' camera (lens 1.45, from high above) before the intro's camera is set; macOS shows the VS screen there, the headset showed the stadium from above for a frame. `usrAcEntranceLoop::init` (wrapped for VT3 in both modes; with `LINDBERGH_VT3_FLOWLOG=1` the flow log's wrap does it instead) has `host_xr.c` hold the next frame: at its start the eyes (the last frame) are copied aside, before it is shown they are put back (`LINDBERGH_VT3_HOLD=0` off; `[xr] frame N: held`; game shots and the black log see the held frame). Checked every frame both eyes on the Quest: the held frame is the one before (the game's own black in Immersive, the VS screen in Classic), in both modes, at every match start; owner confirmed worn (submodule `2c3f4f4`). **Quest driver quirk:** a `glBlitFramebuffer` into layer 1 of a 2D array (`glFramebufferTextureLayer`) wrote nothing - layer 0 copied, layer 1 kept its old content, framebuffer complete, no error - so the copies use `glCopyTexSubImage3D` per layer. (`gl4es_multiview_copy_layers`, the per-eye shadow mask's copy, blits into layer 1 the same way.) (3) **Classic, a top-down/wide 3D view for a split second when the match starts:** Classic's picture was flat only because the scoreboard's long-lens draw kept the zoom count up; for the first 8 frames of each match's intro (before that draw) `stereo.c` made them world frames - a wrong wide view, then six black frames (the fly-by drawn into the HUD's target, of which a world frame shows nothing). VT3 in Classic is now always flat (`flat_all` defaults on for a world-capable game in Classic; `LINDBERGH_FLAT_ALL=0` the old rule). Since then `LINDBERGH_BLACK_LOG` (which reads the eye array) sees nothing in Classic: judge Classic by game shots.

- **Texture LOD bias on GLES (2026-11-11, both modes).** Virtua Tennis 3 sets `GL_TEXTURE_LOD_BIAS` -1 on its crowd, ad boards and more; GLES lacks it, so on the Quest those were a mip level blurrier than on the desktop. gl4es keeps the value per texture (`gltexture_t.lg_lod_bias`, `gl4es_texture_lod_bias(unit)`, quest/gl4es.patch) and `arbprog.c` passes it as `texture2D`'s bias argument (`u_lodb[16]`, uploaded only when a bias is set or was). Default on for VT3 only (`world_mode_capable()`), `LINDBERGH_LOD_BIAS=0|1`. Quest, fixed head pose: crowd / boards edge energy +13..25%, text steady frame to frame. (The gl4es patch also carries `gl4es_multiview_copy_layers`, used by the per-eye ground shadow mask, not yet committed.)

### 8.0.1 Open in immersive mode
scoreboards float in the scene at court level instead of a HUD panel; stadium scale/distance not tuned; panel switch flat / world (Mario Galaxy recomp style) not built yet.


Today the match is drawn as a flat picture on a screen in front of the player (the 2D "theatre" path in `stereo.c` / `host_xr.c` `xo_draw_screen`). The goal is to make it feel like being in the game.

### 8.1 Depth: draw the world in 3D
- Stop treating VT3's camera as a zoom. `stereo.c` reads a lens of ~29 because `vr.camera_in_locals` hands it the **combined** MVP (projection x view x model), not the projection alone. Split it: per draw, the projection is the part constant across the frame's world draws; or find where the game builds `g_transform_mat` (the Cg parameter set through `cgGLSetMatrixParameterfc`/`cgSetMatrixParameter`) and take the projection and view there, before they are multiplied.
- With projection and view separate, render the world per eye with the headset's projection and the eye offset applied in view space (what `stereo.c` already does for hotd4's env-held camera), so the court has real depth; keep the HUD on a panel.
- Scale: a tennis court is 23.77 m; pick a world scale (profile `vr.scale`) so the court is life-size or a "table-top" miniature, both worth trying.

### 8.2 Camera control
- Phase 1, head-tracked: the game's camera stays the anchor; head pose adds rotation/translation on top (look around the stadium, lean over the net).
- Phase 2, free / chosen camera: replace the game's view matrix with one the player picks: behind own player (third person), first person at the player's eyes (needs the player's position: read from game memory or from the player's skinned-model root bone in the bone palette), umpire chair, broadcast. The game still renders by its own camera for culling, so a wider view may need culling turned off or the far player's draw forced.
- Comfort: the broadcast camera moves on its own; in VR that should be smoothed or snapped, with the option to lock it.

### 8.3 In-headset menu
A runtime menu (the XR overlay already draws a settings panel, `host_xr.c` `menu` / `xo_draw_panel`, opened from the controller) with:
- Display mode: **Flat screen** (today) / **Immersive 3D** / **Table-top**.
- Depth strength (IPD scale / world scale), screen distance and size for flat mode.
- Camera: Game camera / Head-tracked offset / Third person / First person / Umpire, plus recenter.
- Comfort: camera smoothing, vignette on camera cuts.
Settings persist through `xr_settings_save` like the existing ones; switches that need a program variant (depth on/off) can rebuild at the next frame.

### 8.4 Order of work
1. Fix the shadows (Section 7.4 #4).
2. Separate projection and view from VT3's MVP; get the court drawn in stereo with depth in the existing pipeline, fixed game camera.
3. Menu entries for flat / immersive / table-top and scale.
4. Head-tracked camera offset; then chosen cameras.
