"""Scrapes asset names out of the retail Cold War build.

Nothing decompressed is ever written down. A fast file is walked a block at a time, each block
is decompressed into memory, scanned, and dropped before the next one is read, so the peak cost
is one block rather than the size of the build. The only thing written is the list of names.

Three containers are read:

  xpak  The metadata section is plain text already: newline delimited "name:value" records. This
        is where Cold War keeps its real asset names, and a scanner that only accepts null
        terminated strings walks straight past it.
  ff    Oodle compressed blocks behind a fixed header. The block table is not word aligned, so
        it is found by searching a byte at a time, and each block header names its own offset,
        which is what proves the chain was found rather than guessed.
  fd    Scanned raw. Whatever plain text it carries is taken; the rest yields nothing and costs
        only the read.

xsub is skipped: it is pure payload, verified three separate ways to hold no names, and it is
by far the largest thing here.
"""
import settings
import ctypes, os, re, sys

ROOT = r"D:\_CW_FILES"
OUT = settings.path("harvest", "harvest")
OODLE = r"D:\Battlenet\Call of Duty Black Ops Cold War\oo2core_8_win64.dll"

# A name is built from these and nothing else, and it has to carry an underscore or a slash.
# Without that the filter keeps every English word in the binary and, worse, every four byte run
# of compressed data that happens to be printable - which is most of what a packed file offers.
# A dot alone does not count as structure: "0.3v" is noise, "wpn_t9_ak47" is not.
NAME = re.compile(rb"[A-Za-z0-9][A-Za-z0-9_/.\-]{5,159}")
SEPARATORS = set(b"_/")

# Enough letters to be a word rather than a number or a fragment of one.
LETTERS = re.compile(rb"[A-Za-z]")

# Compressed data that happens to decode as printable tends to run the same character several
# times over. Nothing the game names does that.
NOISE = re.compile(rb"([A-Za-z0-9])\1{3,}")

# Runs of text are taken between anything that is not printable, so a newline delimited record
# yields its lines one at a time.
RUN = re.compile(rb"[\x20-\x7e]{4,}")

# A block's own offset is the last of its four words, and it is what validates the chain.
BLOCK = 16
BOUNDARY = 0x800000

# Where the block table starts, near enough. The header is a fixed struct, but its size has
# moved between builds, so the table is searched for rather than assumed.
SEARCH_FROM = 0x400
SEARCH_TO = 0x900

names = set()


def keep(text):
    """Whether a run of text looks like something the game would name an asset."""
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
    """Every name-shaped run in a block of bytes."""
    for run in RUN.finditer(data):
        piece = run.group()

        # A metadata record is "key:value"; the value is the name.
        for part in piece.split(b":"):
            for found in NAME.finditer(part):
                text = found.group()
                if keep(text):
                    names.add(text.decode("ascii").lower())


def oodle():
    """The game's own decompressor, which ships beside it."""
    library = ctypes.WinDLL(OODLE)
    call = library.OodleLZ_Decompress
    call.restype = ctypes.c_int64
    call.argtypes = [
        ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64,
        ctypes.c_int32, ctypes.c_int32, ctypes.c_int64,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_int64, ctypes.c_int32,
    ]
    return call


def block_table(head):
    """Where the chain of blocks begins, proved by a block that names its own offset."""
    for offset in range(SEARCH_FROM, min(SEARCH_TO, len(head) - BLOCK)):
        words = int.from_bytes(head[offset + 12:offset + 16], "little")
        if words != offset:
            continue

        compressed = int.from_bytes(head[offset:offset + 4], "little")
        decompressed = int.from_bytes(head[offset + 4:offset + 8], "little")

        if 0 < compressed <= decompressed <= 0x4000000:
            return offset

    return None


def read_fast_file(path, decompress):
    """Walks one fast file, holding a single block at a time."""
    size = os.path.getsize(path)

    with open(path, "rb") as handle:
        head = handle.read(SEARCH_TO + BLOCK)
        offset = block_table(head)

        if offset is None:
            return False

        handle.seek(offset)
        blocks = 0

        while offset < size:
            header = handle.read(BLOCK)
            if len(header) < BLOCK:
                break

            compressed = int.from_bytes(header[0:4], "little")
            decompressed = int.from_bytes(header[4:8], "little")
            aligned = int.from_bytes(header[8:12], "little")
            stated = int.from_bytes(header[12:16], "little")

            if stated != offset:
                break

            # A block with nothing in it means skip to the next boundary.
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

            if produced <= 0:
                # Encrypted, or a codec this does not speak. The block is dropped rather than
                # guessed at, and the file carries on.
                offset += BLOCK + aligned
                handle.seek(offset)
                continue

            take(output.raw[:produced])
            del output

            blocks += 1
            offset += BLOCK + aligned
            handle.seek(offset)

    return blocks > 0


def scan_raw(path, chunk=1 << 24):
    """Reads a file in pieces, keeping only what looks like a name."""
    with open(path, "rb") as handle:
        carry = b""
        while True:
            data = handle.read(chunk)
            if not data:
                break
            take(carry + data)
            carry = data[-256:]


def files(extension):
    found = []
    for base, _, entries in os.walk(ROOT):
        for entry in entries:
            if entry.lower().endswith(extension):
                found.append(os.path.join(base, entry))
    return sorted(found)


def report(stage):
    print(f"  {stage}: {len(names)} names so far", flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)

    packages = files(".xpak")
    print(f"xpak: {len(packages)} files", flush=True)
    for path in packages:
        scan_raw(path)
    report("xpak")

    decompress = None
    try:
        decompress = oodle()
    except OSError as error:
        print(f"the decompressor could not be loaded ({error}); fast files will be read raw",
              flush=True)

    fast = files(".ff")
    print(f"ff: {len(fast)} files", flush=True)
    walked = 0
    for index, path in enumerate(fast, 1):
        try:
            if decompress is not None and read_fast_file(path, decompress):
                walked += 1
            else:
                scan_raw(path)
        except Exception as error:
            print(f"  {os.path.basename(path)}: {error}", flush=True)
        if index % 50 == 0:
            report(f"ff {index}/{len(fast)}")
    print(f"  fast files walked as blocks: {walked}/{len(fast)}", flush=True)
    report("ff")

    data = files(".fd")
    print(f"fd: {len(data)} files", flush=True)
    for index, path in enumerate(data, 1):
        scan_raw(path)
        if index % 100 == 0:
            report(f"fd {index}/{len(data)}")
    report("fd")

    ordered = sorted(names)
    written = os.path.join(OUT, "retail.txt")
    # LF on every platform: these rows get hashed and compared, and a stray CR is part of the
    # name as far as any hash is concerned. See .gitattributes.
    with open(written, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(ordered))

    print(f"wrote {len(ordered)} names to {written}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
