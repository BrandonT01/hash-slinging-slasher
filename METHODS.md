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
| 1 | general search | anything as *beginning + stem + ending* | `confirm_cw` | **exhausted at the committed lists, and re-measuring them does not reopen it** — see below |
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
| 16 | final byte solved backwards | any name one **final character** from a known one, at any of 256 bytes | `scripts/final_byte.py` → `confirm_list` | **1 name per 18 candidates — the best measured here.** In `derive_closure`, so it re-runs free after any pass |
| 17 | tails of length k | any name that is a known one with its **last k characters** replaced | `scripts/tails.py` → `confirm_plan` | k=3: **1,151 in 21s a game.** Subsumes k=1 and 2; `--length 4` for more |
| 18 | heads of length k | any name that is a known one with its **first k characters** replaced | `scripts/tails.py --head` → `confirm_plan` | **692 on Cold War in one pass.** The mirror of 17, untried until 2026-08-22 |
| 19 | uncarried directories | material directories the twelve-directory list omits | `scripts/contributed/mcdp_cores_20260823-023310.py` -> `confirm_plan` | **2,846 on Cold War in one pass.** `mcdp/` is Cold War's second largest material directory and nothing here could emit it |
| 20 | black ops 3 sab sounds, black ops 4 spelling | Black Ops 4 `sound_asset`, the largest pool in either game | `scripts/contributed/bo3_sab_to_bo4_20260823-030223.py` -> `confirm_plan --no-fold` | Black Ops 3's SAB paths lower cased, language directory dropped, every Black Ops 4 tail put back on |
| 21 | recovering a pool's seed corpus | any pool whose ids were injected rather than loaded | `scripts/contributed/sound_takes_20260823-030223.py` | **not a search -- it is what every sound search should have been seeded from.** Cold War `sound_asset`: `all_names/` holds 148, the tables hold 39,199 |
| 22 | uncarried endings | any type, through the endings `data/suffixes.txt` structurally cannot express | `scripts/contributed/uncarried_endings_20260823-040620.py` -> `confirm_plan` | **6,674 names across both games on 2026-08-23, the largest method here.** Yield rises with the segment depth: 1 segment 1,191, 2 segments 2,065, 3 segments 1,800, 4 segments 1,054, 5 segments 564 |
| 23 | uncarried sound endings | `sound_alias` and `sound_asset`, the two largest pools | `scripts/contributed/uncarried_endings_20260823-040620.py --sound-pass` | **1,385 names.** 79% of published sound names end in something `data/sound.suffixes.txt` cannot express -- proportionally the larger of the two ending gaps |
| 24 | measured image channels | `image`, through the channels method 13's hand-written list omits | `scripts/contributed/image_channels_wide_20260823-043005.py` | 36 names, but it widens a derivation `derive_closure` re-runs every round: 231 of 250 real channels were uncarried, `_thermalmap` alone heads 16,000 |
| 25 | all-boundary cores | every method built as core x ending | `scripts/contributed/uncarried_endings_allboundary_20260823-134935.py` -> `confirm_plan` | **the most productive change measured on 2026-08-23.** Not a new method -- a fix to how every ending sweep builds its cores. Turned 2,065 names into 2,553 while using five times fewer endings, and 1,385 sound names into 1,746 in a single pass |
| 26 | MW19 middles, Cold War decorations | any type, through a **third title's** vocabulary | `scripts/contributed/mw19_middles_20260823-160437.py` -> `confirm_plan` | **256 on Cold War and 29 on Black Ops 4, 2026-08-23.** Modern Warfare 2019 does not hash its names, so all 1,167,131 are captured in plain text. Verbatim they are spent; their **middles**, re-decorated with the target game's own affixes, are not |
| 27 | packed-channel parts | `image`, from a title that packs textures into colour channels | `scripts/contributed/mw19_channel_parts_*.py` -> `confirm_list` | **63 names in one second, 1 per 6,559 candidates -- the most efficient method here.** MW19 names a packed image after *every* texture in it, joined by `&`. Splitting them yields 211,306 names that appear nowhere else in that corpus |
| 28 | channel-code swap | `image` and `material` | `scripts/contributed/mw19_channel_swap_*.py` -> `confirm_plan` | **52 names.** The last segment of a packed name is a channel code (`_c _g _n _s`); everything before it is the asset. Cut the code, put the *target* game's endings on -- including the 1,162 codes measured off Cold War's own names that `data/suffixes.txt` does not carry |
| — | localize unfolding | `localizeentry` | `confirm_localize` | **off, and refuses to run.** Worthless — see dead ends |

### Every method that has actually been run

The table above is hand-written, and it holds fifteen methods. **One hundred and four have been
run.** The gap is not neglect — it is that keeping a registry by hand means keeping it by hand,
and nobody did, so the ninety methods missing from it were invisible to everybody who arrived
afterwards and several were invented twice.

So the rest of the registry is computed from the run record and written in below. Regenerate it
after pulling:

```
python scripts/methods_report.py --registry --write
```

Read it **before inventing anything**. A method already here under a name you would not have
guessed is the thing you are about to build again — `ways` counts how many labels one method has
already been run under, and the largest are five and six.

The two halves answer different questions and neither replaces the other. Above: what a method
*reaches*, which is judgement. Below: what it *returned*, which is arithmetic.

<!-- BEGIN GENERATED REGISTRY -->
<!-- generated by scripts/methods_report.py --registry --write; do not edit by hand -->

Every method ever run here, computed from the run record in `submissions/`. Ranked by
candidates per name, best first. `ways` is how many distinct labels this one method has
been run under -- check it before inventing anything, because a method already in this
table under a name you would not have guessed is the thing you are about to rebuild.

| method | ways | runs | names | candidates | 1 name per | best | latest | first | last | state |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| final byte solved backwards | 1 | 15 | 732 | 141,742 | 193 | 18 | 77 | 2026-08-22 | 2026-08-23 | cooling |
| gaps | 2 | 4 | 374 | 246,361 | 658 | 190 | 6,554 | 2026-08-20 | 2026-08-20 | spent |
| black ops 1 build names, verbatim | 1 | 2 | 271 | 651,912 | 2,405 | 1,940 | 3,164 | 2026-08-22 | 2026-08-22 | live |
| black ops 3 build names, respelled, full harvest | 1 | 2 | 148 | 473,642 | 3,200 | 1,691 | 29,602 | 2026-08-22 | 2026-08-22 | spent |
| family gap filling | 1 | 8 | 144 | 610,443 | 4,239 | 654 | 7,805 | 2026-08-19 | 2026-08-23 | spent |
| image siblings of confirmed materials | 1 | 18 | 3,735 | 19,339,863 | 5,178 | 393 | 239,718 | 2026-08-19 | 2026-08-23 | spent |
| image siblings | 3 | 5 | 529 | 4,621,863 | 8,736 | 1,734 | 68,329 | 2026-08-20 | 2026-08-21 | spent |
| channels | 2 | 4 | 916 | 9,598,953 | 10,479 | 2,732 | 602,442 | 2026-08-20 | 2026-08-20 | spent |
| paired-token-blocks-anim | 1 | 1 | 33 | 410,321 | 12,433 | 12,433 | 12,433 | 2026-08-20 | 2026-08-20 | untried |
| black ops 3 build names, verbatim, full harvest | 1 | 2 | 177 | 2,462,622 | 13,913 | 8,858 | 32,402 | 2026-08-22 | 2026-08-22 | cooling |
| alias slot substitution | 4 | 9 | 1,354 | 21,780,323 | 16,085 | 6,535 | 2,047,927 | 2026-08-20 | 2026-08-21 | spent |
| rare-token-compound-splice-anim | 1 | 3 | 30 | 521,194 | 17,373 | 10,849 | 17,385 | 2026-08-20 | 2026-08-20 | live |
| black ops 3 build names, verbatim | 1 | 1 | 4 | 73,303 | 18,325 | 18,325 | 18,325 | 2026-08-22 | 2026-08-22 | untried |
| bo3 mod tools asset file list | 1 | 1 | 3 | 65,355 | 21,785 | 21,785 | 21,785 | 2026-08-22 | 2026-08-22 | untried |
| bo3 mod tools gdt asset names | 1 | 2 | 3 | 84,078 | 28,026 | 21,019 | 42,039 | 2026-08-22 | 2026-08-22 | live |
| paired-token-blocks-alias-deterministic | 1 | 2 | 14 | 481,544 | 34,396 | 24,067 | 60,216 | 2026-08-20 | 2026-08-20 | live |
| paired-token-blocks-anim-deterministic | 1 | 9 | 104 | 3,708,652 | 35,660 | 15,884 | 206,784 | 2026-08-20 | 2026-08-20 | spent |
| image channel completion | 1 | 13 | 729 | 31,429,223 | 43,112 | 5,159 | 47,999 | 2026-08-20 | 2026-08-23 | cooling |
| continuations | 1 | 1 | 776 | 39,892,300 | 51,407 | 51,407 | 51,407 | 2026-08-20 | 2026-08-20 | untried |
| older-title vocabulary | 1 | 2 | 59 | 3,144,542 | 53,297 | 34,939 | 112,305 | 2026-08-21 | 2026-08-21 | cooling |
| black ops 3 build names, respelled | 1 | 1 | 1 | 54,358 | 54,358 | 54,358 | 54,358 | 2026-08-22 | 2026-08-22 | untried |
| alias slot substitution, left context only | 3 | 6 | 1,934 | 109,332,515 | 56,531 | 8,885 | 2,932,361 | 2026-08-20 | 2026-08-20 | spent |
| edits anim | 2 | 5 | 208 | 12,868,629 | 61,868 | 15,318 | 15,318 | 2026-08-20 | 2026-08-20 | live |
| adjacent-token-order-anim | 1 | 1 | 2 | 136,243 | 68,121 | 68,121 | 68,121 | 2026-08-20 | 2026-08-20 | untried |
| paired-token-blocks-anim-lengths2-5-rare | 1 | 5 | 72 | 5,466,329 | 75,921 | 34,115 | 547,307 | 2026-08-20 | 2026-08-20 | spent |
| rare-token-compound-splice-model | 1 | 2 | 60 | 5,611,060 | 93,517 | 80,164 | 80,164 | 2026-08-20 | 2026-08-20 | live |
| rare-token-compound-splice-batch | 1 | 4 | 236 | 26,219,346 | 111,098 | 48,548 | 3,278,056 | 2026-08-20 | 2026-08-20 | spent |
| sound language and encoding variants | 1 | 1 | 38 | 4,296,303 | 113,060 | 113,060 | 113,060 | 2026-08-20 | 2026-08-20 | untried |
| alias slot substitution, right context only | 1 | 2 | 146 | 22,349,656 | 153,079 | 121,544 | 121,544 | 2026-08-20 | 2026-08-20 | live |
| correlated-token-blocks-alias-wide | 1 | 2 | 7 | 1,175,308 | 167,901 | 146,934 | 146,934 | 2026-08-20 | 2026-08-20 | live |
| adjacent-token-order-model | 1 | 2 | 10 | 1,765,338 | 176,533 | 110,332 | 441,340 | 2026-08-20 | 2026-08-20 | cooling |
| modern warfare 2 build names, verbatim | 1 | 1 | 1 | 209,784 | 209,784 | 209,784 | 209,784 | 2026-08-22 | 2026-08-22 | untried |
| paired-token-blocks-model-deterministic | 1 | 6 | 148 | 39,959,454 | 269,996 | 96,527 | 475,923 | 2026-08-20 | 2026-08-20 | cooling |
| token insertion and deletion | 4 | 18 | 1,147 | 319,209,610 | 278,299 | 34,598 | 207,069 | 2026-08-20 | 2026-08-21 | cooling |
| token-insertion-deletion-alias | 1 | 2 | 28 | 7,924,449 | 283,016 | 233,070 | 233,070 | 2026-08-20 | 2026-08-20 | live |
| adjacent-token-order-batch | 1 | 2 | 26 | 7,517,953 | 289,152 | 250,599 | 250,599 | 2026-08-20 | 2026-08-20 | live |
| materials from image cores | 1 | 7 | 110 | 32,142,264 | 292,202 | 68,987 | 68,987 | 2026-08-20 | 2026-08-23 | live |
| per-prefix continuations | 3 | 4 | 538 | 159,447,283 | 296,370 | 79,618 | 1,430,530 | 2026-08-19 | 2026-08-21 | spent |
| slotswap | 2 | 4 | 1,863 | 608,798,751 | 326,784 | 183,556 | 1,578,176 | 2026-08-20 | 2026-08-20 | cooling |
| cross-game sound stem transfer | 1 | 1 | 27 | 11,737,632 | 434,727 | 434,727 | 434,727 | 2026-08-20 | 2026-08-20 | untried |
| templates | 2 | 4 | 379 | 211,107,756 | 557,012 | 286,113 | 2,523,120 | 2026-08-20 | 2026-08-20 | cooling |
| final byte substitution | 1 | 2 | 121 | 70,135,764 | 579,634 | 467,581 | 467,581 | 2026-08-22 | 2026-08-22 | live |
| correlated-token-blocks-material-image-wide | 1 | 6 | 563 | 425,162,272 | 755,172 | 270,359 | 5,907,185 | 2026-08-20 | 2026-08-20 | spent |
| paired-token-blocks-model-lengths2-4 | 1 | 2 | 21 | 18,272,811 | 870,133 | 702,844 | 702,844 | 2026-08-20 | 2026-08-20 | live |
| sibling token substitution | 4 | 7 | 2,477 | 2,261,286,760 | 912,913 | 206,904 | 1,381,969 | 2026-08-19 | 2026-08-21 | cooling |
| edits material | 2 | 5 | 139 | 150,302,473 | 1,081,312 | 439,383 | 1,589,712 | 2026-08-20 | 2026-08-20 | cooling |
| sibling token substitution, right context only | 1 | 1 | 369 | 461,529,482 | 1,250,757 | 1,250,757 | 1,250,757 | 2026-08-19 | 2026-08-19 | untried |
| sound alias slot substitution | 1 | 2 | 3 | 4,119,600 | 1,373,200 | 1,028,660 | 2,062,280 | 2026-08-21 | 2026-08-22 | live |
| family column cross product | 3 | 8 | 348 | 657,442,807 | 1,889,203 | 456,163 | 7,478,471 | 2026-08-19 | 2026-08-22 | spent |
| mcdp | 1 | 1 | 2,846 | 5,545,804,740 | 1,948,631 | 1,948,631 | 1,948,631 | 2026-08-23 | 2026-08-23 | untried |
| sibling token substitution, left context only | 2 | 3 | 1,401 | 3,216,420,428 | 2,295,803 | 769,926 | 3,368,815 | 2026-08-19 | 2026-08-20 | cooling |
| image channel completion, measured channel list | 1 | 2 | 36 | 88,257,624 | 2,451,600 | 2,451,600 | 2,451,600 | 2026-08-23 | 2026-08-23 | live |
| cold war sound stems, black ops 4 spelling | 1 | 1 | 3 | 12,257,370 | 4,085,790 | 4,085,790 | 4,085,790 | 2026-08-21 | 2026-08-21 | untried |
| edits model | 2 | 4 | 12 | 52,757,566 | 4,396,463 | 1,876,636 | 6,607,769 | 2026-08-20 | 2026-08-20 | cooling |
| sab directory and basename recombination | 1 | 1 | 5 | 36,351,762 | 7,270,352 | 7,270,352 | 7,270,352 | 2026-08-21 | 2026-08-21 | untried |
| edits image | 2 | 3 | 12 | 91,292,882 | 7,607,740 | 5,048,388 | 30,538,103 | 2026-08-20 | 2026-08-20 | cooling |
| black ops 4, uncarried two-segment endings | 1 | 1 | 1,468 | 12,179,260,896 | 8,296,499 | 8,296,499 | 8,296,499 | 2026-08-23 | 2026-08-23 | untried |
| per-prefix-continuations-depth2-cap24 | 1 | 1 | 4 | 39,983,007 | 9,995,751 | 9,995,751 | 9,995,751 | 2026-08-20 | 2026-08-20 | untried |
| cold war, uncarried two-segment endings | 1 | 1 | 597 | 12,179,260,896 | 20,400,772 | 20,400,772 | 20,400,772 | 2026-08-23 | 2026-08-23 | untried |
| black ops 4 sound, uncarried two-segment endings | 1 | 1 | 509 | 11,274,140,892 | 22,149,589 | 22,149,589 | 22,149,589 | 2026-08-23 | 2026-08-23 | untried |
| keyword sweep: zombie models | 1 | 1 | 4 | 100,074,665 | 25,018,666 | 25,018,666 | 25,018,666 | 2026-08-21 | 2026-08-21 | untried |
| cold war, uncarried five-segment endings | 1 | 1 | 382 | 9,963,115,100 | 26,081,453 | 26,081,453 | 26,081,453 | 2026-08-23 | 2026-08-23 | untried |
| cold war, uncarried four-segment endings | 1 | 1 | 645 | 18,715,524,480 | 29,016,317 | 29,016,317 | 29,016,317 | 2026-08-23 | 2026-08-23 | untried |
| per-prefix-continuations-depth2-cap48 | 1 | 1 | 2 | 72,302,925 | 36,151,462 | 36,151,462 | 36,151,462 | 2026-08-20 | 2026-08-20 | untried |
| cold war sound, uncarried 1-segment endings | 1 | 2 | 560 | 20,953,836,251 | 37,417,564 | 29,431,729 | 29,431,729 | 2026-08-23 | 2026-08-23 | live |
| black ops 4, uncarried three-segment endings | 1 | 2 | 1,058 | 42,578,054,890 | 40,243,908 | 16,329,961 | 157,676,083 | 2026-08-23 | 2026-08-23 | cooling |
| black ops 4, uncarried four-segment endings | 1 | 1 | 409 | 18,715,524,480 | 45,759,228 | 45,759,228 | 45,759,228 | 2026-08-23 | 2026-08-23 | untried |
| per-prefix-continuations-depth3-cap24 | 1 | 2 | 10 | 472,580,559 | 47,258,055 | 26,254,247 | 236,292,329 | 2026-08-20 | 2026-08-20 | cooling |
| black ops 4, uncarried five-segment endings | 1 | 1 | 182 | 9,963,115,100 | 54,742,390 | 54,742,390 | 54,742,390 | 2026-08-23 | 2026-08-23 | untried |
| cold war, uncarried three-segment endings | 1 | 2 | 742 | 42,578,054,890 | 57,382,823 | 23,804,371 | 203,050,496 | 2026-08-23 | 2026-08-23 | cooling |
| cold war sound, uncarried two-segment endings | 1 | 1 | 195 | 11,273,898,861 | 57,814,865 | 57,814,865 | 57,814,865 | 2026-08-23 | 2026-08-23 | untried |
| heads of length 3 | 1 | 1 | 692 | 46,352,610,953 | 66,983,541 | 66,983,541 | 66,983,541 | 2026-08-22 | 2026-08-22 | untried |
| uncarried two-segment endings over the full published core list | 1 | 2 | 264 | 20,951,727,534 | 79,362,604 | 72,749,053 | 87,298,864 | 2026-08-23 | 2026-08-23 | live |
| uncarried endings over all-boundary truncation cores | 1 | 4 | 3,155 | 320,013,413,468 | 101,430,558 | 76,634,118 | 103,122,995 | 2026-08-23 | 2026-08-23 | live |
| uncarried beginnings over the held vocabulary | 1 | 1 | 7 | 945,274,375 | 135,039,196 | 135,039,196 | 135,039,196 | 2026-08-23 | 2026-08-23 | untried |
| cold war sound, uncarried 3-segment endings | 1 | 2 | 121 | 22,865,684,520 | 188,972,599 | 181,473,686 | 181,473,686 | 2026-08-23 | 2026-08-23 | live |
| uncarried three-segment endings over the full published core list | 1 | 2 | 56 | 13,564,678,200 | 242,226,396 | 165,422,904 | 165,422,904 | 2026-08-23 | 2026-08-23 | live |
| tails of length 3 | 1 | 13 | 1,476 | 430,274,936,998 | 291,514,184 | 35,873,048 | 519,127,602 | 2026-08-22 | 2026-08-23 | spent |
| uncarried endings over published cores | 1 | 6 | 1,191 | 385,019,657,854 | 323,274,271 | 17,624,983 | 4,062,515,784 | 2026-08-23 | 2026-08-23 | spent |
| sound dotted tails | 1 | 2 | 85 | 14,769,804,322 | 343,483,821 | 343,483,821 | 343,483,821 | 2026-08-19 | 2026-08-23 | untried |
| composed numeric endings | 1 | 2 | 14 | 6,497,838,750 | 464,131,339 | 406,114,921 | 406,114,921 | 2026-08-23 | 2026-08-23 | live |
| affix sweep | 1 | 1 | 1 | 532,497,168 | 532,497,168 | 532,497,168 | 532,497,168 | 2026-08-20 | 2026-08-20 | untried |
| animation transition grid | 1 | 2 | 2 | 1,295,625,020 | 647,812,510 | 647,812,510 | 647,812,510 | 2026-08-23 | 2026-08-23 | live |
| cold war sound files, core tails of length 1 and 2 | 1 | 1 | 1 | 881,657,430 | 881,657,430 | 881,657,430 | 881,657,430 | 2026-08-23 | 2026-08-23 | untried |
| all-boundary cores x uncarried endings, 2 segments | 1 | 1 | 163 | 177,157,271,555 | 1,086,854,426 | 1,086,854,426 | 1,086,854,426 | 2026-08-23 | 2026-08-23 | untried |
| family walking, numbers in place | 1 | 15 | 1,169 | 41,462,436,100 | 1,256,437,457 | 384,946,324 | 384,946,324 | 2026-08-19 | 2026-08-23 | live |
| uncarried endings ranks 60001-120000 over published cores | 1 | 2 | 21 | 95,849,557,466 | 4,564,264,641 | 2,995,298,670 | 9,584,955,746 | 2026-08-23 | 2026-08-23 | cooling |
| all-boundary sound cores x uncarried sound endings, 2 segments | 1 | 1 | 37 | 198,601,685,997 | 5,367,613,135 | 5,367,613,135 | 5,367,613,135 | 2026-08-23 | 2026-08-23 | untried |
| black ops 1 build vocabulary | 1 | 2 | 204 | 2,038,307,570,080 | 9,991,703,774 | 6,575,185,709 | 20,799,056,837 | 2026-08-22 | 2026-08-22 | cooling |
| tails of length 4 | 1 | 3 | 292 | 3,436,624,621,132 | 11,769,262,401 | 5,032,108,457 | 384,015,793,800 | 2026-08-22 | 2026-08-23 | spent |
| head of one name, tail of another | 1 | 2 | 7 | 96,000,800,000 | 13,714,400,000 | 8,000,066,666 | 8,000,066,666 | 2026-08-22 | 2026-08-22 | live |
| black ops 3 build vocabulary | 1 | 2 | 293 | 7,358,148,299,220 | 25,113,134,127 | 15,655,634,679 | 63,432,312,924 | 2026-08-22 | 2026-08-22 | cooling |
| tails of length 5 | 1 | 4 | 670 | 19,811,769,907,699 | 29,569,805,832 | 10,653,467,440 | 319,932,215,920 | 2026-08-22 | 2026-08-22 | spent |
| uncarried beginnings, optics and prefixed families | 1 | 2 | 7 | 271,475,197,760 | 38,782,171,108 | 27,147,519,776 | 67,868,799,440 | 2026-08-22 | 2026-08-22 | live |
| images derived from materials | 1 | 12 | 5,363 | 6,891,212,945,064 | 62,082,999,505 | 39,600,932,504 | 47,855,724,037 | 2026-08-19 | 2026-08-22 | live |
| uncarried beginnings | 1 | 2 | 4 | 364,450,467,250 | 91,112,616,812 | 73,924,584,790 | 73,924,584,790 | 2026-08-23 | 2026-08-23 | live |
| mw19 middles under cold war's own decorations | 1 | 1 | 256 | 25,025,670,291,620 | 97,756,524,576 | 97,756,524,576 | 97,756,524,576 | 2026-08-23 | 2026-08-23 | untried |
| general search | 2 | 63 | 105,570 | 1,020,326,453,766,951 | 239,064,305,006 | 35,073,084,706 | 35,073,084,706 | 2026-08-19 | 2026-08-23 | live |
| newer-title cores respelled | 1 | 2 | 61 | 34,510,658,565,958 | 565,748,501,081 | 367,134,665,595 | 1,232,523,520,212 | 2026-08-22 | 2026-08-22 | cooling |
| sound files and aliases | 1 | 42 | 29,703 | 445,924,607,420,656 | 634,316,653,514 | 305,380,319,690 | 2,897,689,870,441 | 2026-08-19 | 2026-08-23 | cooling |
| family walking, whole words | 1 | 14 | 4,175 | - | - | - | - | 2026-08-19 | 2026-08-21 | unmeasured |
| not recorded | 1 | 48 | 2,204 | - | - | - | - | 2026-08-19 | 2026-08-23 | unmeasured |
| bo3 techset tag sweep | 1 | 2 | 1,673 | - | - | - | - | 2026-08-18 | 2026-08-19 | unmeasured |
| cutting at underscores and recombining | 1 | 1 | 435 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| general search, confirmed seeds only | 1 | 3 | 75 | - | - | - | - | 2026-08-20 | 2026-08-20 | unmeasured |
| sound token swaps | 1 | 1 | 6 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| stream-key grammar sweep | 1 | 7 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| stream-tree zone peel | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| map name reconstruction and stream key templating, transferred from cold war | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| materials to images | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| attachment and weapon unfolding | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| path-shaped pools | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| model-derived pools | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| cross-pool decorations | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| numbers in place | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| cross-pool decorations over the whole vocabulary | 1 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| streamkey templating | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| map name reconstruction (map-prefixed tokens harvested from the tables, left-anchored | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| parameterised stream keys | 2 | 2 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| map name reconstruction + stream key templating | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| sound dotted tails as a cross product | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| weapon vocabulary growth, then attachment unfolding | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |
| names already found and verified, but never sent | 1 | 1 | 0 | - | - | - | - | 2026-08-19 | 2026-08-19 | unmeasured |

123 distinct methods, run 151 ways between them, across 545 runs. `names` is what each run
found new to the machine that ran it. A blank candidate count means no run of that method
recorded one, so it cannot be ranked -- see `--unattributed`.
<!-- END GENERATED REGISTRY -->

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

**"Spent" here is not temporary, and re-measuring the lists does not undo it.** This paragraph
used to say the opposite — one command, new lists, new fingerprint, a genuinely different search —
and it was measured false: three consecutive folds returned 55 names, then 294, then 51, the last
on a corpus two and a half times larger. A new fingerprint is a new *name* for the search, not new
ground for it, and the guard that reads the fingerprint cannot tell the difference. Between them,
that advice and a fingerprint nobody could collide with (it mixed in machine-local counts, so one
method grew 48 of them) took this project from 165 names a pass to 2 in an evening.

Re-measure when the lists have lost vocabulary and `derive_lists.py` says so. To find names, take
a method that reaches somewhere the general search cannot.

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

> **RUN TO COMPLETION, 2026-08-21. The measurement the note below asked for now exists.**
> The whole 4.35 trillion candidates, 8,096 seconds on an idle machine against Cold War:
> **43 names** -- 37 material, 5 image, 1 xmodel, 260 raw matches. That is **1 name per 101
> billion candidates**, and it is the most expensive slot in the rotation by a wide margin.
>
> For scale, the general search on the same machine the same night returned 56 names in 2,306
> seconds. Per hour of machine, `images_from_materials` is roughly a fortieth as productive.
>
> **So it earns its place only when nothing better is idle.** It is genuinely not exhausted --
> it is derivative, so every general pass that adds materials reopens it -- but it should run
> last, after the list re-measure, and never in front of a general pass or `swaps`.
>
> Still true and still worth fixing: it is the one confirming binary with **no checkpointed run
> folder**, so a pass killed part way through leaves nothing submittable. Over two and a quarter
> hours that is a real exposure. `confirm_cw` and `confirm_list` write theirs every sixty seconds
> and now mark them `.incomplete` until the run ends; this does neither.

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

## Candidates worth building, with the measurement that decides each

**Read this before inventing a method from scratch.** These are ideas that have been thought
through but not built, each with the cheap check that says whether it is worth the effort. Measuring
first killed three plausible-sounding ideas in an hour on 2026-08-20 — the seams below marked as
dead are *measured* dead, not guessed.

### The ranking metric

A method's worth is what it returns **per candidate**, not what it returns in a pass. Measured on
Black Ops 4 models:

| method | names per candidate |
|---|---|
| `token_edits` | 1 per 94,000 |
| `affix_sweep`, run blind | 1 per 532,000,000 |

**5,600× apart.** Estimate this before committing CPU, not after.

And note that **pool size does not predict yield**: Black Ops 4 `sound_asset` has 70,878 unnamed ids
— more than anything else — and a dedicated pass returned 169, while the general search returned
5,869 the same day. Unnamed-id count tells you what is *left*, not what is *reachable*.

### Measured seams

| seam | measured | verdict |
|---|---|---|
| material ↔ image cores | **15,770 shared** — 11.7% of material's, 12.8% of image's | **strong**, ~60× the model/image pair |
| sound alias names as sound file stems | 706 of 101,673 (0.7%) | dead |
| model cores vs anim cores | **0** shared of 154,525 / 30,337 | dead |
| anim minus last token → model core | 16 of 30,337 (0.1%) | dead |
| model cores vs material cores | 3,300 of 154,525 / 266,575 (~2%) | too weak to pass |
| loader string pool as candidates | **0** of the 159,170 ids a Cold War pass hunts | dead |
| Black Ops 4 SAB paths, recombined from Black Ops 4 names only | **2 new** of 240,000; tail swap **0 new** of 63,165 | dead |
| Cold War sound paths, recombined -- with a corpus **8x denser** | **0 new** of 400,000; tail swap **0 new** of 36,679 | dead |
| Black Ops 4 SAB paths, seeded with **BO2/BO3 SAB directories** | BO3 shares **9.18%** of stems, BO2 1.35% | ~~live~~ **dead** -- the overlap is real and the yield is not; see below |
| Names published for the **newer titles** (`_v2` tables) hashed against our games | **0** of 1,175,524 names, against 336,505 unnamed ids in the two games | dead |
| loader string pool, all pools | 23,301 of 1,480,510 ids (1.6%), 18,691 unnamed — but `scriptbundle` is 17,304 of them | free names, wrong pools |
| material→image with a **different reduction each side** (`no head` / `no ends`) | **75,964 shared — 59.98% of image**, 5× the row above; 181,466 cores only in material | **relation real, ground dead** — see below |
| material→xmodel, same treatment (`no ends` / `no tail`) | **15,270 shared — 15.57% of xmodel**, 5× the "too weak to pass" row above | **relation real, ground dead** — see below |

### Timings measured on 2026-08-22 between 11:19 and 18:55 are not trustworthy — 2026-08-22

A background loop was left running for seven and a half hours without anybody realising, competing
for all sixteen cores with every pass launched in that window. It was believed killed at 11:20:
the `confirm_plan` **child** was killed and the shell was not, so the loop simply started its next
stage. `pkill -f` had matched nothing under Git Bash on Windows and exited quietly, and the absence
of an error was read as success.

**Name counts from that window are unaffected** -- each run writes its own folder and its own
`new` count, and nothing about a hash depends on how busy the machine was. So `692` for heads k=3,
`61` for `cross_era` and the rest all stand.

**Wall-clock figures from that window do not.** Anything quoting how long a pass took, and every
`names/hr` the report derives from `ran for` for a run stamped in it, was measured on a machine
sharing itself with a hidden loop. Do not compare them against a figure measured on an idle one,
and re-measure before quoting any of them as a method's cost.

Figures from **before 11:19 are clean** -- the k=1 to k=5 tails sizings, the overnight run, and the
1-per-18 for `final_byte` were all taken on an idle machine.

Two habits worth keeping:

- **Kill the parent, then check the parent is gone.** Verifying that the current pass died says
  nothing about the loop that will start the next one.
- **`python scripts/running.py`** answers "is anything grinding right now?" -- worth running before
  timing anything, and before assuming the machine is idle.

### A long unattended runner gets silently blocked at twelve hours — 2026-08-22

Worth knowing before writing one. `readiness::require` refuses to search if `start` last passed
more than twelve hours ago, which is right: the tables move and other people submit.

Inside a multi-stage script it does not read as a refusal. A long stage ran, the next stage
was blocked, printed its message into its own log, exited, and **the runner carried on to the
following stage as though it had searched.** The blocked pass reported nothing, found nothing, and
looked exactly like an exhausted method. It was noticed only by reading the log by hand.

If you write a runner that will outlive twelve hours, **re-run `start` between stages**, and check
that each stage actually reported a result rather than assuming it did.

### Nobody had ever replaced the *front* of a name — 2026-08-22

`tails.py` replaces a known name's last *k* characters and works. It exists in that direction for
a historical reason and not a principled one: the end is where the hash keeps a resemblance, which
is what let `final_byte` solve one character, so attention went there and stayed.

The front had never been tried. It is the same cross product with the lists swapped -- stems are
known names with their heads cut off, the k-character strings become the *beginnings* -- and it
costs the same 46 billion candidates.

**692 new names on Cold War in a single pass, none dropped as already claimed.** The best single
pass of the day, from ground nothing had ever asked about.

Two things worth taking from it beyond the names:

- **Check the mirror of anything that works.** The asymmetry here was an accident of how the
  hash's invertibility drew attention, and it left half the space unexamined for the life of the
  project. `--head` is nine lines.
- **`bare` flips meaning between the two.** Replacing tails there is no `begin:` line, so
  `bare: yes` supplies the only opening column and the pass tests nothing without it. Replacing
  heads the k-character strings *are* the beginnings, so `bare` would instead add the headless
  stem alone -- a truncation, which is a different method. Getting this wrong does not fail; it
  reports billions of candidates and scans none.

### Structural overlap has now failed to predict yield three times — 2026-08-22

Every time this project has measured that two name sets *share structure* and concluded a method
was worth building, the method has returned approximately nothing. Three for three:

| what was measured | what it predicted | what it returned |
|---|---|---|
| material↔image cores, 75,964 shared, 59.98% of image | a strong seam | **0 matched** in 190 M candidates |
| BO3 shares 9.18% of Black Ops 4's SAB stems | `sabpaths` rated **live** | **0** in 187 B candidates |
| 2,394,179 newer-title cores absent from our corpus | fresh vocabulary | 61 in 34.5 T -- 1 per 565 billion |

**Overlap says two things are made of similar pieces. It says nothing about whether the pieces
recombine into names that exist.** Treat any "N% shared" figure as a reason to *test*, never as a
result, and put the test result in this file rather than the overlap.

The SAB one is worth spelling out because it was carefully controlled. `scripts/sab_plan.py` asks
`sabpaths`' whole vocabulary product -- 13,311 directories x 93,092 basenames x 150 tails,
187,111,289,412 candidates, unfolded -- against a pool with **70,878 unnamed of 79,263**, the
largest unnamed ground in either game. It returned 0. And the positive control passed: **387 of
391** known Black Ops 4 SAB names *are* reproducible from those three lists, so the plan covered
the right space and the space is empty. The vocabulary of Black Ops 2 and 3 does not carry into
Black Ops 4's sound tree, whatever the stem overlap says.

Older-title corpora hashed **verbatim** were tested at the same time -- `bo2_sab`, `bo3_sab`,
`bo2_ipak`, `cod_constants`, `cod_semantics`, `cod_techsets`, `fnv1a_strings`, 944,345 names: **0
matched folded on either game, 2 matched unfolded on Black Ops 4.**

### The closure multiplies a method's yield, and nothing measures that — 2026-08-22

`cross_era` returned **61** names for 34.5 trillion candidates, which by every column in
`methods_report.py` is among the worst methods ever run here.

Then `derive_closure` ran over what it had confirmed and found **416 more** -- `final_byte` +235,
`tails` +96, image siblings +75, channels +10 -- and round 2 correctly returned 0. Those 61 seeds
became 477 names.

**A method's worth is its own yield plus whatever the closure extracts from its seeds, and the
report can only see the first.** The closure's names are credited to the derivations, which is
correct provenance and misleading economics: it makes seeding methods look worthless and
derivations look better than they are.

Two consequences worth acting on:

- **Run the closure after everything**, including after a method you are about to write off. It is
  free and it has now multiplied one pass by 6.8x.
- **Do not retire a method on its direct yield alone** if it adds names in families nothing else
  reaches. `cross_era` is not worth its machine time twice, but its 61 names were not the point.

### Recombining *across* names is dead; varying *within* one is not — 2026-08-22

Three independent measurements now say the same thing, and together they are the most useful
generalisation this file has.

**Dead — pieces taken from different names and recombined:**

| what | measured |
|---|---|
| cross-type core seams (material→image, material→xmodel), the two strongest ever found here | **0 matched ids** in 190 M candidates, both games |
| head of one name + tail of another, cut at underscores (`scripts/splice.py`) | **7 names in 96 B candidates** — 1 per 13.7 billion |

**Live — one name varied in place:**

| what | measured |
|---|---|
| `final_byte` — last character solved | **1 per 18** |
| `image siblings` / `image channels` — a name respelled for its sibling asset | 1 per 394 / 1 per 5,160 |
| `tails` — last three characters replaced | 1,151 names, **free** (21 s) |
| `gaps`, `variants` — a number moved in place | 1 per 377 |

The reading is that asset names are **not freely recombinable**. A head constrains its tail
semantically, so a head and a tail that never appeared together mostly never will. What is
productive is taking one real name and moving one thing about it.

`splice.py` was listed under *Candidates worth building* from the beginning and never built,
because as a generator it is 4.2e13 candidates and a Python generator emits a million a second.
It is a plan now, it ran in under two minutes a game, and it is dead. **That is the point of the
plan engine** — an idea that sat unbuilt for want of a year and a half of generator time got
settled in four minutes, and the answer is written down instead of waiting for somebody else to
have the same idea.

Before building anything that joins pieces of different names, weigh it against these numbers.

### How far the final-byte solve extends: two characters, and no further — 2026-08-22

The obvious follow-up to the solve below is to extend it to longer tails. It does not extend, and
this is the measurement so nobody spends an evening finding that out.

Shared leading hex digits between the hashes of two names differing in their last *k* characters,
against **0.03** for two entirely unrelated names:

| k | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| mean shared leading digits | **4.26** | 1.41 | 0.11 | 0.07 |

One character is strongly visible in the hash. Two is faint. **From three the pair is
indistinguishable from any two unrelated names** — XOR does not commute with the multiply, so each
further step scatters what the last one left. There is no proximity to filter on and no solve to
generalise.

**What works instead is not proximity but peeling**, which the engine already does. "Is this id a
known name with its last *k* characters replaced" is a plan: stems are known names cut short by
*k*, endings are every *k*-character string over the measured alphabet. `scripts/tails.py` writes
it. Sizes against 922k names and the 37 characters names end in:

| k | endings | candidates | time |
|---|---|---|---|
| 2 | 1,369 | 1.3 B | seconds |
| 3 | 50,653 | 31.7 B | **21 seconds** |
| 4 | 1.87 M | 1.14 T | ~15 minutes |

Each k subsumes the ones below it. **k=3 returned 266 on Cold War and 885 on Black Ops 4, in
twenty-one seconds each.**

### The hash runs backwards for the final byte, and that is a method — 2026-08-22

Contributed as an observation: `p9_example_model_name_1` and `..._2` hash to nearly the same
number. They do, and the reason is exact rather than approximate.

FNV-1a is `h = (h ^ byte) * prime`. For two names differing only in their **last** character the
XOR touches only the low eight bits, so

    h(A) - h(B) = ((h_prefix ^ a) - (h_prefix ^ b)) * prime

and that first term is an integer in [-255, 255]. The difference between the two hashes is always
an exact small multiple of the prime — `_2` is -3x, `_3` is -2x, `_a` is -80x. A few times 1.1e12
apart in a space of 1.8e19, which is what "nearly the same hash" is.

**It holds for the final byte and no other.** One position further in, the difference is carried
through another XOR, XOR does not commute with the multiply, and the multiplier is already 7.1e18
— random. Do not try to generalise it; that is measured, not assumed.

**The relation inverts, so this is a solve rather than a search.** The prime is odd, so

    u = (h(prefix) ^ byte) * prime   =>   byte = (u * prime_inverse) ^ h(prefix)

Take every known name's prefix, ask whether `u * prime_inverse` differs from one of them in the
low eight bits only, and the answer *is* the character. 256 lookups per unnamed id, no strings
built, no candidates hashed.

**Measured, Black Ops 4: 2,523 candidates, 138 confirmed — one name per 18.** The next best method
in this file is image siblings at one per 394. Sweeping the same ground the obvious way took
35,068,642 candidates for 75 names, so solving backwards is ~14,000x cheaper *and* covers more,
because it tests all 256 bytes rather than the 39 a measured alphabet would carry.

Two traps, both paid for:

- **Hash the solved name back.** The solve gives the byte the hash wants; the game hashes a
  *normalised* name. A solved byte that is uppercase or a backslash cannot survive normalisation
  and will never hash to that id. Without the check it reported 11,003 solutions where 63 were
  real, and `confirm_list` matched 0.6% of what it was handed.
- **Its 138 landed as 3.** A brute sweep of the same ground an hour earlier had already claimed
  them. That is `found` against `landed` in `methods_report.py`, and it is the normal case.

### Cross-type core seams are stronger than recorded and yield nothing — 2026-08-22

Both rows above are worth reading carefully, because they are the clearest example in this file of
a measurement that looks like a find and is not.

`cross_type.py --measure` applies **one** reduction to both sides of a pair. `scripts/seams.py`
applies every reduction to each side independently, and under the right pair the material→image
seam is **75,964 shared cores against the recorded 15,770** — 59.98% of every image name in the
corpus. The relation is real and it was being measured five times too weakly. The spelling is real
too: **85.9% of those shared cores reconstruct an actual published image name** when spelled
`begin + core + end` with image's own commonest decorations.

Then it was run. `confirm_plan` put the 181,466 cores material has and image has not through the
engine with those decorations — 113,416,250 candidates against Cold War and the same again against
Black Ops 4 — and matched **0 unnamed ids on either game**. Not zero new: zero matched. The
material→xmodel seam, 78,208,750 candidates each way, likewise **0 and 0**.

So the seam is genuine, thoroughly mined, and **its non-overlapping half does not extend**. A core
that one type has and another has not is overwhelmingly a core the second type never had.

**The lesson is about the headroom column, and it cost four passes to learn.** `seams.py` reports
`only in A` as what a derivation would produce, and both these seams had six figures of it. It
predicted nothing. Relation strength says the relation exists; it does not say the missing side is
missing *because nobody has named it yet*. Only running it says that — and running it is now
minutes, so **run it rather than reasoning about it**.

### The two cheapest checks with the biggest upside

**1. Do confirmed image cores appear as material cores?** — **built and measured, 2026-08-20.**
See method 16 below. The seam is real and the yield is poor: 7 names in Cold War, 10 in Black Ops
4. Do not re-derive it.

**2. Do confirmed model names hash into the `xcollision` and `xskeleton` pools?** `odd_for_pool` in
`src/lib.rs` notes a model id "with the usual `xcollision` and `xskeleton` beside it". If those
siblings share the model's name, every one of ~6,444 confirmed model names is a free name in two
more pools. Ten minutes to test: hash confirmed model names and look for the ids in those pools.
**Ask before grinding it** — neither is among the five wanted types, and check cod-name-db has a
destination table, since a name with nowhere to land is worth less than one that can be published.

### Others, briefly

- **`numbered_grids.py`** — families numbered on *two* axes. `families.py --gaps` walks one; nothing
  fills a hole in the second. Measure: how many names carry two separate numeric tokens.
- **`suffix_chains.py`** — endings compose (`_01` + `_c`). The list is capped at 4,800 *observed*
  endings, so rare compositions are structurally absent. Measure: how many pairwise compositions of
  the top 50 endings are already published but missing from `data/suffixes.txt`.
- **`compound_splice.py`** — head of one name, tail of another, joined at a shared token. Distinct
  from `slotswap` (substitutes in place) and `templates` (crosses within one family). Cap by
  requiring a *rare* shared token or the pair count is quadratic.
- **`token_order.py`** — permute two adjacent middle tokens. Nothing here reorders anything.
  Measure: do any permutations of confirmed names already appear in the tables? If none do, the
  convention is stable and this finds nothing.
- **`cross_game.py`** — try a name confirmed in one title verbatim in the other. `confirm_cw` seeds
  *pieces* across games already, but nothing tries whole names. Nearly free: no generation, just
  hashing a list that exists.
- **`cross_era.py`** — the `_v2` tables (Vanguard, MWII, MWIII, BO6, BO7) re-hashed under *this*
  era's rules. Those games reuse older assets. Note they use a different mask — see `docs/HASHES.md`
  — so re-hash their *names*, never reuse their ids.
- **`map_sets.py`** — map prefixes (`p9_` heads 77,248 published names, `p8_` 66,172, `p7_` 42,516)
  crossed with faction codes and confirmed bodies. Overlaps `slotswap`; measure what it reaches that
  slotswap does not.
- **Black Ops 4 `sound_asset`** — 70,878 unnamed and ~102 ever found, the largest untouched ground.
  The general sound pass gets ~169 a time because its beginnings cannot express deep SAB paths.
  Characterise the 8,385 known SAB names first; a generator built from their path structure is the
  most valuable unbuilt thing here *if* the structure is learnable.
- **`methods_report.py --efficiency`** — not a generator. Every run folder records candidates,
  matches and time. Nothing computes names-per-candidate across them, so the ranking above will go
  stale. Once computed, the rotation could order itself by measured yield.

### Infrastructure, not generators

- **`images_from_materials` has no checkpointed run folder.** `confirm_cw` and `confirm_list` write
  theirs every sixty seconds so a killed pass stays submittable; this one does not. It is also the
  most expensive slot in the rotation, now measured at 2h15m for 43 names — see the note under
  method 3. The checkpointing is the part still missing.
- **`--shard i/n` on `confirm_cw`.** Needed before anyone runs several machines. The search is
  deterministic, so N machines running one method produce identical output.
- **Feed the in-flight survey into `suggest`.** `start` surveys every open pull request and then
  never passes it to `suggest`, so every fresh clone is told to do the same thing. Also break the
  fresh-clone game tie randomly rather than by list order.
- **`snapshot` will silently destroy an injected pool.** Run with no argument it rewrites
  `snapshots/<game>.ids` purely from the loader — which drops Cold War's 50,890 injected
  `sound_alias` ids and Black Ops 4's 79,263 SAB `sound_asset` ids, because Cordycep has no pool
  for either. It takes an output path; a guard that refuses to overwrite a file holding pools the
  loader does not have would be better than remembering to pass one.
- **`name_field_probe` and `loader_strings` need the game open**, and answer two questions that
  have now cost more than one session each: where a pool keeps its name, and what the string pool
  can reach. Both are Cold War-measured only — the Black Ops 4 halves are unrun.

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

## 16. Materials from image cores

`scripts/materials_from_images.py` | **7** (CW), **10** (BO4) | 4.57M candidates per game

The material ↔ image seam run backwards. `images_from_materials` (method 3) goes material → image;
this strips an image name to its core — directory, a leading `i_`, one channel suffix — and offers
that core as a material under all twelve directories, in both the `mtl_` prefixed and bare
spellings. Both forms are needed: of 329,846 material names measured, **67.4% carry `mtl_` and
32.6% do not**, so emitting only the prefixed form gives up a third of the space.

**What it reaches that nothing else does:** material names whose core was only ever confirmed as an
image. There are far more published image names than confirmed materials, so the reverse direction
has the larger corpus — which is why it looked promising.

**Spent by:** its own corpus. It reopens only when new image names are confirmed.

**The estimate was wrong, and how it was wrong is the useful part.** Beforehand this was measured
at 158 hits for Black Ops 4 (1 per 14,456 candidates, against `token_edits` at 1 per 94,000) and it
returned 10. The estimate excluded only names in the *published tables*; the real run also excludes
the **9,583 ids already claimed** by merged submissions and open pull requests, which is what
`wanted_for_search` does and a hand-rolled estimate does not. Estimate against the claimed set, not
the tables, or expect to be out by an order of magnitude.

---

## The compounding loop, measured over one night

`AGENTS.md` §7 says every confirmed name is a new beginning, a new ending and a new numbered
family, so re-measuring the lists reopens a method that reported itself exhausted. That is true.
This is how much, and how fast it decays -- measured 2026-08-20/21 on one machine, both games,
the same binary each time.

| pass | Black Ops 4 | Cold War | lists |
|---|---|---|---|
| 1 | **55** | **56** | as committed |
| 2 | **294** | **303** | after folding in ~800 newly merged names |
| 3 | **51** | -- | after folding in ~2,000 more |

**The second pass is worth five times the first, and the third is worth less than the first.**

The reason is not the *number* of names folded in but where they came from. Fold 1 took in 1,218
names from another contributor's evening -- vocabulary this machine had never seen. Fold 2 took in
~2,000 names, mostly found by *these same passes*, so the beginnings and endings it added were
largely ones the search had just finished using. A corpus that grows by rediscovering its own
neighbourhood does not widen what the lists can express.

**So the loop is fed by other people's names, not by your own.** Re-measure after merging a batch
from somebody else, and expect little from re-measuring after your own pass. `python
scripts/reach.py` will not tell you this -- reach stayed at 94.3% / 92.8% on models across all
three folds, because the ceiling was never what moved.

---

## The ending list is the bottleneck, and it is measurable

Written 2026-08-23, after `mcdp/` and `uncarried_endings` returned 9,520 names between them in one
evening from the same idea.

Both wins came from the same place, and it is not a clever recombination -- it is the observation
that **the committed lists are a cap, and everything outside them is unreachable no matter what
method is pointed at it.** `data/prefixes.txt` carries 700 beginnings and `data/suffixes.txt`
carries 4,629 endings. Measured against the published tables:

    endings carried                4,629      (2,798 of one segment, 1,086 of two, 745 of three)
    uncarried, 1 segment         178,016  heading   620,830 published names
    uncarried, 2 segments        471,768  heading 1,610,162 published names
    uncarried, 3 segments        786,512  heading 4,155,796 published names

**Better than a quarter of the published corpus ends in something no generator here can put on a
name**, and the commonest are not exotic -- `_thermalmap` heads 16,000 alone, and at two segments
the ranking is animation transitions: `_to_walk`, `_to_sprint`, `_to_jog`, `_offset_additive`,
`_empty_ads`.

### Why this was not found by re-measuring

CLAUDE.md §8 is right that re-running `derive_lists.py` does not reopen ground: it changes what a
search is *called* without changing what it can *reach*. That is exactly why this was invisible.
The ending list is **capped**, `derive_lists.py` reports what its ceiling cut, and re-measuring
cannot lift a cap -- so the cut vocabulary was reported honestly every single run and never once
acted on. The fix was not to measure again. It was to take what the cap threw away.

### What it costs, and the shape that works

The cores come from the published names with the same number of segments removed, so a core that
wears `_c` in the tables can be asked about wearing `_thermalmap`. Two things keep it runnable:

  - **Drop dotted endings.** Sound names carry a dotted tail, and at three segments they crowd out
    every ending the other four types use. §5 already says a sound ending tried against a model id
    can only ever be a coincidence. `--sounds` keeps them if a sound pass wants them.
  - **Restrict the cores to one game past two segments.** The ending vocabulary grows faster than
    the core list shrinks, and the published core list makes the plan unrunnable.

### The core list mattered more than the ending list

Added later the same day, and it is the single most productive change made to this method.

Every ending sweep above built its cores the same way: a published name with **exactly as many
trailing segments removed as the ending has**. A two-segment ending could therefore only ever
attach to a name cut two segments from its end. That is an arbitrary restriction, and it was
costing most of the yield.

Cutting every known name at **every** segment boundary instead gives 1,334,022 cores, so a core
that sits five segments deep in one name gets asked about wearing a two-segment ending from
another. Measured 2026-08-23, both games together:

    all-boundary cores x  20,000 endings        602 names
    all-boundary cores x 100,000 endings      2,553 names
    all-boundary cores x 300,000 endings      1,470 names

against 2,065 for the original depth-matched sweep at 200,000 endings. Repeated at the other
depths, both games: 1 segment **316**, 3 segments **1,523**, 4 segments **381**.

It transfers to sound, which breaks at path separators as well as underscores. 839,743 sound
cores against 100,000 uncarried sound endings returned **1,746 names in one pass** -- more than
the entire depth-matched sound sweep (1,385) had returned across six. **The ending list was
never the binding constraint -- the core list was**, and the two multiply: widening the endings
five-fold over the wide core list quadrupled the yield, where widening them over the narrow one
had gone flat.

> **Read those figures as a shape, not as a quota.** They were all taken on 2026-08-23 against
> the corpus as it stood that morning. Reproduced independently that afternoon, after roughly
> 187,000 further names had been claimed by merged and open submissions, the same method on
> Cold War returned **163** at 100,000 endings and **37** on the sound half -- the method is
> intact, the ground under it is not the same ground. This is the ordinary decay every method
> here shows, and it is the reason a yield is only ever a fact about a corpus at a moment. If
> you run this and see tens rather than thousands, nothing is broken; check
> `methods_report.py --efficiency` for where it has decayed to before concluding otherwise.
> The generator that implements this is
> `scripts/contributed/uncarried_endings_allboundary_20260823-134935.py`; it rebuilds the
> all-boundary core list from whatever the corpus holds now, which is the only thing that
> genuinely reopens this ground.

The lesson generalises past this method. When a cross product underperforms, work out which of
the three lists is actually restricting it before widening whichever one is easiest to widen.

### And the cores this project made itself

The corpus grew by roughly 24,000 confirmed names on 2026-08-23, and that changes the core list
in a way re-measuring never can. Cut at every boundary, **156,178 non-sound cores and 319,592
sound cores exist only in `findings/` and the merged submissions** -- they occur nowhere in the
published tables, so no ending sweep had ever crossed them with the ending vocabulary.

    confirmed-only cores x 505,416 endings            746 names
    confirmed-only SOUND cores x 184,215 endings      583 names

This is the distinction §8 is drawing and it is worth stating in the positive. Re-running
`derive_lists.py` reopens nothing because it renames the same reach. New **material** reopens
ground properly, and confirming names is the only thing that produces it -- which is why the
right move after any productive pass is to rebuild the core list and run again, and the wrong
move is to re-measure and run the same thing.

### Where it is spent, and where it is not

Yield by depth, both games, 2026-08-23: 1 segment **1,191**, 2 segments **2,065**, 3 segments
**1,800**, 4 segments **1,054**, 5 segments **564**. It decays with depth rather than with
re-running, because each depth is a different vocabulary rather than a deeper sweep of one.

The obvious next question is the mirror. This is all endings. The beginning list is capped at 700
the same way, and `mcdp/` is one beginning out of that cap worth 2,846 names on its own.
`scripts/contributed/redecorations_20260823-023757.py` ranks uncarried beginnings by how
much of their vocabulary is borrowed, and the general sweep over all 1,075 of them returned
only 7 -- but that sweep used **bare stems and no endings**.

**That question has since been answered, and the answer is no.** Crossing the uncarried beginnings
with the uncarried endings was measured the same day at 229 billion candidates for **0 names** --
see *doubly uncarried* in the dead ends below. A name is reachable through one cap or the other,
not through both at once: the middles that survive stripping a segment off each end are too short
to identify anything. This paragraph originally closed by calling the cross unmeasured, which was
true when it was written and was overtaken within the day; it is kept because the reasoning that
motivated it is still the right reasoning, and only its conclusion moved.

## A third title as spare parts, and which parts are worth taking

Written 2026-08-23, when Modern Warfare 2019 was captured with `snapshot_names` and turned out
to be worth exactly one of the three things tried with it.

Modern Warfare 2019 holds its asset names in plain text -- the name is a `char*` in the header,
not a hash -- so there is nothing to recover from it and it is not a target. What it is, is
**1,167,131 real Call of Duty asset names**, captured to `snapshots/modwar19.names.txt.gz` and
read with `snapshot.name_corpus()`.

**Treat it as spare parts, reached for when a method is short of vocabulary -- not as a place to
point a pass because it is large.** Every asset type is in it deliberately, because a fragment
from one type's name routinely decorates another; take whichever parts serve what you are
building. The question this corpus poses is not "does it match" -- that is answered and the
answer is no -- but **which parts to strip, and which of the target game's affixes to put back
on**. That question is open, and every method below is one answer to it. It shipped Warzone, so it carries a great deal of Cold War's
content: 174,116 of its names mention `t9`, Treyarch's Cold War codename, against 2,632
mentioning `t8`. That ratio is the whole story of what it is good for.

### Verbatim is spent, and was spent before this project existed

    MW19 names against Cold War       2,107 ids, 2,027 of them localizeentry, ZERO wanted
    MW19 names against Black Ops 4    1,106 ids, 1,049 of them localize_entry, ZERO wanted
    already in the published tables   66,842 of the names

The corpus was taken into cod-name-db verbatim about three years ago. Every name the two titles
share **identically** is therefore already published, which is why a verbatim pass returns
nothing and always will. Do not run one.

### Recombining it as cores returns nothing either

    MW19 all-boundary cores x uncarried endings    0 in 184 billion candidates

Worth understanding rather than just avoiding, because the reason generalises. A core is a
*prefix*: it can only put new material on the **front** of a name. Asked what endings actually
followed an MW19 core inside real Cold War names, the answer was 3,886 near-unique tails whose
commonest appeared three times, including `otgun_leveraction` -- a cut through the middle of
"shotgun". Those prefix matches were coincidental character boundaries, not shared vocabulary.

### What works is the middles

The same asset is often in both titles under **the same middle with different decoration** -- a
prefix or a suffix that one title adds and the other does not. So cut each MW19 name at segment
boundaries on *both* ends, which makes the result a morpheme rather than a substring, and
re-decorate with the **target game's own** measured beginnings and endings.

Ceiling measured before spending the machine, as a fraction of known Cold War names the method
could express at all:

    MW19 all-boundary cores x uncarried endings     1.00%   -> returned 0
    MW19 middles x Cold War prefixes and suffixes   7.96%   -> returned 256

and it decomposes into real vocabulary rather than coincidence:

    'i_me_'    + 'decal_water_puddle'              + '_col'
    'c_'       + 't9_rus_pl_spetsnaz_infiltration' + '_torso'
    'ui_icon_' + 'callingcards'                    + '_gilded'

**Measure the ceiling before running this shape.** `mw19_middles.py --reach` does it in a minute
and it is what separated the 7.96% method from the 1.00% one before either cost a night.

Measured and not worth it: `--strip 3` reaches 7.27% against `--strip 2`'s 7.96%, so stripping
deeper costs a third more candidates for less reach.

### Why the corpus is kept whole

The Black Ops 4 return is small and always will be -- the `t8` share is 1.5% of the `t9` share.
The reason the whole corpus is committed rather than the `t9` subset is the titles *after* these
two: Modern Warfare 2019's conventions are what Modern Warfare 2022, 2023 and Black Ops 6
inherit, and those titles reuse its assets directly. It is the seed corpus for the next targets,
not this one.

## What a ceiling predicts, and the filter that hid a tenth of a corpus

Two things were learned the hard way on 2026-08-23 and are cheap for everybody after.

### What a ceiling does and does not predict

`--reach` measures what fraction of *known* target-game names a method could express at all. It
costs a minute and it is worth taking, but it was first written up here as a simple threshold and
that was wrong twice over. The corrected form:

**1. Measure it held out, or it is circular.** A ceiling built by cutting up the same corpus you
then measure against is asking whether a method can reproduce its own input. Cold War item bodies
crossed with Cold War variant tokens measured **61.96%** that way; split the corpus in half and
build the vocabulary from one half only, and the honest figure is **22.62%**.

**2. Even an honest ceiling predicts nothing on its own**, because it measures reach over *named*
names. That 22.62% method returned **0**. The reason is the thing that actually matters:

> **Recombining a corpus with itself is bounded by that corpus.** Every name Cold War's own
> bodies and Cold War's own variants can compose lies inside the region Cold War's vocabulary
> already covers -- and that region is, by definition, the named one. The unnamed assets are
> unnamed *because* they are outside it.

That is why the Modern Warfare 2019 methods pay and this one does not. MW19 is **outside**: it
supplies morphemes Cold War's corpus cannot compose, which is what §8 means by different ground
and §7 by new material. A ceiling is useful for ruling a cross-source method out -- MW19 cores at
1.00% and MW19 material bodies at 1.28% both returned 0, against middles at 7.96% returning 256 --
and useless for ranking a same-source one, which is bounded whatever it measures.

**So the question to ask of a method is not "how high is its ceiling" but "where is its vocabulary
from".** If both halves come from the corpus you are searching, expect nothing, whatever the
measurement says.

### If a filter is discarding a tenth of the data, look at what it is discarding

The Modern Warfare 2019 capture was first read with a filter that dropped every entry containing
`~`, labelled in its own docstring as "a Cordycep composite, not a name the game uses". That
label was half right -- Cordycep does merge those entries -- and being half right stopped the
question. What was actually in them was **two or more real image names joined by `&`**, because
the title packs textures into colour channels and names the asset after all of them:

    c_t9_zmb_ndu_zombie_jacket_n&c_t9_zmb_ndu_zombie_jacket_green_g~13414439723048909555

`_n` and `_g` -- normal and gloss -- either side of the `&`. It cost **211,306 names that appear
nowhere else in the corpus**, 57,149 of them mentioning `t9`, and they turned out to be the most
productive material in the whole capture.

The signal was there before any domain knowledge: the filter was throwing away **121,538 of
1,167,131 entries, 11.6%**. Artefacts are rare. A tenth of a corpus is structure. **When a filter
discards a large fraction, that fraction is the thing to look at, not the thing to drop** -- and
a plausible name for something is not an explanation of it.

## Dead ends

Do not spend a night rediscovering these. Each cost real time.

| Tried | Outcome |
|---|---|
| Sound **alias** names as sound **file** stems | 706 of 101,673 distinct file stems are exactly an alias name — **0.7%**. The two vocabularies are unrelated: aliases are bare underscore names (`amb_computer_loop_1`), files are deep paths with encoding tails. Do not build a generator on this seam. |
| Model cores against anim cores | **Zero** shared, out of 154,525 model and 30,337 anim cores. Taking an anim's name minus its last token as a model name hits 16 of 30,337 (**0.1%**). There is no model/anim seam to exploit. |
| Model cores against material cores | 3,300 shared of 154,525 and 266,575 — about 2%, against the 15,770 that material and image share. Weak enough not to be worth a pass. |
| Recombining **sound file** paths, in either game, at any corpus density | This is the general form of the Black Ops 4 result below, and it settles what that one could not. Cold War `sound_asset` is **40.3% named** -- 39,178 known of 97,217, against Black Ops 4's 5.3% -- so it has eight times the material to recombine from, 2,679 directories and 38,574 basenames. Directory x basename: **0 new of 400,000**. Tail swap across the four commonest endings: **0 new of 36,679**. Importing Black Ops 2 and 3 basenames under Cold War's own directories: **0 new of 600,000**. So corpus density was never the obstacle, and the earlier "the corpus is too small to rebuild from" was the wrong diagnosis even after it was corrected once. A sound file is a *recording*, and its name belongs to the directory it sits in; basenames and directories are not independently combinable the way a material's core and its directory are. Anything reaching these pools has to come from outside the naming -- the SAB files, a build, or the game's own strings. |
| Re-hashing the newer titles' names against these two games | Candidate 15 below proposed this as costing "almost nothing -- no generation at all, just hashing an existing list", which was true, and it returns nothing. Every name in all eight `_v2` tables -- Vanguard, MWII, MWIII, BO6, BO7: `xmaterials`, `ximages`, `xanims`, `xsounds`, `soundbanks`, `soundbanks_aliases`, `animpkgs`, `bones`, **1,175,524 names** -- hashed under *our* rules, folded and unfolded, against the **336,505** ids still unnamed in the wanted types across both games. **Zero.** Not a weak seam; an empty one. The newer engines renamed rather than inherited, so their published vocabulary describes nothing these two titles hold. Costs three minutes to reproduce and needs no game. |
| Recombining Black Ops 4 `sound_asset` (SAB) paths | The largest single opportunity in either game -- **70,876 unnamed of 79,263** -- and recombination does not reach it. Everything anybody knows is **4,212 names, 5.3% of the pool**, and they do not generalise to the rest. Measured 2026-08-20, all against ids nobody can already name: filling holes in numbered families **0 of 1,847**; extending a family past its highest number **0 of 59,052**; swapping the extension tail (`.ln100.pc.snd` -> `.ll100.pc.snd` and the other 15) **78 hits but 0 new** -- every one was a name already published; directory x basename cross product **2 new of 240,000**, or 1 per 120,000, worse than `token_edits` at 1 per 94,000. The structure *is* learnable (24 leading segments, 16 extension tails, depth 2-6) which is what makes this worth writing down: the shape being legible is not the same as the corpus being big enough to rebuild from. Anything that reaches this pool has to come from outside the known names -- the SAB files themselves, or a build. **Corrected 2026-08-21, and the correction is the useful part:** GoastcraftHD's `sabpaths` found that outside source *inside this repository*. `bo2_sab.csv` and `bo3_sab.csv` hold 400,815 Black Ops 2 and 3 audio paths that nothing here had ever used, because they are SDBM-hashed and so are not "our games" for exclusion -- but their *directory* structure transfers, BO3 sharing **9.18%** of its stems against the 0.7% / 0.1% / 0 of the seams recorded dead above. Two further things this measurement got wrong: it read only three sound tables and recovered **4,212** known names where a full sweep finds **8,446**, so "the corpus is too small to rebuild from" was argued from half a corpus; and it tested recombination of Black Ops 4 names against each other, which is the one shape the pool's own structure predicts will fail, since names average 3.7 per directory and a known directory is mostly *unknown* members. Recombining what is already known is dead here. Importing directories from an older title is not. |
| Harvesting the loader's **script string pool** for candidates | Plausible and completely dead for the grind. Every string the loader holds, hashed against the live game: 23,301 of 1,480,510 ids, **1.6%** — and **0 of the 159,170 ids a Cold War pass actually hunts**. The 4,038 hits that do land in targeted pools (2,467 image, 1,567 xmodel) are *all* already in the tables. The reason is structural, not a matter of trying harder: an asset type is reachable from the string pool only if the engine addresses it **by name**, and models, materials and images are addressed by hash. Measure with `loader_strings`. |
| Scanning `xsub` files for names | They hold none. 85 GB of nothing. |
| A NUL-terminated-only string scanner over xpak/ff/fd | Misses roughly 800,000 names. |
| Suspecting the captured id is a **name pointer** rather than a hash | It is a hash. `snapshot` stores `entry.id`, the loader's own pool-entry field, never a dereferenced header. Measured over every asset in all 202 live Cold War pools: bits 0-62 uniform, bit 63 always clear, 12.5% 8-byte aligned (random gives 1/8), and tens of thousands of published names hash straight into it. Separately, `header+0x00` *is* the id in 180 of 202 pools and something else in 22 — `xanim` keeps its id at **+0x70** — but nothing reads that field, so it changes nothing. Re-measure with `name_field_probe`. |
| Salsa20 for the encrypted fast files | Wrong cipher. It is AES-256-CTR, little-endian counter. |
| Training a name classifier on the `_v2` tables | Those are MW2022/BO6 and teach the wrong conventions. |
| Stripping `_geo_rigid_bs_` as its own rule | Underscore truncation already covers it, and mesh names are unobtainable anyway. |
| Feeding the hash tables in as candidate input | A closed loop. 87% of `consolidate`'s work, zero names. |
| Hunting `localizeentry` | The entry holds a pointer to its own unhashed string — the plain text is already in the build. 8,667 confirmed in one pass, all worthless. `confirm_localize` now refuses to run. |
| Hunting `streamkey` | ~290,000 genuine, useless hashes, mostly sequential `d3dbsp` terrain. The largest pool in both games, so anything that "opens up every pool" lands here first. `submit` refuses to send them. |
| Widening `pools` to ~40 asset types by guesswork | One submission did. Nothing useful came of it, and the real findings were buried among the rest. |
| Searching four pools because they had "sound" in the name | `sound`, `sound_asset`, `sound_bank`, `sound_duck`. Only `sound_asset` is worth anything, and only in Cold War. |
| Cross-type generation involving `xanim` and a non-model type | Measured: 13 to 22 shared cores out of tens of thousands. There is no seam. |
| Recombining the **zombies** family into Black Ops 4 xmodels | `contrib/zombie_models.py`, 20260821: every model name already known to carry `zombie`/`zmb`/`zm_` cut into 46,306 stems and recombined against 24 model beginnings and 407 endings. **452,317,008 candidates, 0 matched** -- not a low yield, a zero, against 20,922 unnamed BO4 model ids. The family's vocabulary is not the constraint: the unnamed models are not spelled out of pieces the named zombies models use. A wider ending set is the obvious next try and the measurement says not to bother with the same stems. |
| Re-measuring the lists to reopen a spent method | `derive_lists.py` folds the confirmed names in, the fingerprint changes, and the tool stops saying the search is swept — so it looks like the method reopened. Three consecutive folds: **55 names, then 294, then 51**, the last on a corpus two and a half times larger. The lists are capped, so a fold displaces as much vocabulary as it adds; what reopens a method is different ground. This was `next_step`'s standing advice for a month and is most of how a 165-name pass became a 2-name one. |
| Uncarried beginnings crossed with the whole corpus, in general | The shape that returned 2,846 for `mcdp/` returns almost nothing anywhere else. Measured 2026-08-23: all 1,075 uncarried beginnings against the 879,325-core held vocabulary gave **0 on Black Ops 4 and 7 on Cold War** in 945 M candidates. `mcdp/` worked because 692 of 692 of its cores were borrowed from other directories -- it was a re-decoration of a vocabulary already held. Rank by *borrowed share* before building one of these (`scripts/contributed/redecorations_20260823-023757.py`); the rest of the uncarried beginnings have private vocabularies and this shape cannot reach them. |
| Cold War sound files, numbered takes | 36,971 of the 39,199 recovered basenames end in a number, so this looked like the obvious shape. Swept every index in every measured width against every measured tail on 2026-08-23: **0**. Verified not to be a plumbing failure -- 2,783 of 2,816 numbered seeds reconstruct exactly from the stem and ending lists. The game's take runs are already fully named. |
| Cold War sound files, directory x basename recombination | The same corpus, 248 real directories x 103,120 cores x the 16 commonest tails, 436 M candidates: **0**. Verified the same way -- 31,842 of 31,845 recovered names reconstruct exactly as directory + basename + tail. A Cold War sound basename does not appear under a directory the tables have not already caught it under. |
| Black Ops 4 sound files, numbered takes and recombination | The largest pool in either game (70,878 unnamed of 79,263) and the most expensive negative here: 2,572 directories x 10,538 cores x 13,995 numbered-take endings, **379 billion candidates unfolded, 0 matched** -- not 0 new, 0 hits of any kind. Whatever the unnamed 70,878 are, they are not recombinations of the 5,977 that are named. **Independently checked 2026-08-23** (`scripts/contributed/bo4_sound_plumbing_check_20260823-140622.py`): a zero this total is also the signature of a sweep that never built a valid candidate, so the vocabulary was rebuilt exactly as `bo4_sounds.py` builds it and asked whether it can express the names that *are* known. It can -- **8,581 of 8,583, 100.0%**, against the 99.99% the Cold War negatives were certified at. The plumbing is sound and this zero is a real property of the game. Two scope notes, neither of which reopens it: the engine hunts only *unnamed* ids, so a candidate rebuilding a known sound is correctly not counted as a hit and "0 hits" is consistent with working plumbing; and the recovered corpus has since grown from 5,977 to **8,583**, so the claim is exact for the vocabulary measured and slightly narrower than the corpus now available. |
| Black Ops 4 `sound_asset`, all-boundary cores x uncarried endings | The standing Black Ops 4 sound negative closed *numbered takes* and *directory x basename recombination*, both of which recombine within one segment depth. Method 25 is a different relation -- cores cut at every backslash, underscore and dot, so a core five segments deep in one path can wear a two-segment ending from another -- so it was not covered and was worth one pass. Measured 2026-08-23 against the recovered corpus (8,584 names, method 21, not the 178 in `all_names/`): 35,456 all-boundary cores x 4,434 endings this pool's own names wear and `data/sound.suffixes.txt` cannot express, 157 M candidates unfolded, **0**. The ending gap here is real and large -- 7,424 of 8,584 recovered names, 86%, end in something the carried list cannot say -- so this is not a vocabulary failure. It is the third distinct shape to return zero against this pool, and together they say the unnamed 70,679 are not built from the pieces the named 8,584 are built from, under any recombination tried so far. Generator: `scripts/contributed/bo4_sound_allboundary_20260823-151952.py`. |
| Black Ops 3 SAB names respelled as Black Ops 4 | Black Ops 4 is Black Ops 3's direct sequel on the same audio pipeline, same directories, same dotted-tail grammar -- so the paths ought to carry over. 3.06 billion candidates, lower cased, language directory dropped, every Black Ops 4 tail restored: **0**. |
| Cross-game sound transfer at full recovered vocabulary | METHODS lists this at 27 names, found when the seed corpora were 148 and 172 names. Re-run on 2026-08-23 with the recovered corpora -- 39,199 Cold War paths against Black Ops 4 unfolded, 5,977 Black Ops 4 paths against Cold War folded, both slash spellings: **0 each way**. The bigger corpus does not reopen it. |
| Doubly uncarried -- an uncarried beginning over an uncarried ending | Both halves are productive alone (6,674 names from endings, 2,846 from `mcdp/`), so the cross looked like the obvious next question. 100 uncarried beginnings x 458k middles x 5,000 uncarried two-segment endings, **229 billion candidates: 0**. A name is reachable through one cap or the other, not through both at once -- the middles that survive stripping a segment off each end are too short to identify anything. |
| The animation transition grid, composed rather than observed | `xanim` is the least-named type in both games and has a real grammar: 6,149 published names match `<core>_<from>_to_<to>` over 1,446 cores, 101 from-states and 129 to-states. That grid is 18.8 M combinations and the tables hold 0.03% of it, so composing the two state vocabularies looked like free ground. 50k cores x 13,029 composed transitions: **1 name a game**. The unobserved pairings are unobserved because they do not exist -- a weapon has the transitions its state machine allows and no others. |
| Materials from image cores through the thirteenth directory | `mcdp/` swept against every published material core returned 2,846, so asking the same directory from the image side looked like the other half of the seam. **0 both games.** The material-core sweep had already taken it; image cores add nothing `mcdp/` did not already reach. |
| Modern Warfare 2019 material bodies under Cold War's directories | The exact analogue of the channel swap, and it looked as good: MW19 material names are paths under its own directories (`twc4/` 134,344, `m2o/`, `mo/`, `tm/`), Cold War uses its own thirteen, and the directory names the title while the body names the asset. 243,206 bodies x 13 directories x 5,791 endings, 19.7 billion candidates: **0**. The ceiling explains it -- see *what a ceiling predicts* below. |
| Cold War item bodies crossed with Cold War variant tokens | The shape is real -- a character's materials share a skin token (`mtl_c_t9_usa_canteen_02_woods`, `mtl_c_t9_rus_chopper_pilot_vest_woods`) while the item varies, so swapping the token looked obvious. 4,650 bodies x 67 variants, 311,550 candidates: **0**. Its measured ceiling was 61.96%, which is the highest recorded here and entirely circular -- both lists were cut from the corpus being measured. Held out it is 22.62%, still high, and it still returns nothing: **a corpus recombined with itself cannot leave the region it already covers**, and that region is the named one. |
| MW19's glued `t9<token>` words used as Cold War character names | A real observation used in the wrong slot. MW19 writes the token glued -- `t9woods`, `t9mi6` -- where Cold War separates it (`c_t9_usa_pl_woods_infiltration_torso`), so no underscore tokenizer here had ever seen those 519 tokens; 262 of them are real Cold War segments. But the glued vocabulary is overwhelmingly **weapon behaviour** (`t9standard` 14,794, `t9accurate` 12,895, `t9fastfire` 9,934), not characters, and `t9woods`/`t9mi6` are a rounding error in it. Poured into Cold War's character-model template -- 17 beginnings x 482 tokens x 3,501 tails, 28.7 M candidates -- it returned **0**. The tokens are worth revisiting in a weapon frame; the character frame is measured and closed. |
| Modern Warfare 2019 names used verbatim | The corpus was taken into cod-name-db verbatim about three years ago, so every name the titles share identically is already published. Measured 2026-08-23: **0 in the five wanted types** against both games -- 2,107 Cold War ids of which 2,027 are `localizeentry`, and 1,106 Black Ops 4 ids of which 1,049 are `localize_entry`. 66,842 of the names are already in the tables. There is nothing left in a verbatim pass and there never will be. Use the middles -- method 26. |
| Modern Warfare 2019 names recombined as all-boundary cores | 1.84 M cores from the corpus against the 100,000 uncarried endings, **0 in 184 billion candidates**. A core is only ever a *prefix*, so this can only decorate the front, and the endings that followed an MW19 core in real Cold War names were 3,886 near-unique tails -- commonest appearing three times, including `otgun_leveraction`, a cut through the middle of "shotgun". Coincidental character boundaries, not vocabulary. Cutting at segment boundaries on **both** ends is what makes a middle a morpheme, and that shape returns 256. |
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
