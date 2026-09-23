"""Rhythm-game songs (data/songs/rhythm_*.txt): per-song event census.

    python tools/songs.py DIR               # table of A / B / X events per song
    python tools/songs.py FILE --measures   # one line per measure

The songs are XML exported by High Voltage Software's "SongExporter.xls" and
read by CSongMoveBlockActor::ReadXMLData (TinyXML). <SongInfo> holds the
tempo (BaseAnimSpeed), measure counts, background movie and camera zoom
measures; each <Measure> may carry character and camera animations and the
input events, named by button and numbered by beat:

    APress<n>, BPress<n>, XPress<n>   press on beat n    (X is the shake)
    A2On<n>, A2Off<n>, A2Cnt<n>       a held A: start beat, end beat, count
    CheckOnOff                        scoring on / off from this measure

X is the Wii Remote shake: CDebugRhythmGameUI's input sampler fills slot 2
from CGame::bGetShake (see docs/08-input-and-rhythm.md).
"""
import argparse
import glob
import os
import re


def events(text):
    out = []
    for m in re.finditer(r"<Measure>(.*?)</Measure>", text, re.S):
        body = m.group(1)
        count = int(re.search(r"<Count>\s*(\d+)", body).group(1))
        ev = [(k, int(n), int(v)) for k, n, v in
              re.findall(r"<(APress|BPress|XPress|A2On|A2Off|A2Cnt)(\d+)>\s*(-?\d+)", body)]
        out.append((count, ev))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--measures", action="store_true")
    a = ap.parse_args()
    if a.measures:
        for count, ev in events(open(a.path, encoding="utf-8-sig").read()):
            if ev:
                print(f"{count:4}  " + "  ".join(f"{k}{n}={v}" for k, n, v in ev))
        return
    tot = {"APress": 0, "BPress": 0, "XPress": 0, "A2On": 0}
    print(f"{'song':26} {'A':>5} {'B':>5} {'X':>5} {'holds':>5}")
    for p in sorted(glob.glob(os.path.join(a.path, "rhythm_*.txt"))):
        c = dict.fromkeys(tot, 0)
        for _, ev in events(open(p, encoding="utf-8-sig").read()):
            for k, _, _ in ev:
                if k in c:
                    c[k] += 1
        for k in tot:
            tot[k] += c[k]
        print(f"{os.path.basename(p):26} {c['APress']:5} {c['BPress']:5} {c['XPress']:5} {c['A2On']:5}")
    print(f"{'total':26} {tot['APress']:5} {tot['BPress']:5} {tot['XPress']:5} {tot['A2On']:5}")


if __name__ == "__main__":
    main()
