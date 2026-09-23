# Curiosities

Things the disc reveals that have nothing to do with making it run.

### 1. The developers' ELF shipped on the disc

`Oscar_wii_final_versioned.elf` sits in the root of the file system, 9.7 MB,
with every symbol. It is the executable before conversion to DOL, and
byte-identical where the two overlap. "Oscar" is the codename. It survives
in the engine too: `OscarGlobals`, `OscarHudContainer`,
`OscarScreenContainer`.

### 2. The "debug" rhythm UI is the rhythm game

`CDebugRhythmGameUI::debugRender` is 14.5 KB and `CGame::renderDisplayList`
calls it every frame. It samples the inputs, times them against the beat,
keeps the score and sets the result: `vSetRhythmScoreLevel`,
`vSpawnScoreEffect`, thresholds `sGVar_fBeatTimeThreshold{Vict,Good,Okay}`.
The class was never renamed after it became the real thing. The miss counter
the Flash side updates is called `abxButtonPressedBAD`.

### 3. A PC engine underneath

The Infernal Engine started on PC, and the Wii build keeps the traces:
`CGame::readIni` / `writeIni` / `getStoredMainWindowPosSizeSettings`
compiled to empty stubs, a keyboard column in the logical control mapping,
a render layer still called `APIDLL*` after the PC's renderer DLLs, and
`D3DL` / `D3DTL` vertex-type names in its functions.

### 4. Two languages the box does not mention

The North American disc carries complete German and Italian translations
of every line. The release is catalogued as English, French and Spanish
only.

### 5. Fake credits

`video/FakeRexCredits.bik` (43 MB) is a gag, not a leftover. In episode 2,
act 3 Robbie's puppet Rex says "Granted. ROLL CREDITS!" and `e2a3.dante`
plays it. The real credits are `RealCredits.bik`, 267 MB, the biggest movie
on the disc.

### 6. A spreadsheet wrote the songs

Every rhythm chart begins "exported by SongExporter.xls" under a High
Voltage Software copyright of 2008–2012: the charts were authored in Excel
and exported to XML by a macro.

### 7. SDK libraries two years older than the game

The SDK objects say "release build: Aug 23 2010"; the game's own date
string is "Sep 20 2012".
