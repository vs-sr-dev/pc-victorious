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
| 0x118 | u32 | dependency table checksum |
| 0x11C | u32 | audit trail checksum |
| 0x120 | char[80] | empty on this disc; the game copies it and never reads it |

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
extract, and every name is a plausible path. The entries are in name order,
and so are the payloads; each payload starts on a 32-byte boundary, the
first at 0x180 (the header, rounded up).

After the name table come the dependency records, 0x108 bytes each, then
the audit trail, one 312-byte record per entry of the audit count, to the
end of the file. The dependency count is 0 in all seven archives, so the
inside of a dependency record is not visible on this disc. An audit record:

| Offset | Type | Field |
|---|---|---|
| 0x000 | char[32] | user name |
| 0x020 | u32 | timestamp of the change |
| 0x024 | u32 | action: 0 add, 1 remove, 2 change |
| 0x028 | char[256] | the entry's path |
| 0x128 | u32 | old timestamp |
| 0x12C | u32 | old size |
| 0x130 | u32 | new timestamp |
| 0x134 | u32 | new size |

The action names and the old/new split are d3lm2's (pull request #2). On
this disc every action is 0 and the old fields are 0, as an add would
leave them; remove and change do not occur here.

**Checksums**: all five kinds are CRC-32/MPEG-2 (polynomial 0x04C11DB7, most
significant bit first, initial value 0xFFFFFFFF, no final xor; check value
0x0376E6E7 for `123456789`), over:

| Checksum | Covers |
|---|---|
| header 0x004 | header bytes 0x008–0x170 |
| header 0x10C | the entries and the name table |
| header 0x118 | the dependency table (empty, hence 0xFFFFFFFF) |
| header 0x11C | the audit trail |
| entry 0x18 | the payload as stored |

Checked: every checksum of the seven archives, `tools/pod.py verify`.
d3lm2 found the entries' CRC and named the fields at 0x118 and 0x11C
first, in pull request #2.
The same routine is in the executable as `CCrcCalc` (initial value 0 there,
and it hashes strings with their terminating NUL); nothing in the archive
code calls it.

**What the game reads** (`pod.cpp`: `CPodFile::mount`, `CPodFile::find`,
`CPod::mountDefaultPodFiles`):

* `mount` takes `POD3`, `POD4` and `POD5` (internal versions 300, 400, 500).
  POD3 and POD4 have a 0x120-byte header (`FixBytes(SPod3Header&)`), POD5
  the 0x170 one. POD3 entries are 20 bytes: no uncompressed size, no
  compression.
* Of an entry it reads the name offset, sizes, data offset and compression,
  and skips the timestamp and the checksum. No checksum is verified at
  run time, and the audit trail is not loaded. The dependency table's
  position and count are kept, but nothing in `pod.cpp` reads it.
* Archives are ranked by the priority at 0x064 (`enforceMountPriority`).
* Lookup is a binary search over the entries sorted by name with `stricmp`.
  A second mode replaces each name by `computeStringHashIgnoreCase` and
  sorts by that: `h = (h + upper(c)) * 0x12B9B2CD mod 0xFFFFFFFB` over the
  characters, in 64-bit arithmetic, from 0. Victorious mounts every archive
  without it.

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

`tools/wwise.py`. Standard Wwise, bank version 65, big-endian throughout:
`BKHD` banks and RIFX `.wem` media with format tag 2, which Wwise uses for
DSP-ADPCM on big-endian platforms.

**Banks**: chunks `BKHD`, `DIDX`/`DATA` (media kept in the bank: id, offset,
size), `HIRC` (the objects: type u8, size u32, id u32), `STID`. 39 banks in
`WIISOUND` (one per act, per rhythm game, `global`, `init`, `jukebox`), and
the voice banks with their streamed media in `WIIENSND/.../english(us)`. An
event (type 4) lists actions (type 3); a Play action (0x0403) names a Sound
(type 2: plugin, stream type, source id; type 0 keeps the media in the bank,
1 streams it from `<source id>.wem` beside the bank) or a container whose
children are Sounds. Wwise names events by the FNV-1 hash of the lower-case
name; the banks keep only the hash, but the levels post events by name
(`soundFileName = Play_...` in `.lvl`, strings in `.dante`), which names
3 469 of the 3 908 events.

**Media**: 3 408 mono, 111 stereo, all 32 kHz, each `fmt `, `smpl`, `JUNK`,
`data`. After the usual 0x12 bytes of `fmt ` come 0x0010, the channel mask
(u32) and the sample count (u32); then, from 0x1C, one 0x2E-byte block per
channel laid out as the standard DSP header from its own 0x1C: 16
coefficients, gain, initial predictor/scale and history, the loop's
(`fmt ` is 0x4C bytes mono, 0x7A stereo). The data interleaves the channels
frame by frame, 8 bytes (14 samples) each; the decoder is `wiikit.dsp`'s.
