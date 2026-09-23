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
10. **The rhythm game's clock**: how it relates to the audio clock
    (`soundBeatCallback`), now that the frame rate is known (30 Hz).

## Recompiler fidelity

11. **Single-precision rounding**: `fmadds` & co. round once from double;
    Gekko rounds frC to 25 bits first. `fres`/`frsqrte` are exact instead of
    table estimates. Where does the game notice? Differential runs against
    Dolphin (same inputs, compare memory) will tell.
## Runtime

14. **SYSCONF**: the NAND has none, and `SCCheckStatus` accepts that and
    falls back to an empty configuration. Language, aspect ratio (the
    engine has `vEnableWideScreen`) and sound mode will want a real one.

## Renderer

15. **Nine EFB copies to textures every frame** in the classroom: which
    are they (shadows, a blurred copy for the UI, Scaleform render
    targets)? They look right; knowing them matters for a higher internal
    resolution and for the optional `APIDLL*` cut.
16. **Fog, Z textures, TMEM preloads**: the SDK functions are linked; where
    does the game use them? The renderer reports each on first use.

## Resolved

* *Session 4* — **Which GX features the game really uses**, as far as the
  first classroom: up to five TEV stages, indirect textures (Bink's
  un-swizzling, two indirect stages), signed TEV colour registers, konst
  colours, EFB copies to textures (nine a frame) and to the XFB, display
  lists; 56 TEV/XF configurations. No fog, no Z textures, no TMEM preloads
  yet (`12-renderer.md`).
* *Session 4* — **Frame rate**: 30 frames a second, one per two retraces,
  from the strap screen to the 3D adventure; the title and the game are
  letterboxed 16:9 at 360 lines.
* *Session 4* — **Performance of the recompiled code**: it keeps up. The
  classroom runs at the game's 30 frames a second on about one host core,
  renderer included, at `-O1`.
* *Session 4* — **Where does the main loop wait?** At the title screen,
  for A. It never waited for a Remote to connect.

* *Session 1* — **Is any minigame motion-controlled?** Only the rhythm
  game, and only with a shake (event `X`, 1 040 of 2 220 events).
  No pointing in 3D, swing, tilt or MotionPlus anywhere; no Dante script
  calls `bShake` (`08-input-and-rhythm.md`).
* *Session 1* — **Are the ELF's symbols valid for the retail code?** Yes:
  its loaded bytes equal `main.dol`'s, section for section.
* *Session 3* — **OS cut: SDK functions or IOS IPC?** Both, each where the
  interface is narrowest: for threads only `OSLoadContext` (plus two
  wrappers), since the SDK's scheduler funnels every switch through it; for
  I/O the IPC registers, with IOS emulated as in Dolphin, so the SDK's
  DVD, NAND and ES code runs recompiled (`11-runtime.md`).
* *Session 2* — **Does the executable use `setjmp`/`longjmp` or fibers?**
  No `setjmp`/`longjmp` at all. `OSSwitchFiberEx` only in the Bluetooth
  USB callbacks, which the port drops.
