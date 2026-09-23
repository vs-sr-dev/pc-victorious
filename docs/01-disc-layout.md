# Disc layout

The work is done on the North American release.

| | |
|---|---|
| Title | Nickelodeon Victorious: Taking the Lead |
| Game ID | `S2VEG9` (G9 = D3 Publisher) |
| Developer | High Voltage Software, on Terminal Reality's Infernal Engine |
| Box languages | English, French, Spanish |
| Dump | WBFS, 2 MiB sectors, 712 of 4 482 stored (1.49 GB) |
| Partitions | one, DATA at `0xF800000`, title id `00010000 53325645` |

`python -m wiikit.disc GAME.wbfs --info` prints the above;
`--extract out/` writes the partition as `sys/` + `files/`.

## `sys/`

| File | Size | Notes |
|---|---:|---|
| `main.dol` | 7 465 280 | 2 text + 8 data sections, entry `0x80006310`, bss `0x8071D320`+`0x2F6C7C` |
| `fst.bin` | 1 268 | 46 files |
| `boot.bin`, `bi2.bin`, `apploader.img` | | standard |

## `files/`

| Path | Size | What it is |
|---|---:|---|
| `Oscar_wii_final_versioned.elf` | 9.7 MB | **The linker's ELF, with its symbol table.** Its loaded bytes equal `main.dol` section for section (`03-executable.md`) |
| `WIIART.POD` | 89 MB | UI: Scaleform movies (`flash/*.gfx`) and their bitmaps (`*.tga`), 2D art, materials |
| `WIICOMMON.POD` | 107 MB | world: levels, Dante scripts, animations, skeletons, physics, effects, cinematics, song charts |
| `WIIMODEL.POD` | 7 MB | models (`.smb`, skinned `.bfm`) |
| `WIISET.POD` | 37 MB | the sets (`.bst`): master set, rhythm stages |
| `WIILANGUAGE.POD` | 2.4 MB | all text, five languages |
| `WIISOUND.POD` | 326 MB | Wwise banks and streamed media: music, effects |
| `WIIENSND.POD` | 188 MB | Wwise, English voice |
| `video/*.bik` | 690 MB | 22 Bink movies: logos, rhythm-game backgrounds, credits |
| `HomeButton2/` | 3.8 MB | the SDK's Home Button menu (U8 archives, TPL, CSV) |
| `banner*.tga`, `icon.tga`, `opening.bnr` | | save banner and icon, channel banner |
| `us.txt` | 2 | the two bytes `us` |

## Inside the PODs

7 485 files, none compressed (`tools/pod.py`). By type:

| Type | Files | MB | |
|---|---:|---:|---|
| `.wem` | 3 519 | 493 | Wwise media: RIFX (big-endian), Nintendo DSP-ADPCM, mostly mono 32 kHz |
| `.tex` | 1 032 | 56 | engine textures |
| `.tga` | 840 | 31 | Scaleform bitmaps, plain TGA |
| `.bnk` | 75 | 19 | Wwise sound banks |
| `.ani` | 625 | 17 | animations |
| `.cinemat` | 6 | 78 | cinematics, one per episode plus menus |
| `.bst` | 11 | 37 | sets |
| `.lvl` / `.sec` | 41 / 29 | 7 | levels and level sections, **text** |
| `.dante` | 42 | 3.6 | Dante scripts, compiled but **text** |
| `.bfm` / `.smb` / `.skb` / `.mtb` | 36 / 228 / 19 / 432 | 7 | skinned models, static models, skeletons, materials |
| `.gfx` | 147 | 0.5 | Scaleform movies |
| `.txt` | 293 | 2.6 | dialogue and UI text, song charts, lists |
| others | | | `.tfb` effects, `.phys2b` physics, `.cib` character info, `.atb` animation tables, `.fnt` fonts, `.sbs` |

## How the game is cut

`world/level_list.txt` and the script names give the structure:

* **four episodes of five acts**, `e1a1` to `e4a5`, each a `.lvl` + `.dante`
  pair with a per-act text file in every language;
* `master_set`, the shared stage;
* `romeojuliet_finale`;
* **19 rhythm games**: Andre, Beck, Cat, Jade, Robbie, Sikowitz, Sinjin,
  Trina, each with a "hard" version, plus balcony, crypt and masquerade.
  Each has a chart in `data/songs/` (`08-input-and-rhythm.md`).

## Languages

Text comes in **five** languages, not the three on the box: `de`, `en`,
`es`, `fr`, `it`. Voice is English only (`WIIENSND.POD`, folder
`english(us)`). English has 48 text files, the others 56: English has no
`rhythm_*` files, which subtitle the rhythm-game lines that are only spoken
in English. It has a `master_set.txt` the others lack.
