"""Measure the beginnings and endings Cold War names carry, and write the lists the search reads.

The endings and beginnings a name actually carries are measured rather than guessed, because a
hand written list gets the rare ones right and misses the common ones. A hand list of 33 image
suffixes held five that appear zero times in 752,744 real image names while missing `_cm`, which
appears 12,727 times.

Two sources are measured, and the second is the one nothing else has:

  the Cold War tables      what is already published, which is most of the vocabulary
  the confirmed names      what this work has proved and no table holds

The confirmed names matter out of proportion to their number. The tables show no xmodel with a
directory on it; the confirmed xmodels are full of them -- `clt/`, `cltp/`, `splm/` -- so the
beginnings that reach a whole class of models exist only in what has already been found. A list
measured from the tables alone cannot see them.

Only Cold War is measured. The `_v2` tables are MW2022 and BO6 and teach the wrong conventions,
though every table is still read for exclusion elsewhere.

Writes data/prefixes.txt and data/suffixes.txt, one item per line, and refuses to shrink either:
a pass has to be able to be a superset of the pass before it.
"""
import settings
import collections, os, sys, glob

# A sound name's encoding tail. One confirmed xmodel genuinely carries one -- somebody at Treyarch
# pasted a sound path onto a model, verified in Saluki -- and it is kept and submitted as the fact
# it is. It must not reach *these* lists, though: they are the committed vocabulary every future
# pass builds candidates from, so learning an ending off one developer's slip would aim the whole
# search wrongly for as long as the file survives. Kept as a name, declined as a lesson.
SOUND_TAILS = (".rn75.", ".ln75.")


def teaches_the_wrong_shape(kind, name):
    return not kind.startswith("sound") and any(tail in name for tail in SOUND_TAILS)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = settings.tables_csv()
CONFIRMED = settings.path("findings", "findings")
FROM_MATERIALS = settings.path("findings", "findings")
DATA = os.path.join(HERE, "data")

# The tables that are Cold War rather than a newer game, by their marker density.
COLD_WAR = ["fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages", "fnv1a_xanims"]

# Since the search peels its endings off the wanted ids rather than appending them to every
# stem, an ending costs a share of one pass over those ids instead of a whole pass over the
# stems. That is what pays for these thresholds being an order of magnitude below the old ones.
ONE_MIN = 30        # a single trailing segment
TWO_MIN = 200       # two trailing segments, which multiply out much faster
THREE_MIN = 200     # three trailing segments, which the old lists never measured at all
PREFIX_MIN = 200    # a beginning, which still multiplies the forward work directly
ROOTED_MIN = 100    # a directory carrying a leading token

# What the confirmed names show is rarer by construction -- there are forty thousand of them
# against a million table names -- so it is counted at a lower bar. Endings are cheaper than
# beginnings, since a beginning multiplies the forward work and an ending does not, so the bar
# for a beginning is higher.
FOUND_ENDING_MIN = 5
FOUND_PREFIX_MIN = 40

# Hard ceilings on what one measurement may add. Peeling makes an ending nearly free in time,
# but nothing makes it free in accuracy: a run of n candidates against w unnamed ids is expected
# to match n * w / 2^63 names by coincidence however the work is arranged. These keep a pass to
# roughly two or three such names as the searches feed each other and the lists grow.
MOST_ENDINGS = 4800
MOST_PREFIXES = 700

# Endings a family varies that no table can show, because a model's mesh entry hides them behind
# its own hash.
EXTRA = ["_lod0", "_lod1", "_lod2", "_lod3", "_lod4", "_lod5", "_lod6", "_s1", "_s2", "_s3",
         "_000", "_bc", "_cm", "_dm", "_gm", "_jup", "_lg", "_m0", "_m1", "_v3", "_v4", "_v5",
         "_v6"]
EXTRA_PREFIX = ["mtl_", "t9_", "wm_", "i_", "c_", "i_mtl_", "i_c_"]


def table_names(table):
    path = os.path.join(TABLES, table + ".csv")
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if "," in line:
                yield line.split(",", 1)[1].lower()


def found_names():
    for folder in (CONFIRMED, FROM_MATERIALS):
        # Recursive, because findings are kept per game now -- findings/<game>/ and its run_*
        # folders. A flat glob of the root would quietly measure nothing at all.
        for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
            kind = os.path.basename(path).split(".")[0]

            # localizeentry is never measured: those names are CATEGORY/KEY pairs whose plain
            # text already ships in the build, and their conventions belong to no hunted pool.
            if kind.startswith("localizeentry"):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if teaches_the_wrong_shape(kind, line):
                        continue
                    line = line.strip()
                    if "," in line:
                        yield line.split(",", 1)[1].lower()


def measure(names):
    """Count the beginnings and endings a set of names carries."""
    one, two, three = collections.Counter(), collections.Counter(), collections.Counter()
    prefixes, directories, rooted = collections.Counter(), collections.Counter(), collections.Counter()

    for name in names:
        head, separator, base = name.rpartition("/")
        directory = head + separator

        parts = base.split("_")
        if len(parts) < 2:
            continue

        one["_" + parts[-1]] += 1
        two["_" + "_".join(parts[-2:])] += 1
        if len(parts) >= 4:
            three["_" + "_".join(parts[-3:])] += 1

        # The directory belongs to the beginning: a material name is a path, and the path is
        # part of what the engine hashes.
        prefixes[directory + parts[0] + "_"] += 1
        prefixes[directory + "_".join(parts[:2]) + "_"] += 1

        if directory:
            prefixes[directory] += 1
            directories[directory] += 1
            rooted[directory + parts[0] + "_"] += 1

    return dict(one=one, two=two, three=three, prefixes=prefixes,
                directories=directories, rooted=rooted)


# Measured per table as well as all together. The tables differ in size by an order of
# magnitude, and a single global popularity ranking lets the biggest pool's conventions crowd
# every other pool's out of the ceiling -- the committed lists once carried 9 xanim-shaped
# endings out of 4,800 against 47,859 published xanim names. Each table's own commonest
# beginnings and endings are guaranteed a place first; global popularity fills the rest.
per_table = {table: measure(table_names(table)) for table in COLD_WAR}

published = {key: collections.Counter() for key in
             ("one", "two", "three", "prefixes", "directories", "rooted")}
for measured in per_table.values():
    for key in published:
        published[key].update(measured[key])

confirmed = measure(found_names())

print(f"measured {sum(published['one'].values())} published names and "
      f"{sum(confirmed['one'].values())} confirmed ones", file=sys.stderr)

suffixes, seen = [], set()


def take(counter, threshold, note, cap=None):
    added = 0
    for key, count in counter.most_common():
        if count < threshold or (cap is not None and added >= cap):
            break
        if key not in seen:
            seen.add(key)
            suffixes.append(key)
            added += 1
    print(f"  {note}: +{added}", file=sys.stderr)


# What the confirmed names show comes first, because it is what no published table holds and so
# what the ceiling must never be the thing that drops.
print("endings", file=sys.stderr)
take(confirmed["one"], FOUND_ENDING_MIN, f"confirmed, one segment at >={FOUND_ENDING_MIN}")
take(confirmed["two"], FOUND_ENDING_MIN, f"confirmed, two segments at >={FOUND_ENDING_MIN}")
take(confirmed["three"], FOUND_ENDING_MIN, f"confirmed, three segments at >={FOUND_ENDING_MIN}")

# Each pool's own conventions next, held to a share each, so that what xanim names end in
# cannot be crowded out of the ceiling by the long tail of a table five times its size.
for table in COLD_WAR:
    pool = table.replace("fnv1a_", "")
    take(per_table[table]["one"], ONE_MIN, f"{pool}, one segment", cap=400)
    take(per_table[table]["two"], TWO_MIN, f"{pool}, two segments", cap=200)
    take(per_table[table]["three"], THREE_MIN, f"{pool}, three segments", cap=100)

take(published["one"], ONE_MIN, f"published, one segment at >={ONE_MIN}")
take(published["two"], TWO_MIN, f"published, two segments at >={TWO_MIN}")
take(published["three"], THREE_MIN, f"published, three segments at >={THREE_MIN}")
for item in EXTRA:
    if item not in seen:
        seen.add(item)
        suffixes.append(item)

prefixes, seen_prefix = [], set()


def take_prefix(counter, threshold, note, cap=None):
    added = 0
    for key, count in counter.most_common():
        if count < threshold or (cap is not None and added >= cap):
            break
        if key not in seen_prefix:
            seen_prefix.add(key)
            prefixes.append(key)
            added += 1
    print(f"  {note}: +{added}", file=sys.stderr)


print("beginnings", file=sys.stderr)
# Every directory first, however little used, and from both sources. Ranking beginnings by use
# keeps the largest directory and silently drops the rest, which is the whole of the naming for
# everything that lives under them.
take_prefix(confirmed["directories"], 1, "every confirmed directory")
take_prefix(published["directories"], 1, "every published directory")
take_prefix(confirmed["prefixes"], FOUND_PREFIX_MIN, f"confirmed at >={FOUND_PREFIX_MIN}")

# Each pool's own commonest beginnings, held to a share each, for the same reason as the
# endings above.
for table in COLD_WAR:
    pool = table.replace("fnv1a_", "")
    take_prefix(per_table[table]["prefixes"], PREFIX_MIN, f"{pool} beginnings", cap=60)

take_prefix(published["prefixes"], PREFIX_MIN, f"published at >={PREFIX_MIN}")
take_prefix(published["rooted"], ROOTED_MIN, f"published directory plus token at >={ROOTED_MIN}")
for item in EXTRA_PREFIX:
    if item not in seen_prefix:
        seen_prefix.add(item)
        prefixes.append(item)


def write(name, items, most):
    """Write a list: what this measurement found, then whatever the previous list had that it
    did not reach, and the whole thing held to a ceiling.

    The ceiling binds the total rather than only the new part. Carrying forward every item any
    past measurement ever produced is what a superset rule asks for, but the accuracy cost of a
    search is set by how big the lists are and nothing else, so an unbounded carry spends that
    budget on items too rare to have been measured twice. Measured items come first, so the
    carry is what gets cut.
    """
    path = os.path.join(DATA, name)
    kept = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            previous = [line.strip() for line in handle if line.strip()]
        have = set(items)
        kept = [item for item in previous if item not in have]

    whole = (items + kept)[:most]
    dropped = len(items) + len(kept) - len(whole)

    with open(path, "w", encoding="utf-8") as handle:
        for item in whole:
            handle.write(item + "\n")

    note = f", {dropped} past the ceiling of {most} dropped" if dropped else ""
    print(f"{name}: {len(items)} measured, {len(kept)} carried{note}, {len(whole)} total",
          file=sys.stderr)
    return len(whole)


# Roughly what a general pass draws on, for reporting what the lists will cost it.
PIECES = 25_000_000
UNNAMED = 270_727

endings = write("suffixes.txt", suffixes, MOST_ENDINGS)
beginnings = write("prefixes.txt", prefixes, MOST_PREFIXES)

per_stem = (beginnings + 1) * (endings + 1)
print(f"\na stem now costs {beginnings + 1} forward hashes and reaches {per_stem} candidates",
      file=sys.stderr)
print(f"against {PIECES:,} pieces that is "
      f"{PIECES * per_stem * UNNAMED / 9.223e18:.1f} names expected by coincidence",
      file=sys.stderr)
