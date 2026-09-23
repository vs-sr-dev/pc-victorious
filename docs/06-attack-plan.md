# The porting route

## Static recompilation, with the Wii SDK replaced

Three roads, from most to least work:

| Road | Meaning | Verdict |
|---|---|---|
| Reimplementation | a new engine reading the assets: Dante VM, levels, cinematics, UI | No: Scaleform (147 ActionScript movies) and Wwise (banks and events) would have to be rewritten too |
| Decompilation | rebuild C++ source and compile it for PC | No: 7 000 game functions, and middleware that cannot be relicensed on PC |
| **Static recompilation** | translate the PowerPC code to C++ mechanically; reimplement only the hardware interface (the SDK) | **Yes** |

Why recompilation is unusually favourable here:

1. **Exact function boundaries.** The hardest part of a static recompiler
   (N64Recomp, XenonRecomp, PS2Recomp) is finding functions, switch tables
   and indirect-call targets. Here the symbol table gives all 20 619
   functions with address and size, every literal and every vtable.
2. **Middleware for free.** Scaleform, Wwise, Bink and TinyXML are
   recompiled with the game; nothing of theirs is rewritten, as long as the
   SDK below them behaves.
3. **A small hardware surface.** The SDK is 989 functions, and the ones that
   matter fall in a few groups: GX, AX, OS, DVD, KPAD, NAND, VI.
4. **Plain code.** No REL/RSO modules, no code loaded at run time. Paired
   singles are 0.86% of instructions, and only 32 quantised accesses exist.

## Where to cut, subsystem by subsystem

| Subsystem | Cut | Notes |
|---|---|---|
| CPU | recompiled | Gekko: PPC32 BE + paired singles + `psq_*` with GQRs. `bctrl` resolved through the function table, `bctr` through switch tables |
| Graphics | **the GX FIFO** | The SDK's GX code runs recompiled and writes the command FIFO. We execute the commands (BP/CP/XF registers, primitives, display lists). One layer covers the engine, Scaleform, Bink and any inlined writes to `0xCC008000`. It is also the layer The Last Story's tooling already decodes (555 010 of 555 010 FIFO bytes) |
| Audio | **AX** | A software mixer: DSP-ADPCM / PCM8 / PCM16 voices, sample-rate conversion, volume, loops. Wwise, Bink and the Home Button all sit on it |
| Input | **KPAD** | `KPADRead` filled from the mouse (`08-input-and-rhythm.md`) |
| Files | **DVD** | `DVDOpen/Read/Seek` on the extracted tree, or straight from the WBFS |
| Saves | **NAND** | `NANDOpen/Read/Write` on a save folder |
| System | **OS** | arena and heaps, threads, mutexes, conditions, message queues, alarms, time; cache operations become no-ops |
| Video out | **VI** | a window; `VISetNextFrameBuffer` presents the copied frame |
| Home Button, Bluetooth, low-level WPAD | stubs | not needed on PC |

A higher cut, **later and optional**: replace the `APIDLL*` HAL (93
functions, D3D-like) and `GRendererWiiImpl` (83) directly. That would give
cleaner native resolution and no TEV emulation, but should only be tried
once the FIFO renderer works and can serve as the reference.

## Technology

* The **recompiler** is written in Python on top of `wiikit.ppc`: symbols
  + decoder → one C++ function per guest function, over a context of GPRs,
  FPRs with their paired-single halves, CR, XER, LR, CTR, FPSCR and GQRs.
  It becomes wiikit's layer 4.
* The **runtime** is C++20 (CMake; MSVC or clang-cl) with **SDL3** for window,
  input and audio. **OpenGL 4.5** is the first graphics API, because TEV
  configurations turn into GLSL at run time with the least ceremony. Vulkan
  or D3D12 can come later.
* **Guest memory**: one reserved block mapping `0x80000000` (MEM1, 24 MB)
  and `0x90000000` (MEM2, 64 MB), byte-swapped loads and stores, and
  `0xCC00xxxx` as MMIO, the FIFO write-gather pipe above all.
* **Guest threads** on host threads, with **only one guest thread running
  at a time**: a baton handed over in blocking OS calls. This keeps the
  Wii's single-core, priority-scheduled semantics, which Wwise and the loader
  rely on.
* **Dolphin** is the oracle: FIFO logs, texture dumps, register state,
  frame dumps. Differential testing as in The Last Story.

## Phases

| # | Phase | Checkable milestone |
|---|---|---|
| 0 | **Analysis** ✅ | disc, symbols, formats, input (session 1) |
| 1 | **Recompiler: coverage** | every function in `.text` turns into C++ that **compiles**; switch tables resolved; address → function table |
| 2 | **Runtime: boot** | `__start` → `main` → `CGame::init`; `OSReport` on the console; the PODs open through DVD HLE; the game reaches its first frame (black is fine) |
| 3 | **Graphics** | FIFO command processor, BP/CP/XF state, TEV → GLSL, textures (`wiikit.gxtex` in C++), EFB copies. First target the Bink logos and the Scaleform menus, then an act in 3D. Frames compared with Dolphin |
| 4 | **Input** | mouse → KPAD. Target: **play E1A1 with the mouse** |
| 5 | **Audio** | AX mixer. Target: music and voices, and a **rhythm game in sync** with Wwise's beat callbacks |
| 6 | **PC finish** | window and fullscreen, higher internal resolution, widescreen (the engine has `vEnableWideScreen`), saves, key remapping, two players, no Home Button |

Phases 3, 4 and 5 interleave once the first frame is up.

## Known risks

* **Paired singles and GQRs**: `ps_*` and `psq_*` semantics must be exact;
  few sites, but in math and skinning.
* **Floating point**: `fmadds`, `frsp`, single rounding on double registers
  can shift physics and animation. Compare with Dolphin.
* **Thread scheduling**: if Wwise or Bink depend on strict priorities, the
  one-guest-thread-at-a-time model is the safety net.
* **EFB copies and render-to-texture** (`APIDLLcopyBackBufferToRenderTexture`,
  shadow maps, cube maps): the delicate part of any GX backend.
* **Rhythm-game timing** depends on audio and clocks; measure it early.

## What is never distributed

Only documentation, tools, the recompiler and the runtime. Generated C++,
game data and anything extracted stay local and are produced from one's
own disc.
