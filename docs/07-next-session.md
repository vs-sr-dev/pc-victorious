# TODO — session 4

Phase 3 of the plan: graphics. The game runs its main loop and sends whole
frames of GX commands; the goal is to see them. First target the screens
the boot already goes through: the Wii Strap and health screens, the Bink
logos, then the Scaleform menus.

1. **A window.** SDL3 with an OpenGL 4.5 context, driven from the clock
   thread's VI retrace; `VISetNextFrameBuffer`'s address (VI TFBL) names
   the XFB to present.
2. **The GX state.** `gx.cpp` already parses the stream: keep BP, CP and XF
   state per draw instead of only counting, and decode vertices through the
   VCD/VAT and the CP array registers (indexed attributes).
3. **TEV → GLSL**, one program per TEV configuration, cached; blending,
   depth, culling, scissor and viewport from BP/XF.
4. **Textures**: `wiikit.gxtex` (hardware-verified in The Last Story) ported
   to C++, with TLUTs; a cache keyed by address and format.
5. **EFB copies**: to the XFB (the frame) and to textures (Bink frames,
   render targets). The XFB copy is the "frame done" of `writeEndOfFrame`.
6. **Dolphin as the oracle**: a FIFO log of the boot screens, to check the
   parser and the first frames (`05-open-questions.md` 9).
7. **Side work**:
   * where the main loop waits now: which screen, and whether it asks for a
     Remote (phase 4 will answer with the mouse);
   * the idle loop spins a host core: block the clock-less idle context on
     the interrupt line instead;
   * measure the loop's frame rate against the 59.94 Hz retrace.
