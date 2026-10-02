# TODO — session 8

The six phases of the plan are done: the game boots, draws, plays with the
mouse, sounds, and fits a PC screen. What is left is breadth and proof.

1. **Playing on**: episodes 1 and 2 are played through (`e1a1` to `e2a5`,
   with their rhythm games, Beck's hard one among them). The last sitting,
   97 minutes with an Xbox pad, mouse and keyboard, ended at the close of
   `e2a5` with a clean log but for one audio block without a new AX frame.
   Next is `e3a1`, watching the log for what the
   renderer reports on first use (fog, Z textures, TMEM preloads) and for
   anything the audio skips; the saves across a restart. Through `e4a5`
   and the finale, the `.recomp.json` status becomes `playable`.
2. **The cursor's hot spot**: the pointer is the tip of the pink ring's
   corner, not the hand's fingertip inside it, so a button lights up only
   when the corner is over it. Most likely the game's own design (the ring
   and the hit test come from one position); a real Wii decides. If it is,
   at most a port option, off by default, moving the hand to the corner.
3. **Dolphin as the oracle**: a frame from Dolphin next to the port's, the
   same scene, the same settings (16:9); then differential runs of the
   recompiler's single-precision rounding (`05-open-questions.md` 11).
4. **The language**: which of `--language`'s seven the US disc really
   carries (the `wii_nunchuk_*.tga` hint at seven), and whether the game
   follows SYSCONF or its own save.
5. **Rhythm latency compensation** (`05-open-questions.md` 10), if a harder
   song asks for it: delay the beat callbacks the game receives by the
   output's latency.
6. **A release shape**: one folder a player can run from, what it needs
   (their own disc, the fonts, `dsp_coef.bin`), and how to say so.
