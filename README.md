# pc-victorious

Toward a native PC port of **Victorious: Taking the Lead** (Wii, D3
Publisher / High Voltage Software, 2012), the point-and-click adventure
tie-in to the Nickelodeon series. It was a Wii exclusive and never
re-released. The goal is the game running natively on PC, with the Wii
Remote pointer replaced by the mouse.

This repository documents the disc, its formats and its code, and grows the
tooling for the port. Alongside it grows **wiikit**, a game-agnostic toolkit
for Wii reverse engineering: everything the port needs that is not
specific to Victorious.

## BYOA — Bring Your Own Assets

This repository contains **documentation and tools only**. No game data, no
executables, no assets. You need your own original disc. The work is done on
the North American release, S2VEG9.

## Layout

    docs/            disc, format and code analysis, and the plan
    tools/           Victorious-specific tools, the port's own layer over the runtime, the native self-test
    wiikit/          game-agnostic Wii toolkit
    wiikit/recomp/   the static recompiler (Gekko -> C++)
    wiikit/runtime/  the C++ side: CPU model, guest memory, OS, hardware, IOS, the renderer; wiiboot

## Tools

The Python tools need only Python 3.8+ and no dependencies (pycryptodome,
if installed, speeds up disc decryption). Building the recompiled code needs
CMake, Ninja, a C++20 compiler (clang 22 from MSYS2 is what is used here)
and SDL3; running it needs OpenGL 4.5.
Run from the repository root.

```sh
# the disc: header, partitions; extract the DATA partition (.iso or .wbfs):
# sys/, files/, and the ticket and TMD
python -m wiikit.disc GAME.wbfs --info
python -m wiikit.disc GAME.wbfs --extract build/extract

# the executable: sections, symbols, the ELF against the retail DOL, libraries
python -m wiikit.dol build/extract/sys/main.dol --info
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf \
    --same-as build/extract/sys/main.dol
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf --libs
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf \
    --symbols build/symbols.tsv

# code: a function, its callers, who builds an address, the instruction census
ELF=build/extract/files/Oscar_wii_final_versioned.elf
python -m wiikit.ppc $ELF --func readController
python -m wiikit.ppc $ELF --callers bGetShake__5CGameFi
python -m wiikit.ppc $ELF --xref 0x8079ADA0
python -m wiikit.ppc $ELF --mix
python -m wiikit.cw 'process__19CSongMoveBlockActorFf'

# the game's archives, UI movies and rhythm charts
python tools/pod.py list build/extract/files/WIICOMMON.POD
python tools/pod.py extract build/extract/files/WIICOMMON.POD build/pod/WIICOMMON
python tools/gfx.py build/pod/WIIART/flash --census
python tools/gfx.py build/pod/WIIART/flash/rhythmgamecontrol.gfx --strings
python tools/songs.py build/pod/WIICOMMON/data/songs

# recompile the executable to C++, build it, run the game's code natively
python -m wiikit.recomp $ELF --out build/recomp
cmake -S build/recomp -B build/recomp-build -G Ninja -DCMAKE_CXX_COMPILER=clang++ \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O1 \
    -DWIIKIT_EXTRA=$PWD/tools/selftest.cmake
ninja -C build/recomp-build
build/recomp-build/selftest build/extract/sys/main.dol build/symbols.tsv

# boot the game: the NAND in build/nand, the boot ROM's fonts in build/fonts
# (font_western.bin, font_japanese.bin: Dolphin's Sys/GC has free ones)
# a window opens; the mouse is the Wii Remote's pointer: left button or
# Enter = A, right button or Backspace = B, W A S D or the arrows = d-pad,
# Tab = +, Q = -, 1 and 2, Space or the middle button = shake; Esc pauses
build/recomp-build/wiiboot build/extract --symbols build/symbols.tsv
build/recomp-build/wiiboot build/extract --scale 2 --dump build/shots --dump-every 300
build/recomp-build/wiiboot build/extract --no-video --watch 10     # no window

# standard Wii formats
python -m wiikit.u8 build/extract/files/HomeButton2/homeBtn.arc
python -m wiikit.tpl build/extract/files/HomeButton2/homeBtnIcon.tpl build/icon
```

## Status

Session 5: **the game is played with the mouse.** The pointer follows the
mouse one to one (the game's own cursor smoothing is lifted by the port's
layer, the first code only Victorious needs), A and B are the mouse's
buttons, the rhythm game's shake is Space, and Esc opens the port's own
pause box in place of the Wii's Home Button menu. The first act, E1A1, was
played by hand from the classroom tutorial through the school to its rhythm
game, which keeps time even without sound. Next is the sound.

Session 4: **the game is drawn.** The GX command stream is decoded on the
game's side and drawn with OpenGL 4.5 on the host's main thread: the TEV
becomes generated GLSL in integer arithmetic, indirect textures included,
EFB copies stay on the GPU, and VI presents each frame at the height it
scans out. The Wii Strap screen, the Bink logos, the Scaleform title and
menus, and, past "Press A" with a debugging Remote, Sikowitz's classroom
at Hollywood Arts in 3D all render, at the game's own 30 frames a second on
about one host core. Next is the mouse as the Remote.

Session 3: **the game boots to its main loop.** The runtime replaces the
Wii under the recompiled code: guest threads on host threads with only the
SDK's context switch replaced, interrupts delivered through the game's own
handlers, IOS emulated at the IPC registers, the DSP's micro-codes, the
GX FIFO parsed. From `__start` the SDK reports itself, passes its
anti-modchip check, and the game runs `CGame::init` (the strap screens,
Wwise, the Bink logos) and settles in `CGame::run`, sending whole frames of
GX commands. Nothing is drawn yet: next is the renderer.

Session 2: **the whole executable recompiles to C++, compiles, links and
runs.** All 20 653 functions (1.66 million instructions) become 124 MB of
C++ that clang builds in under two minutes, and the game's own code, run
natively on the retail `main.dol` image, matches the host in 15 of 15 tests:
its `sprintf`, 64-bit division, libm, `qsort` through its comparators, the
SDK's paired-single matrix library, its FPR-based `memcpy`.

Session 1: the disc is read and mapped, and the developers' symbolised ELF
turns out to be on it, byte-identical to the retail executable, with 20 619
named functions. The engine (Infernal Engine), the middleware (Scaleform,
Wwise, Bink) and the archive format are identified. The input question is
answered: the mouse covers the adventure, and the only motion input is a
shake in the rhythm game. The route is static recompilation with the Wii SDK
replaced. wiikit has a disc reader, an executable loader, a demangler and a
Gekko decoder checked over all 1.66 million instructions.

See [docs/00-sessions.md](docs/00-sessions.md) for the log,
[docs/06-attack-plan.md](docs/06-attack-plan.md) for the route,
[docs/07-next-session.md](docs/07-next-session.md) for what is next and
[docs/04-curiosities.md](docs/04-curiosities.md) for the interesting bits.

## Documentation

    00-sessions.md            progress log
    01-disc-layout.md         what is on the disc
    02-container-formats.md   every format, with verified layouts
    03-executable.md          the symbolised ELF, what is linked, engine landmarks
    04-curiosities.md         what the disc reveals about its making
    05-open-questions.md      what is still unknown
    06-attack-plan.md         the porting route
    07-next-session.md        the plan for the next session
    08-input-and-rhythm.md    the input path, the controls, the mouse as the Remote, the rhythm game
    09-recompiler.md          the recompiler, the CPU model, the native tests
    10-wiikit.md              the game-agnostic toolkit
    11-runtime.md             the runtime: OS, interrupts, IOS, DSP, GX; the boot step by step
    12-renderer.md            the renderer: GX on OpenGL, TEV to GLSL, EFB copies, VI

## Licence

MIT — see [LICENSE](LICENSE). This covers the documentation and tools in this
repository only. It says nothing about Victorious: Taking the Lead or the
Victorious series, which remain the property of their rights holders.
