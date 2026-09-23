# The recompiler

`python -m wiikit.recomp GAME.elf --out build/recomp` turns the whole
executable into C++. The generated build compiles, links, and runs the game's
own code natively: 15 of 15 differential tests pass (below).

## From symbols to C++ functions

`wiikit/recomp/program.py` builds the model:

| | Victorious |
|---|---:|
| **Units**: sized function symbols in `.text`, plus non-zero gaps between them | 20 622 (20 619 functions + 3 gaps) |
| **Entry points**: unit starts, then to a fixed point: every `bl` target, every `b`/`bc` target outside its unit, every backward branch out of an inner entry's body | 20 653 |
| of which inside a unit | 31: `__save_gpr` / `__restore_gpr` (13 each), `__save_fpr`, `__restore_fpr`, 3 TRK stubs |
| **Switch tables**: `bctr` fed by `lwzx` off a `lis`/`addi` base, size from the table's data symbol | 266 |
| **Instructions** | 1 661 203 |

Every entry becomes `void f_XXXXXXXX(PPCContext& c)`, covering its code up to
the end of its unit. Inside it:

| Guest | C++ |
|---|---|
| branch inside the body | `goto L_XXXXXXXX;`; a backward one first checks for interrupts (`PPC_POLL`), or waits for one (`PPC_IDLE`) when the loop only reads the small-data area and compares, so that only an interrupt can end it |
| branch to another unit | tail call: `{ f_Y(c); return; }` |
| `bl` | `c.lr = next; f_Y(c);` |
| `blr` | `return;` |
| `bctr` with a table | `switch (c.ctr) { case ...: goto L_...; }` |
| other `bctr` (virtual tail calls: `lwz r12, off(r12); mtctr; bctr`) | `ppc_call_indirect(c, c.ctr); return;` |
| `bctrl`, `blrl` | `ppc_call_indirect`: binary search in the sorted address → function table |

Each instruction becomes one statement in its own block, so a `goto` never
jumps over an initialisation. The original disassembly follows as a comment.

**Hooks.** Functions named in `runtime/hooks.txt` (and `--hooks` files)
are generated as `orig_XXXXXXXX`, and `hooks.cpp` defines `f_XXXXXXXX` as
a slot: the runtime fills it with `ppc_hook("OSLoadContext", fn)`, which
returns the original for wrappers; an empty slot runs the original. The
list is by name, so it serves any symbolised game; Victorious has 47 of its
functions (`11-runtime.md`). `@name` lines ask for a data symbol's address.

**Safe points.** A backward branch closes a loop: 13 617 of them in
Victorious check the interrupt line, one relaxed atomic load, and call
`ppc_poll` if it is up. So does `mtmsr` when it sets MSR[EE]. `mtspr`/`mfspr`
of DEC, TBL and TBU are runtime services.

Generated files are rewritten only when their content changes: adding a
hook recompiles two files, not two hundred.

Anomalies the model reports, all harmless:

* **1 "unresolved" table**, `__ptmf_scall`: it loads CTR with `lwzx`, but
  from a pointer-to-member descriptor, not a switch table. It is emitted as
  an indirect call, which is correct.
* **2 bad targets**: `__OSDBJump`'s `bla 0x60`, a jump into the hardware
  debugger's low-memory stub. It becomes a runtime error if ever reached.
* **1 637 `.long`**: all in the gap at `0x80004380`, an 8 KB data island
  in `.init`, and 16 in the gap after `__flush_cache`. No code reaches them.

## The CPU model (`wiikit/runtime/ppc.h`)

`PPCContext`: 32 GPRs; 32 FPRs as `f[]` (ps0, as double) plus `ps1[]`; the CR
as 32 one-byte bits; LR, CTR; XER as SO/OV/CA/byte-count; FPSCR, MSR, GQRs,
segment registers, and a 1024-entry array for every other SPR.

Memory is a 4 GiB host reservation at `g_mem`, addressed directly by the
guest address. MEM1 (`0x80000000`, 24 MiB) and MEM2 (`0x90000000`, 64 MiB)
are committed (`mem.cpp`). Loads and stores byte-swap. `0xCC000000`–
`0xCDFFFFFF` goes to `ppc_mmio_read/write`: the hardware registers,
including the GX FIFO pipe at `0xCC008000`.

Gekko rules taken from Dolphin's interpreter:

* single-precision arithmetic, `frsp` and `fres` fill **both** ps0 and ps1;
  double arithmetic, `fmr`, `fneg`, `fabs` touch ps0 only;
* `lfs` loads into both halves; `lfd` into ps0;
* `psq_l`/`psq_st` (de)quantise through the GQR named by the instruction:
  float, u8, u16, s8, s16, with a signed 6-bit scale; W=1 loads 1.0 into ps1;
* `fctiw[z]` returns `0xFFF80000` in the upper word;
* `stwcx.` always succeeds: only one guest thread runs at a time.

**Known approximations**, to revisit when differential tests against
Dolphin find them:

* `fmadds` and friends compute in double and round once; Gekko rounds
  frC to 25 bits first;
* `fres`, `frsqrte`, `ps_res` and `ps_rsqrte` are exact, where the hardware
  gives an estimate from a table;
* FPSCR exception bits are not maintained (only FPCC and the rounding mode);
* `sc`, `rfi`, `tw`, MMIO, the time base and the decrementer are runtime
  services: `wiikit_stub` aborts on the first four, `wiikit_hw` implements
  them (`11-runtime.md`).

Addresses at or above `0xC0000000` take one more branch, to `ppc_io_*`: the
uncached mirrors of MEM1 and MEM2, the hardware, the locked cache.

## Building

```sh
python -m wiikit.recomp build/extract/files/Oscar_wii_final_versioned.elf --out build/recomp
cmake -S build/recomp -B build/recomp-build -G Ninja -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O1 \
      -DWIIKIT_EXTRA=$PWD/tools/selftest.cmake
ninja -C build/recomp-build
```

Generation takes 16 s and writes 201 files, 124 MB. With clang 22 at `-O1`
on 18 threads the build takes 1 min 38 s: a 73 MB static library, and a
58 MB link-check executable holding all 20 653 functions. No generated
function fails to compile.

The generated build is a static library `recomp` plus the runtime
(`runtime/runtime.cmake`): `wiikit_core` (memory, dispatch, hooks) with
either `wiikit_stub` (no hardware: `linkcheck`, `selftest`) or `wiikit_hw`
(`wiiboot`, the game). `-DWIIKIT_EXTRA=file.cmake` lets a project add its
own targets.

## Differential tests: the game's code, run natively

`tools/selftest.cpp` loads the retail `main.dol` into guest memory, sets r1,
r2 and r13, and calls recompiled functions by name, checking each result
against the host:

```
$ selftest build/extract/sys/main.dol build/symbols.tsv
main.dol loaded, entry 80006310, 20598 symbols
strings
  ok    strlen  26
  ok    strcmp less
  ok    strcmp equal
  ok    atoi  -4242
  ok    strtod  314.159000
sprintf (varargs, integers, strings, doubles)
  ok    sprintf  "Tori has 12345 fans, 99.500% hip, 0xDEADBEEF, [Jade  ] 1.2346e+03 0.000125"
64-bit integer helpers
  ok    __div2i / __mod2i / __div2u on 2000 random pairs
libm
  ok    sin / cos at 7 points  worst |error| 3.81e-21
qsort through game comparators (indirect calls)
  ok    qsort 200 ints with fileEntryCmpFuncByNameHash
  ok    qsort 12 names with sortMe (case-insensitive)  Andre Beck cat festus jade Lane rex Robbie sikowitz Sinjin tori Trina
SDK matrix library (paired singles)
  ok    PSMTXConcat  max |error| 1.91e-06
  ok    PSMTXMultVec  max |error| 0.00e+00
  ok    PSMTXInverse  |A * inv(A) - I| 9.54e-07
memcpy / memset (the game's, FPR-based copies)
  ok    memcpy, 200 random sizes and alignments (bit-exact through FPRs)
  ok    memset
15 passed, 0 failed
```

What each test exercises:

* **`sprintf`**: the PowerPC varargs convention (a register save area filled
  in the prologue, CR1[eq] flagging FP arguments) and MSL's number
  formatting. Byte-identical to the host's output.
* **64-bit helpers**: carry chains (`addc`/`adde`/`subfe`), `cntlzw`,
  shifts across register pairs.
* **`qsort`**: callbacks through `ppc_call_indirect`, and a comparator that
  tail-calls `__tri_stricmp`.
* **Paired-single matrix code** (`PSMTXConcat`, `PSMTXMultVec`,
  `PSMTXInverse`): `psq_l`/`psq_st`, `ps_madd`, `ps_merge*`, `ps_sum*`.
* **`memcpy`**: 8-byte copies through `lfd`/`stfd`, which must be bit-exact
  for any data, NaN patterns included.

## The runtime

Phase 2 built it: `11-runtime.md`.
