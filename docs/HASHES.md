# Which file is which, and which hash it uses

Everything this project checks against lives in [cod-name-db](https://github.com/echo000/cod-name-db),
and its files do not all use the same hash. Getting the mask wrong is the commonest reason a
correct name fails to resolve, and it fails silently — the name simply looks unknown.

This is the mapping, from Saluki's own loading code (`name_db_manager.rs` for which file belongs to
which game, `constant.rs` / `search.rs` / `sound.rs` for the offsets and masks). It comes from the
author of both Saluki and cod-name-db, which makes it the strongest available statement of what is
correct. Every rule below was verified empirically against the file contents.

## The table

| File | Game(s) | Hash of the name | Key stored as |
|---|---|---|---|
| `fnv1a_xmodels.csv` | **BO4, BOCW** | FNV-1a 64, Treyarch offset | 63-bit (bit 63 cleared) |
| `fnv1a_xanims.csv` | **BO4, BOCW** | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_ximages.csv` | **BO4, BOCW** | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_xmaterials.csv` | **BO4, BOCW** | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_<language>_xsounds.csv` (×12) | **BO4, BOCW** | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_xsounds.csv` | **BO4, BOCW** *(legacy — superseded by the per-language files; not loaded by current Saluki)* | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_soundbanks_aliases.csv` | **BO4, BOCW** *(not loaded by current Saluki, but where both games' alias names belong)* | FNV-1a 64, Treyarch offset | 63-bit |
| `fnv1a_strings.csv` | **BOCW** (bone names, notify/script strings) | FNV-1a 64, Treyarch offset | **60-bit** (top 4 bits cleared) |
| `fnv1a_xanims_v2.csv` | MWIII, BO6, BO7, WZ Mobile | FNV-1a 64, **IW offset** | 63-bit |
| `fnv1a_ximages_v2.csv` | MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, IW offset | 63-bit |
| `fnv1a_xmaterials_v2.csv` | MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, IW offset | 63-bit |
| `fnv1a_xsounds_v2.csv` | Vanguard, MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, IW offset | 63-bit |
| `fnv1a_soundbanks_v2.csv` | MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, IW offset | 63-bit |
| `fnv1a_animpkgs_v2.csv` | MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, IW offset | 63-bit |
| `fnv1a_soundbanks_aliases_v2.csv` | Vanguard, MWII, MWIII, BO6, BO7, WZM | FNV-1a 64, **Treyarch offset** | **full 64-bit, no mask** |
| `fnv1a_bones.csv` | MWII, MWIII | **FNV-1a 32** | full 32-bit |
| `fnv1a_bones_v2.csv` | BO6, BO7, WZM | FNV-1a 64, **Treyarch offset** | **full 64-bit, no mask** |
| `bo2_sab.csv` | BO2 `.sab` audio | **SDBM**, seed 5381, lowercased | 32-bit |
| `bo3_sab.csv` | BO3 `.sab` audio | SDBM, seed 5381, lowercased | 32-bit |
| `bo2_ipak.csv` | BO2 `.ipak` images | *not a hash of the name* — native ipak entry keys | 64-bit |
| `cod_semantics.csv` | all games | *not derivable* — engine-provided semantic hashes | 32-bit |
| `cod_constants.csv` | all games | *not derivable* — engine-provided constant hashes | 32-bit |

## Where to get them, and why it is git rather than the releases

cod-name-db publishes **both**, and they are not the same thing:

| | what it is | how fresh |
|---|---|---|
| `csv/` in the git repository | **the source of truth.** The README says so in its first line, and every rule above is a statement about these files. | the commit itself |
| a GitHub release (`hash_pkg.zip`) | the **compiled** `.cdb` binaries Saluki loads, built from those csv | published minutes *after* the commit — 0.0.279 went out at 22:09 for a csv commit at 22:07 |

So `fetch-tables` clones `csv/` with a shallow, blobless, sparse checkout, and that is correct
rather than a shortcut: the release is downstream of the thing we need, arrives later, and is in a
format this project would have to decompile to read. Releases are for Saluki users; the csv are
for anyone computing against the names.

`start` reports which upstream commit the local checkout is on, and it deliberately does *not*
report file modification times — those are set by our own fetch, so a freshly downloaded copy of
month-old data would report itself as brand new, which is precisely backwards.

## The offsets

One algorithm, two starting offsets. That is the only difference between the plain files and the
`_v2` files.

```
Treyarch era (BO4, BOCW, and the aliases/bones exceptions): 0xCBF29CE484222325
IW era (the _v2 files)                                    : 0x47F5817A5EF961BA
prime                                                     : 0x100000001B3

hash = offset
for each byte of the lowercase name:
    hash = (hash XOR byte) * prime          64-bit wrapping multiply
```

Fold backslashes to forward slashes before hashing. Asset names are lowercase in every game.

**Masking.** The engines use the top bit of an asset hash as a flag, so most keys are stored with
bit 63 cleared: `key = hash & 0x7FFFFFFFFFFFFFFF`. The exceptions are in the table above.

## What this means for this repository

**Only the non-`_v2` files are our games.** `src/bin/confirm_cw.rs` has the list, as
`COLD_WAR_TABLES`. Reading a `_v2` table for *vocabulary* teaches the wrong conventions and is a
known dead end. Reading every table for *exclusion* is free and correct, and `table_keys()` does
exactly that — it re-hashes the stored name as well as taking the stored key, which covers all
three masks without having to know which file used which.

**The twelve per-language sound tables are this game and were being missed.** Until this was
found, `COLD_WAR_TABLES` named only the legacy `fnv1a_xsounds.csv` — 57,593 names. The twelve
files Saluki actually loads hold **825,316 distinct names** between them, and their overlap with
the legacy file is **exactly zero rows**: the legacy names end `.ln75.pc.all.snd` and the current
ones end `.rn75.pc.<lang>.snd`. Sound names are the richest seed material in the whole set — full
directory paths, speaker codes, and dotted tails no other table carries. Every general pass run
before this fix had one fourteenth of the sound vocabulary available to it.

Reproduce that:

```
cd cod-name-db/csv
wc -l fnv1a_xsounds.csv                                  # 57593
cat fnv1a_*_xsounds.csv | cut -d, -f2- | sort -u | wc -l # 825316
comm -12 <(cut -d, -f2- fnv1a_xsounds.csv | sort -u) \
         <(cut -d, -f2- fnv1a_english_xsounds.csv | sort -u) | wc -l   # 0
```

**A note on `fnv1a_xsounds_v2.csv`:** where the full original path is known, keys verify as the
IW-offset hash of the lowercased, forward-slashed path at 63 bits. Many rows carry
community-reconstructed display names whose exact spelling differs, so not every existing row
re-hashes. New contributions should.

## Verifying a contribution by hand

```python
def fnv1a64(name, offset):
    h = offset
    for b in name.lower().replace("\\", "/").encode():
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h

TREYARCH = 0xCBF29CE484222325
IW       = 0x47F5817A5EF961BA

# BO4 / BOCW asset:                 fnv1a64(name, TREYARCH) & 0x7FFFFFFFFFFFFFFF
# MWII/MWIII/BO6/BO7/WZM asset:     fnv1a64(name, IW)       & 0x7FFFFFFFFFFFFFFF
# BOCW string:                      fnv1a64(name, TREYARCH) & 0x0FFFFFFFFFFFFFFF
# soundbank aliases v2 / bones v2:  fnv1a64(name, TREYARCH)
```

`scripts/snapshot.py` implements the BO4/BOCW case as `snapshot.fnv1a`.

## Types with no home yet

cod-name-db carries tables for models, anims, images, materials and sounds. Some identified asset
types have **no destination file at all** — a confirmed `technique_set` name has nowhere upstream
to land, and Black Ops 4 alone holds 3,597 of them with zero previously named.

Proposing and seeding those tables upstream is the most valuable non-grinding contribution
available, because it turns whole pools' worth of findings from unpublishable into publishable.

---

*Source: the cod-name-db README by its author, cross-checked against Saluki's loading code. Last
verified against the repository contents 2026-08-19 (33 csv files present).*
