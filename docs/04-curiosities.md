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

### 8. The disc checks the drive for a modchip

Before `main` runs, the SDK's `__DVDCheckDevice` asks the drive for two
things a genuine Wii drive refuses: raw sectors past the end of the disc,
and a DVD-video key. If either succeeds, the drive is a modified one and the
game stops at "Error #001, unauthorized device has been detected", in the
console's language. An emulated drive has to fail both, with the right error
codes (`11-runtime.md`).

### 9. The error handler is called `reallyGTFO`

The engine's fatal-error function is `reallyGTFO(const char*, ...)`, fed by
two globals, `gtfoSourceFile` and `gtfoSourceLine`. It guards things like
"Frame queue is full!" and "Can't allocate memory for the wpad, there's big
trouble."

### 10. A GameCube font check in a Wii game

A static constructor in `gcutil.cpp` loads the console's boot-ROM font with
`OSInitFont` and panics if it cannot: "ROM font is available in boot ROM
ver 0.8 or later". The file name and the message are GameCube-era; the font
sits next to `ui\wii_controller_buttons.tga` in the same object.

### 11. The OS asks for a password to set up memory

`BATConfig`, which maps MEM1 and MEM2 through the BAT registers, ends in a
loop that never exits unless its argument is `0xBA2CF`. The SDK's own caller
passes it; anything else calling the function hangs there.
