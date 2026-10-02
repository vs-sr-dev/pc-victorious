# Open questions

Resolved questions move to the bottom with the session that settled them.

## Input

3. **`wii_nunchuk_*.tga`** (7 languages): a controller-help screen, or is the
   Nunchuk used somewhere?

## Data

5. **Dante bytecode**: the text form lists strings, data, natives and
   reference lists; the code itself is not decoded. Not needed for a
   recompiled port, useful for understanding scripts.
7. Formats named but not described: `.tex`, `.smb`, `.bfm`, `.skb`, `.ani`,
   `.mtb`, `.bst`, `.cinemat`, `.tfb`, `.phys2b`, `.cib`, `.atb`, `.lvl`.
   They are not needed for a recompiled port (the game reads them itself)
   but would matter for modding or for a higher-level renderer.

## Code

8. **Debug features in the retail build**: `DebugLevelSelectScreen` (with
   its `.swf`), `CDevMenuNode`, `CEditorTools`, cheat processing. Reachable?
10. **Rhythm latency compensation.** (Not felt in play so far: the beat
    windows seem wide enough for the output's 30-40 ms.) The rhythm game judges presses on its
    audio clock; the player hears and sees 20 ms of audio queue plus the
    device's buffer, and up to two frames of renderer queue, later. Taking
    that off the press time where `CDebugRhythmGameUI::debugRender` makes it
    (it reaches `addnewInputs`) would make the best grades land on the beat.

## Recompiler fidelity

11. **Single-precision rounding**: `fmadds` & co. round once from double;
    Gekko rounds frC to 25 bits first. `fres`/`frsqrte` are exact instead of
    table estimates. Where does the game notice? Differential runs against
    Dolphin (same inputs, compare memory) will tell.
## Renderer

15. **Nine EFB copies to textures every frame** in the classroom: which
    are they (shadows, a blurred copy for the UI, Scaleform render
    targets)? They look right; knowing them matters for a higher internal
    resolution and for the optional `APIDLL*` cut.

## Runtime

17. **Stutters on loads**: rare, short hitches when a dialogue opens, and
    with them some audio blocks skipped for want of a new AX frame (51 to
    100 in the session that played episodes 3 and 4 through). The likely cause:
    `/dev/di` reads are served synchronously inside the IPC call, so the
    whole guest waits on the host's disk, a USB hard disk here, where the
    console's drive works alongside the CPU and answers with an interrupt.
    To check with `WIIKIT_AUDIODBG`; the fix would answer reads from a
    worker thread.

## Resolved

* *Session 8* — **Fog, Z textures, TMEM preloads**: not used. The whole
  game, from `e1a1` through the finale and the credits, was played with
  the renderer reporting each on first use, and none was reported. The
  fog machines of episode 4 are drawn without GX fog.
* *Session 8* — **Wwise media**: the DSP coefficients sit in the RIFX
  `fmt ` chunk from 0x1C, 0x2E bytes a channel, as in the standard DSP
  header from its own 0x1C; the channels interleave frame by frame
  (`02-container-formats.md`, `tools/wwise.py`).
* *Session 7* — **Two-player rhythm mode**: the players take turns on the
  same Remote; the active player only chooses whose score is kept
  (`08-input-and-rhythm.md`).

* *Session 7* — **SYSCONF**: the port writes one in the NAND on the first
  run (16:9, English, stereo). With the 16:9 setting the game draws full
  448-line anamorphic frames instead of letterboxing into 360
  (`11-runtime.md`).

* *Session 6* — **The rhythm game's clock**: Wwise's beat callbacks follow
  the AX frames it renders, and the AI paces those on the host clock; with
  sound on, the game stays in time with what is heard, up to the output's
  latency (question 10 now).
* *Session 6* — **Performance with the renderer on**: the heaviest scene so
  far (the first episode's nightclub) holds 30 fps, the game's thread idle
  60% of the time, once psq_l/psq_st stopped calling `ldexp` and the GX
  record stopped allocating (`11-runtime.md`, Measuring).
* *Session 5* — **What is `SController+0xC8`?** `KPADStatus.acc_speed`,
  the change of acceleration between samples. `bGetShake` wants it at 0.4
  or more in each of the last two frames (`08-input-and-rhythm.md`).
* *Session 5* — **The logical controls.** 42 entries; the game proper asks
  only for the pointer (0x10, 0x14), A (0x18) and B (0x19). The rest serve
  engine leftovers (cars, boats, a free camera) and debugging; the menus
  read the button slots directly (`08-input-and-rhythm.md`).
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
