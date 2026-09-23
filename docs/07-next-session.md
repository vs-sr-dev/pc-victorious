# TODO — session 5

Phase 4 of the plan: input. The renderer reaches the first classroom with a
debugging Remote (keys, the mouse as a raw pointer); the goal is the mouse
as the Wii Remote, well enough to **play E1A1**.

1. **The pointer.** The tutorial asks "Point the Wii Remote at Jade, and
   press A": check that the game's cursor follows the mouse
   (`CAdventureCursor`, `CGame::processPointer`) and that hovering and
   clicking a character works. Then the feel: the Remote's pointer is
   smoothed by KPAD (`KPADSetPosParam`) and the game may filter it again;
   the mouse should map one to one.
2. **The controls table.** Read `CGame::setDefaultControlMapping` once for
   all logical controls (`05-open-questions.md` 2), and give each a
   default key.
3. **The shake** for the rhythm game: what `SController+0xC8` holds
   (`05-open-questions.md` 1) and a key that produces it.
4. **The Home Button menu**: the game can open it; decide whether it is
   kept (it needs its own `homeBtn.arc` resources and the Remote's
   speaker) or answered as "closed".
5. **Renderer leftovers**, as they appear while playing: fog, Z textures,
   TMEM preloads (each reported once when first used), texture eviction,
   CPU access to the EFB.
6. **Side work**: a frame from Dolphin for the classroom, side by side
   (the first use of Dolphin as the oracle); the renderer's cost per frame
   at `--scale 2` and above.
