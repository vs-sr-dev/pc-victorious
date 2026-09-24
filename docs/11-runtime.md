# The runtime: the Wii replaced

`wiikit/runtime` is what the recompiled code runs on. `wiiboot` loads the
game from an extracted disc and runs `__start`: the SDK then boots as it
does on a console, and every piece of hardware it meets is answered here.
Session 3 took Victorious from `__start` through `OSInit`, `main`,
`CGame::init` and into `CGame::run`, its main loop, with the Bink logos
played, Wwise running on a silent AX, and frames of GX commands flowing.

```
wiiboot build/extract [--nand DIR] [--fonts DIR] [--symbols build/symbols.tsv]
                      [--mmio-log] [--watch SECONDS]
                      [--no-video] [--scale N] [--dump DIR] [--dump-every N] [--quit-after SECONDS]
```

The video options belong to the renderer, `12-renderer.md`. The game runs
on its own threads; the process's main thread runs the window.

| Option | |
|---|---|
| `--nand` | the NAND as a host folder (saves, SYSCONF); `build/nand` by default |
| `--fonts` | the boot ROM's fonts, `font_western.bin` and `font_japanese.bin`; `build/fonts` by default. Dolphin's `Sys/GC` has free ones (Droid Sans, Apache 2.0) |
| `--symbols` | names guest addresses in logs and crash reports |
| `--mmio-log` | the first read and first write of every hardware register, with the guest function that made it |
| `--watch N` | every N seconds: the running guest thread's call chain, where every other thread waits, the decrementer, the GX statistics |

## Where the cuts are

The rule was to replace as little of the SDK as possible, and to cut where
the interface is narrow and the same for every game.

| Layer | Cut | Why there |
|---|---|---|
| Threads | **one function**, `OSLoadContext` | the SDK's scheduler, mutexes, message queues, alarms all run recompiled; only the context switch cannot |
| Interrupts | the exception vector | delivered at safe points through the game's own handlers |
| Disc, NAND, ES, STM | **the IPC registers** | the SDK's IOS client runs recompiled; IOS itself is emulated, as in Dolphin |
| GX | the write-gather pipe and CP/PE registers | the command stream is parsed, decoded and drawn with OpenGL (`12-renderer.md`) |
| DSP | the mailboxes | the ROM, init and AX micro-codes in HLE; AX mixes in C++ (`13-audio.md`) |
| Wii Remote | **the WPAD/KPAD API** | the Bluetooth stack below never starts |
| Console | `__write_console` | MSL's output: `printf`, `OSReport` |

The alternative for the OS was to replace `OSCreateThread`, `DVDRead`,
`NANDOpen` and the rest at the function level. The SDK code showed a better
cut: its scheduler already funnels every switch through `OSLoadContext`,
and its IOS client talks to four registers.

Replaced functions are listed by name in `runtime/hooks.txt`; the
recompiler gives each a slot (`hooks.cpp`) and keeps the original callable.
Victorious uses 47 of them, all SDK functions, so the list serves any game
with symbols.

## Guest threads on host threads

Each guest thread lives on a host thread of its own (64 MB of stack: the
C++ call chain nests as deeply as the guest's). A baton makes sure exactly
one runs at a time, as on the Wii's single core.

`SelectThread` saves the current thread with `OSSaveContext` (which returns
0, and 1 when the thread is resumed) and ends in `OSLoadContext(next)`,
which would restore the registers and `rfi`. The hook instead hands the
baton to the host thread carrying `next`, starting one if the context is
new (`OSCreateThread` marks it), and parks. When its own context is loaded
again, the parked host thread wakes inside `OSLoadContext`, returns, and
`SelectThread` returns: the same place the thread would have resumed from
`OSSaveContext`, except that `SelectThread` then returns the thread pointer
instead of 0, which all eight callers ignore.

A thread function that returns calls `OSExitThread`, as the LR that
`OSCreateThread` set up would. A reused `OSThread` retires the old host
thread.

## Interrupts at safe points

Devices raise a line (`os_raise`). The recompiled code checks it at every
backward branch (13 617 places) and whenever `mtmsr` sets MSR[EE]: that is
enough, since any wait loop has a back-edge. Delivery follows
`OSExceptionVector`: r3–r5, CR, LR, CTR, XER, SRR0/1 are saved into the
current `OSContext`, which is flagged as an exception context, and the
handler from the table at `0x80003000` runs with r3 = exception, r4 =
context, on a copy of the registers and the interrupted stack. Its closing
`OSLoadContext(context)` just returns; if the handler rescheduled, the host
thread parks inside `SelectThread` like any other and the delivery finishes
when it is resumed.

External interrupts come through PI's cause and mask; the decrementer from
the host clock.

**Loops only an interrupt can end.** With nothing to run, the SDK's
`SelectThread` spins on `RunQueueBits` with interrupts enabled, and a
host core spun with it. The recompiler recognises such loops (a back-edge
over loads from the small-data area and compares, nothing else: 16 in
Victorious, the idle loop and the DVD and AX waits) and emits `PPC_IDLE`,
which blocks the host thread until a device raises the line, for at most
1 ms. One guest thread runs at a time, so nothing else could have changed
the word they watch.

## Time

The time base runs at 60.75 MHz (a quarter of the 243 MHz bus) from the
host's steady clock. `mttb` moves it; the decrementer, which counts on its
own, is kept unaffected. A clock thread keeps host time: VI retraces at
59.94 Hz, the AI DMA's blocks, and the decrementer's deadline. On Windows
it sleeps on a high-resolution waitable timer and yields only through the
last 200 µs; condition-variable timeouts on MinGW are as coarse as the
15.6 ms system tick, and `OSSleepTicks(200 µs)` otherwise took a whole
frame.

## Memory

A 4 GiB host reservation indexed by the guest address. MEM1 (24 MiB),
MEM2 (64 MiB) and the 16 KiB locked cache at `0xE0000000` are committed.
Addresses from `0xC0000000` take one extra branch: the uncached mirrors of
MEM1 and MEM2 fold onto them, `0xCC000000`–`0xCDFFFFFF` is the hardware.

## Boot (`boot.cpp`)

What the system menu, IOS and the apploader leave for a disc game:
`main.dol` loaded; the disc header at `0x80000000`; BI2 at `0x817FE000`
and the FST just below it, with the arena ending there; the clocks, and
IOS's memory map for IOS 56 (the TMD's), with values as in Dolphin's HLE
boot. `OSInit` checks three of them: the boot flags at `0x315C`/`0x315D`
and the IOS version against the expected one at `0x3188`.

## The hardware (`hw.cpp`, `gx.cpp`)

| Device | What is modelled |
|---|---|
| PI | cause (computed from the devices) and mask; CPU FIFO base, end, write pointer |
| VI | DI0–DI3 retrace interrupts; the beam position from the clock; for the renderer, the XFB address (TFBL) and the active lines (VTR) |
| DSP | reset, halt, mailboxes (writing the low half sends; the DSP takes it at once), ARAM DMA (no ARAM: done at once), the AI DMA with its per-block interrupt |
| EXI | three channels, immediate and DMA transfers; channel 0 device 1 is the IPL chip: RTC, SRAM, the debug UART, and the boot ROM's fonts |
| SI | no controllers: every transfer ends in "no response" |
| CP, PE | GX FIFO linked or not; PE draw-done and tokens; FIFO breakpoints |
| Hollywood | IPC (IOS), its interrupt flags and mask, GPIOs, the AV encoder's I2C (every byte ACKed) |

Everything else reads back what was written, and `--mmio-log` shows it.

**GX.** The pipe writes the FIFO in RAM at PI's write pointer, which is
also how display lists get built. When the FIFO is linked to the GP, the
stream is parsed: CP, XF and BP loads, display-list calls, primitives
sized from the vertex descriptor and formats. The GP is always idle, having
consumed everything written. Victorious paces its frames with **FIFO
breakpoints**: at the end of a frame it arms one at the write pointer, and
the CP interrupt that fires when the GP gets there frees a slot in its
two-frame queue. An armed breakpoint is therefore reached at once.

**DSP micro-codes**, in high-level emulation:

* ROM: after a reset announces itself (`0x8071FEED`) and takes the ten
  mails of `__DSP_boot_task`, then starts the task, AX so far.
* The init code `__OSInitAudioSystem` runs once: one mail.
* AX: `0xDCD10000` at start. Every audio frame the SDK sends `0xBABE0080`
  and a command list; AX answers `0xDCD10002` (yield), the task manager
  replies `0xCDD10003` and calls AX's resume callback, which prepares the
  next frame on the next AI DMA interrupt (every 3 ms: 0x180 bytes of 16-bit
  stereo at 32 kHz). Since session 6 each list is mixed before the answer
  (`ax.cpp`, `13-audio.md`), and each AI DMA block goes to the host's audio
  device as it starts.

## IOS (`ios.cpp`, `disc.cpp`)

The protocol is Dolphin's: a request is a 0x20-byte block (command, result,
fd, arguments) sent by physical address with PPCMSG and X1; IOS
acknowledges it (Y2), carries it out, writes 8, the result and the original
command at +0, +4, +8, and replies (Y1, ARMMSG). Y1/Y2 raise the Hollywood
IPC interrupt when enabled. A request can stay pending (STM's event hook).

| Device | |
|---|---|
| `/dev/di` | reads served from the extracted tree: `disc.cpp` rebuilds the partition as regions (system files at their offsets, every file where the FST puts it). Errors are kept for `RequestError`, which the device check needs (below) |
| `/dev/fs`, file paths | the NAND on a host folder: files, directories, attributes, rename, delete |
| `/dev/es` | title id, data directory, ticket and TMD views, from `ticket.bin` and `tmd.bin` |
| `/dev/stm/*` | accepted; the event hook stays pending |
| anything else | "no such device": `/dev/net/kd/*` (WiiConnect24), `/dev/usb/oh1/57e/305` (Bluetooth) |

**The device check.** Before `main`, `__DVDCheckDevice` asks the drive to
read raw sectors past the end of the disc and to report a DVD-video key. A
real drive refuses both, with errors `0x052100` and `0x053100`; a drive that
obliges is a modchip, and the game stops at "Error #001, unauthorized
device has been detected". The emulated drive has to fail exactly.

## The Wii Remote (`wpad.cpp`)

The public WPAD and KPAD API is replaced: WPAD is ready, and one Remote is
connected, on channel 0, driven by the host: the mouse as the pointer,
keys for the buttons and the shake (`08-input-and-rhythm.md`), filling one
0xF0-byte `KPADStatus` per `KPADRead`. The Bluetooth stack (WUD, BTA/BTE)
never starts, so nothing waits for the HCI dongle.

## A port's own layer

Whatever only one game needs stays out of wiikit: a project links its own
code into `wiiboot` through its `WIIKIT_EXTRA` CMake file, and that code
registers itself with a static `RtGameLayer`, whose install function
`wiiboot` runs after the runtime's hooks. The functions it replaces are
given to the recompiler as a second hook list (`--hooks`). Victorious's
layer is `tools/victorious.cpp`, with `tools/victorious-hooks.txt`.

## Measuring

| Environment | |
|---|---|
| `WIIKIT_PERF=1` | every second: fps, frame time, and on the game's thread the time spent decoding vertices and textures and waiting for the renderer; the renderer's time |
| `WIIKIT_PROFILE=1` | (Windows) a sampling profiler of the thread holding the baton, ~600 samples a second; every ten seconds the hottest addresses, and for samples inside a DLL the executable's function that called in (unwound on a copy of the stack) |

`python tools/profile_resolve.py build/recomp-build/wiiboot.exe run.err
build/symbols.tsv` names the addresses with `nm`: runtime functions by their
C++ names, recompiled ones by their guest names.

Session 6's case, the nightclub of the first episode at 16-19 fps: the
renderer busy a quarter of the time; on the game's thread about 40% in
`std::ldexp` (every
`psq_l` and `psq_st` computed its GQR scale with a libm call, and the
engine skins on the CPU with quantised paired singles) and about 30% in page
faults and copies of the GX record (a fresh vector every megabyte). With the
scale built from its exponent bits and the record's buffers recycled, the
scene runs at 30 fps with the game's thread idle 60% of the time.

## The boot, step by step

What each run stopped on, in order, and what it took:

| Stop | Cause | Answer |
|---|---|---|
| `rfi` in `RealMode` | `BATConfig` sets the BATs from real mode | `RealMode` hooked to a no-op: the address space is flat |
| `OSFatal` "unauthorized device" | the device check | DI errors kept for `RequestError` |
| `OSPanic` "ROM font is available in boot ROM ver 0.8 or later" | `CROMFont::init` loads the IPL font over EXI | the boot ROM with the fonts; EXI DMA addresses in MEM2 (the mask was cutting bit 28) |
| main thread asleep in `writeEndOfFrame` | the decrementer never fired: the clock planned in time-base units and the game rewrote the time base | the clock keeps host time |
| same place, one frame per 200 µs sleep | coarse condition-variable timeouts | millisecond waits, then yields |
| same place, forever | the two-frame queue is freed by FIFO breakpoints | breakpoints reached at once, CP interrupt |
| `BTA_Init` waiting for the HCI transport | Bluetooth | WPAD/KPAD replaced |
| `__DSP_boot_task` waiting for the mailbox to empty | nothing took the mails | the ROM and AX micro-codes in HLE, taking each mail at once |
| `__AXOutInitDSP` waiting for AX's init mail | only mails with bit 31 set were delivered, so the boot task never completed | bit 31 is the mailbox's "full" flag, set by the write |
| — | `CGame::run`: the main loop | |
