"""Scaleform GFx movies (.gfx): unpack to a plain SWF-like stream, list strings.

    python tools/gfx.py FILE.gfx --out FILE.swf
    python tools/gfx.py FILE.gfx --strings
    python tools/gfx.py DIR --census

A GFx movie is an SWF with its own signatures: 'GFX' (uncompressed) or 'CFX'
(zlib, like SWF's 'CWS'). Byte 3 is the SWF version, 0x04 a u32 LE file
length, and in the CFX form everything after byte 8 is one zlib stream. Bitmaps
are not embedded: the movie names external images (here `<Movie>_I<n>.tga`
next to it in WIIART.POD/flash), as gfxexport produces them.
"""
import argparse
import glob
import os
import re
import struct
import zlib


def unpack(data):
    sig = data[:3]
    if sig == b"CFX":
        return b"GFX" + data[3:8] + zlib.decompress(data[8:])
    if sig == b"GFX":
        return data
    raise ValueError(f"not a GFx movie ({sig!r})")


def strings(body, n=3):
    return [m.decode("latin1") for m in re.findall(rb"[\x20-\x7e]{%d,}" % n, body)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--out")
    ap.add_argument("--strings", action="store_true")
    ap.add_argument("--census", action="store_true")
    a = ap.parse_args()
    if a.census:
        for p in sorted(glob.glob(os.path.join(a.path, "**", "*.gfx"), recursive=True)):
            d = open(p, "rb").read()
            body = unpack(d)
            size, = struct.unpack_from("<I", d, 4)
            imgs = len(set(re.findall(rb"[\w]+_I[0-9A-F]+\.tga", body)))
            print(f"{d[:3].decode()} v{d[3]}  {size:8}  {imgs:4} images  {os.path.basename(p)}")
        return
    body = unpack(open(a.path, "rb").read())
    if a.out:
        with open(a.out, "wb") as f:
            f.write(body)
        print(f"{len(body)} bytes -> {a.out}")
    if a.strings:
        print("\n".join(strings(body)))


if __name__ == "__main__":
    main()
