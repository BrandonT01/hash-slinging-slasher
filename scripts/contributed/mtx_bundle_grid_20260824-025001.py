r"""The cosmetic-bundle grid: item wrappers crossed with the theme vocabulary they wrap.

    python contrib/mtx_bundle_grid.py --write-plan plans/mtx_grid.txt
    bin\windows\confirm_plan.exe plans/mtx_grid.txt --size
    bin\windows\confirm_plan.exe plans/mtx_grid.txt

## Why this ground

`_mtxitem` names are the microtransaction store: calling cards, emblems, charms, stickers,
weapon blueprints, operator skins, vehicle horns. Measured 2026-08-24 across every table
cod-name-db publishes and every name this repository has confirmed:

    5,652 names end in `_mtxitem`.   0 of them are published.   All 5,652 were found here.

That is the whole reason to point something at it. Every other family a generator can seed
from is mostly *already named upstream*, so a pass spends its candidates rebuilding rows the
tables already hold. This family is 100% ours, which means its unnamed remainder has never
been claimed by anybody.

## Why a grid rather than a recombination

METHODS records that pieces taken from *different* names do not recombine (splice: 1 per 13.7
billion; cross-type cores: 0 in 190 M). The exception it also records is a *grid* -- a family
whose axes are real product structure, where the unobserved cells are unobserved because
nobody wrote them down rather than because they cannot exist.

A cosmetic bundle is exactly that. A season ships a theme as a calling card *and* an emblem
*and* a charm *and* a blueprint, under one name. Measured: 213 of 3,982 theme cores (5.3%)
already appear under two or more item families, and the calling-card/emblem pair carries most
of them -- `quartermaster`, `moonshiner`, `zombiepark`, `jacklinks`, `sovietnavy`. Those are
the cells somebody happened to record. The grid is far larger than the record.

So the axes are learned rather than assumed:

  * **wrappers** -- every token-prefix and every `_mtxitem`-terminated token-suffix that at
    least `--min-support` names carry. `callingcards_` x `_s5_mtxitem`,
    `paintjob_stickers_` x `_base_ms_mtxitem`, `po_c_t9_gen_pl_esports_male_` x `_away_pc_mtxitem`.
  * **themes** -- whatever sits between a wrapper pair on a name that carries both.

and the plan asks every theme under every wrapper.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import snapshot

ROOT = snapshot.ROOT
MARK = "_mtxitem"


def mtx_names():
    names = {n.strip().lower().replace("\\", "/") for n in snapshot.confirmed_names() if n.strip()}
    for table in ("fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages", "fnv1a_xanims"):
        names |= {n.strip().lower().replace("\\", "/") for n in snapshot.table_names(table) if n.strip()}
    return sorted(n for n in names if n.endswith(MARK))


def wrappers(names, depth, support):
    """Token-prefixes and `_mtxitem`-terminated token-suffixes carried by `support` names."""
    heads, tails = collections.Counter(), collections.Counter()
    for name in names:
        tokens = name.split("_")
        for i in range(1, min(depth, len(tokens) - 1) + 1):
            heads["_".join(tokens[:i]) + "_"] += 1
        for j in range(1, min(depth, len(tokens) - 1) + 1):
            tails["_" + "_".join(tokens[-j:])] += 1
    return (
        sorted(h for h, n in heads.items() if n >= support),
        sorted(t for t, n in tails.items() if n >= support and t.endswith(MARK)),
    )


def themes(names, heads, tails, shortest):
    """Whatever sits between a wrapper pair, on a name that carries both."""
    heads, tails = sorted(heads, key=len, reverse=True), sorted(tails, key=len, reverse=True)
    out = set()
    for name in names:
        for head in heads:
            if not name.startswith(head):
                continue
            for tail in tails:
                if not name.endswith(tail):
                    continue
                middle = name[len(head) : len(name) - len(tail)]
                if len(middle) >= shortest and not middle.startswith("_") and not middle.endswith("_"):
                    out.add(middle)
    return sorted(out)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--depth", type=int, default=4, help="tokens a wrapper may be long")
    parser.add_argument("--min-support", type=int, default=6, help="names a wrapper must appear on")
    parser.add_argument("--shortest-theme", type=int, default=3)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    names = mtx_names()
    print("names ending %s: %s" % (MARK, format(len(names), ",")), file=sys.stderr)

    heads, tails = wrappers(names, options.depth, options.min_support)
    cores = themes(names, heads, tails, options.shortest_theme)
    print(
        "wrappers: %s head(s) x %s tail(s)   themes: %s"
        % (format(len(heads), ","), format(len(tails), ","), format(len(cores), ",")),
        file=sys.stderr,
    )

    base = os.path.splitext(options.write_plan)[0]
    for suffix, rows in (("begins", heads), ("stems", cores), ("ends", tails)):
        with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
            handle.write("\n".join(rows) + "\n")

    with open(options.write_plan, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by contrib/mtx_bundle_grid.py. Regenerate rather than editing.\n"
            "#\n"
            "# Every cosmetic theme this project has recovered, asked under every store-item\n"
            "# wrapper it has recovered. 0 of the %s seed names are published upstream.\n"
            "\n"
            "label: cosmetic bundle grid, themes x item wrappers\n"
            "begin: @%s.begins.txt\n"
            "stem:  @%s.stems.txt\n"
            "end:   @%s.ends.txt\n"
            "bare:  no\n" % (format(len(names), ","), base, base, base)
        )

    print(
        "\nwrote %s\nabout %s candidates."
        % (options.write_plan, format(len(heads) * len(cores) * len(tails), ",")),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
