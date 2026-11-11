"""Terminal Reality POD5 archive reader (Infernal Engine).

The Wii build ships the same little-endian POD5 container the PC Infernal Engine
games use (Ghostbusters, BloodRayne 2, ...). The full description, and what the
game's own CPodFile does with each field, is in docs/02-container-formats.md.

Header (LE, 0x170 bytes):
    0x000  'POD5'
    0x004  u32  checksum of header bytes 0x008-0x170
    0x008  char comment[80]        "Release format assets"
    0x058  u32  file_count
    0x05C  u32  audit_count
    0x060  u32  revision
    0x064  u32  priority
    0x068  char author[80]
    0x0B8  char copyright[80]
    0x108  u32  index_offset
    0x10C  u32  checksum of the index (entries + name table)
    0x110  u32  names_size
    0x114  u32  depend_count
    0x118  u32  checksum of the dependency table
    0x11C  u32  checksum of the audit trail
    0x120  char [80]               (empty on this disc)
At index_offset: file_count x 28-byte entries
    u32 name_off, size, offset, uncompressed_size, compression, timestamp, checksum
then the NUL-terminated name table (names_size bytes), depend_count x 0x108-byte
dependency records, and audit_count x 312-byte audit records.

Every checksum is CRC-32/MPEG-2: poly 0x04C11DB7, MSB first, init 0xFFFFFFFF,
no final xor. An entry's covers its stored bytes.

Usage:
    python tools/pod.py list <file.POD>
    python tools/pod.py extract <file.POD> <out_dir>
    python tools/pod.py verify <file.POD> [...]
"""
import os
import struct
import sys
import zlib

ENTRY = 28
DEPEND = 0x108
AUDIT = 312

_REV = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))


def crc32_mpeg2(data):
    """CRC-32/MPEG-2. An MSB-first CRC is the bit reverse of the reflected CRC
    of the bit-reversed bytes, so zlib does the work."""
    r = zlib.crc32(data.translate(_REV)) ^ 0xFFFFFFFF
    return int(f"{r:032b}"[::-1], 2)


assert crc32_mpeg2(b"123456789") == 0x0376E6E7


class Pod:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        h = self.header = self.f.read(0x170)
        if h[:4] != b"POD5":
            raise ValueError(f"{path}: not POD5 ({h[:4]!r})")
        self.comment = h[8:0x58].split(b"\0")[0].decode("latin1")
        self.count, self.audit_count = struct.unpack_from("<2I", h, 0x58)
        (self.index_off, self.index_crc, self.names_size, self.depend_count,
         self.depend_crc, self.audit_crc) = struct.unpack_from("<6I", h, 0x108)
        self.f.seek(self.index_off)
        self.index = self.f.read(self.count * ENTRY + self.names_size)
        names = self.index[self.count * ENTRY:]
        self.entries = []
        for i in range(self.count):
            no, size, off, usize, comp, ts, crc = struct.unpack_from("<7I", self.index, i * ENTRY)
            name = names[no:names.index(b"\0", no)].decode("latin1")
            self.entries.append(dict(name=name, size=size, offset=off, usize=usize,
                                     comp=comp, ts=ts, crc=crc))

    def read_raw(self, e):
        self.f.seek(e["offset"])
        return self.f.read(e["size"])

    def read(self, e):
        data = self.read_raw(e)
        if e["size"] != e["usize"]:
            data = zlib.decompress(data)
        return data

    def tables(self):
        """The dependency table and the audit trail, after the name table."""
        self.f.seek(self.index_off + len(self.index))
        return self.f.read(self.depend_count * DEPEND), self.f.read(self.audit_count * AUDIT)

    def verify(self):
        """Every checksum and the 32-byte payload alignment; returns the failures."""
        bad = []
        if crc32_mpeg2(self.header[8:]) != struct.unpack_from("<I", self.header, 4)[0]:
            bad.append("header")
        if crc32_mpeg2(self.index) != self.index_crc:
            bad.append("index")
        depend, audit = self.tables()
        if crc32_mpeg2(depend) != self.depend_crc:
            bad.append("dependency table")
        if len(audit) != self.audit_count * AUDIT or crc32_mpeg2(audit) != self.audit_crc:
            bad.append("audit trail")
        for e in self.entries:
            if crc32_mpeg2(self.read_raw(e)) != e["crc"]:
                bad.append(e["name"])
            if e["offset"] % 32:
                bad.append(e["name"] + " (offset not 32-aligned)")
        return bad


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "verify":
        failed = 0
        for path in sys.argv[2:]:
            p = Pod(path)
            bad = p.verify()
            failed += bool(bad)
            print(f"{path}: {p.count} files, {p.depend_count} dependencies, "
                  f"{p.audit_count} audit records: " + ("ok" if not bad else "BAD " + ", ".join(bad)))
        sys.exit(1 if failed else 0)
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
