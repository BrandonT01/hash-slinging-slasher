# The script library

Two kinds of thing live here, and the difference matters.

**Reconnaissance** answers "what should I run tonight?" Run these before choosing a method; they
cost seconds and they are the difference between a night that adds something and a night that
repeats somebody.

**Generators** are methods. They print candidate names to standard output and you pipe them into
`confirm_list`, which does the careful half — the game's hash, the unnamed set, exclusion against
the tables, the run notes, results that only ever grow.

```
python scripts/continuations.py | bin\windows\confirm_list.exe - --label "per-prefix continuations"
```

That is the whole shape of inventing a method here. **You do not have to write Rust.** A method is
a program that prints names; anything that can print names is a method.

---

## Reconnaissance

| script | answers |
|---|---|
| `coverage.py` | where the unnamed assets actually are, per pool, per game. **Run this before believing a pool is worth a night.** |
| `methods_report.py` | what every submission in this repository was, what it cost and what it returned. `--by-method` is the useful view; `--duplicates` shows which submissions returned identical names. |
| `families.py` | the shape of what has been found — directories, leading and trailing tokens, segment counts, numbered families and which members are missing. |
| `cross_type.py --measure` | how strongly one asset type's names predict another's. Measured, not assumed. |
| `snapshot.py` | run directly for a one-line summary per game. Used as a library by everything else. |
| `check_docs.py` | whether the documentation still describes the repository that exists. Runs in CI. |
| `reach.py` | **what share of known names the lists could rebuild at all.** A ceiling, not a yield: whatever the lists cannot express, no pass can find however long it runs, and nothing in a run says so. `--missing` names the commonest beginnings and endings not carried. |

## Generators

| script | builds candidates by |
|---|---|
| `continuations.py` | offering each prefix the tokens measured to follow **that** prefix, rather than the tokens that are globally common. Directory prefixes get the whole vocabulary. |
| `families.py --gaps` | filling the holes in numbered families — a family with three confirmed members is evidence about a fourth that no global rule can match. |
| `cross_type.py --from A --to B` | taking cores that exist in one asset type and spelling them the way another type spells things. Check `--measure` first: some pairs have no seam at all. |
| `sound_languages.py` | respelling a known sound in each of the twelve shipped languages and three encoding tags. Black Ops 4 only — Cold War's language tables are already complete. |
| `image_channels.py` | offering every other channel (`_c`, `_n`, `_g`, `_o`, `_m`, `_s`, `_r` …) of an image we hold one channel of. 88.8% of cores carry more than one. |
| `token_edits.py` | names one token longer or shorter than a known name. The only generator here that changes a name's length; everything else substitutes. |
| `materials_from_images.py` | stripping an image name to its core and offering it as a material, under all twelve directories and in both the `mtl_` and bare spellings. The material/image seam run backwards -- `images_from_materials` is the forward direction. **Measured near-spent**: 7 names in Cold War and 10 in Black Ops 4. |
| `affix_sweep.py` | **every** short prefix and suffix exhaustively, around stems you choose. The only generator that does not need a token to have been measured first — so it reaches affixes used once in the game, which no frequency-ranked list can hold. Sizes itself against a time budget and refuses to exceed it. Targeted, not scheduled: see METHODS.md. |

## Measuring

| script | |
|---|---|
| `derive_lists.py` | regenerates `data/prefixes.txt` and `data/suffixes.txt` from the tables **and** the confirmed names. Run it after a productive pass: it folds every new name into the lists, which changes the general search's fingerprint and genuinely reopens the method. |
| `harvest_retail.py` | scrapes strings out of an unpacked game build. Only useful to somebody who owns one. |
| `settings.py` | reads `config.toml`. A library, not a command. |

---

## Contributing a script

The easiest way is to name it when you confirm:

```
python my_generator.py | confirm_list - --label "what it is" --script my_generator.py
```

`--script` copies it into the run, and `submit` puts it in the pull request under
`scripts/contributed/`. Two other routes work as well, so getting this wrong is hard: anything in
`contrib/` is carried, and so is any **new** file in `scripts/` itself. This is not politeness.
The names you found go into a table and are finished; the thing that found them makes every later
contributor faster, and that compounding is the only reason this project can outrun the size of
the problem.

### Your script gets moved, so do not count parent directories

This is the one thing that has broken every contributed script at once. You write a generator in
`contrib/` or in `scripts/`, and `submit` files it under `scripts/contributed/`. A path built from
a fixed number of parents is then correct where you wrote it and wrong where it lands:
`os.path.dirname(os.path.dirname(__file__)) + "/scripts"` resolves to the repository root from
`contrib/`, and from `scripts/contributed/` it resolves to a *scripts/scripts* that has never
existed. Relying on `import snapshot` working because `snapshot.py` happens to sit next to you has
the same fault — it does, until the file moves.

All four scripts in `scripts/contributed/` shipped broken this way and none of them could be run
by anybody who pulled them. Find the root instead, and do it **before** importing `snapshot`
rather than under `if __name__ == "__main__"`, which runs far too late:

```python
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot
```


**This is not hypothetical.** Seven scripts are named in the notes of submissions already merged
here -- `attachments.py`, `crosspool.py`, `modelvariants.py`, `numbervariants.py`, `pathmine.py`,
`soundtails.py`, `streamkeys.py` -- and **not one of them exists**. Between them they found tens of
thousands of names, and every later contributor has had to start without them. Find that list for
yourself with `grep -rho "scripts/[a-z_]*\.py" submissions/ | sort -u`.

A contributed script must have, at the top, in its docstring:

- **what problem it solves**, in one sentence
- **how to run it**, as a line that can be copied
- **what it reads** and **what it writes**
- **whether it is reusable or one-off** — a one-off is still worth contributing, labelled as one
- **what it measured**, if it measured anything: candidates produced, matches, how long

Do not contribute a script with no docstring. A generator nobody can tell the purpose of is worse
than no generator, because somebody will spend an hour working out what it was for.

## Writing a generator

Three rules, and the first is the only one that is really a rule.

1. **Build from names already known to be real.** The published tables, everybody's merged
   submissions, what this machine has confirmed. Never thin air. The median confirmed name has
   seven or eight underscore-separated segments; the space of word sequences that long passes
   2^63 long before the name does, so composing names out of a dictionary cannot work and
   recombining fragments of real names is the only shape that does.

2. **Print to standard output, one name per line, and stream.** `confirm_list` holds one batch at
   a time, so a generator that streams costs no disk at all. A `hash,name` line is accepted too,
   so a results file can be piped straight back in.

3. **Do not expand endings yourself.** The Rust engine peels endings off the wanted ids rather
   than appending them to candidates, which makes an ending nearly free; writing them out as text
   multiplies your output by 4,800 and asks the same question for a terabyte of disk. Generate
   interesting stems; let the general search dress them.

Check the arithmetic before running: a run of *n* candidates against *w* unnamed ids expects
`n * w / 2^63` matches by coincidence. `confirm_list` prints it. Anything seeded is effectively
zero; only unconstrained character sweeps get near one.
