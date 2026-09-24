# TODO — session 6

Phase 5 of the plan: audio. The game plays with the mouse, the rhythm game
included, but in silence: AX runs on the DSP HLE and mixes nothing. The goal
is **music and voices**, and a rhythm game that stays in sync with what is
heard.

1. **The AX mixer.** The game's Wwise drives AX voices (DSP-ADPCM and PCM,
   their parameter blocks in main memory); the DSP HLE already answers the
   micro-code's mails. Mix the voices on the host (sample-rate conversion,
   volume envelopes, the main and aux buses), and play the result through
   SDL3's audio at 32 kHz. Dolphin's AX HLE is the reference.
2. **The audio clock.** The rhythm game's beats come from Wwise
   (`soundBeatCallback`), which counts the AX frames it renders. Once sound
   is heard, AI's DMA pace and the host's audio device must agree, or the
   beats drift from the music (`05-open-questions.md` 10).
3. **Streams**: the Bink movies' audio and any streamed music (Wwise's
   stream manager on DVD).
4. **The Remote's speaker**: Wwise's speaker manager sends it a stream;
   `WPADCanSendStreamData` says no. Decide whether those sounds go to the
   main mix instead.
5. **Side work, as time allows**: SYSCONF (language, aspect ratio, sound
   mode, `05-open-questions.md` 14); how the second player joins the
   rhythm game (`05-open-questions.md` 4); a frame from Dolphin next to the
   classroom's; the renderer's cost at `--scale 2`.

Nothing from the renderer's list (fog, Z textures, TMEM preloads) showed up
in twelve minutes of E1A1: it stays reported on first use.
