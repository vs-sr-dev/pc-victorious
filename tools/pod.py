"""Terminal Reality POD5 archive reader (Infernal Engine).

The Wii build ships the same little-endian POD5 container the PC Infernal Engine
games use (Ghostbusters, BloodRayne 2, ...).

Header (LE, 0x170 bytes):
    0x000  'POD5'
    0x004  u32  checksum
    0x008  char comment[80]        "Release format assets"
    0x058  u32  file_count
    0x05C  u32  audit_count
    0x060  u32  revision
    0x064  u32  priority
    0x068  char author[80]
    0x0B8  char copyright[80]
    0x108  u32  index_offset
    0x10C  u32  index checksum
    0x110  u32  names_size
    0x114  u32  depend_count
    0x118  u32  ?  (0xFFFFFFFF)
    0x11C  u32  ?
Index at index_offset: file_count x 28-byte entries
    u32 name_off, size, offset, uncompressed_size, compression, timestamp, checksum
followed by the NUL-terminated name table (names_size bytes).

Usage:
    python tools/pod.py list <file.POD>
    python tools/pod.py extract <file.POD> <out_dir>
"""
import os
import struct
import sys
import zlib

ENTRY = 28


class Pod:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        h = self.f.read(0x170)
        if h[:4] != b"POD5":
            raise ValueError(f"{path}: not POD5 ({h[:4]!r})")
        self.comment = h[8:0x58].split(b"\0")[0].decode("latin1")
        self.count, = struct.unpack_from("<I", h, 0x58)
        self.index_off, _, self.names_size = struct.unpack_from("<3I", h, 0x108)
        self.f.seek(self.index_off)
        idx = self.f.read(self.count * ENTRY + self.names_size)
        names = idx[self.count * ENTRY:]
        self.entries = []
        for i in range(self.count):
            no, size, off, usize, comp, ts, crc = struct.unpack_from("<7I", idx, i * ENTRY)
            name = names[no:names.index(b"\0", no)].decode("latin1")
            self.entries.append(dict(name=name, size=size, offset=off, usize=usize,
                                     comp=comp, ts=ts, crc=crc))

    def read(self, e):
        self.f.seek(e["offset"])
        data = self.f.read(e["size"])
        if e["size"] != e["usize"]:
            data = zlib.decompress(data)
        return data


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    p = Pod(path)
    if cmd == "list":
        print(f"# {path}: {p.count} files, comment={p.comment!r}")
        for e in p.entries:
            print(f"{e['offset']:10x} {e['size']:10d} {e['usize']:10d} {e['comp']:3d}  {e['name']}")
    elif cmd == "extract":
        out = sys.argv[3]
        for e in p.entries:
            dst = os.path.join(out, *e["name"].replace("\\", "/").split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(p.read(e))
        print(f"{p.count} files -> {out}")


if __name__ == "__main__":
    main()
