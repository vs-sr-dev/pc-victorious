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

## Session 4 — graphics: from the strap screen to the first classroom

Goal: phase 3 of the plan. Draw the GX stream the game already sends,
starting with the screens of the boot: the Wii Strap, the Bink logos, the
Scaleform menus.

Results:

* **The renderer** (`12-renderer.md`): SDL3 and OpenGL 4.5 on the host's
  main thread. The guest side of the FIFO decodes whatever reads guest
  memory at the moment the game believes the GP read it (vertices through
  the arrays, XF matrices from indexed arrays, textures through TMEM's
  palettes, hashed and cached) and records it; the renderer draws the
  record from its own BP and XF mirrors, up to two frames behind. TEV
  configurations become GLSL programs in integer arithmetic, indirect
  stages included; EFB copies stay on the host GPU, as textures or as XFB
  frames; each VI retrace presents the XFB that VI's registers name, at the
  height VI scans out.
* **Everything the boot shows renders** at the first attempt that compiled:
  the Wii Strap screen, the D3 Publisher and other Bink logos (five TEV
  stages, two indirect stages, signed colour registers), the Scaleform
  title screen. Two defects, both visible only in the picture, and both
  spotted by eye during the session: short lines in the Bink frames
  (texture coordinates truncated to fixed point a hair short of an exact
  texel edge, under Bink's indirect un-swizzling) and a stretched title (the
  game letterboxes to 16:9 through VI: 360 of 480 lines).
* **The first classroom.** With a debugging Remote on channel 0 (keys and
  the mouse, `wpad.cpp`, and scripted presses with `WIIKIT_PAD`), "Press A"
  leads to the main menu, and "Start New Game" to Sikowitz's classroom at
  Hollywood Arts, in 3D: Tori, Jade and Sikowitz skinned and lit, the
  tutorial prompt over the scene. 56 programs, about 190 draws and
  9 EFB copies to textures per frame; no fog, no Z textures, no TMEM
  preloads so far.
* **Side questions answered.** The main loop's wait was the title screen's
  "Press A". The game runs at **30 frames a second**, one per two
  retraces, from the strap screen to the classroom. The SDK's idle loop
  had kept a host core spinning: the recompiler now finds loops that only
  an interrupt can end (16 in the executable: `SelectThread`'s idle loop,
  the DVD and AX waits) and blocks them on the interrupt line; the clock
  thread sleeps on a high-resolution waitable timer instead of yielding
  through its last 2 ms. At the title screen the process went from 1.85
  host cores to 0.27; the classroom takes about one.
* The native self-test still passes, 15 of 15.

## Session 5 — input: the mouse as the Wii Remote

Goal: phase 4 of the plan. Replace the debugging Remote with the mouse, well
enough to play the first act, E1A1.

Results:

* **The input path read out** (`08-input-and-rhythm.md`): what
  `readController` copies from each `KPADStatus` into the game's
  `SController`, the button slots, and the 42 logical controls of
  `setDefaultControlMapping`. The game proper asks for four: the pointer's
  two axes, A and B; the menus read the button slots directly, + opens the
  pause menu, and Home runs the SDK's own Home Button menu. The two input
  questions left open since session 1 are closed: the shake is KPAD's
  `acc_speed`, over 0.4 for two frames running.
* **The mouse is the pointer, one to one.** Two things stood between them.
  The pointer was spread over the whole 4:3 screen while the game shows
  360 of its 480 lines, so the cursor moved a quarter less than the mouse
  vertically: −1..1 now spans the picture VI shows. And the adventure
  cursor smooths the pointer again after KPAD, 30% of the way per frame,
  about a fifth of a second of lag with a mouse: the port puts it on its
  target each frame. The Windows pointer hides over the picture; the game
  draws its own.
* **A port's own layer.** That fix is the first thing only Victorious needs,
  so it does not go into wiikit: `tools/victorious.cpp` is linked into
  `wiiboot` by the project's CMake file, registers itself with the runtime
  (`RtGameLayer`), and replaces the functions of a second hook list that
  the recompiler takes with `--hooks`. Rebuilding after a new hook
  recompiled only the files it touched.
* **The controls**: the mouse's buttons for A and B, W A S D for the d-pad,
  Tab for +, Q for −, 1 and 2, Space or the middle button for a shake. Home
  has no key: Esc opens a native pause box (Resume, Quit) in place of the
  Wii's menu, whose "Wii Menu" and "Reset" mean nothing on a PC.
* **E1A1 played**, by hand, for twelve minutes: the classroom tutorial,
  dialogue, the inventory and its side-quest items, menus, cutscenes, the
  hunt for Sikowitz's pages through the school, and the rhythm game, where
  A, B and the shake each land, and A and B in all three of the game's
  forms (a press, a hold, a run of presses). The rhythm game keeps time
  though nothing is heard yet; the track of icons that pulse on the beat
  makes it playable by eye as well. 204 shader programs, 3.6 million draws,
  and not one report of a GX feature the renderer lacks.
* The native self-test still passes, 15 of 15.

## Session 6 — audio, and the frame rate held

Goal: phase 5 of the plan. Music and voices, and the rhythm game in sync
with what is heard.

Results:

* **The AX micro-code in C++** (`ax.cpp`, `13-audio.md`). Wwise plays on the
  DSP's hardware voices, so the mixer has to be the DSP's: the command list
  of this SDK read from `__AXNextFrame`, the 0x140-byte parameter block
  checked field by field against the SDK's own `AXSetVoice*` stores, and
  Dolphin's AXWii HLE as the reference for what each command does: DSP-ADPCM
  and PCM decoding, the polyphase resampler with the DSP ROM's table, the
  volume envelope, low-pass and biquad, the ramped mix into main and three
  aux buses, the aux effects' round trip through the CPU, the compressor,
  the Remote speakers' 6 kHz mix.
* **Heard at the first run**: the Bink logos' music, the menus, the
  background music, the cast's voices, the rhythm games. A rare buzz on room
  changes was the AI replaying a 3 ms frame the busy guest had not yet
  refilled: such a block is now skipped.
* **Latency.** The SDL3 stream holds 20 ms of sound, its speed nudged by at
  most 2% to keep that level against the drift between the host's clock and
  the sound card's (measured: 1.0000 ± 0.0001). The rhythm game is playable
  by ear; its best grade wants a press a hair early, since what is heard and
  seen trails the game's audio clock by the output's latency.
* **The frame rate.** The first episode's nightclub ran at 16-19 fps. New
  measuring tools (`WIIKIT_PERF`, and a sampling profiler that unwinds out of
  DLLs, `WIIKIT_PROFILE` with `tools/profile_resolve.py`) found neither the
  GPU nor the recompiled game at fault: `std::ldexp`, called by every
  quantised paired-single load and store for its scale (the engine skins on
  the CPU), and page faults on the GX record's fresh buffers. The scale is
  now built from its exponent bits and the buffers are recycled: 30 fps
  held, the game's thread idle 60% of the time in that scene. `-O2` was
  tried on the way and changed nothing.
* **The write-gather pipe** delivers 32-byte bursts, as the hardware does,
  instead of every store running the FIFO parser under a lock.
* **Played by hand** through the first episode's second act and its
  rhythm game, with sound, for over half an hour in several runs.
* The native self-test still passes, 15 of 15.

## Session 7 — the PC finish

Goal: phase 6 of the plan. The game plays with the mouse, with sound, at 30
frames a second; make it a PC game rather than a Wii in a window.

Results:

* **SYSCONF** (`sysconf.cpp`, `11-runtime.md`). The NAND had none, and the
  SDK's fallback is a 4:3 console, on which Victorious letterboxes its 16:9
  picture into 360 lines. The port now writes one on the first run (16:9,
  English, stereo, no Remotes paired), in the layout Dolphin writes;
  `--aspect` and `--language` change it and the change stays. At boot
  `enableWidescreen` sees `SCGetAspectRatio() == 1` and the engine goes
  widescreen: VI's VTR goes from 180 to 224 lines a field, and every frame
  is drawn anamorphic at 640 × 448, presented at 16:9. Checked first without
  a window, from the VI registers, for both settings.
* **The window.** The TV's shape comes from SYSCONF; the picture is as large
  as the window allows and centred, and the presenter and the mouse share
  one rectangle, so the cursor stays under the mouse at any size (checked by
  hand at 1920 × 1080). `--window WxH` sets the first size (1280 × 720 by
  default). F11 or Alt+Enter, or `--fullscreen`, switch to SDL's borderless
  fullscreen at the desktop's mode: on an ultrawide the picture keeps 16:9
  with bars at the sides, and nothing else on the desktop moves.
* **The internal resolution.** The EFB, and every EFB copy with it, already
  scaled with `--scale`; the texture coordinates, fixed point in 1/128 of a
  texel and sampled normalised, read a larger copy where the game expects.
  At 1080 lines the models' stair-steps were the one thing that looked
  wrong: the scale now defaults to enough EFB lines for the screen's height
  (× 3 at 1080 or 1440 lines, × 2 at 720). At × 3 (1920 × 1584) the game
  looks clean and holds 30 fps; no reports from the renderer, the EFB
  copies (six a frame there) right.
* **Keys from a file** (`build/keys.txt`, `--keys`), written with the
  defaults when missing: each Remote button, then SDL key names and mouse
  buttons, the side buttons included. Esc, F11 and Alt+Enter are fixed.
* **Two players** in the rhythm game take turns on one Remote: input is
  always read from controller 0, and the active player only decides whose
  score is kept. Nothing to add on a PC.
* **Rhythm latency** was not felt in play: the beat windows absorb the
  output's 30-40 ms. The compensation stays an open question (10).
* **Played by hand** in several runs, the longest nine minutes, at 30 fps
  with other programs open alongside; no GX feature reported missing.
