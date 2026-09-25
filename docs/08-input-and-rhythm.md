# Input, and the one place motion matters

The question: is replacing the Wii Remote pointer with the mouse enough, or
do some minigames need real motion input?

**Answer:** the pointer covers the whole adventure. The only motion input is
a **shake** (a threshold on acceleration) in the **rhythm game**, where it is
also the most common event. There is no 3D pointing, swing, tilt or
MotionPlus. On PC a key does the job; a quick mouse flick can be an option.

## The input path

```
KPADRead ──► pollControls() ──► readController(int, KPADStatus*)    805FA500, 2148 B
                                     │  44 × SController::setButtonState
                                     ▼
                         SController[n]   stride 0x3C9C, array at 80861398
                                     │  +0xC8: the shake value (float)
                                     ▼
                         SControlInstance: logical controls by tag
                         isPressed / justPressed / getControlState(i)
                                     │
      ┌──────────────────────────────┼─────────────────────────────────┐
 CGame::processPointer          CAdventureCursor               CScaleformGFx::addWiiPointer
 (getControlState × 2 = x, y)   the point-and-click cursor     the pointer as the GFx mouse
```

* `CGame` has a **logical control layer**: `findLogicalControlByTag`,
  `get{Axis,Button,Key}MappingForLogicalControl`, `setDefaultControlMapping`,
  `debounceControls`. The key column comes from the PC engine and does
  nothing on Wii.
* Scripts barely touch input: `enableCURSOR(int)` (40 calls) and
  `rumbleController(int, float)` (1). `bShake(int)` is exported to Dante but
  **no script calls it**. The "bShake" in the `.dante` files belongs to
  `bShakespeareQuestActive`.
* **Where the port plugs in:** `readController`, or `KPADRead` itself as
  HLE (the choice made: see below). Fill a `KPADStatus` from the mouse: position → pointer, left button →
  A, right button → B, a key → an acceleration spike. The rest of the game
  stays as it is.

## What `readController` makes of a `KPADStatus`

Read out in session 5 (`805FA500`). Each Remote fills one `SController`
(stride `0x3C9C`, `gController` at `80861398`): the axes as floats from
`+0x90`, the buttons as ints from `+0x690` (the previous frame's copy at
`+0x750`).

| `SController` | From `KPADStatus` | |
|---|---|---|
| `+0x90`, `+0x94` | `ex_status` stick x, −y | Nunchuk only, else 0 |
| `+0x98..+0xA0` | `acc` | and its change from the last frame at `+0xCC..+0xD4` |
| `+0xB0`, `+0xB4` | `pos` | the pointer, −1..1; 0 when `dpd_valid_fg` is 0 |
| `+0xB8` | `dist` | |
| **`+0xC8`** | **`acc_speed`** | the shake |
| `+0x3C98` | `dpd_valid_fg` | the pointer is on the screen |

Button slots (`setButtonState(slot, …)`): 0 A, 1 B, 2 1, 3 2, 4 +, 5 −,
6 Home, 7 Z, 8 C, 9–12 the d-pad (turned with the Remote's orientation,
`+0x88`), 13–15 tilts (`acc × acc_value > 0.05` per axis), and 0x1C–0x1F A,
1, 2, B again.

**The shake** (`CGame::bGetShake`): `|acc_speed| ≥ sGVar_fShakeThreshold`
(**0.4**), in each of the last `sGVar_nShakeFramesFilter` (**2**) frames
of a five-frame ring. `acc_speed` is KPAD's change of acceleration between
samples: a Remote swung hard, not a Remote tilted.

## The logical controls

`CGame::setDefaultControlMapping` fills 42 entries of 0x1C bytes: a source
(button slot, axis or key), a type (1 button, 2 and 4 axis, 3 key, 5 key
pair, 7 axis as a button) and flags. What the executable actually asks for
(`isPressed`, `justPressed`, `justReleased`, `debounce`, `getControlState`
with a constant):

| Control | Source | Asked by |
|---|---|---|
| 0x10 | axis 8, pointer x | `CGame::processPointer`; `CCar`, `CBoat` |
| 0x14 | axis 9, pointer y | `CGame::processPointer`, `CGameView::process` |
| **0x18** | slot 0x1C, A | `CAdventureCursor::vUpdateInput`, the rhythm game's `updateInput`, `loadThreadProc` |
| **0x19** | slot 0x1F, B | `CAdventureCursor::vUpdateInput`, `updateInput` |
| 0x06, 0x08, 0x0A–0x0D, 0x11–0x13 | buttons, the Nunchuk stick | `CPhysBallActor`, the free-flying camera, `processSlewControls`: engine leftovers and debugging |

The game proper needs **the pointer, A and B**, and the shake for the
rhythm game. The menus read the button slots directly
(`SScaleformController::handleInput` turns every slot into a Scaleform key;
`processMenuControls` opens the pause menu on **+**), and the Home button
runs the SDK's own Home Button menu (`wiiHandleHomeButton`: `HBMCreate`,
`HomeButton2/`, `HBMCalc`/`HBMDraw` in its own loop).

## The mouse as the Remote (session 5)

The cut is `KPADRead` (`wpad.cpp`), with the Remote on channel 0:

| Remote | PC |
|---|---|
| pointer | the mouse over the picture |
| A | left button, Enter |
| B | right button, Backspace |
| d-pad | W A S D, the arrows |
| + | Tab |
| − | Q |
| 1, 2 | 1, 2 |
| shake | Space, middle button |
| Home | none: Esc opens the port's own pause box (Resume / Quit) |

Since session 7 the buttons come from a key file, `build/keys.txt` (next to
the extracted disc; `--keys FILE` for another), written with the defaults
above when there is none. Each line is a Remote button, then the keys (by
SDL's names) and mouse buttons (`Mouse Left`, `Right`, `Middle`, `X1`,
`X2`) that press it:

```
A     = Return, Keypad Enter, Mouse Left
Shake = Space, Mouse Middle
```

A name SDL does not know is reported and skipped. Esc, F11 and Alt+Enter
(fullscreen) are fixed; with Alt held, Enter is not A.

* **The pointer** is −1..1 across the picture as it is shown: the width
  of the screen (4:3 or 16:9, as SYSCONF says), and only the lines VI scans
  out (448 of 480 at 16:9; 360 on a 4:3 console, where the game letterboxes
  16:9). Mapped over the whole 4:3 screen, the cursor had moved a quarter
  less than the mouse vertically. The presenter and the mouse share one
  rectangle, whatever the window's shape or fullscreen. The game turns `pos` into pixels
  with `SController::getPointerXY`, linearly over `PIXX` × `PIXY`. Over the
  picture the Windows pointer is hidden: the game draws its own.
* **The cursor's smoothing.** `CAdventureCursor::vUpdateInput` moves the
  cursor 30% of the way to the pointer each frame (0.3 at `@35897`), once
  it is more than 0.02 away: at 30 frames a second it takes about 220 ms to
  cover 90% of a move, which hides a Remote's tremor and turns a mouse into
  lag. The port's layer (`tools/victorious.cpp`) runs the original, then
  puts the cursor on the target, as the game itself does when the pointer
  comes back onto the screen. The constant is shared with the cursor's alpha
  fade, so it is not patched. With that, the cursor lies under the mouse, one
  to one.
* **The shake** swings the acceleration ±2 g along x from one sample to the
  next while the key is held: `acc_speed` is 2 on the first sample and 4
  after, far over 0.4. Holding the key is a Remote shaken without pause.
* **Home** reaches the game from no key. Its Home Button menu would ask for
  "Wii Menu" and "Reset", which mean nothing on a PC; Esc opens a native box
  instead, which also pauses the game (the renderer stops, and the game
  with it once its two-frame queue is full).

## The rhythm game

* **Charts**: `WIICOMMON/data/songs/rhythm_*.txt`, one per song, parsed by
  `CSongMoveBlockActor::ReadXMLData*` (TinyXML). `<SongInfo>` gives the
  tempo (`BaseAnimSpeed`), the measure counts, the background Bink movie and
  camera zoom measures. Each `<Measure>` can carry animations and events:

  | Tag | Meaning |
  |---|---|
  | `APress<n>` / `BPress<n>` / `XPress<n>` | press on beat n |
  | `A2On<n>` / `A2Off<n>` / `A2Cnt<n>` | a held A |
  | `CheckOnOff` | scoring on or off |

* **UI**: `RhythmGameControl` (C++) drives `rhythmgamecontrol.gfx`
  (ActionScript) with `bHandleButtonPress`, `vHandleButtonRelease`,
  `vBeatWindowOpen/Closed`, `vBeatTrailReleaseWindowOpen`. The button
  index (0–2) travels in the `FlashEvent` at `+0x10`;
  `abxButtonPressedBAD[3]` counts misses per button.
* **Scoring**: in `CDebugRhythmGameUI::debugRender` (14.5 KB), called every
  frame from `CGame::renderDisplayList+0x41C` despite the name
  (`04-curiosities.md`).
* **Input sampling**: `updateInput()` (`8009D800`) fills
  `abxButtonPressed[3]`:

  ```
  [0] = isPressed(logical control 0x18)   A
  [1] = isPressed(logical control 0x19)   B
  [2] = CGame::bGetShake(0)               X = shake
  ```

  `bGetShake(n)` = `|SController[n].+0xC8| > sGVar_fShakeThreshold`.

* **Events over all 19 charts** (`python tools/songs.py .../data/songs`):

  | A | B | X (shake) | held A |
  |---:|---:|---:|---:|
  | 619 | 561 | **1 040** | 115 |

* **Timing** is driven by audio: `CSongMoveBlockActor::soundBeatCallback`,
  from Wwise. A port with loose audio timing would put the rhythm game out
  of sync.
* **Two players** take turns on one Remote. `updateInput` reads controller
  0 whoever plays (`isPressed`, `bGetShake(0)`); the active player
  (`GameGlobals+0x24D18`, set to the first by `RhythmSelectScreen` and moved
  on by `AfterActionReviewScreen` after each song) only decides whose score
  `debugRender` keeps. On a PC the mouse is passed, as the Remote was.
