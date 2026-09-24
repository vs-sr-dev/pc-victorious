# TODO — session 7

Phase 6 of the plan: the PC finish. The game plays with the mouse, with
sound, at its 30 frames a second; what is left is making it a PC game
rather than a Wii in a window.

1. **Widescreen, properly.** The game letterboxes 16:9 inside a 4:3 picture
   (360 of 480 lines). The engine has `vEnableWideScreen`, and the SDK reads
   the aspect ratio from SYSCONF (`SCGetAspectRatio`): a real SYSCONF in the
   NAND with 16:9 (`05-open-questions.md` 14) should give full-height
   anamorphic frames, to present at 16:9. Language and sound mode come from
   the same file.
2. **The window**: fullscreen (a key, and a flag), aspect-correct scaling
   on any window shape, the mouse mapping following.
3. **Internal resolution**: `--scale 2` and above, checked for quality (EFB
   copies at scale, the Bink frames, the text) and cost; perhaps a default.
4. **Rhythm latency compensation** (`05-open-questions.md` 10): take the
   output's latency off the press time, so the best grades land on the beat.
5. **Keys**: a small configuration file for the key map; a second player for
   the rhythm game (`05-open-questions.md` 4).
6. **Playing on**: past the first episode, watching the log for what the
   renderer reports on first use (fog, Z textures, TMEM preloads) and for
   anything the audio skips.
7. **Side work**: a frame from Dolphin next to the port's, the first use of
   Dolphin as the oracle.
