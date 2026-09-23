# wiikit — the game-agnostic toolkit

## The idea

The same idea as [ps2kit](https://github.com/vs-sr-dev/pc-extermination/tree/main/ps2kit),
for the Wii. Each Wii game has its own engine and formats, but a large part
of every port is the *same* work: the same disc encryption, executable
formats, CPU, SDK and GPU. wiikit collects that shared part. It grows inside
this project: each piece is written because Victorious needed it, then kept
free of Victorious-specific knowledge. Game formats (POD5, Dante, song charts)
live in `tools/`.

Some of it was first written for two earlier Wii studies (The Last Story and
Final Fantasy Crystal Chronicles: The Crystal Bearers): the disc extractor,
the GX texture decoder, TPL, U8 and DSP-ADPCM. Here those pieces are
consolidated into one package, with dependencies removed.

## Layers

| Layer | Question it answers | Now | Next |
|---|---|---|---|
| 1. Recognise | What is on this disc? | `disc --info`: game id, partitions, WBFS usage | a `fingerprint`: magics, SDK library dates, middleware found by symbol or string (Scaleform, Wwise, Bink, NW4R, Home Button) |
| 2. Extract | Turn standard formats into standard files | `disc` (ISO and WBFS, AES, FST), `u8`, `tpl`, `gxtex`, `dsp` | palette formats C4/C8/C14X2, BRSTM/BRSAR, THP, BNR |
| 3. Map code | What does the code do, where? | `dol` (DOL and ELF, one address map, symbols, `--same-as`, `--libs`), `cw` (CodeWarrior demangler), `ppc` (Gekko decoder with paired singles, disassembly, callers, lis/addi and SDA xrefs, instruction census) | switch-table recovery, SDK function signatures for stripped games, FIFO log decoding from The Last Story |
| 4. Translate | Turn Gekko code into C++ | — | the recompiler (session 2 onward) |
| 5. Runtime | Replace the hardware | — | OS, DVD, NAND, KPAD, VI, AX mixer, GX FIFO renderer |

## Principles

* Pure Python, no dependencies, for layers 1–3. The ps2kit rule applies here
  too. The one exception is speed, not function: `aes` uses pycryptodome
  when it is installed (1.3 MB/s in pure Python, a whole disc in about 18
  minutes, against seconds), and gives the same bytes either way.
* Every claim is checked on a real disc before it goes in.
* Game knowledge stays out.

## Checks behind each module

| Module | Checked by |
|---|---|
| `aes` | the FIPS-197 C.1 vector; equal to pycryptodome on a random cluster and on disc data (`python -m wiikit.aes`) |
| `disc` | re-extraction equal to the previous extractor for all 46 files. `main.dol` is now cut at the end of its last section (the old extractor ran on to the FST, 192 bytes more) |
| `dol` | `--same-as`: all ten DOL sections equal in the ELF |
| `cw` | 20 619 of 20 619 function names demangled, including templates, conversion operators and anonymous namespaces |
| `ppc` | 1 658 815 instructions, none undecoded; equal to capstone on every non-paired-single instruction up to standard aliases; paired-single fields checked by prologue/epilogue symmetry in 1 393 functions |
| `gxtex` | The Last Story: byte-identical to textures Dolphin dumped from the running game |
| `tpl`, `u8` | the Home Button archives on this disc (105 files; the icon decodes correctly) |
| `dsp` | Crystal Bearers' audio, by ear and spectrogram |

## Known gaps

* `ppc.text` renders standard simplified mnemonics (`sub`, `clrrwi`, `mr.`,
  `crclr`…). Tools that need the canonical operation use `decode()`'s
  `op` and fields, never the text.
* Constant tracking in `ppc.Tracker` is linear through a function and
  ignores control flow. That is enough for CodeWarrior's `lis`/`addi` pairs;
  a real data-flow pass will come with the recompiler.
