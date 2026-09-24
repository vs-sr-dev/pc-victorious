# Audio: the AX mixer, and the way to the speakers

Session 6. Music, voices, sound effects and the Bink movies' sound, all
through one path: the game's Wwise drives the SDK's AX library, AX hands the
DSP a command list every 3 ms, the port mixes it in C++, and the AI DMA's
blocks go to an SDL3 audio stream.

```
Wwise (recompiled) ──► AX library (recompiled): voices = parameter blocks in MEM1/MEM2
                              │  every AI interrupt: __AXOutNewFrame → __AXNextFrame
                              ▼
        mail 0xBABE0000|size, command list address      (hw.cpp: the DSP's mailbox)
                              ▼
                  ax.cpp: the AX micro-code in C++ ──► 96 samples of L/R into the SDK's buffer
                              ▼
        AI DMA block starts (hw.cpp, host clock) ──► audio.cpp: SDL3 stream, 32 kHz
```

## Who uses AX

Wwise uses the DSP's **hardware voices**: `CAkVPLSrcNode::GetHardwareVoices`
acquires AX voices, `CAkSrcBankADPCM` and `CAkSrcFileADPCM` play DSP-ADPCM
from banks and streamed files, `SetPitch` sets the resampler, and the mix
buses run their effects as AX aux callbacks on the CPU
(`CAkVPLMixBusNode::SetInsertFx`). The Home Button menu has its own AX
synthesiser (`__HBMSYNNoteOn`). So the mixer has to be the DSP's, voice by
voice; there is no single stream to catch.

## The command list of this SDK

Read from `__AXNextFrame` (`801083B0`), which writes the list:

| Command | Arguments | |
|---|---|---|
| 0x00 | studio address | set up the mixing buffers: a start value and a delta per buffer |
| 0x01 / 0x02 / 0x03 | address | add / subtract / add-and-subtract last frame's surround into L/R (by output mode) |
| 0x04 | first PB | run the voice list |
| 0x05 / 0x06 / 0x07 | volume, out, in | aux A / B / C: send the bus to the CPU's effect, mix back what it returned |
| 0x08 / 0x09 | volume, 6 addresses | the same for Dolby Pro Logic II |
| 0x0A | threshold, release frames, table | the compressor |
| 0x0D | 4 addresses | the Remotes' speakers |
| 0x0B / 0x0C | volume, surround, L/R | the output (0x0C in DPL2 mode) |
| 0x0E | | end |

This is what Dolphin calls the "new" AXWii micro-code, and Dolphin's HLE
(`AXWii.cpp`, `AXVoice.h`) is the reference for what each command does.

## The parameter block

0x140 bytes per voice (`__AXSyncPBs` copies them with that stride). The
layout changed twice across Wii SDKs; this one was read from the stores of
`AXSetVoice*` into the voice's copy of its PB (at `AXVPB+0x28`):

| PB | Field | Checked by |
|---|---|---|
| +0x10 | running | `AXSetVoiceState` (+0x38) |
| +0x12 | stream flag | `AXSetVoiceType` (+0x3A) |
| +0x14 | mixer: 12 volume/delta pairs | |
| +0x52 | depop values | |
| +0x6A | volume envelope | `AXSetVoiceVe` (+0x92) |
| +0x6E | addresses: loop flag, format, loop, end, current | `AXSetVoiceLoop` (+0x96) |
| +0x7E | ADPCM: coefficients, gain, predictor/scale, history | |
| +0xA6 | resampler: ratio, fraction, last four samples | `AXSetVoiceSrc` (+0xCE) |
| +0xB4 | ADPCM loop context | |
| +0xBA | low-pass | |
| +0xC2 | biquad | |
| +0xD6 | Remote speaker: on, mixer control, mixer, depop, resampler, filter | `AXSetVoiceRmtOn` (+0xFE) |

So: **no per-millisecond update field**, and a **full biquad** before the
Remote fields. In Dolphin's terms, the variant that only skips `updates`,
with the new filters.

## The mixer (`ax.cpp`)

Per voice and frame, 96 samples:

* **The accelerator** fetches from main memory (physical addresses: MEM1,
  or MEM2 with bit 28): 4-bit DSP-ADPCM with its header byte every eight
  bytes, 8- and 16-bit PCM scaled by the gain. At the end address it loops
  (with the loop context, or keeping the history for streams) or stops a
  one-shot voice.
* **The resampler**: 4-tap polyphase with the DSP ROM's coefficient table,
  or linear, or none; the phase and the last four samples carry over.
  The table is `dsp_coef.bin` (Dolphin's free one, in the same folder as the
  boot ROM's fonts); without it the resampler is linear.
* **The volume envelope** (unsigned on the Wii), the one-pole **low-pass**,
  the **biquad**.
* **The mix**: each bus L, R, S of main and aux A/B/C, on or off, with or
  without per-sample volume ramps; the Remote's speakers at 6 kHz through
  their own resampler and filter.

Then the aux buses go to the CPU and come back one frame later, the
compressor applies its gain table, and the output writes main L/R clamped to
16 bits, **right then left**, where the SDK's AI callback will DMA it from.

## To the speakers (`audio.cpp`)

At each AI DMA block the runtime reads the block's samples from memory and
puts them in an SDL3 audio stream at the AI's rate (32 kHz).

* **The two clocks.** The AI's pace comes from the host clock (the clock
  thread), the device's from its own crystal. The stream starts with 20 ms
  queued and its playback speed is nudged, at most ±2%, to hold that level:
  measured at 20 ± 3 ms, speed 1.0000 ± 0.0001. Heard sound stays 20 ms
  (plus the device's own buffer) behind the game's audio clock.
* **Late frames.** When the guest is too busy to take the AI interrupt in
  time (a heavy load), AX has not refilled the buffer and the AI would play
  the previous 3 ms again: a buzz. Such a block is not played (one in a
  ten-minute run).
* `--no-audio` leaves the device closed; `WIIKIT_AUDIODUMP=file.wav` writes
  everything played; `WIIKIT_AUDIODBG=1` reports the queue and the speed.

## Checks

* By ear, a whole play session: the Bink logos' music, the menus, the
  background music, the voices (the series' own cast), the rhythm game.
* By numbers, before listening: the first minute's dump is silent, then
  music-like (the difference between samples a tenth to a half of the
  signal, where noise gives 1.4).
* **The Remote's speaker**: no voice has used it so far. Wwise is told the
  speaker cannot take data (`WPADCanSendStreamData`), so nothing is lost.

## The rhythm game and latency

The rhythm game's beats come from Wwise, which counts the AX frames it
renders; its judging windows are 32 ms (Victorious), 64 (Good) and 128
(Okay). What the player hears and sees comes later than the game counts:
the audio queue (20 ms) and the device, and the renderer's queue of up to
two frames. Playable; the best grades want a press a hair early.
Compensating would mean taking the output latency off the press time where
`CDebugRhythmGameUI::debugRender` makes it (`05-open-questions.md`).
