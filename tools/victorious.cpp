// Victorious: Taking the Lead — the port's own layer over the wiikit runtime.
//
// Linked into wiiboot by victorious.cmake; the functions it replaces are
// listed in victorious-hooks.txt, which the recompiler takes with --hooks.
// What belongs here is what only this game needs: changes of feel for the
// mouse, not emulation.
#include "rt.h"

namespace {

// The adventure cursor. CAdventureCursor::vUpdateInput reads the pointer in
// pixels into the target (+0x20, +0x24; +0x28 is the depth the collision
// check keeps), then moves the cursor (+0x14..+0x1C) 30% of the way there
// each frame, once it is more than 0.02 away: at 30 frames a second, about
// 220 ms to cover 90% of a move. That smoothing hides the Remote's shake;
// with a mouse it is lag. The cursor jumps to the target, as the game itself
// does when the pointer comes back onto the screen; +0x2C..+0x34 are the
// copy it keeps of the cursor while the pointer is on the screen.
PPCFunc orig_vUpdateInput;

void vUpdateInput(PPCContext& c) {
    uint32_t self = c.r[3];
    orig_vUpdateInput(c);
    bool off_x = ld8(self + 0x39), off_y = ld8(self + 0x3A);   // the target is off the screen
    if (off_x || off_y) return;
    for (uint32_t i = 0; i < 12; i += 4) {
        uint32_t v = ld32(self + 0x20 + i);
        st32(self + 0x14 + i, v);
        st32(self + 0x2C + i, v);
    }
}

void install() {
    orig_vUpdateInput = ppc_hook("vUpdateInput__16CAdventureCursorFf", vUpdateInput);
    if (!orig_vUpdateInput) rt_log("victorious: no CAdventureCursor::vUpdateInput hook (recompile with --hooks)");
}

RtGameLayer layer("Victorious", install);

}  // namespace
