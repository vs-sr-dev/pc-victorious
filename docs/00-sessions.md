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
