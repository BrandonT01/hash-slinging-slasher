"""Black Ops 3's own asset names, read out of the retail build Steam ships.

    python contrib/harvest_bo3.py                 find the build, harvest into borrowed/
    python contrib/harvest_bo3.py --limit 4       first four containers, to try it
    python contrib/harvest_bo3.py --zone PATH     point it at a zone folder yourself

**What problem it solves.** METHODS.md says, in three separate places, that the biggest pools are
only reachable "from outside the known names -- the SAB files, a build, or the game's own
strings", and every attempt to get outside has run into a wall: the newer titles' tables are
measured **dead** (0 of 1,175,524), and Black Ops 4 and Cold War are installed as **CASC** --
BLTE-framed 1 GB archives, Cold War's fast files AES-256-CTR on top -- so a raw scan of one
returns byte-coincidence noise and nothing else.

Black Ops 3 is the exception, and it is the one that matters most: it is Black Ops 4's direct
predecessor, Steam ships it as **loose, unencrypted fast files**, and cod-name-db has **no Black
Ops 3 model, material, image or anim table at all** -- only `bo3_sab`, which is audio. So this is
a large, closely related vocabulary the project has never seen, and older-title vocabulary is the
densest transfer measured here (`config.toml`: 1 new per 19,591 candidates).

**Why nobody had read it.** The containers use the same block chain Cold War does -- a 16-byte
record whose fourth word is its own offset, payload following -- with two differences that each
look like "this file is not readable" rather than "you are one constant out":

  - the chain starts at **0x248**, and `harvest_retail.py` searches from `0x400`, so it walks past;
  - the payload is zlib with a **4 KB window**, so the header byte is **0x48, not 0x78**. Every
    scanner that hunts for 0x78 -- including the first three written for this -- reports the file
    as having no zlib in it at all, which is exactly what a compressed-and-encrypted container
    looks like. The test that actually holds is `(cmf & 0x0F) == 8 and (cmf << 8 | flg) % 31 == 0`.

Tested with Cold War's own `oo2core_8_win64.dll` first, which returns 0: it is not Oodle, and that
negative is what sent the search back to deflate.

**Reads** every `.ff` and `.fd` under the build's `zone/` folder, one block at a time, so the peak
cost is one block rather than the size of the build. Nothing decompressed is written down.
**Writes** the names it finds to `borrowed/bo3_build.txt`, which is what `[paths] borrowed` in
`config.toml` already points at -- so the next general pass picks the whole vocabulary up as
pieces with no further wiring, and `scripts/old_titles.py` can respell it.

**Measured, 2026-08-22:** see the run notes in the submission this shipped with.
"""
import argparse
import glob
import os
import sys
import zlib

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

# The name filters live in `harvest_retail.py` and are deliberately not copied: they encode what a
# Treyarch asset name looks like against compressed data that happens to decode as printable, and
# two copies of that would drift apart.
import harvest_retail

# Where Steam puts it, in the order worth trying. `--zone` overrides all of this.
LIKELY = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Call of Duty Black Ops III\zone",
    r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops III\zone",
    r"E:\SteamLibrary\steamapps\common\Call of Duty Black Ops III\zone",
    r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III\zone",
]

BLOCK = 16
BOUNDARY = 0x800000

# Black Ops 3 puts the chain at 0x248. Cold War's is past 0x400. Search wide enough for both
# rather than carrying a per-title constant the next build breaks.
SEARCH_FROM = 0x100
SEARCH_TO = 0x900


def zlib_header_at(blob, at):
    """Whether a zlib stream starts here, without assuming the usual 32 KB window.

    The window size lives in the high nibble of CMF, so a 4 KB stream begins 0x48 and a 32 KB one
    begins 0x78. Hunting for 0x78 alone is what hid this entire build.
    """
    if at + 1 >= len(blob):
        return False
    cmf = blob[at]
    return (cmf & 0x0F) == 8 and ((cmf << 8 | blob[at + 1]) % 31) == 0


def block_table(head):
    """Where the chain begins, proved by a block that names its own offset."""
    for offset in range(SEARCH_FROM, min(SEARCH_TO, len(head) - BLOCK)):
        if int.from_bytes(head[offset + 12:offset + 16], "little") != offset:
            continue
        compressed = int.from_bytes(head[offset:offset + 4], "little")
        decompressed = int.from_bytes(head[offset + 4:offset + 8], "little")
        if 0 < compressed <= decompressed <= 0x4000000:
            return offset
    return None


def walk_chain(path):
    """One container, block by block. Returns how many blocks actually decompressed."""
    size = os.path.getsize(path)
    blocks = 0

    with open(path, "rb") as handle:
        head = handle.read(SEARCH_TO + BLOCK)
        offset = block_table(head)
        if offset is None:
            return 0

        handle.seek(offset)

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

            try:
                output = zlib.decompressobj().decompress(payload[:compressed], decompressed)
            except zlib.error:
                # A codec this does not speak, or a damaged block. Dropped rather than guessed at,
                # and the file carries on -- the same rule `harvest_retail` follows.
                output = b""

            if output:
                harvest_retail.take(output)
                blocks += 1

            offset += BLOCK + aligned
            handle.seek(offset)

    return blocks


def walk_stream(path, window=1 << 16):
    """A container that is one zlib stream rather than a chain -- which is what `.fd` files are.

    Inflated in pieces, so a 27 MB expansion never costs more than a piece at a time.
    """
    with open(path, "rb") as handle:
        head = handle.read(window)

        start = None
        for at in range(len(head) - 1):
            if not zlib_header_at(head, at):
                continue
            try:
                probe = zlib.decompressobj().decompress(head[at:], 1 << 20)
            except zlib.error:
                continue
            if len(probe) > 4096:
                start = at
                break

        if start is None:
            return 0

        handle.seek(start)
        machine = zlib.decompressobj()
        carry = b""
        produced = 0

        while True:
            chunk = handle.read(1 << 22)
            if not chunk:
                break
            try:
                out = machine.decompress(chunk)
            except zlib.error:
                break
            if out:
                produced += len(out)
                # A name can straddle two pieces, so the tail of one is prefixed to the next.
                harvest_retail.take(carry + out)
                carry = out[-256:]
            if machine.eof:
                break

    return 1 if produced else 0


def find_zone(given):
    if given:
        return given
    for path in LIKELY:
        if os.path.isdir(path):
            return path
    return None


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", help="the build's zone folder")
    parser.add_argument("--limit", type=int, help="only this many containers, to try it")
    parser.add_argument("--out", default=os.path.join(_root, "borrowed", "bo3_build.txt"))
    args = parser.parse_args(argv)

    zone = find_zone(args.zone)
    if not zone or not os.path.isdir(zone):
        raise SystemExit(
            "no Black Ops 3 zone folder found. Pass --zone <path>; it is the folder holding\n"
            "the .ff and .fd files, under the Steam install."
        )

    # Recursive, because not every build keeps its containers in one folder: Black Ops 3 does,
    # Black Ops 1 splits them into `Common/` and a folder per language.
    containers = sorted(glob.glob(os.path.join(zone, "**", "*.ff"), recursive=True))
    containers += sorted(glob.glob(os.path.join(zone, "**", "*.fd"), recursive=True))
    if args.limit:
        containers = containers[:args.limit]

    print("%d container(s) in %s" % (len(containers), zone), file=sys.stderr)

    read = 0
    for index, path in enumerate(containers, 1):
        before = len(harvest_retail.names)
        got = walk_chain(path) or walk_stream(path)
        if got:
            read += 1
        print(
            "  [%3d/%3d] %-46s %s %+7d  (%d total)"
            % (
                index, len(containers), os.path.basename(path)[:46],
                "ok" if got else "--", len(harvest_retail.names) - before,
                len(harvest_retail.names),
            ),
            file=sys.stderr,
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        for name in sorted(harvest_retail.names):
            handle.write(name + "\n")

    print(
        "read %d of %d containers; %d distinct names -> %s"
        % (read, len(containers), len(harvest_retail.names), args.out),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
