# The renderer: GX on OpenGL

Session 4 gave the runtime a window. The game's GX command stream, already
parsed in session 3, is now drawn with OpenGL 4.5 through SDL3: the Wii
Strap screen, the Bink logos, the Scaleform title and menus, and the 3D
adventure all render, at the game's own 30 frames a second.

```
wiiboot build/extract [--scale N] [--dump DIR] [--dump-every N] [--quit-after SECONDS] [--no-video]
```

| Option | |
|---|---|
| `--scale N` | internal resolution: the EFB at N × 640 × 528 |
| `--dump DIR` | a PNG of the window every `--dump-every` retraces (60 by default) |
| `--quit-after S` | leave after S seconds, with statistics |
| `--no-video` | no window: the stream is only parsed, as in session 3 |

## Two sides of one stream

The GX cut stays where session 3 put it, at the FIFO. What changed is that
the parser now produces a **record** for the renderer (`video.h`), and the
work is split by one rule: whatever reads guest memory happens on the
guest side, at the moment the game believes the GP read it.

```
guest threads (gx.cpp)                         host main thread (video.cpp)
─────────────────────────────                  ─────────────────────────────
FIFO / display lists parsed                    BP and XF mirrors
BP, XF (also from indexed arrays) ── BP, XF ─► TEV/XF config → GLSL (gxshader.cpp)
vertices via VCD/VAT/arrays      ── DRAW ───►  GL state, streaming VBO, draw
textures via TMEM palettes,      ── TEX* ───►  GL textures by id
  hashed, cached, decoded                      EFB copies: to textures, to XFB
XFB copy                         ── FRAME ──►  VI retrace: present TFBL's XFB
```

The GP is always idle in this runtime: the game sees every command consumed
at once, and may reuse a vertex buffer, a texture or a display list the
moment it has sent it. Reading them at parse time makes that safe, and the
renderer can then run behind the game on its own thread: at most two frames
behind, after which the game waits. Only one host thread ever touches
OpenGL, although several guest threads draw.

**The record.** A byte stream of BP writes (after the BP mask), XF writes,
draws with their vertices already decoded into one fixed 132-byte layout
(position, normal, binormal, tangent, two colours, eight texture
coordinates, nine matrix indices), texture uploads and binds, and frame
marks. A missing vertex colour reads as white.

**Textures** are decoded to RGBA8 (`gxtex.cpp`, the C++ side of
`wiikit.gxtex`, with the CI formats through TMEM's palettes) and cached by
address, format, size, mip levels and palette. The bytes are hashed again
only after `GXInvalidateTexAll`, which is when TMEM's cache would reload
them; rewriting a texture map's registers makes the parser look again.

**EFB copies** stay on the host GPU. A copy to a texture is converted to
what its target format would decode to (intensity formats through the
YUV weights, depth copies from the depth buffer) and remembered by address
with a hash of the RAM there: a later texture at that address is the copy,
unless the CPU has since written something else in its place. A copy to the
XFB becomes a frame, by address.

## TEV to GLSL

One program per configuration, cached under a key made of the registers
that change the code: colour channels and texgens from XF, TEV stages,
orders, konst selectors and swap tables, indirect stages and the alpha test
from BP. Everything else is data read at run time: the vertex shader reads
the whole of XF memory from a storage buffer (matrices, lights, projection,
viewport), the fragment shader gets a uniform block (TEV registers, konst
colours, alpha references, texture sizes, indirect matrices). Victorious
uses 56 programs from the boot to the first classroom.

The TEV is integer, as on the hardware and after Dolphin: A, B and C are
8-bit, D and the registers signed 11-bit, the lerp is
`(A·(256 − C) + B·C) >> 8` with C widened to 0..256, and results clamp to
0..255 or to −1024..1023. The compare modes, bias, scale, swap tables,
konst selections and the four indirect stages with their matrices, wraps,
bump alpha and "add previous" are all generated. Texture coordinates are
fixed point, texels × 128, which is the space indirect offsets live in.

Blending uses dual-source output: the TEV colour drives the blend factors
while the destination-alpha constant, when enabled, is what is written.
Logic ops, subtractive blending and colour/alpha update masks map directly;
a pixel format without alpha reads destination alpha as 1.

## Geometry conventions

* **Depth.** GX clip space runs from −w (near) to 0 (far), and the viewport
  maps it to `farZ + zRange · z/w` in units of 2²⁴. The vertex shader
  applies that before the divide, with `glClipControl` set to 0..1.
* **Rows.** The EFB is stored top row first, as on the console; the usual
  negative viewport height then needs no flip. GX's clockwise front faces
  are counter-clockwise for GL over the same rows.
* **Viewport and scissor** subtract the scissor offset register (BP 0x59),
  which carries the 342-pixel bias.

## Presenting: VI decides

On each 59.94 Hz retrace the renderer presents the XFB copy whose address
VI's top-field register (TFBL) holds. VI also decides the height: the active
lines in VTR, centred in a 480-line 4:3 screen. Victorious shows its strap
screens at 448 lines and letterboxes everything after them to 16:9: the
Bink logos, the title and the game are 640 × 360 XFBs that VI scans out as
360 of the 480 lines. Stretching them to the full screen had made everyone
a third taller.

## Two things only the pictures showed

| Seen | Cause | Answer |
|---|---|---|
| short one-pixel lines across the Bink videos, at fixed rows | Bink draws with a swizzled Y plane (640 × 448) and two chroma planes, and un-swizzles them through two tiny index textures (128 × 4 and 64 × 4) whose texels are offsets for the indirect stages. Many samples land exactly on a texel edge; the float interpolation fell a hair short of the fixed-point value (12799.9997 for 12800) and nearest filtering took the texel before | texture coordinates are rounded to fixed point, not truncated, and sampled half a unit inside the texel |
| the title screen and the game stretched vertically | the 360-line XFBs presented as full 4:3 | the picture's height from VI's active lines (above) |

## The debugging aids

| Environment | |
|---|---|
| `WIIKIT_TEXDUMP=DIR` | every texture upload (first 400, 64 × 64 and up) as a PNG |
| `WIIKIT_SHADERDUMP=DIR` | every generated program's source, and the uniforms of its first draw |
| `WIIKIT_VIDBG=1` | VI register writes |
| `WIIKIT_GLDEBUG=1` | a debug GL context, errors to the console |
| `WIIKIT_PAD="50:A 70:A 72:@0.2,-0.1"` | scripted Remote input: buttons (A B 1 2 + - H U D L R, X a shake) pressed for 150 ms at those seconds, or the pointer moved |

## A Remote for testing

Session 4 put a debugging Remote on channel 0 to get past "Press A"; in
session 5 it became the mouse-driven Remote (`08-input-and-rhythm.md`).
`WIIKIT_PAD` still scripts it, with X for a shake.

## Not done yet

* **Fog** and **Z textures**: not drawn; the parser reports them the first
  time a draw uses them. The first classroom uses neither.
* **TMEM preloads** (`GXLoadTexObjPreLoaded`): reported, not modelled. Not
  seen yet.
* **Emboss texgens** copy their source coordinates without the light offset.
* **Line width and point size** are GL's defaults.
* **EFB copies are never written to RAM**: a game that reads one back with
  the CPU would see stale memory. The **CPU's own EFB access** at
  `0xC8000000` (peek and poke) is not modelled.
* **Textures are never evicted**, on either side.
* **Pixel quantisation** of the RGBA6 and RGB565 EFB formats, the copy
  filter (deflicker) and gamma are ignored.
* Dolphin has not been used as an oracle yet: every check so far is by eye.
