# Open questions

Resolved questions move to the bottom with the session that settled them.

## Input

1. **What is `SController+0xC8`?** `CGame::bGetShake` compares its absolute
   value with `sGVar_fShakeThreshold`. It is filled in `readController`
   (`805FA500`) from `KPADStatus`: raw acceleration, `acc_speed`, or a
   filtered value (the debug menu has "Shake frames filer")? The mouse/key
   substitute must produce the same kind of value.
2. **Logical controls 0x18 and 0x19** are A and B for the rhythm game; the
   whole table comes from `CGame::setDefaultControlMapping`. It should be
   read out once, for all controls.
3. **`wii_nunchuk_*.tga`** (7 languages): a controller-help screen, or is the
   Nunchuk used somewhere?
4. **Two-player rhythm mode** (`is2PlayerRhythmGameActive`): how does the
   second player join, and on which Remote?

## Data

5. **Dante bytecode**: the text form lists strings, data, natives and
   reference lists; the code itself is not decoded. Not needed for a
   recompiled port, useful for understanding scripts.
6. **Wwise media**: where the DSP coefficients sit in the RIFX `fmt ` chunk
   (format tag 2, 0x4C bytes).
7. Formats named but not described: `.tex`, `.smb`, `.bfm`, `.skb`, `.ani`,
   `.mtb`, `.bst`, `.cinemat`, `.tfb`, `.phys2b`, `.cib`, `.atb`, `.lvl`.
   They are not needed for a recompiled port (the game reads them itself)
   but would matter for modding or for a higher-level renderer.

## Code

8. **Debug features in the retail build**: `DebugLevelSelectScreen` (with
   its `.swf`), `CDevMenuNode`, `CEditorTools`, cheat processing. Reachable?
9. **Which GX features the game really uses**: TEV stage counts, indirect
   textures, EFB copy formats, fog. A FIFO log from Dolphin answers this
   before the renderer is written.
10. **Frame rate**: 30 or 60 Hz, and how the rhythm game's clock relates to
    the audio clock (`soundBeatCallback`).

## Recompiler fidelity

11. **Single-precision rounding**: `fmadds` & co. round once from double;
    Gekko rounds frC to 25 bits first. `fres`/`frsqrte` are exact instead of
    table estimates. Where does the game notice? Differential runs against
    Dolphin (same inputs, compare memory) will tell.
12. **OS cut**: SDK-function HLE or IOS IPC HLE (`07-next-session.md`).

## Resolved

* *Session 1* — **Is any minigame motion-controlled?** Only the rhythm
  game, and only with a shake (event `X`, 1 040 of 2 220 events).
  No pointing in 3D, swing, tilt or MotionPlus anywhere; no Dante script
  calls `bShake` (`08-input-and-rhythm.md`).
* *Session 1* — **Are the ELF's symbols valid for the retail code?** Yes:
  its loaded bytes equal `main.dol`'s, section for section.
* *Session 2* — **Does the executable use `setjmp`/`longjmp` or fibers?**
  No `setjmp`/`longjmp` at all. `OSSwitchFiberEx` only in the Bluetooth
  USB callbacks, which the port drops.
