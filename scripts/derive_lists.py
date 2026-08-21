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
import collections, os, re, sys, glob

# A sound name's encoding tail. One confirmed xmodel genuinely carries one -- somebody at Treyarch
# pasted a sound path onto a model, verified in Saluki -- and it is kept and submitted as the fact
# it is. It must not reach *these* lists, though: they are the committed vocabulary every future
# pass builds candidates from, so learning an ending off one developer's slip would aim the whole
# search wrongly for as long as the file survives. Kept as a name, declined as a lesson.
SOUND_TAILS = (".rn75.", ".ln75.")

# The pools whose names teach nothing, in both games' spellings. Mirrors `LOW_VALUE_POOLS` in
# src/lib.rs; `scripts/check_docs.py` fails if that list gains an entry this one does not have.
LOW_VALUE = frozenset(
    {"localizeentry", "localize_entry", "streamkey", "xmodelmesh", "xmodelmesh_v2"}
)


def teaches_the_wrong_shape(kind, name):
    return not kind.startswith("sound") and any(tail in name for tail in SOUND_TAILS)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = settings.tables_csv()
CONFIRMED = settings.path("findings", "findings")
FROM_MATERIALS = settings.path("findings", "findings")

# Everybody's merged work, which is the vocabulary that actually widens these lists.
#
# This was measured on 2026-08-21 and it is the reason this path exists at all. Folding in 1,218
# names merged from another contributor took the general search from 55 names to 294. Folding in
# ~2,000 names found by *these same passes* took the next one to 51 -- worse than before the fold,
# on a corpus two and a half times larger. A search that re-measures its own output learns the
# beginnings and endings it has just finished using; it is somebody else's names that describe
# ground this machine has never been near.
#
# And until that day, `submissions/` was never read here at all: 103,320 names from every
# contributor, sitting committed in the repository, feeding nothing. They reach the published
# tables eventually, but "eventually" is upstream's merge schedule, not tonight's pass.
SUBMISSIONS = os.path.join(HERE, "submissions")

DATA = os.path.join(HERE, "data")

# `submissions/` names a file `<kind>_<yyyymmdd-hhmmss>.txt`; `findings/` names it `<kind>.txt`.
STAMPED = re.compile(r"_\d{8}-\d{6}$")

# The tables that are Cold War rather than a newer game, by their marker density.
# **Order matters.** Each table gets a capped share below, but the shares are taken in this order
# and the ceiling binds long before the list ends -- so a table placed last gets whatever is left,
# which on the first attempt at this was nothing at all: adding the sound tables at the end
# contributed 313 beginnings and **zero** endings. Smallest and least-represented first.
COLD_WAR = [
    # Sound, which these lists were blind to until the sound pools became something we grind.
    # `sound_asset` and `sound_alias` are now ~138,000 of the wanted ids across the two games, and
    # not one beginning or ending had ever been measured from a sound name. Each table gets its
    # own guaranteed places below before global popularity fills the rest, so adding them widens
    # the vocabulary rather than letting the biggest pool crowd the others out.
    "fnv1a_soundbanks_aliases",
    "fnv1a_english_xsounds",
    "fnv1a_xsounds",
    "fnv1a_xanims",
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
]

# `fnv1a_xsounds` is the Black Ops 4 SAB table and is **mixed**: 8,403 of its names use
# backslashes and 49,189 use forward slashes, none use both. The backslash rows are the SAB
# entries, whose ids are the hash of the unfolded string.
#
# They are measured anyway, with the separator normalised to `/` below, because the *shape* of a
# sound path is the same either way and only the separator differs. Keeping one canonical list
# costs no slots and loses nothing: a `--no-fold` run translates `/` back to `\` as it loads, so
# the same measured vocabulary serves both normalisations. Measuring them twice, once per
# separator, would have spent half the ceiling saying the same thing.

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

# What must survive every regeneration, whatever else is measured.
#
# These lists are capped, so measuring a new table does not grow them -- it *displaces* whatever
# ranked lowest. That failure is silent by construction: the file still has its 700 lines and
# still looks healthy, while the beginnings that reach most of the game have quietly gone. It has
# happened once already. Adding the sound tables made `published["directories"]` thousands of deep
# sound paths long, that take had no cap, and it consumed the whole ceiling: `p9_`, `i_`, `mtl_`,
# `attach_` and `vm_` all disappeared in one run.
#
# Nothing downstream would have complained. Every later pass would simply have found less, for as
# long as the file survived. So the list refuses to be written without them.
#
# The counts are how many published names each one heads, measured from the tables, and they are
# the argument for the entry being here. Anything added should carry the same justification.
MUST_KEEP_PREFIXES = {
    "p9_": 77248, "p8_": 66172, "p7_": 42516, "attach_": 27504,   # xmodel
    "mtl_": 343794, "i_": 403889, "c_": 16617,                    # material, image
    "vm_": 18088, "ai_": 11226, "sdr_": 6976,                     # xanim
    "ui_": 31742, "volume0_": 52256,                              # image
    # The twelve material directories. `mc/` heads 496,666 names and `ec/` heads 25, which is
    # exactly why they cannot be chosen by popularity.
    "mc/": 496666, "wc/": 7979, "clt/": 5762, "splm/": 3899, "vd/": 2340, "cltp/": 2278,
    "ei/": 1639, "mcs/": 1638, "vdd/": 110, "el/": 103, "mcp/": 40, "ec/": 25,
}

# The endings the game most depends on, and the same guard as the beginnings above.
#
# This list is capped too, and it displaces the same way. Measuring the sound tables pushed out
# endings covering 115,606 published names in one run -- `_proxy`, `_maps1`, `_maps2` and `_col`
# among them -- and nothing said so: the file still had its 4,800 lines. These forty are the
# most-used trailing segments across models, materials, images and anims, covering 748,684
# published names between them, and the run refuses to produce a list without them.
#
# The numbers are how many published names each ending closes, and they are the argument for the
# entry being here. Anything added should carry the same.
MUST_KEEP_ENDINGS = {
    '_c': 120466, '_01': 105373, '_n': 95007, '_g': 51864,
    '_02': 42455, '_o': 40176, '_m': 35669, '_s': 33768,
    '_03': 20182, '_r': 18651, '_view': 14575, '_world': 14229,
    '_04': 11420, '_metal': 9763, '_decal': 8879, '_dead': 7619,
    '_16': 7607, '_05': 7132, '_a': 6923, '_b': 6705,
    '_proxy': 6043, '_icon': 5754, '_maps1': 5748, '_on': 5660,
    '_maps2': 5262, '_red': 4909, '_e': 4627, '_06': 4625,
    '_white': 4474, '_wet': 4474, '_glass': 4399, '_black': 4214,
    '_1': 4141, '_wood': 3904, '_cst': 3846, '_2': 3773,
    '_base': 3704, '_large': 3625, '_blend': 3581, '_snow': 3458,
}

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
                # Normalised to forward slashes so one list serves both normalisations -- see the
                # note beside COLD_WAR. A `--no-fold` search translates them back.
                yield line.split(",", 1)[1].lower().replace(chr(92), "/")


# Which confirmed pools belong to which group's lists. A sound ending tried against a model id
# can only ever be a coincidence, so measuring one group's names into the other's list spends a
# capped ceiling on vocabulary that cannot match -- exactly what `derive`'s docstring describes
# and what widening to `submissions/` would otherwise have made much worse, since it carries 77
# `sound_alias` and 19 `sound_asset` files.
GENERAL_POOLS = frozenset({"xanim", "xmodel", "material", "image"})
SOUND_POOLS = frozenset({"sound_alias", "sound_asset"})


def found_names(pools=None):
    # Deduplicated, because `CONFIRMED` and `FROM_MATERIALS` are the same directory and the
    # pair walked it twice -- counting this machine's own names at double weight against everybody
    # else's at single. The takes below are popularity rankings against a fixed ceiling, so that
    # doubling directly displaced other contributors' vocabulary, which is the opposite of what
    # reading `submissions/` is for.
    seen_folders = []
    for folder in (CONFIRMED, FROM_MATERIALS, SUBMISSIONS):
        if folder not in seen_folders:
            seen_folders.append(folder)

    for folder in seen_folders:
        # Recursive, because findings are kept per game now -- findings/<game>/ and its run_*
        # folders. A flat glob of the root would quietly measure nothing at all.
        for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
            kind = STAMPED.sub("", os.path.basename(path).split(".")[0])

            # The low-value pools are never measured, and there are more of them than one.
            #
            # A localize entry is a CATEGORY/KEY pair whose plain text already ships in the build;
            # a mesh name ends in 26 base32 characters hashed from the mesh itself; a streamkey is
            # a sequential `d3dbsp` terrain string. None of their conventions belong to a hunted
            # pool, and an ending measured off one aims every later pass slightly wrongly.
            #
            # This used to test `startswith("localizeentry")`, which is one spelling of one of
            # them -- and `submissions/` carries `localize_entry_*.txt`, the Black Ops 4 spelling
            # that `LOW_VALUE_POOLS` in src/lib.rs names explicitly. Reading everybody's
            # submissions made that gap live.
            if kind in LOW_VALUE or kind.startswith("pool_"):
                continue

            # Only the pools this group's lists will be used against.
            if pools is not None and kind not in pools:
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

            # And every leading segment of it, not only the whole thing.
            #
            # A candidate is `beginning + stem + ending`, and the stem is any piece cut at a mark
            # -- so `fly/footsteps/stakeout/fs_asphalt_walk_01` is reachable from the beginning
            # `fly/` with a long stem just as well as from its entire directory. Counting only the
            # full directory meant deep paths contributed one very specific beginning each and no
            # short ones, and 700 slots cannot hold thousands of those. Measured: it left Black
            # Ops 4's sound names 19.2% reachable, on the largest unnamed pool in the project.
            #
            # The short ones are worth far more per slot: `fly/` heads thousands of names where
            # `fly/footsteps/stakeout_overrides/asphalt_walk/` heads 158.
            for index, character in enumerate(directory[:-1]):
                if character == "/":
                    directories[directory[: index + 1]] += 1

    return dict(one=one, two=two, three=three, prefixes=prefixes,
                directories=directories, rooted=rooted)


# Measured per table as well as all together. The tables differ in size by an order of
# magnitude, and a single global popularity ranking lets the biggest pool's conventions crowd
# every other pool's out of the ceiling -- the committed lists once carried 9 xanim-shaped
# endings out of 4,800 against 47,859 published xanim names. Each table's own commonest
# beginnings and endings are guaranteed a place first; global popularity fills the rest.
def derive(tables, suffix_file, prefix_file, keep_endings, keep_prefixes, lean_sound=True,
           pools=None):
    """Measure one group of tables into its own pair of lists.

    **One budget per search, not one budget shared.** The ceilings exist because coincidental
    matches scale with `stems x beginnings x endings`, and that is a real cost -- but a sound
    ending tried against a model id can only ever be a coincidence, never a match. Mixing every
    table into one capped list therefore made both halves worse: the sound vocabulary displaced
    endings covering 115,606 published names, and in exchange the model passes gained endings that
    could not match anything they were hunting.
    Measured separately, each search gets the whole ceiling for vocabulary that can actually reach
    what it is looking for. Nothing is sacrificed and the coincidence rate per pass goes *down*,
    because no pass carries the other's endings any more.
    """
    global suffixes, seen, prefixes, seen_prefix, per_table, published, confirmed, COLD_WAR
    COLD_WAR = tables

    per_table = {table: measure(table_names(table)) for table in COLD_WAR}

    published = {key: collections.Counter() for key in
                 ("one", "two", "three", "prefixes", "directories", "rooted")}
    for measured in per_table.values():
        for key in published:
            published[key].update(measured[key])

    confirmed = measure(found_names(pools))

    print(f"measured {sum(published['one'].values())} published names and "
          f"{sum(confirmed['one'].values())} confirmed ones", file=sys.stderr)

    # Seeded with what must survive, before anything competes for the ceiling. A guard that only
    # *detects* the loss leaves somebody to fix it by hand every time a table is added; taking these
    # first means the loss cannot happen, and the guard below becomes the belt to this pair of braces.
    suffixes, seen = list(keep_endings), set(keep_endings)


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
    # Held to a share, not given the whole budget.
    #
    # Confirmed names come first because they are what no published table holds. That was right
    # when there were a few thousand of them. After a night's grinding there were 253,120, which
    # produced 13,199 endings on their own -- nearly three times the entire 4,800 ceiling -- so
    # every published ending was measured, ranked, and then dropped by the cap before it could be
    # written. `_01.rn75.pc.en.snd` ends 30,786 published names and was not carried; sound-file
    # ending reach measured 27.8% with the names sitting in the table being measured.
    #
    # So confirmed keeps its priority but not the whole ceiling. The published tables are the only
    # source of vocabulary this project has not already found, and a list that cannot see them
    # stops learning anything new.
    confirmed_share = max(1, (MOST_ENDINGS * 3) // 5)
    print("endings", file=sys.stderr)
    take(confirmed["one"], FOUND_ENDING_MIN, f"confirmed, one segment at >={FOUND_ENDING_MIN}",
         cap=confirmed_share // 3)
    take(confirmed["two"], FOUND_ENDING_MIN, f"confirmed, two segments at >={FOUND_ENDING_MIN}",
         cap=confirmed_share // 3)
    take(confirmed["three"], FOUND_ENDING_MIN, f"confirmed, three segments at >={FOUND_ENDING_MIN}",
         cap=confirmed_share // 3)

    # Each pool's own conventions next, held to a share each, so that what xanim names end in
    # cannot be crowded out of the ceiling by the long tail of a table five times its size.
    # Sound gets a much smaller share than the rest, and the reason is diversity rather than
    # importance. Its endings are hundreds of near-identical variants -- `_01.rn75.pc.en.snd`,
    # `_02.rn75.pc.en.snd`, on and on -- so each slot buys far less reach than a model ending does,
    # and the numbered part is what `confirm_variants` walks anyway. Given the full share they took
    # 418 slots and displaced endings covering 115,606 published names, `_proxy`, `_maps1`, `_maps2`
    # and `_col` among them.
    SOUND_TABLES = {"fnv1a_soundbanks_aliases", "fnv1a_english_xsounds", "fnv1a_xsounds"}

    for table in COLD_WAR:
        pool = table.replace("fnv1a_", "")
        # `lean` exists so that sound endings do not displace general ones -- a sound ending is
        # `_01.rn75.pc.en.snd`, `_02.rn75.pc.en.snd`, on and on, so each slot buys little reach in
        # a general pass.
        #
        # It must NOT apply when building the sound list itself. It did, and the sound list was
        # starved by a rule written to protect the general list *from* it: `_01.rn75.pc.en.snd`
        # alone ends 30,605 published names and was not carried, and only 9 of 4,800 sound endings
        # were dotted at all. Measured effect: sound-file ending reach of 27.8% where the names
        # were sitting right there in the table being measured.
        lean = lean_sound and table in SOUND_TABLES
        take(per_table[table]["one"], ONE_MIN, f"{pool}, one segment", cap=60 if lean else 400)
        take(per_table[table]["two"], TWO_MIN, f"{pool}, two segments", cap=30 if lean else 200)
        take(per_table[table]["three"], THREE_MIN, f"{pool}, three segments", cap=15 if lean else 100)

    take(published["one"], ONE_MIN, f"published, one segment at >={ONE_MIN}")
    take(published["two"], TWO_MIN, f"published, two segments at >={TWO_MIN}")
    take(published["three"], THREE_MIN, f"published, three segments at >={THREE_MIN}")
    for item in EXTRA:
        if item not in seen:
            seen.add(item)
            suffixes.append(item)

    prefixes, seen_prefix = list(keep_prefixes), set(keep_prefixes)


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
    # Every *shallow* directory first, however little used. Ranking these by popularity keeps `mc/`
    # and drops `ec/`, which heads only 25 names and is the whole of the naming for everything under
    # it -- the failure this take exists to prevent.
    #
    # Deep directories are capped, and that distinction is not cosmetic. Sound paths are directories
    # several segments long and there are thousands of them, so taking every one at threshold 1
    # consumed the entire 700-slot ceiling the moment the sound tables were measured: `p9_`, `i_`,
    # `mtl_`, `attach_` and `vm_` all vanished from the list, and `p9_` alone heads 45,879 xmodels.
    # Shallow ones are few enough to take whole; deep ones have to earn their place.
    def shallow(counter):
        return collections.Counter({k: v for k, v in counter.items() if k.count("/") <= 1})


    def deep(counter):
        return collections.Counter({k: v for k, v in counter.items() if k.count("/") > 1})


    take_prefix(shallow(confirmed["directories"]), 1, "every shallow confirmed directory")
    take_prefix(shallow(published["directories"]), 1, "every shallow published directory")
    take_prefix(deep(confirmed["directories"]), 1, "deep confirmed directories", cap=40)
    take_prefix(deep(published["directories"]), 1, "deep published directories", cap=120)
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




    def guard_lists(prefixes, must_keep):
        """Refuse to write a list that has lost a beginning the game depends on."""
        have = set(prefixes)
        missing = sorted(k for k in must_keep if k not in have)

        if missing:
            print("", file=sys.stderr)
            print("REFUSING TO WRITE: the measurement dropped beginnings that must not be lost:", file=sys.stderr)
            for key in missing:
                print("    %-12s heads %d published names" % (key, must_keep[key]), file=sys.stderr)
            print("", file=sys.stderr)
            print("A capped list displaces rather than grows. Something newly measured has crowded", file=sys.stderr)
            print("these out -- cap that take, or raise MOST_PREFIXES, but do not ship this.", file=sys.stderr)
            raise SystemExit(1)




    def guard_endings(endings, must_keep):
        """Refuse to write an endings list that has lost one the game depends on."""
        have = set(endings)
        missing = sorted(k for k in must_keep if k not in have)

        if missing:
            print("", file=sys.stderr)
            print("REFUSING TO WRITE: the measurement dropped endings that must not be lost:", file=sys.stderr)
            for key in missing:
                print("    %-14s closes %d published names" % (key, must_keep[key]), file=sys.stderr)
            print("", file=sys.stderr)
            print("A capped list displaces rather than grows. Cap whatever was newly measured, or", file=sys.stderr)
            print("raise MOST_ENDINGS -- but do not ship this.", file=sys.stderr)
            raise SystemExit(1)


    def write(name, items, most, guard=None):
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

        # Checked against what will actually be written, after the ceiling has cut it. Guarding the
        # input would pass happily while the file that lands is gutted.
        if guard is not None:
            guard(whole)

        with open(path, "w", encoding="utf-8") as handle:
            for item in whole:
                handle.write(item + "\n")

        note = f", {dropped} past the ceiling of {most} dropped" if dropped else ""
        print(f"{name}: {len(items)} measured, {len(kept)} carried{note}, {len(whole)} total",
              file=sys.stderr)
        return len(whole)


    endings = write(suffix_file, suffixes, MOST_ENDINGS,
                    (lambda got: guard_endings(got, keep_endings)) if keep_endings else None)
    beginnings = write(prefix_file, prefixes, MOST_PREFIXES,
                       (lambda got: guard_lists(got, keep_prefixes)) if keep_prefixes else None)

    return endings, beginnings


# The two groups. Each is measured on its own and gets the whole ceiling, because each is used by
# a different search: an ordinary pass hunts models, materials, images and anims, and a sound pass
# hunts `sound_asset` and `sound_alias`. Neither carries vocabulary that cannot reach what it is
# looking for.
GROUPS = [
    (
        "the general lists",
        ["fnv1a_xanims", "fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages"],
        "suffixes.txt",
        "prefixes.txt",
        MUST_KEEP_ENDINGS,
        MUST_KEEP_PREFIXES,
    ),
    (
        "the sound lists",
        ["fnv1a_soundbanks_aliases", "fnv1a_english_xsounds", "fnv1a_xsounds"],
        "sound.suffixes.txt",
        "sound.prefixes.txt",
        {},
        {},
    ),
]

# Roughly what a general pass draws on, for reporting what the lists will cost it.
PIECES = 25_000_000
UNNAMED = 270_727

for title, tables, suffix_file, prefix_file, keep_e, keep_p in GROUPS:
    print("", file=sys.stderr)
    print(f"=== {title} ===", file=sys.stderr)
    # The sound group must not lean on itself -- see `lean` in `derive`.
    sound = title == "the sound lists"
    endings, beginnings = derive(tables, suffix_file, prefix_file, keep_e, keep_p,
                                 lean_sound=not sound,
                                 pools=SOUND_POOLS if sound else GENERAL_POOLS)

    per_stem = (beginnings + 1) * (endings + 1)
    print(f"a stem costs {beginnings + 1} forward hashes and reaches {per_stem} candidates",
          file=sys.stderr)
    print(f"against {PIECES:,} pieces that is "
          f"{PIECES * per_stem * UNNAMED / 9.223e18:.1f} names expected by coincidence",
          file=sys.stderr)
