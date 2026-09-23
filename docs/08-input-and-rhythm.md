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
  HLE. Fill a `KPADStatus` from the mouse: position → pointer, left button →
  A, right button → B, a key → an acceleration spike. The rest of the game
  stays as it is.

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
* **Two players**: `is2PlayerRhythmGameActive`, `getActiveRhythmGamePlayer`
  need a second "controller" on PC (gamepad or a second key set).
