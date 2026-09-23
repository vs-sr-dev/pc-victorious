# Session log

## Session 1 — disc analysis, the route, and wiikit

Goal: understand the disc and the code, answer whether any part of the game
needs real motion input, and choose a porting route.

Results:

* **Disc read from WBFS** with no external tools (`wiikit.disc`, AES in pure
  Python): one DATA partition, 46 files, 1.43 GB (`01-disc-layout.md`).
* **The developers' ELF is on the disc** with its symbol table: 49 210
  symbols, 20 619 named functions with full C++ signatures. Its loaded
  bytes equal `main.dol` section for section, so the names describe the
  retail code (`03-executable.md`).
* **Engine and middleware identified**: High Voltage Software on Terminal
  Reality's Infernal Engine (POD5 archives, Dante scripts, an `APIDLL*`
  render HAL with PC origins), Scaleform GFx, Wwise, Bink, TinyXML. About 8%
  of the code touches the hardware.
* **POD5 solved**: the PC format unchanged, little-endian, uncompressed;
  7 485 files in seven archives (`02-container-formats.md`).
* **Content mapped**: 4 episodes × 5 acts, a master set, a finale, 19
  rhythm games; text in five languages although three are advertised;
  Dante scripts and levels are text.
* **Input answered** (`08-input-and-rhythm.md`): the pointer covers the
  adventure, through one function (`readController`) and a logical control
  layer. The only motion input is a **shake in the rhythm game**, where it
  is the most frequent event (1 040 of 2 220). The scoring lives in a class
  still called `CDebugRhythmGameUI`.
* **Route chosen** (`06-attack-plan.md`): static recompilation with the SDK
  replaced: GX at the FIFO, AX mixer, KPAD from the mouse, DVD, NAND, OS
  threads one at a time.
* **wiikit started** (`10-wiikit.md`): `disc`, `aes`, `dol`, `cw`, `ppc`,
  `gxtex`, `tpl`, `u8`, `dsp`.
* Seven curiosities (`04-curiosities.md`), among them fake credits for a
  puppet and the developers' ELF itself.

Two corrections on the way.

The first census of middleware grouped functions by a crude prefix match
and put the engine's `GameGlobals_*` script natives under Scaleform. The
demangler-based census in `wiikit.dol --libs` replaces it. The SDK also went
from 536 to 989 functions once the prefix list was complete.

The texture decoder first copied here was Crystal Bearers' copy, which
predates The Last Story's two hardware-verified fixes (CMPR weights 5/8 and
3/8; intensity in alpha for I4/I8). `wiikit.gxtex` is The Last Story's
version.

Validation of the new decoder, since everything later depends on it:
decoding all 1 658 815 instructions leaves none unknown. Against capstone,
every instruction capstone understands renders the same once standard
aliases are normalised. The 27 remaining differences are alias spellings
only, and capstone cannot decode `fcmpo` at all. capstone reads the paired
singles as POWER VSX, so for those the check is structural: all 1 393
functions that save f14–f31 with `psq_st` restore the same registers from
the same offsets.

## Session 2 — the recompiler: the whole executable compiles, and runs

Goal: phase 1 of the plan, every function turned into C++ that compiles.

Results:

* **The program model** (`wiikit/recomp/program.py`): 20 622 units (the
  sized function symbols plus three gaps of hand-written code), 20 653 entry
  points found to a fixed point. The 31 entries inside units are
  CodeWarrior's `__save_gpr`/`__restore_gpr` entry points and three TRK
  stubs. Before writing it, the control flow was measured: every `bl` to the
  middle of a function lands in those register save/restore routines, every
  unconditional branch out of a function lands on a function start (2 564
  tail calls), and only two functions (the OS exception vectors) have no
  terminator.
* **Switch tables**: 266 found from the `lwzx`/`mtctr`/`bctr` pattern, sized
  by the table's own data symbol. One base is lost across a branch in
  `CVoxelGrid::insert` and is recovered by a fallback: the only data table
  whose entries all point into that function. Of the other `bctr`, 447
  take CTR from a `lwz`, virtual tail calls (`lwz r12, off(r12); mtctr r12;
  bctr`), and 6 go through function pointers.
* **The emitter** (`wiikit/recomp/emit.py`) covers all 169 operations the
  game uses. The CPU model is `wiikit/runtime/ppc.h`: Gekko's paired singles
  with GQR quantisation, and single-precision results filling both halves as
  in Dolphin.
* **It compiles and links**: 1 661 203 instructions → 201 files, 124 MB of
  C++ in 16 s; clang 22 at `-O1` builds it in 1 min 38 s on 18 threads, and
  the link check holds all 20 653 functions in one 58 MB executable. The one
  compile error of the first build was `__OSDBJump`'s absolute call to the
  debugger stub at `0x60`, which no longer becomes a direct call.
* **It runs** (`tools/selftest.cpp`): the retail `main.dol` is loaded into a
  4 GiB guest address space and the game's own recompiled code is called
  natively. `sprintf` produces byte-identical output with varargs and
  doubles. `__div2i`/`__mod2i`/`__div2u` are right on 2 000 random pairs,
  `sin`/`cos` within 4e-21, and `qsort` sorts through two different game
  comparators by indirect calls. The SDK's paired-single `PSMTXConcat`,
  `PSMTXMultVec` and `PSMTXInverse` agree with the host, and `memcpy` is
  bit-exact through the FPRs for 200 random sizes and alignments.
  **15 of 15.**

Two mistakes on the way, both in the test, not the recompiler: "Hollywood
Arts High School" has 26 characters, not 27, and the `memset` check read
bytes that the previous test had left in the scratch area.

Also settled: no `setjmp`/`longjmp` anywhere in the executable, and
`OSSwitchFiberEx` only in Bluetooth code the port drops. Thread switching is
`OSLoadContext`, called from the scheduler, interrupts and exceptions: a
clean cut for phase 2.

## Session 3 — the runtime: from `__start` to the main loop

Goal: phase 2 of the plan, boot. Run `__start` natively as far as
`CGame::init`, and decide where to cut the operating system.

Results:

* **The OS cut, decided by reading the SDK** (`11-runtime.md`). The
  scheduler funnels every context switch through `OSLoadContext`, so that
  one function is replaced and everything else (run queues, mutexes, message
  queues, alarms) runs recompiled. Guest threads live on host threads, one
  running at a time. Interrupts arrive at safe points (the 13 617 backward
  branches, and `mtmsr` enabling them) through the game's own handlers, as
  `OSExceptionVector` would call them. For I/O the cut is the IPC registers:
  the SDK's DVD, NAND and ES code runs recompiled against IOS emulated as in
  Dolphin, with the disc served from the extracted tree.
* **The recompiler grew hooks and safe points** (`09-recompiler.md`):
  functions named in `runtime/hooks.txt` get a replaceable slot and keep
  their original; 47 in Victorious, all SDK functions, found by name.
* **The runtime** (`wiikit/runtime`, `wiiboot`): OS threads and interrupts,
  time base and decrementer, PI, VI, DSP with the ROM, init and AX
  micro-codes (silent), AI DMA, EXI with the IPL chip (RTC, SRAM, the boot
  ROM's fonts), SI, the Hollywood registers, IOS (`/dev/di`, `/dev/fs`,
  `/dev/es`, `/dev/stm`), the GX FIFO with a command parser, the HLE boot
  state, and WPAD/KPAD replaced with "no Remote connected".
* **The game boots.** The SDK reports itself ("Revolution OS … Console
  Type: Retail 33, Firmware 56.22.29 … MEM1 Arena 0x80a3bfa0 – 0x817fdb00"),
  passes its anti-modchip device check, and the game says "Starting up the
  application...". `APIDLLinit` sets up GX, `CGame::init` shows the Wii
  Strap screens, starts Wwise on AX and plays the Bink logos on their own
  threads, and the game enters **`CGame::run`**, its main loop. In a
  three-minute run it stays there, stable, eight guest threads alive; in
  the second minute it sent 4 million GX commands, 83 670 primitives and
  about 30 EFB copies a second. Nothing is drawn yet.
* The tools grew for it: `--mmio-log` (every hardware register the boot
  touches, with the function that touched it) and `--watch` (every few
  seconds, where each guest thread is). `wiikit.disc --extract` now writes
  the ticket and TMD too; the TMD says the game runs on IOS 56.

The boot, one stop at a time, is tabulated in `11-runtime.md`. Four of the
stops were mistakes of this runtime, not missing features:

* EXI DMA addresses were masked to 26 bits, which cut MEM2's physical
  addresses: the ROM font was read into the wrong place and `OSInitFont`
  found no font.
* The clock thread planned in time-base units; the game rewrites the time
  base, the plan jumped, and the decrementer never fired. It keeps host time
  now.
* Its condition-variable timeouts had the 15.6 ms granularity of the
  Windows tick through winpthreads: `OSSleepTicks(200 µs)` took a frame.
* The DSP mailbox's top bit was taken for part of the mail; it is the
  "full" flag the write sets, and the boot mails without it were lost.

Two SDK behaviours were worth reading before emulating: `writeEndOfFrame`
paces the game with GX FIFO breakpoints, not draw-done, and the device
check needs the drive to *fail* in exactly the right way (`04-curiosities.md`).
