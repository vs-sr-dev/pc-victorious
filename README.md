# pc-victorious

Toward a native PC port of **Victorious: Taking the Lead** (Wii, D3
Publisher / High Voltage Software, 2012), the point-and-click adventure
tie-in to the Nickelodeon series. It was a Wii exclusive and never
re-released. The goal is the game running natively on PC, with the Wii
Remote pointer replaced by the mouse.

This repository documents the disc, its formats and its code, and grows the
tooling for the port. Alongside it grows **wiikit**, a game-agnostic toolkit
for Wii reverse engineering: everything the port needs that is not
specific to Victorious.

## BYOA — Bring Your Own Assets

This repository contains **documentation and tools only**. No game data, no
executables, no assets. You need your own original disc. The work is done on
the North American release, S2VEG9.

## Layout

    docs/     disc, format and code analysis, and the plan
    tools/    Victorious-specific tools
    wiikit/   game-agnostic Wii toolkit

## Tools

Everything needs only Python 3.8+ and no dependencies (pycryptodome, if
installed, speeds up disc decryption). Run from the repository root.

```sh
# the disc: header, partitions; extract the DATA partition (.iso or .wbfs)
python -m wiikit.disc GAME.wbfs --info
python -m wiikit.disc GAME.wbfs --extract build/extract

# the executable: sections, symbols, the ELF against the retail DOL, libraries
python -m wiikit.dol build/extract/sys/main.dol --info
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf \
    --same-as build/extract/sys/main.dol
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf --libs
python -m wiikit.dol build/extract/files/Oscar_wii_final_versioned.elf \
    --symbols build/symbols.tsv

# code: a function, its callers, who builds an address, the instruction census
ELF=build/extract/files/Oscar_wii_final_versioned.elf
python -m wiikit.ppc $ELF --func readController
python -m wiikit.ppc $ELF --callers bGetShake__5CGameFi
python -m wiikit.ppc $ELF --xref 0x8079ADA0
python -m wiikit.ppc $ELF --mix
python -m wiikit.cw 'process__19CSongMoveBlockActorFf'

# the game's archives, UI movies and rhythm charts
python tools/pod.py list build/extract/files/WIICOMMON.POD
python tools/pod.py extract build/extract/files/WIICOMMON.POD build/pod/WIICOMMON
python tools/gfx.py build/pod/WIIART/flash --census
python tools/gfx.py build/pod/WIIART/flash/rhythmgamecontrol.gfx --strings
python tools/songs.py build/pod/WIICOMMON/data/songs

# standard Wii formats
python -m wiikit.u8 build/extract/files/HomeButton2/homeBtn.arc
python -m wiikit.tpl build/extract/files/HomeButton2/homeBtnIcon.tpl build/icon
```

## Status

Session 1: the disc is read and mapped, and the developers' symbolised ELF
turns out to be on it, byte-identical to the retail executable, with 20 619
named functions. The engine (Infernal Engine), the middleware (Scaleform,
Wwise, Bink) and the archive format are identified. The input question is
answered: the mouse covers the adventure, and the only motion input is a
shake in the rhythm game. The route is static recompilation with the Wii SDK
replaced. wiikit has a disc reader, an executable loader, a demangler and a
Gekko decoder checked over all 1.66 million instructions.

See [docs/00-sessions.md](docs/00-sessions.md) for the log,
[docs/06-attack-plan.md](docs/06-attack-plan.md) for the route,
[docs/07-next-session.md](docs/07-next-session.md) for what is next and
[docs/04-curiosities.md](docs/04-curiosities.md) for the interesting bits.

## Documentation

    00-sessions.md            progress log
    01-disc-layout.md         what is on the disc
    02-container-formats.md   every format, with verified layouts
    03-executable.md          the symbolised ELF, what is linked, engine landmarks
    04-curiosities.md         what the disc reveals about its making
    05-open-questions.md      what is still unknown
    06-attack-plan.md         the porting route
    07-next-session.md        the plan for the next session
    08-input-and-rhythm.md    the input path, and the rhythm game's shake
    10-wiikit.md              the game-agnostic toolkit

## Licence

MIT — see [LICENSE](LICENSE). This covers the documentation and tools in this
repository only. It says nothing about Victorious: Taking the Lead or the
Victorious series, which remain the property of their rights holders.
