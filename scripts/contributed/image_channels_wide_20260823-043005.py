"""Image channel completion, with the channel list measured instead of hand-written.

    python contrib/image_channels_wide.py --audit      what the committed list misses
    python contrib/image_channels_wide.py              write the plan's two lists

## The gap

`scripts/image_channels.py` (METHODS.md method 13) is one of the derivations `derive_closure.py`
re-runs after every pass, so its reach is multiplied by every other method here. It carries a
hand-written list of **20** channels:

    c n g o m s r e col nml icon large spc gls ao d h a mask small

Measured against `fnv1a_ximages` and `fnv1a_ximages_v2` on 2026-08-23, the channels it does not
carry include the 8th commonest trailing token in the entire image corpus:

    _thermalmap 16,000   _cm 12,727   _v2 5,043   _normal 3,095   _depth 3,088
    _albedo 3,051        _specular 2,736   _cos 2,551   _geo 2,316   _render 2,045
    _xl 1,981            _sm 1,627   _swatch 1,370   _atlas 1,199   _preview 1,154
    _dmg 1,071           _flipbook 1,038

`_thermalmap` alone heads more image names than fourteen of the twenty carried channels do.

This is the same shape as `contrib/uncarried_endings.py`, which returned 6,674 names the same day,
and as `mcdp/`, which returned 2,846: **a hand-written list is a cap, and everything outside it is
unreachable no matter what is pointed at it.** The fix is never to re-measure -- re-measuring
reports the cap honestly and changes nothing -- it is to take what the cap threw away.

Kept in `contrib/` rather than edited into `scripts/image_channels.py` because `submit` will not
carry a script the library already holds, so an edit there would not reach anybody.
"""

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CARRIED = {"c", "n", "g", "o", "m", "s", "r", "e", "col", "nml", "icon", "large",
           "spc", "gls", "ao", "d", "h", "a", "mask", "small"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--top", type=int, default=250,
                        help="how many measured channels to carry")
    parser.add_argument("--min-count", type=int, default=40,
                        help="a token has to head this many images to count as a channel")
    args = parser.parse_args()

    import snapshot

    published = snapshot.table_names("fnv1a_ximages", "fnv1a_ximages_v2")

    counted = collections.Counter()
    for name in published:
        cut = name.rfind("_")
        if cut > 0:
            counted[name[cut + 1:]] += 1

    # A channel is a trailing token that many different cores wear. Pure numbers are take
    # indices rather than channels -- `scripts/image_channels.py` excludes them too, and the
    # numbered-family methods already own that ground.
    channels = [token for token, count in counted.most_common()
                if count >= args.min_count and not token.isdigit() and len(token) <= 14]
    channels = channels[:args.top]

    if args.audit:
        missing = [t for t in channels if t not in CARRIED]
        print(f"{len(CARRIED)} carried, {len(channels)} measured, {len(missing)} uncarried")
        for token in missing[:30]:
            print(f"  {counted[token]:7}  _{token}")
        return

    # The cores: every image we know to be real, with its own channel taken off.
    names = list(published) + list(snapshot.confirmed_names("image"))
    known = set()
    cores = set()
    for name in names:
        name = name.strip().lower().replace("\\", "/")
        if not name or "_" not in name:
            continue
        known.add(name)
        head, _, tail = name.rpartition("_")
        if head and (tail in CARRIED or tail in channels or len(tail) <= 2):
            cores.add(head)

    (ROOT / "contrib" / "chan_cores.txt").write_text(
        chr(10).join(sorted(cores)) + chr(10), encoding="utf-8")
    (ROOT / "contrib" / "chan_ends.txt").write_text(
        chr(10).join("_" + token for token in sorted(channels)) + chr(10), encoding="utf-8")
    print(f"{len(cores)} cores, {len(channels)} channels "
          f"-> {len(cores) * len(channels):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
