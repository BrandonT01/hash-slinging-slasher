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
import zlib

BO4 = r"D:\Battlenet\Call of Duty Black Ops 4"
COLDWAR = r"D:\Battlenet\Call of Duty Black Ops Cold War"
ROOTS = {"BLKOPS04": BO4, "BLKOPSCW": COLDWAR}
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


MAGIC = b"TAff0000"
# A fast file inside an archive cannot be longer than this, and the cap is what stops a corrupt
# block header walking the chain off into the next file.
LONGEST = 1 << 27


def walk_embedded(handle, base, decompress, ceiling):
    """Walk one fast file that starts at `base` inside a larger container.

    CASC stores an already-Oodle-compressed fast file with BLTE mode 'N', so the bytes sit in the
    archive verbatim and the block chain can be walked in place. Offsets inside the chain are
    relative to the fast file's own start, which is what validates it: a block names its own
    offset, and a wrong `base` fails on the first block rather than producing plausible rubbish.
    """
    handle.seek(base)
    offset = block_table(handle.read(SEARCH_TO + BLOCK))
    if offset is None:
        return 0
    blocks = 0
    while offset < min(LONGEST, ceiling - base):
        handle.seek(base + offset)
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
    return blocks


BLTE = b"BLTE"
# A single archive entry bigger than this is payload -- audio, textures -- and reassembling it
# costs memory for nothing. Fast files that carry names are far below it.
BIGGEST_ENTRY = 1 << 28
# A CASC archive entry is preceded by a 16 byte key, its own size, flags and a checksum.
ENTRY_HEADER = 30
# A frame that is not a fast file is only worth reading as text if it *is* text. Compressed
# payload decodes as printable noise often enough to pass the name filter -- 6,092 strings from
# one probe, 0 of which matched an id -- so the density is checked before a single one is kept.
PRINTABLE = set(range(0x20, 0x7f)) | {9, 10, 13}
TEXTY = 0.60


def blte_entry(handle, start):
    """Reassemble one BLTE framed archive entry, or None if it is not one.

    This is the piece the raw scan cannot do. CASC frames every entry: a chunk table, then the
    chunks, **each prefixed by a one byte mode**. So even a chunk stored uncompressed is not
    contiguous with the next one -- there is a mode byte between them every 256 KB or so -- and a
    fast file's block chain, whose offsets are relative to its own start, dies at the first
    boundary. Walking the frame properly is what turns 11 names an archive into a build.

    Modes: `N` raw, `Z` zlib. `F` is a recursive frame and `E` is encrypted (Salsa20 with a key
    from the build's key ring); neither is reassembled here, and an entry carrying one is dropped
    rather than guessed at.
    """
    # The archive entry header sits in front of the frame: a 16 byte key, then the entry's own
    # total size. That size is what bounds a single chunk frame, which carries no chunk table.
    if start < ENTRY_HEADER:
        return None
    handle.seek(start - ENTRY_HEADER + 16)
    stated = int.from_bytes(handle.read(4), "little")
    if not ENTRY_HEADER < stated <= BIGGEST_ENTRY:
        return None
    ends = start - ENTRY_HEADER + stated

    handle.seek(start)
    head = handle.read(8)
    if len(head) < 8 or head[:4] != BLTE:
        return None
    header_size = int.from_bytes(head[4:8], "big")

    if header_size == 0:
        # One chunk, no table: the mode byte follows the header and the rest is the chunk.
        raw = handle.read(ends - start - 8)
        if len(raw) < 2:
            return None
        if raw[:1] == b"N":
            return raw[1:]
        if raw[:1] == b"Z":
            try:
                return zlib.decompress(raw[1:])
            except zlib.error:
                return None
        return None

    table = handle.read(header_size - 8)
    if len(table) < 4:
        return None
    count = int.from_bytes(table[1:4], "big")
    if count == 0 or count > 4096 or len(table) < 4 + count * 24:
        return None

    pieces = []
    total = 0
    handle.seek(start + header_size)
    for index in range(count):
        row = 4 + index * 24
        compressed = int.from_bytes(table[row:row + 4], "big")
        decompressed = int.from_bytes(table[row + 4:row + 8], "big")
        if compressed < 1 or decompressed > BIGGEST_ENTRY:
            return None
        total += decompressed
        if total > BIGGEST_ENTRY:
            return None
        raw = handle.read(compressed)
        if len(raw) < compressed:
            return None
        mode, body = raw[:1], raw[1:]
        if mode == b"N":
            pieces.append(body)
        elif mode == b"Z":
            try:
                pieces.append(zlib.decompress(body))
            except zlib.error:
                return None
        else:
            return None
    return b"".join(pieces)


def texty(data, sample=1 << 12):
    """Whether a frame is text rather than payload that happens to decode as printable."""
    head = data[:sample]
    if not head:
        return False
    return sum(byte in PRINTABLE for byte in head) / len(head) >= TEXTY


def walk_bytes(data, decompress):
    """Walk a fast file already held in memory. Same chain, no seeking."""
    offset = block_table(data[: SEARCH_TO + BLOCK])
    if offset is None:
        return 0
    blocks = 0
    while offset + BLOCK <= len(data):
        header = data[offset:offset + BLOCK]
        compressed = int.from_bytes(header[0:4], "little")
        decompressed = int.from_bytes(header[4:8], "little")
        aligned = int.from_bytes(header[8:12], "little")
        if int.from_bytes(header[12:16], "little") != offset:
            break
        if decompressed == 0:
            offset = (offset // BOUNDARY + 1) * BOUNDARY
            continue
        if compressed == 0 or decompressed > 0x4000000 or aligned > 0x4000000:
            break
        payload = data[offset + BLOCK:offset + BLOCK + aligned]
        if len(payload) < compressed:
            break
        output = ctypes.create_string_buffer(decompressed)
        produced = decompress(
            bytes(payload[:compressed]), compressed, output, decompressed,
            0, 0, 0, None, None, None, None, None, 0, 0,
        )
        if produced > 0:
            take(output.raw[:produced])
            blocks += 1
        del output
        offset += BLOCK + aligned
    return blocks


def find_magic(path, limit=None, chunk=1 << 26, magic=MAGIC):
    """Every offset in a container where `magic` appears."""
    out = []
    read = 0
    with open(path, "rb") as handle:
        carry = b""
        while True:
            piece = handle.read(chunk)
            if not piece:
                break
            buffer = carry + piece
            start = read - len(carry)
            index = buffer.find(magic)
            while index >= 0:
                out.append(start + index)
                index = buffer.find(magic, index + 1)
            carry = piece[-len(magic):]
            read += len(piece)
            if limit and read >= limit:
                break
    return out


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
    parser.add_argument("--embedded", default=None,
                        help="how many CASC archives to walk for embedded fast files, or 'all'")
    parser.add_argument("--blte", default=None,
                        help="how many CASC archives to read as BLTE frames, or 'all'")
    parser.add_argument("--from-archive", type=int, default=0, help="skip this many archives")
    parser.add_argument("--game", default="BLKOPS04", choices=sorted(ROOTS),
                        help="which installed build to read")
    parser.add_argument("--out", default="contrib/bo4_harvest.txt")
    options = parser.parse_args(argv)

    if options.fast:
        decompress = oodle()
        if decompress is None:
            raise SystemExit("no Oodle DLL found beside either game")
        folder = os.path.join(root, "LPC")
        for entry in sorted(os.listdir(folder)):
            if not entry.endswith(".ff"):
                continue
            before = len(names)
            blocks = read_fast_file(os.path.join(folder, entry), decompress)
            print("  %-58s %3d block(s)  +%s" % (entry, blocks, len(names) - before), flush=True)

    if options.archives:
        folder = os.path.join(root, "Data", "data")
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

    if options.embedded:
        decompress = oodle()
        if decompress is None:
            raise SystemExit("no Oodle DLL found beside either game")
        folder = os.path.join(root, "Data", "data")
        archives = sorted(
            entry for entry in os.listdir(folder)
            if entry.startswith("data.") and entry[5:].isdigit()
        )[options.from_archive:]
        if options.embedded != "all":
            archives = archives[: int(options.embedded)]
        cap = int(options.cap_gb * (1 << 30)) if options.cap_gb else None
        for entry in archives:
            path = os.path.join(folder, entry)
            size = os.path.getsize(path)
            starts = find_magic(path, limit=cap)
            before, walked = len(names), 0
            with open(path, "rb") as handle:
                for index, base in enumerate(starts):
                    ceiling = starts[index + 1] if index + 1 < len(starts) else size
                    if walk_embedded(handle, base, decompress, ceiling):
                        walked += 1
            print("  %-16s %5d fast file(s), %5d walked  +%s  (total %s)"
                  % (entry, len(starts), walked, len(names) - before, format(len(names), ",")),
                  flush=True)
            # Written after every archive: a scan of the whole build is hours, and a killed run
            # should leave everything it had already found.
            with open(options.out, "w", encoding="utf-8") as handle:
                handle.write("\n".join(sorted(names)) + "\n")

    if options.blte:
        decompress = oodle()
        if decompress is None:
            raise SystemExit("no Oodle DLL found beside either game")
        folder = os.path.join(root, "Data", "data")
        archives = sorted(
            entry for entry in os.listdir(folder)
            if entry.startswith("data.") and entry[5:].isdigit()
        )[options.from_archive:]
        if options.blte != "all":
            archives = archives[: int(options.blte)]
        cap = int(options.cap_gb * (1 << 30)) if options.cap_gb else None
        for entry in archives:
            path = os.path.join(folder, entry)
            starts = find_magic(path, limit=cap, magic=BLTE)
            before, read, fast = len(names), 0, 0
            with open(path, "rb") as handle:
                for base in starts:
                    data = blte_entry(handle, base)
                    if data is None:
                        continue
                    read += 1
                    # A fast file does not have to start at the frame: a frame is a run of
                    # 256 KB chunks and an entry can carry several files, so every occurrence
                    # of the magic inside the reassembled bytes is walked, not only offset 0.
                    inside = 0
                    place = data.find(MAGIC)
                    while place >= 0:
                        if walk_bytes(data[place:], decompress):
                            inside += 1
                        place = data.find(MAGIC, place + 1)
                    fast += inside
                    if not inside and texty(data):
                        take(data)
            print("  %-16s %7d frame(s), %6d read, %5d fast  +%s  (total %s)"
                  % (entry, len(starts), read, fast, len(names) - before,
                     format(len(names), ",")), flush=True)
            # Written after every archive: the whole build is hours, and a killed run should
            # leave behind everything it had already found.
            with open(options.out, "w", encoding="utf-8") as handle:
                handle.write("\n".join(sorted(names)) + "\n")

    with open(options.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(names)) + "\n")
    print("\n%s name-shaped string(s) -> %s" % (format(len(names), ","), options.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
