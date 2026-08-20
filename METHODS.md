# Methods

`AGENTS.md` says how to run. This says **what to run, what it reaches that nothing else does, and
how to tell when it is spent** — so that a fresh assistant with no memory of last night does not
run whichever method is listed first and re-sweep ground that is already bare.

Read this before choosing. Then check what has already been done:

```
python scripts/methods_report.py --by-method     what has been run here, and what it returned
python scripts/coverage.py --five                where the unnamed assets actually are
```

---

## The registry

| # | method | reaches | run it with | status |
|---|---|---|---|---|
| 1 | general search | anything as *beginning + stem + ending* | `confirm_cw` | **exhausted at the committed lists.** Re-measure first — see below |
| 2 | per-prefix continuations | families the global lists cannot express | `scripts/continuations.py` → `confirm_list` | reaches 496 the general search misses, but only **5** were new to the community |
| 3 | materials → images | `image`, through the strongest measured cross-type seam | `images_from_materials` | productive after any material gain |
| 4 | numbers in place | family members whose number sits mid-name | `confirm_variants` | productive; widen with `swaps` |
| 5 | family gap filling | holes between confirmed family members | `scripts/families.py --gaps` → `confirm_list` | thin (1 new in 22,594) — mostly covered by 4 |
| 6 | cross-type spelling | one type's cores spelled as another's | `scripts/cross_type.py` → `confirm_list` | **measure the seam first.** Only 2 of 12 pairs are worth it |
| 7 | sound dotted tails | everything past the first dot | `confirm_sounds` | reopened — see the sound vocabulary note |
| 8 | reading the tables and extending | whatever the community half-finished | any generator → `confirm_list` | never exhausts; depends on noticing |
| 9 | cross-game techset pairs | `techset` / `technique_set` | `techset_probe`, `techset_pair` | BO4 productive; Cold War conclusively ruled out |
| 10 | sibling token substitution | one **non-numeric** token in the *middle*, both sides kept | `scripts/contributed/slotswap_20260819-225818.py` → `confirm_list` | productive: 2,789 names over four runs. Widen with `--cap`, `--context` |
| 11 | family column cross product | names differing in **two or more** places at once | `scripts/contributed/templates_20260819-220821.py` → `confirm_list` | 115 on top of a freshly-swept slotswap. Narrow ground, real ground |
| 12 | sound language and encoding variants | the same sound in the other eleven languages | `scripts/sound_languages.py` → `confirm_list` | Black Ops 4 only: 38. Cold War returns 0 — its language tables are already complete |
| 13 | image channel completion | the other channels of an image we hold one channel of | `scripts/image_channels.py` → `confirm_list` | 456 BO4, 59 CW. Compounds with method 3, which seeds from the other side |
| 14 | token insertion and deletion | names one token **longer or shorter** than a known name | `scripts/token_edits.py` → `confirm_list` | 700 BO4, 384 CW across all four types. The only method that changes a name's length |
| 15 | affix sweep | affixes used **once** in the game, which no measured list can hold | `scripts/affix_sweep.py` → `confirm_list` | **targeted only.** Blind: 1 name per 532 M candidates. Aimed at a family you suspect: the only thing that reaches it |
| — | localize unfolding | `localizeentry` | `confirm_localize` | **off, and refuses to run.** Worthless — see dead ends |

---

## The shape of the problem

**Regenerate these rather than trusting them:** `python scripts/coverage.py --five`.

| | Cold War | Black Ops 4 |
|---|---|---|
| assets captured | 1,626,209 | 1,023,902 |
| filled pools | 202 | 156 |
| unnamed in pools worth searching | 204,407 | 185,686 |
| **unnamed in the five types that matter** | **136,467** | **141,889** |

Per pool, the five types, unnamed / total:

| | Cold War | Black Ops 4 |
|---|---|---|
| `image` | 46,198 / 245,235 | 60,316 / 167,360 |
| `material` | 37,758 / 158,158 | 50,551 / 122,750 |
| `xmodel` | 20,826 / 85,612 | 20,922 / 61,139 |
| `xanim` | 12,386 / 28,468 | 10,001 / 21,968 |
| `sound_asset` (files) | 19,301 / 97,217 | **70,878 / 79,263** |
| `sound_alias` (alias names) | **43,603 / 50,890** | 23,790 / 50,043 |
| `sound` (banks — not wanted) | — | 99 / 100 |

**The two sound pools are not loader assets and had to be put there.** Sound files live in SAB
files Cordycep never opens; alias names live inside the bank assets as hashes. Both were read out
of the games — the SABs directly, the aliases through Amadeus, which knows those record layouts —
and injected. Cold War's aliases are only **14.3% named**, which makes them the least-worked
ground in either game.

They go to *different* tables upstream — files to `fnv1a_xsounds.csv`, aliases to
`fnv1a_soundbanks_aliases.csv` — so the pools must not be confused. Aliases need no `--no-fold`;
their names carry no backslashes.

Nobody has come close to finishing either, and the two games are not the same problem:

- **Cold War** is where most of the work has been done, and its sound pool is worth 19,301 names.
- **Black Ops 4 is now the bigger prize outright.** It is image and material rich and under 60%
  named in both, and its `sound_asset` pool — injected from the SAB files, since the loader never
  sees those sounds — is **70,878 unnamed of 79,263, only 10.6% named**. That is the single largest
  untouched pool in either game. Grind it with `--no-fold`.

Both games use the same hash and the same normalisation, so one implementation serves both, and
`--game BLKOPS04` on any search is all it takes to switch.

**Grind both.** Until recently the project ground only Cold War, because `config.toml` does not
exist in a fresh clone and the fallback was Cold War -- so a repository calling itself a Cold War
and Black Ops 4 solver got its Black Ops 4 work from exactly one contributor. `start` alternates by
how many passes each game has had on the machine, findings are kept per game in `findings/<game>/`,
and `submit` opens one pull request per game titled `[BLKOPS04] findings from ...`. Setting `game`
in `config.toml` turns the alternation off and that choice is then respected.

### Two figures that were wrong, and are corrected here

> **`xmodelmesh` in Cold War is 271,840 ids, not 827,935.** The larger figure came from a line in
> `confirm_cw` that subtracted the wanted set from *every* unnamed id and attributed the whole
> difference to the mesh pool. Most of that difference was pools the machine simply was not asked
> to search — `streamkey` alone is 420,229. The line now reports the two separately.

> **An earlier version called Black Ops 4 an animation goldmine, worthless for materials, citing
> xanim 259,051 and material 100.** The pool counts had been labelled with Cold War's enum, and
> the games number their types differently. The 259,051 was `xmodelmesh`. `snapshots/*.pools.txt`
> is now correct for both, and the table above is generated from the snapshots themselves.

### What is not reachable, and why the counts shrink

**`xmodelmesh`.** A mesh name is `<model>_s1_geo_rigid_bs_` plus twenty-six characters of base32
that are a hash of the mesh itself. No rule can produce it, and leaving these in *doubles* the ids
a candidate can hit by coincidence, so they are dropped as unreachable rather than counted as work
remaining.

**Everything the tables resolve.** By far the largest saving: 1,626,209 Cold War assets narrow to
136,467 actually hunted.

---

## "New" means new to the community, not new to your machine

Read this before quoting a number at anybody, including yourself.

A run reports what it was the first *on this clone* to reach. On a fresh clone that is everything
it finds, which makes a first pass look spectacular and means almost nothing: the 430 the general
search returns on a fresh clone are the same 430 that five contributors have already submitted,
and the honest figure for them is **zero**.

Measured here, 2026-08-19 — four Cold War runs on a clone that started with no findings at all:

| run | found | new to the community |
|---|---|---|
| general search, committed lists | 430 | **0** |
| per-prefix continuations | 496 | **5** |
| family gap filling | 1 | **1** |
| general search, widened sound corpus | 102 | **24** |
| **distinct across all four** | **1,029** | **30** |

`submit` gets this right on its own — it drops everything already merged or sitting in an open pull
request, so those four runs send 30 names rather than 1,029. The trap is in the *reporting*: a run
note saying `new: 496` means new to this machine, and quoting that as the method's yield overstates
it by two orders of magnitude. That is exactly how the entry for method 2 above came to be wrong
the first time it was written down.

And the same pass on Black Ops 4, where the gap is far starker:

| run | found | new to the community |
|---|---|---|
| general search, Black Ops 4, 51 minutes | 15,747 | **16** |

Fifty minutes of every core, and 15,731 of those names were already claimed — almost the whole of
GoastcraftHD's earlier 13,858-name submission, re-derived from scratch.

**Judge a method by what `submit` actually sent.** And note which way the surprise ran on Cold War:
the widened sound corpus looked like the weakest of the four by run-note figures and was in fact
the strongest by a factor of five.

### The searches now exclude claimed names too, which is why that pass could happen

That Black Ops 4 run was possible because `wanted` was built from the **published tables alone**.
The tables lag the community by days, so a name merged into `submissions/` here — or sitting in an
open pull request — was still "unnamed" as far as cod-name-db was concerned, and the search kept
hunting it.

`loader::wanted_for_search` now also drops everything in `state/claimed.txt`, which `start` writes.
Measured immediately afterwards:

| | ids hunted before | after |
|---|---|---|
| Black Ops 4 | 141,881 | **124,758** |
| Cold War | 136,467 | **135,416** |

Twelve percent off a Black Ops 4 pass, and the saving grows every time anybody submits. It buys
accuracy as well as time: fewer ids means proportionally fewer coincidental matches. It also makes
a run's own figures honest by construction rather than by the reader remembering to check them.

---

## Duplicates are now handled by the software

The long instruction that used to live here — check `submissions/`, remove what somebody else
already sent — was correct and did not work, because a contributor cannot see a pull request that
is still open. It is now enforced instead of requested:

- `start` reads every open pull request and every merged submission, and writes what is claimed.
- `submit` re-reads them at the moment of sending and drops anything already claimed.
- Every run carries a **fingerprint** of its inputs, and a search whose fingerprint has already
  been submitted refuses to start.

Independent rediscovery is still not a finding. You no longer have to remember that.

---

## How to read a method

- **Builds from** — what raw material it recombines. Never thin air.
- **Reaches** — the slice of unnamed ids only this gets at. The reason to run it.
- **Run it with** — the command.
- **Spent when** — the signal it has stopped paying.

---

## 1. The general search

**Builds from** every seed there is: the published tables for this game, every name already
confirmed, everybody's merged submissions, strings scraped from a build, names borrowed from the
other game.

**Reaches** anything expressible as *beginning + stem + ending*. The workhorse and the widest net.

**Run it with** `confirm_cw` for models, materials, images and anims, and `confirm_cw --sounds`
for sound files and aliases — two passes, not one. Add `--no-fold` to a Black Ops 4 sound pass.

They are separate because a sound ending tried against a model id can only ever be a coincidence,
never a match: the vocabularies cannot reach each other's targets. Sharing one run made both
halves worse, and sharing one capped list made them worse again — sound displaced endings covering
115,606 published names while contributing endings the general pass could never use. Apart, each
gets its own measured pair (`data/sound.*.txt`), its own full ceiling, and hunts only the ids it
can reach: 121,549 and 94,668 on Black Ops 4 rather than 216,217 mixed.

**Check the ceiling before blaming the method.** `python scripts/reach.py` reports what share of
*known* names each list pair could rebuild — if it cannot express a name we already have, it will
never find the unnamed ones beside it. That measurement found Black Ops 4's sound names 19.2%
reachable: deep paths were contributing one hyper-specific beginning each, `fly/footsteps/
stakeout_overrides/asphalt_walk/` heading 158 names, and never `fly/`, which heads thousands.
Counting every leading segment took it to 100%.

`confirm_cw seeds` uses only confirmed names, which is small enough
to run in minutes and worth repeating after a long pass to pick up siblings.

**Measured**, 2026-08-19, Cold War, committed lists (700 beginnings, 4,800 endings), fresh clone:

```
12,395,196 distinct pieces   41.72 T equivalent candidates   1058 s   430 names
```

**Spent — and this is the important part.** That 430 is the same 430 for everybody. Five
contributors have submitted it, **byte for byte identical in every file**, because the method is
deterministic and a fresh clone gives everyone identical inputs. Two more submitted the same 372
from method 3 the same way. The fingerprint now stops the sixth.

"Spent" here is temporary, and reopening it is one command: **`python scripts/derive_lists.py`**
folds every name confirmed since into the beginnings and endings. New lists are a new fingerprint
and a genuinely different search. That is the compounding loop — **run a pass, re-measure, run
again** — and it is why a single pass judged alone means nothing.

**The sound vocabulary was missing and is now not.** `COLD_WAR_TABLES` named only the legacy
`fnv1a_xsounds.csv` (57,593 names). The twelve per-language files Saluki actually loads hold
**825,316 distinct names**, with *zero* rows in common with the legacy file. Every general pass
before this had one fourteenth of the sound vocabulary. See `docs/HASHES.md`. **The first pass
after this fix is a different search with a much larger corpus; expect it to pay.**

The engine peels endings off the wanted ids rather than appending them to stems, because the hash
runs backwards. Read the comments in `src/search.rs` before touching any of it.

## 2. Per-prefix continuations

**Builds from** every prefix that occurs in a known name, and the tokens measured to follow *that
prefix* — not the tokens that are common overall.

**Reaches** the families the global lists structurally cannot express. The general search offers
`mc/` and `i_c_t8_mp_spe_` the same 700 beginnings and 4,800 endings, when what actually follows
them has almost nothing in common.

**Run it with**

```
python scripts/continuations.py --depth 2 --cap 24 \n    | confirm_list - --label "per-prefix continuations" --script scripts/continuations.py
```

**Measured**, first run, Cold War, 2026-08-19:

```
39,490,781 candidates   51 s   1,837 matched   496 new to this clone   5 new to the community
```

It reaches ground the general search's committed lists do not: 496 names in 51 seconds against 430
from an 18-minute exhaustive pass. **But only 5 of those 496 were new to the community.** The other
491 had already been found by other contributors, mostly through `images_from_materials` and
`confirm_variants`. So this reaches *differently*, not *further* — worth running because it gets at
families the global lists cannot express, not because it out-yields what already exists.

The generator was the bottleneck, not the search — `confirm_list` sustains 64.3 M candidates/s from
a file and saw 0.8 M/s through a Python pipe.

Directory prefixes are given the entire vocabulary rather than a capped list, because there are
only about fifty of them and they head a large share of what this recovers.

**Spent when** a round adds little *and* re-running after folding the finds back in adds little.
It is self-feeding like the general search: each new name is a new prefix and a new continuation.
Then raise `--depth` or `--cap`, which is a different search again.

## 3. Materials to images

**Builds from** confirmed and published material names.

**Reaches** `image`, through the strongest cross-type relationship there is. **Measured**:
material and image share **15,770 cores — 11.7% of material's, 12.8% of image's**, far above any
other pair. Strip `mtl_`, try `i_` plus every semantic suffix (`_c _n _g _o _m _s _r`, which are
image's seven commonest trailing tokens by a distance), and also try it with no prefix at all.

**Run it with** `images_from_materials`.

**Spent when** the confirmed material set has not grown. Purely derivative — it yields exactly
nothing on unchanged input, so run it *after* a general pass, never before.

Material names are paths, and there are **twelve** directories: `mc/ wc/ clt/ splm/ vd/ mcs/ ei/
cltp/ vdd/ el/ mcp/ ec/`. Verified against the tables — `mc/` heads 496,666 names and `ec/` heads
25. Popularity ranking keeps the first two and discards the naming of everything under the other
ten. Carry all twelve.

## 4. Numbers in place

**Builds from** confirmed names containing a number.

**Reaches** family members that beginning-stem-ending rules structurally cannot, because the number
usually sits in the *middle*. `p7_jun_brick_pillar_128` and `p7_jun_brick_pillar_32` differ where
no prefix or suffix rule can vary.

**Run it with** `confirm_variants`, or `confirm_variants swaps` to substitute whole tokens.

**This is the method that fits `xanim`.** Published xanim names run to ten and more segments, so
an ends-only rule under-reaches them badly — the middle of a ten-segment name only exists as a
stem if a nearly identical sibling was already cut. The tables hold 50,427 whole xanim names, and
walking their numbered fields in place is exactly what this does.

**Spent when** the ranges around known members have been walked past their natural end. Widen with
`swaps` before concluding it is finished.

## 5. Family gap filling

**Builds from** numbered families with two or more confirmed members, across *everybody's*
submissions rather than one run's.

**Reaches** the holes. A family with `_01`, `_02` and `_04` confirmed is evidence about `_03` that
no popularity-ranked ending list can match.

**Run it with** `python scripts/families.py --gaps | confirm_list - --label "family gap filling"`.

**Measured**: 22,594 candidates, under a second, **1 new name**. Thin, because method 4 already
walks numbered families thoroughly. Worth running anyway — it costs a second and it works across
contributors, which `confirm_variants` does not. Do not spend a night on it.

`python scripts/families.py` with no arguments is the more valuable half: it reports the shape of
what has been found, which is what suggests the next generator.

## 6. Cross-type spelling

**Builds from** the *cores* of one asset type's names — the name with its own type's decorations
stripped — spelled with another type's decorations.

**Reaches** assets whose sibling in another type is already named. **Measure the seam first**, with
`python scripts/cross_type.py --measure`. Measured shared cores, 2026-08-19:

| from → to | shared cores | share of source |
|---|---|---|
| material ↔ image | 15,770 | 11.7% / 12.8% |
| xmodel ↔ material | 3,318 | 3.5% / 2.5% |
| xanim → xmodel | 478 | 3.7% |
| xmodel → image | 195 | 0.2% |
| material ↔ xanim | 22 | 0.0% |
| image ↔ xanim | 13 | 0.0% |

**Two pairs are worth mining and the rest are not.** A model→image method or anything involving
`xanim` and a non-model type would be a night thrown away, and that is now a measurement rather
than an opinion.

**Run it with** `python scripts/cross_type.py --from xmodel --to material | confirm_list - --label
"model to material"`.

**Spent when** the source type stops gaining names.

## 7. Sound dotted tails

**Builds from** confirmed sound names and their tails, like `.rn75.pc.en.snd`.

**Reaches** sound names the general search structurally cannot, because it treats a dot as the end
of a name and can never put one back on. Everything past the first dot is invisible to every other
method.

**Run it with** `confirm_sounds`.

It searches four pools -- `sound_asset`, `sound`, `sound_bank`, `sound_duck` -- and that has been
read as scope drift. It is not. In Cold War `sound_asset` holds 97,217 ids against `sound_bank`'s
107 and `sound_duck`'s 191, so the other three widen the wanted set by **0.3%** and are peeled in
the same batch. Widening is cheap exactly when the added pools are small; widening into
`streamkey` would add 420,229 ids and quadruple the coincidence rate. `python
scripts/coverage.py` is how to tell those two cases apart, and it is what to run before widening
anything.

**Reopened.** The tail vocabulary was measured from a table holding 57,593 names when 825,316 were
available, and the two use *different* tail conventions — `.ln75.pc.all.snd` against
`.rn75.pc.<lang>.snd`. Cold War's `sound_asset` has 19,301 unnamed.

**Black Ops 4's sounds were invisible and now are not.** Its `sound` pool holds a hundred assets
because that pool is *banks* — the one entry of it that resolves is `mp_embassy.all` — while the
individual sounds live in SAB files the loader never opens. Confirmed against a live Cordycep
session with a full 1,023,902-asset load, matching the committed snapshot exactly.

Those SAB files have since been read and their ids injected as **`sound_asset`, index 170**:
**79,263 sound ids, 70,878 of them unnamed**, which makes it the largest single opportunity in
either game. Three things about them are not optional:

- **They are `sound_asset`, never `sound`.** Files and banks go to different tables upstream.
- **Their names keep their backslashes**, and the id is the hash of exactly that. Grind them with
  `--no-fold`. Measured: 8,385 of 8,385 known names reproduce unfolded, **0** folded. Without the
  flag the search matches nothing and looks completely healthy doing it.
- **The dotted-tail method still applies** — these names end `.ln100.pc.snd` and the like.

## 8. Reading the tables and extending them

**Builds from** what the tables already resolve — read for shape, then generate the neighbours that
are missing.

**Reaches** whatever the community half-finished. If a table holds `..._01` through `..._07` and
the game has more, this finds them. The most open-ended method here and the least automated: it is
somebody *looking* and noticing.

**Run it** by writing a generator that prints the neighbours and piping it into `confirm_list`.
That is now a script rather than a Rust binary, which is the whole reason this method is worth
listing.

**Spent when** — it does not, in the way the others do. It depends on noticing, and the tables grow.

**One trap, already paid for.** Feeding the tables in as candidate *input* is a closed loop: every
name in a table is resolved by definition, so it cannot be a find. It was 87% of `consolidate`'s
work for **zero** names. The tables are a source of *vocabulary* and an *exclusion list*, never a
candidate set.

## 9. Cross-game techset pairs, and the whole-tag sweep

**Builds from** a sibling game that ships the same thing unhashed. Black Ops III ships its
techsetdefs as plain files, and the newer games carry assets left over from it, so one material
exported from two games pairs a plain name with the newer game's hash. Three such pairs turn a
found transformation into a proof.

**Reaches** the techset pools, which nothing else touches. A techset name is `<base>#<8 hex>`, and
the tag is a 32-bit compile stamp that cannot be predicted — but 32 bits is small enough to
**sweep whole**: with per-digit hash-state reuse, all 4.29 billion tags for one base cost about two
seconds. A base is therefore *proved or conclusively ruled out*, never merely unswept.

**Run it with** `techset_probe` (a file of candidate bases) and `techset_pair` (known
`target_hash,plain_name` pairs).

Established 2026-08-18/19:

- **Black Ops 4** `technique_set` (3,597 ids, zero previously named): names are `<base>#<8hex>`
  with BO3's base vocabulary. Material-class sets carry `mc/` (`mc/lit_backlit#f4b74e85`);
  screen/2d/compute sets are bare (`zombie_blood#a60c435b`). Tags are per-permutation and
  `#a60c435b` is commonest. 1,322 names fell in the first 53-minute sweep.
- **BO4 simplified BO3's stems** — `lit_weapon` → `lit`, `lit_emissive_scroll` → `lit_emissive` —
  so trailing-qualifier truncation of known stems is a real seed transform.
- **Cold War** `techset` (7,096 unnamed): *not* reachable from BO3 stems under any 32-bit tag.
  Full sweeps of every stem × every tag came back empty, which is a conclusive no for that shape.

**Spent when** the base vocabulary stops growing. The tag side is never the problem.

> These names currently have **nowhere upstream to land** — cod-name-db has no techset table.
> Proposing one is worth more than another night of grinding. See `docs/HASHES.md`.

---

## 10. Sibling token substitution

**Contributed by GoastcraftHD**, 2026-08-19. This is the first method in this registry that an
assistant invented, wrote and submitted rather than one that shipped with the repository.

**Builds from** the corpus's own vote on what may stand in a given place. For every known name and
every token slot in it, the slot's *context* is the token before and the token after; every name
in the corpus votes on what has been seen in that context, and each word so measured is then
offered to every other name carrying the same two neighbours. Numbers fold to `#` when forming a
context, so `_01_` and `_07_` count as the same neighbour and a family shares one vocabulary
instead of splitting it per member.

**Reaches** the commonest kind of sibling in this game's naming, and the one the first three
methods structurally cannot produce: two names identical but for a single **non-numeric** word in
the middle. The general search recombines `beginning + stem + ending`, so it can replace a head or
a tail but never a middle with both sides intact. `confirm_variants` does change a middle token,
but only a numeric one -- `_01` becomes `_02`, `_wood` never becomes `_metal`. Continuations grow a
prefix rightwards, so a known tail cannot be preserved.

**Run it with**

```
python scripts/contributed/slotswap_20260819-225818.py | bin\windows\confirm_list.exe - ^
    --label "sibling token substitution" --script scripts/contributed/slotswap_20260819-225818.py
```

Measured, all Black Ops 4 unless stated:

| run | form | names |
|---|---|---|
| `20260819-215128` | slot alphabets, both neighbours | **1,081** |
| `20260819-215527` | same, Cold War | **76** |
| `20260819-222734` | widened: `--cap 40`, digits allowed | **972** |
| `20260819-225513` | `--context left` only | **660** |

**Spent by** its own success at one setting, and reopened by loosening the context. Keying a slot
on *both* neighbours is precise and cannot reach a name whose other neighbour is also unknown --
it requires the pair to have been seen together already. `--context left` or `--context right`
keys on one side, which is looser and less certain but reaches names the two-sided form cannot;
that change alone returned 660 more after the two-sided form had stopped paying.

---

## 11. Family column cross product

**Contributed by GoastcraftHD**, 2026-08-19.

**Builds from** a family treated as a table. Names are bucketed by their leading tokens and token
count so that members line up column for column, each column's alphabet is measured across the
bucket, and columns with a *small* measured alphabet are taken to be the family's axes. Every
member is then re-emitted with the full cross product of those alphabets.

**Reaches** names that differ from everything known in **two or more places at once** -- the slice
no other method here can produce, because every one of them moves a single degree of freedom:
the general search varies the stem, `confirm_variants` a number, method 10 one token, family gap
filling one numeric axis. One degree of freedom cannot reach two, however long it runs, and a grid
is mostly more than one step from any published corner of it.

**Run it with**

```
python scripts/contributed/templates_20260819-220821.py | bin\windows\confirm_list.exe - ^
    --label "family column cross product" --script scripts/contributed/templates_20260819-220821.py
```

Returned **115** on Black Ops 4 (`20260819-220550`) — immediately after method 10 had swept the
same corpus, so that number is what multi-axis reached *on top of* single-axis, which is the only
honest way to read it.

**The guard that makes it safe, and why it is not optional.** Columns with a *large* alphabet are
deliberately left alone: they identify the individual asset rather than offering a choice. Drop
that rule and the method walks straight into the largest trap in the repository. The image table's
highest-scoring grid is

```
volume0_state0_gi_xyz_texture_mip2_f788ac97_3        187,200 cells
```

where `f788ac97` is a **content hash**. Treated as an axis it has 32 attested values and looks
perfectly healthy, and the grid is densely populated, so a fill-ratio check passes it too. The
result would be 187,200 candidates spent guessing hash tails — unpredictable by construction. That
is `streamkey` in a new costume, and an upper bound on column alphabet is the only thing that
stops it.

**Spent by** the bucket key. `--key 3` fixes three leading tokens; families that share a shape but
not a prefix are never compared. Re-run with a different `--key` before calling it exhausted.

---

## 12. Sound language and encoding variants

**Builds from** the fact that every shipped language is a separate asset with its own id, and the
name differs by two characters. Measured across the twelve per-language tables: `en` 123,368,
`ru` 121,209, `es` 121,207, `fj` 121,155, `fr` 121,115, `ea` 121,097, `bp` 121,083, `ge` 121,082,
`ko` 121,032, `po` 121,011, `it` 120,930, `ms` 112,060. Those being so close is the argument — the
sets are near-parallel, so a name in one is evidence about eleven ids.

**Reaches** `sound_asset`, and it is the only method that gets there without rebuilding the whole
path from the lists.

**Run it with** `python scripts/sound_languages.py | confirm_list - --no-fold` (Black Ops 4).

Measured: **38 on Black Ops 4, 0 on Cold War.** The zero is the useful half — Cold War's twelve
language tables are already complete, so this is spent there and will stay spent. Black Ops 4's
SAB names have **no language segment at all** (`fly\emotes	eddybear_in.ln100.pc.snd` is stem,
encoding, platform), and a first version that required one silently skipped every Black Ops 4
name — that is, it skipped the entire pool it was written for while looking like it ran.

**Spent by** the language tables being complete. Re-run only after a pass that confirms new sound
files.

---

## 13. Image channel completion

**Builds from** a texture being authored once and exported as several maps. Measured on
`fnv1a_ximages`: **110,517 of 124,417 distinct cores (88.8%) already appear under more than one
channel**, so the odds a confirmed image is the only channel that exists are under one in eight.

**Reaches** `image`, from confirmed **images**. Method 3 (`images_from_materials`) reaches the same
pool from confirmed **materials**, so the two seed from disjoint material and feed each other: a
channel found here is a core for the next material pass and vice versa.

**Run it with** `python scripts/image_channels.py | confirm_list -`.

Measured: **456 on Black Ops 4, 59 on Cold War**, from 2.35 M candidates.

**Spent by** the channel list. Widen it from the table when new suffixes appear; it is measured,
not guessed.

---

## 14. Token insertion and deletion

**Builds from** the observation that every other method here *substitutes* and none changes a
name's length. The general search rebuilds `beginning + stem + ending`; `confirm_variants` swaps a
number; `slotswap` swaps one token; `templates` swaps several. All keep the token count the seed
had. So a name that is a known name **plus or minus one word** is unreachable by all of them,
however long they run:

```
p9_rus_apartment_tower_sign_01
p9_rus_apartment_stone_tower_sign_01      an insertion -- reachable by nothing else
```

That shape is common here because artists qualify a name as an asset set grows — a `wall` becomes
a `stone_wall` when a second material appears — and both spellings survive in the build.

**Reaches** all four of model, material, image and anim.

**Run it with** `python scripts/token_edits.py --type model | confirm_list -`.

Measured, one pass each: Black Ops 4 **model 139, material 423, image 72, anim 66**; Cold War
**model 21, material 179, image 112, anim 72**. 13.1 M candidates for models.

Deletions need no vocabulary and are the higher-precision half (`--no-insert`). Insertions are
seeded per position *and per leading token*, so a name beginning `p9_` is offered what follows
`p9_` elsewhere rather than the type's globally common words — a global vocabulary at every
position produces more candidates than the general search and reaches less.

**Spent by** `--cap` and the corpus. Deletions exhaust in one pass against a fixed corpus;
insertions reopen whenever either changes.

---

## 15. Affix sweep

**Contributed 2026-08-20.** The only method here that does not require a token to have been
measured before it can be offered.

**Builds from** nothing but the alphabet. For each stem it emits every combination of a short
leading and trailing token — `a_stem_a`, `a_stem_b`, … `aa_stem_a`, … `aba_stem_zz` — over the
36 characters real affixes actually use.

**Reaches** a permanent blind spot in every other method. Everything else recombines *measured*
vocabulary, and a frequency-ranked list of 4,800 endings structurally **cannot hold a token used
once**. Measured across the four general tables there are 341 distinct leading tokens of one to
three characters and 2,044 trailing ones; the common ones are carried by every list, and the long
tail — which is most of the distinct values — is carried by none.

Brute force is the *right* tool here, and only here, because the space is genuinely small: 36
characters over four positions is 1.7 million, a rounding error beside the 2^63 that makes word
composition hopeless. Point the same idea at whole words and it becomes the mistake `Order of
resort` warns about.

**Run it with**

```
python scripts/affix_sweep.py --type model --stems 200 | bin\windows\confirm_list.exe - ^
    --label "affix sweep" --script scripts/affix_sweep.py
```

### Targeted, not scheduled — and the measurement says so plainly

A blind run on Black Ops 4 models: **62 stems, 532,497,168 candidates, 1 name.**

| method, BO4 models | names per candidate |
|---|---|
| `token_edits` | 1 per 94,000 |
| **affix sweep, blind** | **1 per 532,000,000** |

That is roughly **5,600× less efficient per candidate**, and it is the whole argument. An hour buys
about 500 stems against a corpus of 250,000 — 0.2% coverage. As a rotation item it is poor value
next to almost anything else here.

**Its value is entirely in choosing the stems.** Use it when you have a reason to believe a
particular family holds more — a set a pass has just cracked open, a map whose assets are half
recovered — and sweep *those* stems exhaustively. It answers "is there more here?" completely,
which no other method can, rather than "what is there?" cheaply, which several do better.

The one it found blind shows the shape it reaches:
`c_t8_zmb_dlc3_mannequin_female_static_standpose_body_color_01` — a common `c_` prefix *and* a
common `_01` suffix, on the same stem, which needs both ends varying at once on a stem the general
search never cut as a piece.

**A negative result here is worth recording.** A targeted sweep is exhaustive over its stems, so if
a family you expected to be productive returns nothing, that is a strong measured statement about
that family rather than a shrug — and it is expensive to rediscover.

### Sized before it runs, and it refuses to exceed it

Candidates go as `stems x (L+1) x 36^L` for combined affix length `L`, so `L` is solved for rather
than chosen: 186,624 candidates per stem at L=3, 8.4 million at L=4. `--hours` sets the budget
(default 1) and the script prints the plan before emitting a line. There is no flag to force a
longer sweep, because one that takes a fortnight is not a method, it is a mistake nobody notices
for a fortnight.

**Do not reach for this when a pass returns little.** Low findings usually mean the *lists* need
re-measuring, not that brute force is needed — re-measuring took sound-file ending reach from 27.8%
to 96.7% in one command. Running a sweep when a starved list is the real problem burns an hour and
finds nothing.

**Separators are gated per type, and that is measured.** `/` appears 98,384 times in short material
affixes but always closing a directory code (`mc/`, `wc/`), never scattered through one — so it is
applied as a separator rather than swept as a character, which is both correct and 1.12x cheaper at
L=4. `.` is swept nowhere: sound dots live in long fixed tails the endings list already reaches.

**Spent by** its stems, never by the alphabet. Re-running over the same stems at the same length
returns exactly what it returned before; re-running over new ones is a new search.

---

## Adding a method

**This is the highest-value thing anybody does here**, and it no longer requires writing Rust.
`confirm_list` takes candidate names on standard input and does the careful half. A method is a
program that prints names.

A new method earns its place by answering the **reaches** question: what slice of the unnamed ids
does it get at that nothing above does? A method that covers ground the general search already
covers is not a new method, it is a slower one.

When you add one:

1. **Name the generator when you confirm:** `confirm_list - --label "..." --script <path>`. It is
   copied into the run and `submit` puts it in the pull request under `scripts/contributed/`.
   Anything in `contrib/`, and any new file in `scripts/`, is carried too. Give it the docstring
   `scripts/README.md` asks for.
2. **Read the library first.** `start` prints every script and what it is for, so that inventing
   something that already exists under another name takes a deliberate effort rather than an
   ordinary lapse of memory.
3. Add a section here in the same shape, with the numbers your run measured.
4. Say honestly what it is spent by.
5. **If it did not work, put it in the dead ends below.** A measured negative is worth as much as
   a find, and costs the next person nothing.

---

## Order of resort

Seeded methods first, always. That is where the yield is and they compound.

Exhaustive or random character combination is a legitimate **last** resort once seeded methods are
genuinely exhausted — never a starting point. The arithmetic says why: the median confirmed name
has seven or eight underscore-separated segments, and the space of sequences that long passes 2^63
long before the name does. Past four segments the hash stops being a filter and becomes a
checksum: there are more candidate strings than there are hashes, every one an equally valid
preimage, and no amount of speed changes that. Only a prior can. Fragment recombination *is* that
prior.

If you do get there, constrain it with what has been measured — known directories, known prefixes,
known segment shapes, known endings. This is also the only regime where collisions matter: a
41.7 T candidate pass expects 0.617 coincidental matches, and a seeded pass of forty million
expects 0.0000. Every binary prints the figure.

---

## Dead ends

Do not spend a night rediscovering these. Each cost real time.

| Tried | Outcome |
|---|---|
| Sound **alias** names as sound **file** stems | 706 of 101,673 distinct file stems are exactly an alias name — **0.7%**. The two vocabularies are unrelated: aliases are bare underscore names (`amb_computer_loop_1`), files are deep paths with encoding tails. Do not build a generator on this seam. |
| Model cores against anim cores | **Zero** shared, out of 154,525 model and 30,337 anim cores. Taking an anim's name minus its last token as a model name hits 16 of 30,337 (**0.1%**). There is no model/anim seam to exploit. |
| Model cores against material cores | 3,300 shared of 154,525 and 266,575 — about 2%, against the 15,770 that material and image share. Weak enough not to be worth a pass. |
| Scanning `xsub` files for names | They hold none. 85 GB of nothing. |
| A NUL-terminated-only string scanner over xpak/ff/fd | Misses roughly 800,000 names. |
| Salsa20 for the encrypted fast files | Wrong cipher. It is AES-256-CTR, little-endian counter. |
| Training a name classifier on the `_v2` tables | Those are MW2022/BO6 and teach the wrong conventions. |
| Stripping `_geo_rigid_bs_` as its own rule | Underscore truncation already covers it, and mesh names are unobtainable anyway. |
| Feeding the hash tables in as candidate input | A closed loop. 87% of `consolidate`'s work, zero names. |
| Hunting `localizeentry` | The entry holds a pointer to its own unhashed string — the plain text is already in the build. 8,667 confirmed in one pass, all worthless. `confirm_localize` now refuses to run. |
| Hunting `streamkey` | ~290,000 genuine, useless hashes, mostly sequential `d3dbsp` terrain. The largest pool in both games, so anything that "opens up every pool" lands here first. `submit` refuses to send them. |
| Widening `pools` to ~40 asset types by guesswork | One submission did. Nothing useful came of it, and the real findings were buried among the rest. |
| Searching four pools because they had "sound" in the name | `sound`, `sound_asset`, `sound_bank`, `sound_duck`. Only `sound_asset` is worth anything, and only in Cold War. |
| Cross-type generation involving `xanim` and a non-model type | Measured: 13 to 22 shared cores out of tens of thousands. There is no seam. |
| Reading candidates with `BufRead::lines()` | Not a search dead end but the same lesson: the `String` per candidate *was* the program, capping `confirm_list` at 5.2M/s against 64.3M/s for raw bytes. |

---

## A quirk worth knowing, and deliberately not fixed: ids in two of the five types

**This is not a correctness problem and it does not block anything.** It is written down so the
next person who notices the numbers does not spend an evening on it.

`loader::unnamed` maps each id to **one** pool, and the one it keeps is whichever has the lowest
index — `wanted.entry(id).or_insert(pool)`. Where an id sits in two of the five targeted types at
once, that choice is arbitrary rather than correct, and the name is written to the wrong file
locally.

Measured 2026-08-19: **141 such ids in Black Ops 4, 94 in Cold War.** Regenerate with

```
python scripts/coverage.py            # per-pool totals
```

and a short script over `snapshot.read(...).records` grouping pools by id.

**Almost all of it is `image` + `material`** — 139 of the 141 in Black Ops 4, 90 of the 94 in Cold
War. And an id in both pools means exactly what it says: the game holds an image *and* a material
under that one name, because the id is the hash of the name and both assets carry it. Filing it as
either is **true**. What happens is that it is not *also* listed under the other, so one CSV
upstream is short a row it could have had.

So this under-reports; it does not mis-report. `validate` passes it because the id genuinely is in
the pool it was filed under, and nothing wrong reaches the community tables. The remaining four
ids across both games are single instances of `xanim`+`xmodel`, `image`+`xmodel` and
`material`+`xmodel`.

**Fixing it means `wanted` becoming `id -> Vec<pool>` and every search emitting a row per pool** —
a signature change through six binaries, to gain a couple of hundred duplicate rows. Not worth it
now. If somebody does it, drive the choice from name shape the way `misfiled` does: three separate
bugs in this codebase have come from guessing an asset type against the wrong evidence, and every
one of them looked perfectly reasonable in the log.

---

## What is still not recorded

The fingerprint records that a *configuration* was swept. It does not record which *ranges* within
a method were swept — so `confirm_variants` walking `_01` to `_64` of one family and stopping is
still invisible to the next assistant.

That is the obvious next improvement to how this project remembers itself, and it is smaller than
it looks now that `RunNote` carries arbitrary measurements: a method that records the ranges it
covered into its run note would make this file far more useful than it currently is.
