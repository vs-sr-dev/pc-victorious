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

The compression field is the engine's ECompressionType (COMPRESSION below).
Type 0 (stored) and type 1 (the engine's LZW) are decoded; the others are
named but not implemented yet.

Usage:
    python tools/pod.py list <file.POD>
    python tools/pod.py extract <file.POD> <out_dir>
    python tools/pod.py verify <file.POD> [...]     checksums, alignment, decoding
    python tools/pod.py lzwtest <file.POD> [...]    LZW round trip on every entry
"""
import os
import struct
import sys
import zlib

ENTRY = 28
DEPEND = 0x108
AUDIT = 312

# ECompressionType, from getCompressor(ECompressionType, bool) in the Victorious
# executable: the codec, or the chain of codecs, each type decodes with.
COMPRESSION = {
    0: "stored",
    1: "LZW",
    2: "RLE",
    3: "DBC",
    4: "Huffman",
    5: "Fibonacci",
    6: "RLE (2)",
    7: "RLE (4)",
    8: "RLE+BWT+MTF+RLE+Huffman",
    9: "BWT+MTF+LZW",
    10: "RLE+BWT+MTF+RLE+Fibonacci",
}

_REV = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))


def crc32_mpeg2(data):
    """CRC-32/MPEG-2. An MSB-first CRC is the bit reverse of the reflected CRC
    of the bit-reversed bytes, so zlib does the work."""
    r = zlib.crc32(data.translate(_REV)) ^ 0xFFFFFFFF
    return int(f"{r:032b}"[::-1], 2)


assert crc32_mpeg2(b"123456789") == 0x0376E6E7


# --- LZW (CLZWCompress / CLZWDecompress, CLZWDictionary) -----------------------
#
# Codes start 8 bits wide over a dictionary of 0x2000 entries whose first 256
# are the bytes. A code is written MSB first, its bits packed into bytes from
# the least significant bit up; bits are only written while they can differ
# from next-1 (the highest code that can occur): where next-1 has a 0 bit and
# every bit so far has matched it, the bit is implied 0 and not stored. After a
# code, prev + first byte of the current word is added (one step later than
# textbook LZW, so a code is always known when it is read). Adding when next is
# a power of two widens the codes by one bit; adding when the dictionary is
# full resets it instead, and the code that follows adds nothing.

LZW_ENTRIES = 0x2000
LZW_BITS = 8


class _LzwDictionary:
    def __init__(self):
        self.words = [bytes([i]) for i in range(1 << LZW_BITS)]
        self.reset()

    def reset(self):
        del self.words[1 << LZW_BITS:]
        self.children = {}
        self.next = 1 << LZW_BITS
        self.width = LZW_BITS

    def add(self, first, prev):
        """prev's word + first; True when the dictionary was full and reset."""
        if self.next >= LZW_ENTRIES:
            self.reset()
            return True
        if self.next & (self.next - 1) == 0:
            self.width += 1
        self.words.append(self.words[prev] + bytes([first]))
        self.children[(prev, first)] = self.next
        self.next += 1
        return False


def lzw_decompress(data, size):
    d = _LzwDictionary()
    out = bytearray()
    bitpos, total = 0, len(data) * 8
    prev = -1
    while len(out) < size:
        mask, limit, bound, code = 1 << (d.width - 1), d.next - 1, True, 0
        while mask:
            if bound and not limit & mask:
                mask >>= 1
                continue
            if bitpos >= total:
                raise ValueError(f"LZW: input ends at {len(out)} of {size} bytes")
            if data[bitpos >> 3] >> (bitpos & 7) & 1:
                code |= mask
            else:
                bound = False
            bitpos += 1
            mask >>= 1
        if code >= len(d.words):
            raise ValueError(f"LZW: code {code} not in the dictionary ({d.next} entries)")
        word = d.words[code]
        out += word
        if prev >= 0 and d.add(word[0], prev):
            code = -1
        prev = code
    if len(out) > size:
        raise ValueError(f"LZW: {len(out) - size} bytes too many")
    return bytes(out)


def lzw_compress(data):
    d = _LzwDictionary()
    out = bytearray()
    acc = nbits = 0

    def put(code):
        nonlocal acc, nbits
        mask, limit, bound = 1 << (d.width - 1), d.next - 1, True
        while mask:
            if not (bound and not limit & mask):
                bit = 1 if code & mask else 0
                acc |= bit << nbits
                nbits += 1
                if not bit:
                    bound = False
            mask >>= 1
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8

    w = prev = -1
    first = 0
    for ch in data:
        if w < 0:
            w, first = ch, ch
            continue
        nxt = d.children.get((w, ch))
        if nxt is not None:
            w = nxt
            continue
        put(w)
        if prev >= 0 and d.add(first, prev):
            prev = -1
        else:
            prev = w
        w, first = ch, ch
    if w >= 0:
        put(w)
    if nbits:
        out.append(acc & 0xFF)
    return bytes(out)


def decode(comp, data, size):
    if comp == 0:
        return data
    if comp == 1:
        return lzw_decompress(data, size)
    raise NotImplementedError(f"compression {comp} ({COMPRESSION.get(comp, 'unknown')}) not supported yet")


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
        return decode(e["comp"], self.read_raw(e), e["usize"])

    def tables(self):
        """The dependency table and the audit trail, after the name table."""
        self.f.seek(self.index_off + len(self.index))
        return self.f.read(self.depend_count * DEPEND), self.f.read(self.audit_count * AUDIT)

    def verify(self):
        """Every checksum, the 32-byte payload alignment, and the decoding of
        compressed entries; returns the failures and the entries skipped."""
        bad, skipped = [], []
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
            raw = self.read_raw(e)
            if crc32_mpeg2(raw) != e["crc"]:
                bad.append(e["name"])
            if e["offset"] % 32:
                bad.append(e["name"] + " (offset not 32-aligned)")
            if e["comp"]:
                try:
                    decode(e["comp"], raw, e["usize"])
                except NotImplementedError:
                    skipped.append(e)
                except ValueError as x:
                    bad.append(f"{e['name']} ({x})")
        return bad, skipped


def _census(entries):
    n = {}
    for e in entries:
        n[e["comp"]] = n.get(e["comp"], 0) + 1
    return ", ".join(f"{c} {COMPRESSION.get(k, f'type {k}')}" for k, c in sorted(n.items()))


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "verify":
        failed = 0
        for path in sys.argv[2:]:
            p = Pod(path)
            bad, skipped = p.verify()
            failed += bool(bad)
            note = f" (not decoded: {_census(skipped)})" if skipped else ""
            print(f"{path}: {p.count} files ({_census(p.entries)}), {p.depend_count} dependencies, "
                  f"{p.audit_count} audit records: " + ("ok" if not bad else "BAD " + ", ".join(bad)) + note)
        sys.exit(1 if failed else 0)
    if cmd == "lzwtest":
        failed = 0
        for path in sys.argv[2:]:
            p = Pod(path)
            n = packed = unpacked = 0
            for e in p.entries:
                data = p.read(e)
                z = lzw_compress(data)
                if lzw_decompress(z, len(data)) != data:
                    print(f"  round trip FAILED: {e['name']}")
                    failed += 1
                n += 1
                packed += len(z)
                unpacked += len(data)
            print(f"{path}: {n} files, {unpacked} -> {packed} bytes")
        sys.exit(1 if failed else 0)
    p = Pod(path)
    if cmd == "list":
        print(f"# {path}: {p.count} files, comment={p.comment!r}")
        for e in p.entries:
            print(f"{e['offset']:10x} {e['size']:10d} {e['usize']:10d} {e['comp']:3d}  {e['name']}")
    elif cmd == "extract":
        out = sys.argv[3]
        skipped = []
        for e in p.entries:
            try:
                data = p.read(e)
            except NotImplementedError as x:
                print(f"  skipped {e['name']}: {x}")
                skipped.append(e)
                continue
            dst = os.path.join(out, *e["name"].replace("\\", "/").split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
        print(f"{p.count - len(skipped)} files -> {out}" +
              (f"; {len(skipped)} skipped ({_census(skipped)})" if skipped else ""))
        sys.exit(1 if skipped else 0)


if __name__ == "__main__":
    main()
