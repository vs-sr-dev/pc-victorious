# Container formats

Only what has been checked against the disc goes in here. Formats named in
`01-disc-layout.md` but not described below are not decoded yet.

## WBFS

See `wiikit/disc.py` for the layout. Checked: the partition read through the
WBFS table extracts to the same bytes as the reference extractor used for
The Last Story and Crystal Bearers.

## POD5 (Terminal Reality)

`tools/pod.py`. The PC Infernal Engine's archive, unchanged on Wii: **little
endian**, while everything the Wii SDK touches is big-endian.

Header, 0x170 bytes:

| Offset | Type | Field |
|---|---|---|
| 0x000 | char[4] | `POD5` |
| 0x004 | u32 | checksum |
| 0x008 | char[80] | comment: `Release format assets` |
| 0x058 | u32 | file count |
| 0x05C | u32 | audit entry count (equals the file count here) |
| 0x060 | u32 | revision (1000) |
| 0x064 | u32 | priority (1000) |
| 0x068 | char[80] | author (empty) |
| 0x0B8 | char[80] | copyright (empty) |
| 0x108 | u32 | index offset |
| 0x10C | u32 | index checksum |
| 0x110 | u32 | name table size |
| 0x114 | u32 | dependency count |

At the index offset: one 28-byte entry per file, then the name table.

| Offset | Type | Field |
|---|---|---|
| 0x00 | u32 | name offset into the name table |
| 0x04 | u32 | stored size |
| 0x08 | u32 | data offset |
| 0x0C | u32 | uncompressed size |
| 0x10 | u32 | compression (0 on every file of this disc) |
| 0x14 | u32 | timestamp |
| 0x18 | u32 | checksum |

Names use `\` as separator. Checked: all 7 485 entries of the seven archives
extract, and every name is a plausible path.

## Scaleform GFx movies (`.gfx`)

`tools/gfx.py`. An SWF with Scaleform's signatures: `CFX` + version + u32
length, then one zlib stream (the `CWS` form of SWF), or `GFX` uncompressed.
All 147 movies are `CFX`: 114 of version 10, 33 of version 8. Bitmaps
are external, named `<Movie>_I<hex>.tga`, as Scaleform's `gfxexport` writes
them. The ActionScript inside is readable: method names such as
`bHandleButtonPress`, `vBeatWindowOpen`, and the key constants `KEY_ACCEPT`,
`KEY_CANCEL`, `KEY_UP`…

## Dante scripts (`.dante`)

Text: the output of the Dante compiler, not source. A header, then sections:

```
// DANTE compiled program
1      // File version
1176   // VM data size
14314  // VM code size
BEGIN STRINGS
00000000 "GA_potted_plant"
...
```

Lines are tagged: `C` code symbols (`void __E1A2_init()`), `D` data
(`bool bTask1Complete`), `N` native imports with full signatures
(`bool CCastMemberBase::bNavigateTo{@CCastMemberBase}(@CActor)`), `I`
imports, and `@XXXX` reference lists. The executable exposes **747 native
functions** to the VM, the `*_proxy__FPv` symbols, and runs the programs in
`DanteVirtualMachine`. The bytecode encoding is not decoded yet; in a
recompiled port the VM runs as it is and this does not block anything.

## Levels (`.lvl`, `.sec`)

Text, `key = value`, starting with `version = 19` and the set file
(`set-filename = Master_Set.pst`). Not described further yet.

## Rhythm-game charts (`data/songs/rhythm_*.txt`)

`tools/songs.py`. XML (UTF-8 with BOM), "exported by SongExporter.xls",
© High Voltage Software 2008–2012. The events are described in
`08-input-and-rhythm.md`.

## Wwise (`.bnk`, `.wem`)

Standard Wwise: `BKHD` banks and RIFX `.wem` media with format tag 2, which
Wwise uses for DSP-ADPCM on big-endian platforms. The SDK's DSP-ADPCM decoder
is in `wiikit.dsp`. How the coefficients sit in the `fmt ` chunk is next
session's work.
