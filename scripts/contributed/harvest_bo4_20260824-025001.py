r"""Asset names scraped out of the Black Ops 4 build itself.

    python contrib/harvest_bo4.py --fast                 the loose LPC fast files
    python contrib/harvest_bo4.py --archives 4           sample four CASC archives and report
    python contrib/harvest_bo4.py --archives all         every archive, hours of I/O

Every dead end recorded against Black Ops 4 `sound_asset` ends the same way: "anything reaching
this pool has to come from outside the naming -- the SAB files, a build, or the game's own
strings." Three recombination shapes have returned 0 against 70,707 unnamed ids, and the SAB
files are not the answer -- checked 2026-08-24, `zone/snd/**/*.sabl` and `.sabs` carry FLAC
payload and a hash table and **no plaintext whatsoever**, which is why the pool is 89% unnamed
in the first place.

The build is the answer that is left, and it is on this disk.

  * `LPC/*.ff` -- loose fast files, Oodle compressed in the same block chain Cold War uses, read
    here with the game's own decompressor. 10.4 MB across twelve files.
  * `Data/data/data.NNN` -- the CASC archives, 141 GB. BLTE framed, so most of it is compressed
    and yields nothing, but frames stored uncompressed give their text up to a raw scan. Sample
    first, because a full pass is hours and the sample says whether they are worth it.

Nothing decompressed is written down: a block is decompressed into memory, scanned, and dropped.
The only output is the name list. The filter is `scripts/harvest_retail.py`'s, which is the one
already tuned against this failure mode -- a run of printable bytes inside compressed data is
mostly printable noise, so a name has to carry a separator, three letters, and no run of one
character repeated four times.
"""
import argparse
import ctypes
import os
import re
import sys

BO4 = r"D:\Battlenet\Call of Duty Black Ops 4"
# Black Ops 4 ships Oodle 6; Cold War's 8 reads it too, and either is taken.
OODLES = (
    os.path.join(BO4, "oo2core_6_win64.dll"),
    r"D:\Battlenet\Call of Duty Black Ops Cold War\oo2core_8_win64.dll",
)

NAME = re.compile(rb"[A-Za-z0-9][A-Za-z0-9_/.\-]{5,159}")
SEPARATORS = set(b"_/")
LETTERS = re.compile(rb"[A-Za-z]")
NOISE = re.compile(rb"([A-Za-z0-9])\1{3,}")
RUN = re.compile(rb"[\x20-\x7e]{4,}")

BLOCK = 16
BOUNDARY = 0x800000
SEARCH_FROM = 0x400
SEARCH_TO = 0x900

names = set()


def keep(text):
    if len(text) < 6 or len(text) > 160:
        return False
    if not any(byte in SEPARATORS for byte in text):
        return False
    if len(LETTERS.findall(text)) < 3:
        return False
    if NOISE.search(text):
        return False
    return True


def take(data):
    for run in RUN.finditer(data):
        for part in run.group().split(b":"):
            for found in NAME.finditer(part):
                text = found.group()
                if keep(text):
                    names.add(text.decode("ascii").lower())


def oodle():
    for path in OODLES:
        if not os.path.exists(path):
            continue
        library = ctypes.WinDLL(path)
        call = library.OodleLZ_Decompress
        call.restype = ctypes.c_int64
        call.argtypes = [
            ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64,
            ctypes.c_int32, ctypes.c_int32, ctypes.c_int64,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int64, ctypes.c_int32,
        ]
        return call
    return None


def block_table(head):
    for offset in range(SEARCH_FROM, min(SEARCH_TO, len(head) - BLOCK)):
        if int.from_bytes(head[offset + 12:offset + 16], "little") != offset:
            continue
        compressed = int.from_bytes(head[offset:offset + 4], "little")
        decompressed = int.from_bytes(head[offset + 4:offset + 8], "little")
        if 0 < compressed <= decompressed <= 0x4000000:
            return offset
    return None


def read_fast_file(path, decompress):
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        offset = block_table(handle.read(SEARCH_TO + BLOCK))
        if offset is None:
            return 0
        handle.seek(offset)
        blocks = 0
        while offset < size:
            header = handle.read(BLOCK)
            if len(header) < BLOCK:
                break
            compressed = int.from_bytes(header[0:4], "little")
            decompressed = int.from_bytes(header[4:8], "little")
            aligned = int.from_bytes(header[8:12], "little")
            if int.from_bytes(header[12:16], "little") != offset:
                break
            if decompressed == 0:
                offset = (offset // BOUNDARY + 1) * BOUNDARY
                handle.seek(offset)
                continue
            if compressed == 0 or decompressed > 0x4000000 or aligned > 0x4000000:
                break
            payload = handle.read(aligned)
            if len(payload) < compressed:
                break
            output = ctypes.create_string_buffer(decompressed)
            produced = decompress(
                payload[:compressed], compressed, output, decompressed,
                0, 0, 0, None, None, None, None, None, 0, 0,
            )
            if produced > 0:
                take(output.raw[:produced])
                blocks += 1
            del output
            offset += BLOCK + aligned
            handle.seek(offset)
    return blocks


def scan_raw(path, chunk=1 << 25, limit=None):
    read = 0
    with open(path, "rb") as handle:
        carry = b""
        while True:
            piece = handle.read(chunk)
            if not piece:
                break
            take(carry + piece)
            carry = piece[-200:]
            read += len(piece)
            if limit and read >= limit:
                break
    return read


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fast", action="store_true", help="walk the loose LPC fast files")
    parser.add_argument("--archives", default=None,
                        help="how many CASC archives to raw scan, or 'all'")
    parser.add_argument("--cap-gb", type=float, default=None,
                        help="stop each archive after this many GB")
    parser.add_argument("--out", default="contrib/bo4_harvest.txt")
    options = parser.parse_args(argv)

    if options.fast:
        decompress = oodle()
        if decompress is None:
            raise SystemExit("no Oodle DLL found beside either game")
        folder = os.path.join(BO4, "LPC")
        for entry in sorted(os.listdir(folder)):
            if not entry.endswith(".ff"):
                continue
            before = len(names)
            blocks = read_fast_file(os.path.join(folder, entry), decompress)
            print("  %-58s %3d block(s)  +%s" % (entry, blocks, len(names) - before), flush=True)

    if options.archives:
        folder = os.path.join(BO4, "Data", "data")
        archives = sorted(
            entry for entry in os.listdir(folder)
            if entry.startswith("data.") and entry[5:].isdigit()
        )
        if options.archives != "all":
            wanted = int(options.archives)
            step = max(1, len(archives) // wanted)
            archives = archives[::step][:wanted]
        cap = int(options.cap_gb * (1 << 30)) if options.cap_gb else None
        for entry in archives:
            before = len(names)
            read = scan_raw(os.path.join(folder, entry), limit=cap)
            print("  %-16s %6.2f GB  +%s  (total %s)"
                  % (entry, read / (1 << 30), len(names) - before, format(len(names), ",")),
                  flush=True)

    with open(options.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(names)) + "\n")
    print("\n%s name-shaped string(s) -> %s" % (format(len(names), ","), options.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
