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
    0x118  u32  depend_crc
    0x11C  u32  audit_crc
Index at index_offset: file_count x 28-byte entries
    u32 name_off, size, offset, uncompressed_size, compression, timestamp, checksum
followed by the NUL-terminated name table (names_size bytes).
Depend at index_offset + file_count * 28 + names_size: depend_count x 264-byte dependency entries
Audit at index_offset + file_count * 28 + names_size + depend_count * 264: audit_count x 312-byte entries

Usage:
    python tools/pod.py <file.POD>
    python tools/pod.py list <file.POD>
    python tools/pod.py verify <file.POD>
    python tools/pod.py extract <file.POD> <out_dir>
"""
import os
import struct
import sys
import zlib
import datetime
from termcolor import colored
from crccheck.crc import Crc32Mpeg2

ENTRY  = 28
DEPEND = 264
AUDIT  = 312

def ActionString(action):
    if action == 0: return "Add"
    if action == 1: return "Remove"
    if action == 2: return "Change"

class Audit:
    def __init__(self, src):
        self.user = bytes(struct.unpack_from("<32B", src, 0x00)).split(b'\x00')[0].decode('latin-1')
        self.uts, self.action  = struct.unpack_from("<2I", src, 0x20)
        self.path = bytes(struct.unpack_from("<256B", src, 0x28)).split(b'\x00')[0].decode('latin-1')
        self.old_uts, self.old_len = struct.unpack_from("<2I", src, 0x128)
        self.new_uts, self.new_len = struct.unpack_from("<2I", src, 0x130)
    def __str__(self):
        return f"[NFO][AUD] [{("0").rjust(10)}|{("0").rjust(10)}] [{str(datetime.datetime.fromtimestamp(self.uts)).split('.')[0]}|{ActionString(self.action).rjust(19)}] {self.user}\n[NFO][AUD] [{self.new_len:10}|{self.old_len:10}] [{str(datetime.datetime.fromtimestamp(self.old_uts)).split('.')[0]}|{str(datetime.datetime.fromtimestamp(self.new_uts)).split('.')[0]}] {self.path}"

class Depend:
    def __init__(self, src):
        self.data = bytes(struct.unpack_from("<264", src, 0x00))
    def __str__(self):
        return f"{data:264x}"

class Pod:

    def __init__(self, path):
        self.check_crc = False
        self.path = path
        self.f = open(path, "rb")
        h = self.f.read(0x170)
        if h[:4] != b"POD5":
            raise ValueError(f"{path}: not POD5 ({h[:4]!r})")
        self.comment = h[8:0x58].split(b"\0")[0].decode("latin1")
        self.count, self.audit_count = struct.unpack_from("<2I", h, 0x58)
        self.index_off, self.index_crc, self.names_size = struct.unpack_from("<3I", h, 0x108)
        self.depend_count, self.depend_crc, self.audit_crc = struct.unpack_from("<3I", h, 0x114)
        self.f.seek(self.index_off)

        self.index   = self.f.read(self.count         *  ENTRY)
        self.names   = self.f.read(self.names_size            )
        self.depends = self.f.read(self.depend_count  * DEPEND)
        self.audits  = self.f.read(self.audit_count   *  AUDIT)

        self.entries = []
        for i in range(self.count):
            no, size, off, usize, comp, ts, crc = struct.unpack_from("<7I", self.index, i * ENTRY)
            name = self.names[no:self.names.index(b"\0", no)].decode("latin1")
            self.entries.append(dict(name=name, size=size, offset=off, usize=usize,
                                     comp=comp, ts=ts, crc=crc))

    def read(self, e):
        self.f.seek(e["offset"])
        data = self.f.read(e["size"])
        err = False
        chk = 0xFFFFFFFF
        if self.check_crc == True:
            chk = Crc32Mpeg2.calc(data)
            if e["crc"] != chk:
                err = True
        if e["size"] != e["usize"] and e["comp"] == 1:
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    err = True

        if err:
            print(colored(f"[WRN][ENT] [{e['size']:10d}|{e['usize']:10d}] [{e['comp']:6d}] [{e['crc']:08X}|{chk:08X}] [{e['offset']:010X}] {e['name']}", "red"))
        else:
            print(colored(f"[NFO][ENT] [{e['size']:10d}|{e['usize']:10d}] [{e['comp']:6d}] [{e['crc']:08X}|{chk:08X}] [{e['offset']:010X}] {e['name']}", "green"))

        return data


def main():
    if len(sys.argv) > 2:
        cmd, path = sys.argv[1], sys.argv[2]
    else:
        cmd = ""
        path = sys.argv[1]

    p = Pod(path,)
    if cmd == "verify":
        p.check_crc = True
        cmd = "list"
    if cmd == "list":
        for e in p.entries:
            p.read(e)
        for i in range(p.depend_count):
            print(Depend(p.depends[i * DEPEND:]))
        for i in range(p.audit_count):
            print(Audit(p.audits[i * AUDIT:]))
    elif cmd == "extract":
        out = sys.argv[3]
        for e in p.entries:
            dst = os.path.join(out, *e["name"].replace("\\", "/").split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(p.read(e))
        print(f"{p.count} files -> {out}")
    print(colored(f"[NFO][CNT] [{p.count:10d}|{p.depend_count:10d}] [{p.comment:39}] {path}", "yellow"))

if __name__ == "__main__":
    main()
