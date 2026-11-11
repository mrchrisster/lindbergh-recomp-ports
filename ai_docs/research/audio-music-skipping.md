# Music plays skipping / not clean (investigation, 2026-11-11)

Owner's report after a full match worn (build before `1b1988b`): "music
plays skipping / not clean". Build worker, macOS runs plus unattended Quest
runs (submodule `fa83fd6` and later).

**Summary for the owner**
1. Found and fixed: the music skipped about a third of a second, about three
   times a second, on every platform (macOS too). The game streams music
   through a small ring (0.34 s). At the end of each lap our sound code
   reported the play position as "end of the ring" instead of "start of the
   ring". The game took that for an empty ring and wrote a whole new lap over
   the audio still waiting to play. So each lap one lap of music was thrown
   away, and the decoder ran at about 2.4x the speed it was heard.
2. After the fix, the music written equals the music played (1.01x), on
   macOS and on the Quest. The heard music is a continuous copy of the
   decoder's output.
3. Not found: no sign of the other usual causes. The device was never late,
   the stream never ran dry, the mixer never waited on a lock, and no file
   read was slow. Those were checked on macOS and in unattended Quest runs.
   The headset was not worn, so the display was not running at 120 Hz.
4. Also improved: effects recorded at 22/44.1 kHz were played back by picking
   the nearest sample (rough, aliased). They are now interpolated.
5. Still to check by ear: the game's sound effects push the mix over full
   scale at times (up to 3x on macOS, 4x on the Quest), and a soft limiter squashes them. That may
   sound "not clean" in loud moments (a cheering crowd plus hits). It is
   measured but not changed (see 4.4).

## 1. The audio path

```
ADX file (AFS on disk) --fread 1 MB--> CRI file system thread
  --> SJ (stream joint) --> ADX decoder (ADXT_ExecServer)
  --> LBRNA (Lindbergh renderer: lbrna_Process -> playing_proc / trans_proc)
  --> SEGAAPI ring buffer in guest memory (16-bit stereo 48 kHz, 65536 bytes
      = 16384 frames = 341 ms), SEGAAPI_UpdateBuffer after each write
  --> hle_segaapi.c mix() on the SDL audio thread
      (CoreAudio on macOS; OpenSL ES on the Quest, SDL 2.32.10, 2 buffers;
       48 kHz float stereo, 1024-frame blocks = 21.3 ms)
  --> soft limiter (knee 0.8) --> player volume / mute --> device
```

- **Who drives the decoder:** CRI's ADXM threads, real host threads
  (`hle_pthread.c`). `lxsync_thrd_proc` sleeps 16.67 ms (`usleep(0x411a)`)
  and broadcasts a condition. `adxm_vsync_proc` waits on it and runs
  `SVM_ExecSvrVsync` twice (decode, `LBRNA_Process`). `adxm_mwidle_proc`
  runs the idle/file servers. **The game's frame rate does not pace the
  music.** The game thread only issues Play / Stop / volume calls.
- **The ring protocol** (`lbrna_*` in the ELF, disassembled):
  `lbrna_update_play_position` reads `SEGAAPI_GetPlaybackPosition` into
  `+0x4c`, adds the distance moved (mod size) to the played total
  `+0x58/0x5c`. `lbrna_get_num_free_in_buffer`: play `+0x4c` vs write `+0x48`.
  If play < write, free = size - write (to the ring's end). Otherwise free =
  play - write. **The writer fills up to the play position**, so the ring is
  normally full and holds one lap (341 ms) of future audio.
  `lbrna_trans_proc` converts the decoder's samples to 16-bit and writes
  min(free, available) at the write cursor, then calls `UpdateBuffer`.
  `lbrna_fill_proc` writes silence at the stream's end. `prep_proc` resets
  the position to 0, clears the ring and pre-fills it.
- **Effects:** 16 mono 5.4 s buffers (criau synth voices) at 22050 / 44100 /
  48000 Hz, set per sound with `SetSampleRate`. Four 341 ms stereo rings
  (flags 0, looping); only the first carried music in these runs.
- **Mixer** (`hle_segaapi.c`): walks every playing buffer straight out of
  guest memory and advances `pos` (frames, double) by rate / 48000 per
  output frame. Looping voices wrap at the loop end. The game's position
  read is `pos * frame_bytes`, unlocked, so it moves in 21.3 ms steps.

## 2. The bug (proven on macOS, same code and block size on the Quest)

The wrap test sat at the *top* of the per-frame loop: a voice wrapped only
when the next frame was read. The music ring is 16384 frames = exactly 16
mixer blocks at step 1.0, so at the end of every 16th block `pos` was left
equal to the ring size. Between blocks lbrna read position **65536**: play
>= write (0, just wrapped), so free = 65536 - 0 = the whole ring. It wrote
32 KB at 0, then (next tick, play 4096 < write 32768) 32 KB more to the
ring's end. Every lap it overwrote the full lap of audio queued for
playback.

SEGAAPI log (`LINDBERGH_SEGA_LOG=1`, new `update` lines), before:
```
update 0x22f84480 at 61440 +4096, mixer at 65536, lead 65536
update 0x22f84480 at 0 +32768,    mixer at 65536, lead 65536   <- "empty"
update 0x22f84480 at 32768 +32768, mixer at 4096, lead 61440   <- rest of the lap
update 0x22f84480 at 0 +4096,     mixer at 4096,  lead 65536
```

Fix (`fa83fd6`): wrap a looping voice right after the block if it ended on
its loop end, and never report the loop end from `GetPlaybackPosition` (it
is the loop's start). `LINDBERGH_SEGA_POS_WRAP=0` restores the old
behaviour. Other games: any looping ring whose length is a multiple of 1024
frames at its own rate hit the same bug.

## 3. Measurements

### 3.1 macOS (`scripts/vt3-repro.sh round0 mac ...`, muted; the dump is
taken before mute)

| | before | after |
|---|---|---|
| decoder output written / played (ring writes vs mixer advance, `update` log) | 55.4 s / 23.3 s = **2.38** | 90.8 s / 90.1 s = **1.01** |
| position read as ring size | 187 times in 23 s | 0 |
| music written in a 150 s run (`AUDIO_DUMP_WRITES`) | 246 s | 126 s |
| played music continues the decoder's output (341 ms pieces, 40-70 s, `cont.py`) | 2 of 60 | 40 of 60 (4 jumps; the rest quiet or ambiguous) |
| clicks in the streamed rings alone (`scripts/wav_glitches.py`, from 20 s) | 140 / min | 77 / min (the decoder's own output: 97 / min, i.e. music transients) |
| clicks at mixer block boundaries (position mod 1024, last 1/16) | 164 of 453 | (not clustered) |
| starvation events, late device blocks | 0, 0 | 0, 0 |
| stream lead min (how far the game had written ahead) | 299 ms of 341 | 299 ms |
| mixer time per 21 ms block / lock wait | <= 0.06 ms / <= 0.01 ms | same |

Regression: Classic `prize` on macOS, slate 3482 -> 4083 and 8477 -> 9078
(601 frames), next rounds start.

### 3.2 Quest (unattended)

APK with `fa83fd6` + `77875a4`, `prize`, Immersive,
`LINDBERGH_AUDIO_KEEP_ON_PAUSE=1 LINDBERGH_SEGA_METER=1 LINDBERGH_SEGA_LOG=1
LINDBERGH_AUDIO_DUMP=/sdcard/VirtuaTennis3/vt3_Lindbergh/mix.wav
LINDBERGH_AUDIO_DUMP_STREAMS=1`. Backend: `openslES`, 1024-frame blocks:
the same lap/block alignment as macOS.

**Pacing in these runs:** the headset was not worn. The XR session went
1 -> 5 -> 6 -> 1 (stopped) and focus was lost before the audio opened, so
the game was paced at 60 fps by the clock. There was no 120 Hz display and
no compositor load. Without `KEEP_ON_PAUSE`, SDL paused the OpenSL device
~2 s after it opened (one health line, a 2 s WAV). So the numbers below
show the mixer and stream under the game's own load, not under the worn
120 Hz load.

| | old (`LINDBERGH_SEGA_POS_WRAP=0`) | fixed |
|---|---|---|
| music ring: written / played | 102.4 s / 46.8 s = **2.19** | 71.7 s / 70.0 s = **1.02** |
| second ring (voices): written / played | 23.1 / 16.0 = 1.45 | 15.4 / 14.7 = 1.05 |
| position read as ring size | 332 + 70 times | 0 |
| clicks in the streamed rings, 30-140 s | 196 / min | 124 / min |
| starvation events | - | 0 in 133 health periods |
| device late blocks / max callback gap | - | 0 / 27.1 ms (block 21.3) |
| stream lead min | - | 320 ms of 341 |
| mix time / lock wait, max per block | - | 0.84 ms / 0.22 ms |
| `[io] slow read` (> 50 ms) | none | none |
| mix peak before the limiter | - | up to 4.0; worst 10 s: 21.5% of samples over 0.8, 11.5% over 1.0 |

Regression on this APK: Classic `prize` - slates 3988 -> 4589, 8994 ->
9594, 13979 -> 14580 (601 frames), next rounds start. Immersive `prize` -
slate 7534 -> 8135 (601). The first slate, 3173 -> 3533, is cut short by
the menu script's `z` taps, which run to frame 3600 (known). `[world] mode
immersive (env) ... shadow 2048 (vr.cfg)`, `[sega]` lines as before.

## 4. Hypotheses checked

1. **Device underruns** (OpenSL ES buffer too small, the audio thread late):
   new counter `device N late of M blocks (gap max ...)`. macOS 0, gap max
   23.4 ms (block 21.3). Quest: see 3.2. The lock is held for <0.1 ms, so the
   game thread cannot block the mixer.
2. **Refill paced by game frames (120 Hz display, 55-58 fps):** ruled out by
   the code. The ADX server runs on its own 16.67 ms `usleep` thread, not on
   the game loop. With a ring of 341 ms and a refill every 16.7 ms, the
   refill would have to stall for ~300 ms to starve. New counters
   `starved N events` / `stream lead min` stayed at 0 / 299 ms. A slow
   `/sdcard` (FUSE) read stalling the file thread is the remaining way to
   starve. The new `[io] slow read` log (reads over 50 ms) logged none on
   either platform. The music is read in 1 MB `fread`s.
3. **Resampling:** the music ring is 48 kHz = the output, so it is not
   resampled. Effects at 22.05 / 44.1 kHz were nearest-sample. They are now
   linear (`LINDBERGH_AUDIO_INTERP=0` gives the old behaviour). Loop points:
   only the position bug (above).
4. **Clipping:** the mix peaks at 1.3-3.1 (macOS) and up to 4.0 (Quest)
   before the limiter during play. Up to 15% (macOS) / 21% (Quest) of the samples in a
   10 s window are over 0.8, and up to 8% / 11% are over 1.0, so the soft knee works hard in loud
   stretches. The cause is the effects (crowd, hits, voices) summed at full
   send level; the music ring is at volume 0.25 (peak 0.25-0.5). Not
   changed: the original board's level is unknown, and a gain change would
   alter the balance the owner has heard. A per-game `sound_gain` (LGJ uses
   0.4) is the knob if the owner hears distortion in loud moments.
5. **Position jumps:** the reported position moves in 21.3 ms steps (one
   block). lbrna only needs it to be monotonic within a lap. The bug above
   was the one bad value.

## 5. Diagnostics added (all in `hle_segaapi.c` unless noted)

- `[sega-api] health: ...` every 10 s when anything went wrong, every 2 s
  with `LINDBERGH_SEGA_METER=1`. Fields: starved events / ms (the mixer
  played a streamed ring past what the game had refilled), stream lead min,
  device late blocks and max callback gap, lock wait and mix time, the
  limiter's load (% over 0.8 / 1.0).
- `[sega-api] mixing at 48000 Hz, 1024-frame blocks (openslES)` names the
  backend.
- `LINDBERGH_AUDIO_DUMP=<path>`: the final mix (after the limiter, before
  volume/mute) as a WAV, header refreshed every period.
  `LINDBERGH_AUDIO_DUMP_STREAMS=1`: also `<path>.streams.wav` (the streamed
  rings only). `LINDBERGH_AUDIO_DUMP_WRITES=1`: `<path>.writes.<buf>.wav`,
  what the decoder wrote, in write order.
- `LINDBERGH_SEGA_LOG=1`: also each `CreateBuffer`'s format/size and each
  ring `update` with the mixer's position and lead.
- `hle_libc.c`: `[io] slow read: N ms for B bytes` (over
  `LINDBERGH_IO_SLOW_MS`, default 50), `LINDBERGH_IO_LOG=1`,
  `LINDBERGH_IO_DELAY=<ms>[,<every>]` (test: a slow disk).
- `host_sdl.c`: `LINDBERGH_AUDIO_KEEP_ON_PAUSE=1` (test). An unworn headset
  pauses the Activity, and SDL pauses the audio device ~2 s after start, so
  without this an unattended run has no mixer.
- `scripts/wav_glitches.py`: level, clicks (second-difference outliers),
  dropouts, repeated blocks in a dump.

## 6. Dead ends / limits

- The click detector also fires on the music's own transients (the
  decoder's output alone gives ~97 / min). Use it to compare runs, not as an
  absolute count. Clustering by position mod 1024 (block boundaries) or mod
  16384 (ring laps) is what pointed at the bug.
- Unworn, the Quest session stops at state 6 -> 1 and the game is paced at
  60 by the clock: no 120 Hz display, no compositor. Audio timing under the
  real worn load is inferred, not measured.
