# wiikit — the game-agnostic toolkit

wiikit grew here, from session 1 to session 7: everything the port needed
that was not specific to Victorious (the disc, the executable, the Gekko
decoder, the recompiler, the whole runtime). When a second port began
(Dragon Quest Swords), it was split out with its history into its own
repository, **[vs-sr-dev/wiikit](https://github.com/vs-sr-dev/wiikit)**, and
comes back here as a submodule at `wiikit/`, pinned to a known commit.

Its layers, principles, the checks behind each module and its known gaps
are in wiikit's own README, not repeated here, so that there is one copy.
How its recompiler, runtime, renderer and audio work stays written up in
this repository, with Victorious as the case: `09-recompiler.md`,
`11-runtime.md`, `12-renderer.md`, `13-audio.md`.

What Victorious gave wiikit, in short: the disc reader and extractor
(consolidated from The Last Story's and Crystal Bearers' tools), `dol`,
`cw`, `ppc`, the recompiler (session 2), the runtime's OS, IOS and
hardware (3), the GX renderer (4), the Remote on the mouse (5), the AX
mixer and audio output (6), SYSCONF and the PC window (7).

What stays here: game formats (`tools/pod.py`, `gfx.py`, `songs.py`), the
port's own layer (`tools/victorious.cpp`, `victorious-hooks.txt`,
`victorious.cmake`) and the native self-test.

A wiikit change is checked on every port before it goes in; for this one,
that means the game still boots, plays and sounds.
