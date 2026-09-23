# The executable

## A symbolised twin of `main.dol`

`files/Oscar_wii_final_versioned.elf` is a big-endian ELF32 with 13 `PT_LOAD`
segments, a `.symtab` of **49 210 symbols** and a 1.46 MB string table.
Of those, **20 619 are sized functions** with their CodeWarrior-mangled C++
names, so every function comes with its class and full signature. The rest
are 23 834 data objects, including every string literal (`@NNNN`) and
vtable (`__vt__*`), plus 3 381 section symbols and 951 file symbols.

```
$ python -m wiikit.dol Oscar_wii_final_versioned.elf --same-as main.dol
  T0  80004000  2740  same
  ...
  D7  8071EBA0  5520  same
IDENTICAL
```

Every byte the retail DOL loads is the same byte at the same address in the
ELF: `main.dol` is this ELF run through `makedol`. The symbols therefore
describe the code that actually runs. `_SDA_BASE_` = `0x8071F7A0` (r13),
`_SDA2_BASE_` = `0x80726BA0` (r2).

Build: CodeWarrior with the RVL SDK. The SDK libraries carry "release build: Aug 23
2010" (one Jul 30 2010), and the game itself "Sep 20 2012".

## What is linked

`python -m wiikit.dol ELF --libs`, by naming convention:

| Library | Functions | KB | % of code |
|---|---:|---:|---:|
| Engine and game classes | 7 127 | 2 256 | 34.8 |
| Scaleform GFx | 5 994 | 2 026 | 31.3 |
| Free functions (engine C API, Dante proxies, math) | 2 898 | 973 | 15.0 |
| Wwise | 2 054 | 613 | 9.5 |
| RVL SDK | 989 | 204 | 3.1 |
| Bluetooth stack | 654 | 157 | 2.4 |
| Home Button (`homebutton`, `nw4hbm`) | 525 | 136 | 2.1 |
| MSL / runtime | 156 | 54 | 0.8 |
| Bink | 109 | 34 | 0.5 |
| TinyXML | 113 | 28 | 0.4 |

The hardware-facing part (SDK, Bluetooth, Home Button) is under 8% of the
code; everything above it, middleware included, only talks to the SDK.

## Engine landmarks

* `CGame` (`8000c230`…): `init`, `run`, `gameLoop*`, `simulate`,
  `processKeys`, `processPointer`, `renderDisplayList`, and a logical
  control layer (`08-input-and-rhythm.md`).
* **PC leftovers**, stubbed to 4 bytes on Wii: `CGame::readIni`, `writeIni`,
  `getStoredMainWindowPosSizeSettings`, and a keyboard column in the control
  mapping (`getKeyMappingForLogicalControl`).
* **Render HAL**: 93 `APIDLL*` functions (~29 KB), a D3D-like fixed-function
  API: `APIDLLtriList`, `quadList`, `polyList*`, `setTransform`,
  `setViewport`, `setFog`, `setSrcBlend`, `beginRenderToTexture`,
  `copyBackBufferToRenderTexture`, `beginShadowMapRender`,
  `beginCubeMapRender`, `setMatrixPalette`, `allocVertexBuffer`… The name
  comes from the PC engine, where renderers were DLLs. On Wii they are GX
  underneath. Models are GX vertex arrays behind `SGCPacketHeader::render`
  (`GXSetArray`), with state from `setRenderStates(int, EWiiVertexType,
  SGCPacketHeader*)`.
* **Scaleform's renderer**: `GRendererWiiImpl` (83 functions), the other
  big GX client, plus `Draw_Bink_textures` for movies.
* **Scripting**: `DanteVirtualMachine` and 747 `*_proxy__FPv` natives.
* **Threads** created by: Wwise (`CAkAudioThread`, `CAkIOThread`,
  `CAkBankMgr`), Bink (`rrThreadCreate`), the engine (`createThread`), and
  the Home Button's AX sound.

## The instruction mix

`python -m wiikit.ppc ELF --mix` over all 20 619 functions:
**1 658 815 instructions, 169 distinct operations, none undecoded**.
Paired singles: 14 224 instructions (0.86%) in 1 437 functions. Almost all
are `psq_l` / `psq_st` with W=0, I=0, which is how CodeWarrior saves f14–f31
in prologues (checked: all 1 393 functions that save them restore the same
registers from the same offsets). Only **32** are quantised (GQR 1, 2, 3, 5).
22 of them are in `APIDLLpolyListGCBoneVertex`, the skinning path, and the
other 10 in the Home Button's math, which the port drops. 719 `bctr`, mostly
switch tables; virtual calls are `bctrl`.
No REL or RSO modules exist: all code is in the DOL.
