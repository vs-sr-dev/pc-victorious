"""Wwise sound banks and media: named events, and .wem to WAV.

    python tools/wwise.py events POD [--all]       # each named event: bank, media, length
    python tools/wwise.py wav POD OUTDIR NAME...   # an event's sounds as WAV files
    python tools/wwise.py wem FILE.wem OUT.wav     # one .wem as a WAV file

POD is the extracted pod directory (build/pod). The banks are Wwise v65,
big-endian: chunks BKHD, DIDX/DATA (media kept in the bank), HIRC (the
objects), STID. Wwise names events by the 32-bit FNV-1 hash of the
lower-case name; the names themselves are not in the banks, but the levels
and scripts that post them carry them (`soundFileName = Play_...` in .lvl,
strings in .dante, and the executable). An event's Play actions (type
0x0403) point at a Sound (its source is in the bank or a streamed
<id>.wem beside it) or at a container whose children are Sounds.

The media are RIFX, format tag 2: Nintendo DSP-ADPCM, 32 kHz, mono or
stereo. After the usual 0x12 bytes of `fmt ` come 0x0010, the channel mask
(u32) and the sample count (u32); then, from 0x1C, one 0x2E-byte DSP header
tail per channel (16 coefficients, gain, the initial predictor/scale and
history, the loop's). The data interleaves the channels frame by frame:
8 bytes, 14 samples each.
"""
import argparse
import glob
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from wiikit import dsp  # noqa: E402

BANK_DIRS = ["WIISOUND/sound/generatedsoundbanks/wii",
             "WIIENSND/sound/generatedsoundbanks/wii/english(us)"]


def fnv1(name):
    h = 2166136261
    for c in name.lower().encode():
        h = ((h * 16777619) & 0xFFFFFFFF) ^ c
    return h


def riff_chunks(d, start):
    out, p = {}, start
    while p + 8 <= len(d):
        size = struct.unpack(">I", d[p + 4:p + 8])[0]
        out[d[p:p + 4]] = (p + 8, size)
        p += 8 + size + (size & 1 if start == 12 else 0)
    return out


class Bank:
    def __init__(self, path):
        self.path, self.dir = path, os.path.dirname(path)
        self.name = os.path.basename(path)[:-4]
        d = open(path, "rb").read()
        c = riff_chunks(d, 0)
        self.objs, self.media = {}, {}
        if b"HIRC" in c:
            o = c[b"HIRC"][0]
            p = o + 4
            for _ in range(struct.unpack(">I", d[o:o + 4])[0]):
                kind, size, oid = struct.unpack(">BII", d[p:p + 9])
                self.objs[oid] = (kind, d[p + 9:p + 5 + size])
                p += 5 + size
        if b"DIDX" in c:
            o, size = c[b"DIDX"]
            data = c[b"DATA"][0]
            for i in range(o, o + size, 12):
                mid, off, n = struct.unpack(">III", d[i:i + 12])
                self.media[mid] = d[data + off:data + off + n]

    def wem(self, mid):
        if mid in self.media:
            return self.media[mid]
        path = os.path.join(self.dir, "%d.wem" % mid)
        return open(path, "rb").read() if os.path.exists(path) else None

    def sounds(self, event):
        """Media ids an event plays, in order."""
        out, seen = [], set()

        def walk(oid):
            if oid in seen or oid not in self.objs:
                return
            seen.add(oid)
            kind, b = self.objs[oid]
            if kind == 2:                       # Sound: plugin, stream type, source id
                out.append(struct.unpack(">I", b[8:12])[0])
            elif kind in (5, 6):                # random/sequence, switch: its children
                for i in range(len(b) - 3):
                    v = struct.unpack(">I", b[i:i + 4])[0]
                    if v != oid and self.objs.get(v, (0,))[0] in (2, 5, 6):
                        walk(v)

        kind, b = self.objs[event]
        for k in range(struct.unpack(">I", b[:4])[0]):
            act = self.objs.get(struct.unpack(">I", b[4 + 4 * k:8 + 4 * k])[0])
            if act and act[0] == 3 and struct.unpack(">H", act[1][:2])[0] == 0x0403:
                walk(struct.unpack(">I", act[1][2:6])[0])
        return out


def write_wav(d, path):
    """A DSP-ADPCM .wem as a WAV file; returns its length in seconds."""
    c = riff_chunks(d, 12)
    f = c[b"fmt "][0]
    tag, ch, rate = struct.unpack(">HHI", d[f:f + 8])
    if d[:4] != b"RIFX" or tag != 2:
        raise ValueError("not a DSP-ADPCM .wem")
    count = struct.unpack(">I", d[f + 0x18:f + 0x1C])[0]
    o, size = c[b"data"]
    frames = [d[o + 8 * n:o + 8 * n + 8] for n in range(size // 8)]
    pcm = []
    for i in range(ch):                         # from 0x1C, the DSP header's tail
        coefs = struct.unpack(">16h", d[f + 0x1C + 0x2E * i:f + 0x3C + 0x2E * i])
        h1, h2 = struct.unpack(">hh", d[f + 0x3E + 0x2E * i:f + 0x42 + 0x2E * i])
        pcm.append(dsp.decode(b"".join(frames[i::ch]), coefs, count, h1, h2))
    dsp.write_wav(path, pcm, rate)
    return count / rate


def event_names(pod):
    names = set()
    files = glob.glob(os.path.join(pod, "**", "*.lvl"), recursive=True)
    files += glob.glob(os.path.join(pod, "**", "*.dante"), recursive=True)
    files += glob.glob(os.path.join(pod, "..", "extract", "**", "*.elf"), recursive=True)
    for f in files:
        names.update(m.decode() for m in re.findall(rb"\b(?:Play|Stop|Pause|Resume)_[A-Za-z0-9_]+", open(f, "rb").read()))
    return names


def banks(pod):
    return [Bank(p) for d in BANK_DIRS for p in sorted(glob.glob(os.path.join(pod, d, "*.bnk")))]


def wem_seconds(d):
    c = riff_chunks(d, 12)
    f = c[b"fmt "][0]
    return struct.unpack(">I", d[f + 0x18:f + 0x1C])[0] / struct.unpack(">I", d[f + 4:f + 8])[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("events")
    e.add_argument("pod")
    e.add_argument("--all", action="store_true", help="also events that play nothing")
    w = sub.add_parser("wav")
    w.add_argument("pod")
    w.add_argument("outdir")
    w.add_argument("names", nargs="+")
    m = sub.add_parser("wem")
    m.add_argument("file")
    m.add_argument("out")
    a = ap.parse_args()

    if a.cmd == "wem":
        print("%.2f s" % write_wav(open(a.file, "rb").read(), a.out))
        return
    bs = banks(a.pod)
    names = event_names(a.pod) if a.cmd == "events" else set(a.names)
    hashes = {fnv1(n): n for n in names}
    total = named = 0
    for b in bs:
        events = [o for o, (k, _) in b.objs.items() if k == 4]
        total += len(events)
        for o in events:
            if o not in hashes:
                continue
            named += 1
            media = b.sounds(o)
            if a.cmd == "events":
                if media or a.all:
                    lens = ", ".join("%d %.1fs" % (mid, wem_seconds(b.wem(mid))) for mid in media if b.wem(mid))
                    print("%-20s %-40s %s" % (b.name, hashes[o], lens))
            else:
                os.makedirs(a.outdir, exist_ok=True)
                for k, mid in enumerate(media):
                    out = os.path.join(a.outdir, "%s%s.wav" % (hashes[o], "_%d" % k if len(media) > 1 else ""))
                    print("%s (%s, %d): %.2f s" % (out, b.name, mid, write_wav(b.wem(mid), out)))
    if a.cmd == "events":
        print("# %d of %d events named" % (named, total))


if __name__ == "__main__":
    main()
