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

### 12. Bink's frames are stored scrambled

On the Wii, Bink does not hand GX a picture. Its luma plane (a 640 × 448
I8 texture for a 640 × 360 video) and its two chroma planes are stored in
a scrambled order, and two tiny index textures, 128 × 4 and 64 × 4, hold
offsets: a column step of eight texels and a row step of one per unit.
Drawing a frame takes five TEV stages and two indirect stages that use
those offsets to fetch each pixel's Y, Cb and Cr from where the decoder put
them, then signed colour registers to turn YCbCr into RGB. Offsets like
these land exactly on texel edges, which is why a renderer that rounds its
texture coordinates the wrong way draws stray lines across the video
(`12-renderer.md`).

### 13. Everything after the strap screen is letterboxed

The Wii Strap and health screens are 448-line pictures. From the Bink
logos on, the game renders and copies 640 × 360 frames, 16:9, and has VI
scan them out as 360 of the 480 lines, black above and below: widescreen
presentation on a 4:3 setting, done in the video interface rather than
in the renderer.

### 14. The cursor is smoothed twice

KPAD already smooths the Remote's pointer (`KPADSetPosParam`). The
adventure cursor then smooths it again: each frame it moves 30% of the way
to where the Remote points, and ignores moves under 0.02. On a Remote held
in the air that turns a trembling hand into a steady cursor; under a mouse
it is a cursor that trails about a fifth of a second behind
(`08-input-and-rhythm.md`).

### 15. The control table remembers cars and boats

Of the 42 logical controls `setDefaultControlMapping` sets up, the game
asks for four: the pointer's two axes, A and B. Most of the others are read
only by `CCar::process`, `CBoat::process`, `CPhysBallActor` and a
free-flying debugging camera, driven by the Nunchuk's stick. They are the
Infernal Engine's, from games where one drove; nothing in Hollywood Arts
calls them.

### 16. The rhythm game can be played in silence

For a session the port had no sound: AX ran and mixed nothing. The rhythm
game was played through anyway, every press, hold and shake landing in its
window. Its beats come from Wwise (`soundBeatCallback`), which counts the AX
frames it renders whether or not anyone hears them, and the screen carries
the rhythm too: the icons slide along a track to the press point and pulse
on the beat.

### 17. Promo codes, in plain text

The options menu has a "Promo Code" screen. `PromoCodeScreen::vInitialize`
copies nine five-digit codes out of the executable, one set for North
America and one for everywhere else (`bIsNorthAmericanBuild`), each made of
the digits 1 to 5 only. Each unlocks something once (a flag, a group of
forty-two or sixteen items, the "Romeo & Juliet" finale level, or 500 more of a
saved counter); a code already used says so. For the North American disc
they are 55521, 41332, 52311, 21154, 31543, 13524, 53142, 42111 and 55242.

### 18. A plot twist from the sound library

When Jade's twist lands in the second episode's cinematic, the game plays
`Play_JadeStingerCine2` (bank `e2a1`, streamed `550380195.wem`, 4 seconds,
stereo): a few dissonant orchestral notes rising to a hit. Heard in play and
recognised by ear, it is a stock effect: Sound Ideas' "Suspense Accents —
Orchestral Suspense Climax Accent" (on *Elements Café 10 Production
Elements*), the same as Dick De Benedictis' "Evil Mind 3", and the sting of
countless cartoons, SpongeBob SquarePants and Phineas and Ferb among them,
and of today's "plot twist" clips. A Nickelodeon game scored from the same
shelf as Nickelodeon's shows.

The cinematics have a dozen such stingers (`python tools/wwise.py events
build/pod | grep -i sting`); `Play_IntroStingers` holds six of them, and the
first cinematic's reuses the second's closing one.

### 19. A rap sheet, under California law

The game's puzzles are solved the sitcom way, and Hollywood Arts is in Los
Angeles. Read with the California codes at hand (for fun, not as legal
advice), from the English lines in `WIILANGUAGE/world/en` (act 3.2 is
episode 3, act 2):

* **Jade cuts up Tori's script** (episode 1, act 5): "I sort of cut and
  scattered the pages", "Cut them up, and threw them away"
  (`E1A5C02L17`, `L27`). Vandalism (Penal Code § 594) to the value of a few
  sheets of paper, littering (§ 374.4), and a confession nobody asked for.
* **Jade buys Pear Pads for the boys only** (2.1, 2.4), and the boys are
  the four judges Sikowitz names for the "Audition-Off" (`Cinemat_E2L14`).
  Gifts to the judges of a school audition break no statute: bribery is of
  public officials, vote-buying is in public elections, commercial bribery
  is of employees. A matter for the school's rules.
* **Tori holds Trina's joke book** until she dances near Robbie: "I'll give
  it back after you dance near Robbie"; Trina: "Ok, I get it. It's a hostage
  situation" (2.3, `E2A3C08L12`, `E2A3C20L03`). Property kept to force an
  act is in the neighbourhood of extortion (§ 518).
* **Tori can show Trina's diary** around: the game has an answer for Andre
  ("her penmanship is terrible"), Cat and Robbie, who learns from it that she
  would rather kiss Rex (`E2A3C14`). How far it goes is the player's choice;
  each reader is one more count of public disclosure of private facts, a
  privacy tort.
* **Robbie's Pear Pad**: "Aw man! I dropped my Pear Pad! I guess the
  Internet was right -- they do spontaneously combust!" (`E2A3C10L01`).
  Dancing near someone is no tort and he dropped it himself; a tablet that
  bursts into flames when dropped is Pear's problem, under the strict product
  liability California's Supreme Court created (*Greenman v. Yuba Power
  Products*, 1963). Tori's next line asks him for his vote (`L04`).
* **Sinjin's method**: "I just record Jade saying lots of things, then edit
  it so that she... says how much she loves me" (`E2A4C06L10`). He keeps a
  copy of the one he cuts for Tori "to add to my Jade collection" and shows
  he can do the same to Tori's voice (`E2A4C08L02`, `L06`). California is an
  all-party-consent state: recording a confidential conversation needs
  everyone's consent (§ 632). His advice when Jade will not say "bribed" is
  "So, bribe her", and Tori tries (`E2A4C06L17`, `E2A4C07L33`).
* **The spliced sentence**, "I bribed everyone with Pear Pads"
  (`E2A4C08L03`), is forged in its words and true in its facts: Jade has
  just said "I don't think you understand why I bought them for the boys"
  (`E2A4C07L26`). Truth is a defence to defamation. It never comes to
  that: Beck hears it once and says "Sounds like some good splicing by
  Sinjin?", and Tori owns up on the spot (`E2A4C09L04`, `L05`). A recording
  fails authentication when the school already knows who edits them; the
  act's puzzle chain, recorder, words, bribe and splice, ends in one line.

Episode 3 raises the money for the school play, and the record grows:

* **The bake sale's ingredients** (3.2). The frosting is earned from
  Festus and the coconut is Sikowitz's gift, but the cherries come from the
  drinks at Karaoke-Dokie, "I'm sure they're ok with me borrowing a few
  cherries", and the vanilla extract from a fancy restaurant: "I have a
  vanilla emergency... I'll just borrow this" (`E3A2C16L01`, `L02`).
  Borrowing does not cover what goes into the dough: taking property
  without consent, to keep, is petty theft under $950 (Penal Code §§ 484,
  488). The game knows. Examined, the cherries make Tori ask "Am I a
  horrible person? Did I just steal these?" (`Examine_Cherries_01`). Nobody
  answers.
* **Trina's raffle** (3.3), at a party at the Asphalt Café, sells tickets
  for the play. California allows raffles only to private non-profits
  qualified in the state for at least a year, registered with the Attorney
  General every year, and giving at least 90 % of the takings to charitable
  purposes (§ 320.5). Two sisters at a party are none of these. Without
  that exception, a prize, chance and a price make a lottery, and drawing
  one is a misdemeanour (§§ 319, 320). Then comes the draw. "...AND THE
  WINNER OF THE RAFFLE IS... OTIS!" "...what do I win?" "errrr... a
  prize! [...] I forgot. Just give him something" (`E3A3C16L01`–`L08`).
  The player chooses from a saw, a cup o' cheese, a hot dog, mystery meat,
  or a fizzy drink at a party where drinks are free (`E3A3C17`). § 320.5
  defines a raffle as the distribution of prizes by chance among people
  who have paid. Here the prize was chosen after the draw, by whoever
  carried it over.
* **Otis's pay** (3.4): "Do you realize I'm paid in bags of old potato
  chips?", and "Principal Dickers sometimes doesn't pay me. He says it
  builds 'character'" (`E3A4C18L02`, `E3A4C25L08`). Wages are paid in
  money. Labor Code § 212 forbids paying them in anything redeemable
  "otherwise than in money", and § 220, which spares public employers
  several of the wage rules, does not spare them this one. Old chips are
  not even redeemable.
* **Dickers's detentions** (3.5). Before he will hear Tori out, the vice
  principal hands her three slips, "already signed", that make "whoever I
  give it to [...] serve detention tonight": "I don't care who gets them,
  just get'em out there", then "better yet, give them to your friends,
  Vega" (`Examine_Detention_Slip`, `E3A5C08L11`, `E3A5C09L07`). Detention
  is the staff's answer to a pupil's own conduct, and it may last at most
  one hour after the close of the school day (California Code of
  Regulations, title 5, § 353). No rule foresees blank punishments signed
  in advance and handed out by a pupil as the price of a meeting. Told
  that her outfit is too cute, Cat agrees to serve. Trina refuses,
  with a threat to tell their mother "about the time you snuck out of the
  house" (`E3A5C22L04`, `E3A5C24L03`): extortion again, this time by
  threatening to expose a secret (§ 519).

The villain's record is the lightest: a few cents of paper and some gifts.
The heroine's holds coercion, a diary exposed as widely as the player
likes, two petty thefts and three detentions served by the innocent. The
worst records belong to Sinjin and to the school's vice principal.

### 20. Jade will not dance

Every rhythm game has its character's own lines (`Play_Rhythm<Name>_*`,
spoken in English and subtitled in the other languages' `rhythm_*.txt`).
They cheer the player on, and the character dances. Jade stands still and
talks about the game itself, in ten asides of her own
(`Play_RhythmJade_Jade_01` to `_10`, also in her hard version). Heard in
play: "Ooh, look at the sparkly things!" (the sparks a good press throws)
and "Let go of the button!". The subtitles give the rest: is that good,
is that the best you can do, a timing game, huh, this noise gives her a
headache, does she have to stand here, and don't expect her to dance.
Her intro asks whether they are really playing a game. Her outro grants
that the score is not bad, and says not to expect her to do it again. No
other character's lines mention the game.

### 21. The credits roll to "Take a Hint"

After the finale, three rhythm games in a row that stage the school's
Romeo and Juliet (`balcony`, `crypt`, `masquerade`, remixes of the game's
songs with period instruments), the credits play to "Take a Hint", sung
in the series by Victoria Justice and Elizabeth Gillies (Tori and Jade).
It is also the last of the five songs on a jukebox in the game
(`Juke_Box_09` in `ui.txt`). The credits are a movie,
`RealCredits.bik`, so their text is pixels, and one name is misspelt in
them: the Italian localisation's Paola Menzaghi is credited as "Paola
Menazghi". The chart files carry a typo too: the masquerade's is
`rhythm_maquerade.txt` ("exported by SongExporter.xls" as
`Rhythm_Maquerade.xml`), while its sound bank and subtitles are spelt
right.
