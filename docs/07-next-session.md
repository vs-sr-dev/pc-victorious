# TODO — session 9

The game is played through: all four episodes, `e1a1` to `e4a5`, the
Romeo and Juliet finale and the credits, with the saves across many
restarts. `.recomp.json` says `playable`. What is left is polish and proof.

1. **Stutters on loads** (`05-open-questions.md` 17): rare hitches when a
   dialogue opens, with audio blocks skipped. First a run with
   `WIIKIT_AUDIODBG` to see where the guest is when a frame goes missing;
   if it is a disc read, `/dev/di` answers from a worker thread and the
   IPC reply comes when the data is in, as on the console.
2. **The cursor's hot spot**: the pointer is the tip of the pink ring's
   corner, not the hand's fingertip inside it, so a button lights up only
   when the corner is over it. Most likely the game's own design (the ring
   and the hit test come from one position); a real Wii decides. If it is,
   at most a port option, off by default, moving the hand to the corner.
3. **Dolphin as the oracle**: a frame from Dolphin next to the port's, the
   same scene, the same settings (16:9); then differential runs of the
   recompiler's single-precision rounding (`05-open-questions.md` 11).
4. **The language**: the text comes in five languages (`de`, `en`, `es`,
   `fr`, `it`), `--language` offers seven; which the game follows,
   SYSCONF or its own save, and how it falls back on Japanese or Dutch.
5. **Rhythm latency compensation** (`05-open-questions.md` 10), if a song
   asks for it; none has so far, the finale's three included.
6. **A release shape**: one folder a player can run from, what it needs
   (their own disc, the fonts, `dsp_coef.bin`), and how to say so; an SSD
   for the extracted disc while item 1 is open.
