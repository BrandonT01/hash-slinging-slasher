"""Reads a captured snapshot and the hash tables, so a script can ask what is still unnamed.

Every analysis script here needs the same three things: the ids a game holds, which pool each one
sits in, and which of them the community can already name. This is that, once.

The pool names are parsed out of `src/lib.rs` rather than copied into this file. Copying them
would work today and be wrong within a month -- there are two lists of two hundred entries, the
games number their asset types differently, and a stale copy does not fail loudly. It mislabels
findings, which is worse.

Usage as a library:

    import snapshot
    snap = snapshot.read("snapshots/blkopscw.ids")     # -> Snapshot
    known = snapshot.known_hashes()                    # -> set of ints
    snap.unnamed(known)                                # -> {id: pool index}

Run it directly for a one-line summary of every snapshot in the repository.
"""
import glob
import os
import re
import struct
import sys

import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAGIC = b"CODIDS"
RECORD = 10

BASIS = 0xCBF29CE484222325
PRIME = 0x100000001B3
ID_MASK = 0x7FFFFFFFFFFFFFFF

# Pools no rule can reach or that are known to be worth nothing. Kept in step with
# LOW_VALUE_POOLS and UNREACHABLE on the Rust side; `check_docs.py` fails if they drift.
SKIP = {"xmodelmesh", "streamkey", "localizeentry", "localize_entry"}

# The five asset types this project is actually for.
IMPORTANT = {"xmodel", "xanim", "image", "material", "sound_asset", "sound"}


def fnv1a(name):
    """The game's hash: FNV-1a 64, lowercased, backslashes folded to forward slashes.

    Both games use it and so do all the non-`_v2` tables. See docs/HASHES.md for which files use
    which offset and which mask -- getting the mask wrong is the commonest reason a correct name
    fails to resolve.
    """
    h = BASIS
    for byte in name.strip().lower().replace("\\", "/").encode("utf-8", "replace"):
        h = ((h ^ byte) * PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def fnv1a_nofold(name):
    """The same hash, leaving backslashes alone.

    Black Ops 4's SAB sound names are stored with literal backslashes and their ids are the hash
    of exactly that. Measured against the 8,385 of them cod-name-db already names: 8,385 reproduce
    this way, 0 with the usual fold. Every other table folds harmlessly, because its names already
    use forward slashes.
    """
    h = BASIS
    for byte in name.strip().lower().encode("utf-8", "replace"):
        h = ((h ^ byte) * PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def _pool_lists():
    """The two asset-type enums, read out of src/lib.rs so there is one copy of them anywhere."""
    source = open(os.path.join(ROOT, "src", "lib.rs"), encoding="utf-8").read()
    out = {}

    for constant, game in (("POOLS", "BLKOPSCW"), ("BO4_POOLS", "BLKOPS04")):
        match = re.search(
            r"pub const %s: &\[&str\] = &\[(.*?)\];" % constant, source, re.S
        )
        if not match:
            raise SystemExit("src/lib.rs no longer declares %s in the expected shape" % constant)
        out[game] = re.findall(r'"([^"]+)"', match.group(1))

    return out


POOLS = _pool_lists()


class Snapshot:
    def __init__(self, game, records):
        self.game = game
        self.records = records          # list of (id, pool index)
        self.pools = POOLS.get(game, [])

    def pool_name(self, index):
        return self.pools[index] if index < len(self.pools) else "pool_%d" % index

    def by_pool(self):
        """{pool name: [ids]}, in pool order."""
        out = {}
        for asset_id, pool in self.records:
            out.setdefault(self.pool_name(pool), []).append(asset_id)
        return out

    def unnamed(self, known, skip=SKIP):
        """{id: pool name} for everything the tables cannot name."""
        out = {}
        for asset_id, pool in self.records:
            name = self.pool_name(pool)
            if name in skip:
                continue
            if asset_id in known:
                continue
            out[asset_id] = name
        return out

    def __len__(self):
        return len(self.records)


def read(path):
    with open(path, "rb") as handle:
        blob = handle.read()

    if len(blob) < 16 or blob[:6] != MAGIC:
        raise SystemExit("%s is not a snapshot file" % path)

    version, name_length = struct.unpack_from("<HH", blob, 6)
    if version != 1:
        raise SystemExit("%s is snapshot version %d, and this reads version 1" % (path, version))

    at = 10
    game = blob[at:at + name_length].decode("utf-8")
    at += name_length

    (count,) = struct.unpack_from("<Q", blob, at)
    at += 8

    records = []
    for index in range(count):
        offset = at + index * RECORD
        asset_id = int.from_bytes(blob[offset:offset + 8], "little")
        pool = int.from_bytes(blob[offset + 8:offset + 10], "little")
        records.append((asset_id, pool))

    return Snapshot(game, records)


def snapshots():
    """Every snapshot in the repository, newest game first is not meaningful so: sorted."""
    folder = settings.path("snapshots", "snapshots")
    return sorted(glob.glob(os.path.join(folder, "*.ids")))


def known_hashes(tables=None):
    """Every hash the community tables already resolve, under both spellings of the top bit.

    Both the stored key and the hash of the stored name are taken, because the files do not all
    store keys at the same width -- `fnv1a_strings.csv` masks to sixty bits, and the two `_v2`
    exceptions store the full sixty-four. Re-hashing the name covers all of them.
    """
    folder = tables or settings.tables_csv()
    known = set()

    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                key, _, name = line.partition(",")
                try:
                    value = int(key.strip(), 16)
                    known.add(value)
                    known.add(value & ID_MASK)
                except ValueError:
                    pass
                if name.strip():
                    h = fnv1a(name)
                    known.add(h)
                    known.add(h & ID_MASK)

    return known


def table_names(*tables):
    """The names one or more tables hold, without their keys."""
    folder = settings.tables_csv()
    out = []

    for table in tables:
        path = os.path.join(folder, table + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _, _, name = line.partition(",")
                name = name.strip()
                if name:
                    out.append(name)

    return out


def confirmed_names(kind=None):
    """Everything this machine has confirmed, plus every merged submission in the repository.

    Both, deliberately. What this machine found is the freshest seed material there is, and what
    everybody else submitted is the same thing from twenty other machines.

    `kind` narrows to one asset type, and any script measuring a *convention* must pass it. The
    files are named for the pool a name was filed under -- `material.txt` in a findings run,
    `material_20260819-041239.txt` in a submission -- so the type is recoverable, and mixing types
    silently destroys exactly the measurement being taken. Getting this wrong makes every asset
    type look like it wears every other type's decorations.
    """
    out = []

    for folder in (settings.path("findings", "findings"), os.path.join(ROOT, "submissions")):
        for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
            stem = os.path.splitext(os.path.basename(path))[0]

            if kind and stem != kind and not stem.startswith(kind + "_"):
                continue

            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    key, _, name = line.partition(",")
                    name = (name or key).strip()
                    if name:
                        out.append(name)

    return out


if __name__ == "__main__":
    found = snapshots()
    if not found:
        raise SystemExit("no snapshots found; they ship with the repository")

    print("reading the tables (a few seconds)", file=sys.stderr)
    known = known_hashes()

    for path in found:
        snap = read(path)
        left = snap.unnamed(known)
        important = sum(1 for pool in left.values() if pool in IMPORTANT)
        print(
            "%-10s %8d assets  %8d unnamed and reachable  %8d of those in the five types"
            % (snap.game, len(snap), len(left), important)
        )
