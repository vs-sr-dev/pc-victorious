# TODO — session 8

The six phases of the plan are done: the game boots, draws, plays with the
mouse, sounds, and fits a PC screen. What is left is breadth and proof.

1. **Playing on**: past the first episode, watching the log for what the
   renderer reports on first use (fog, Z textures, TMEM preloads) and for
   anything the audio skips; the saves across a restart.
2. **Dolphin as the oracle**: a frame from Dolphin next to the port's, the
   same scene, the same settings (16:9); then differential runs of the
   recompiler's single-precision rounding (`05-open-questions.md` 11).
3. **The language**: which of `--language`'s seven the US disc really
   carries (the `wii_nunchuk_*.tga` hint at seven), and whether the game
   follows SYSCONF or its own save.
4. **Rhythm latency compensation** (`05-open-questions.md` 10), if a harder
   song asks for it: delay the beat callbacks the game receives by the
   output's latency.
5. **A release shape**: one folder a player can run from, what it needs
   (their own disc, the fonts, `dsp_coef.bin`), and how to say so.
