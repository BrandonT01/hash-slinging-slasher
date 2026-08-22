# Every name this project has recovered

**Generated. Do not edit anything here by hand** -- `scripts/collect_names.py` rewrites it
whenever a submission lands, and an edit would be overwritten without warning. Corrections
belong in a submission, which is the record these are built from.

One file per game and asset type, `hash,name`, sorted by name. Together they are every name
in every merged submission in `submissions/`, with duplicates removed.

## Why you might want these rather than `submissions/`

`submissions/` answers *who found what, when, and by which method* -- it is the provenance
record and the input to `scripts/methods_report.py`. It is several hundred folders, and
anybody who just wants the names has had to walk and merge them. That loop is written once,
here, and the answer committed.

These are **not** a substitute for the community tables in `cod-name-db`. Those are the
published truth and are what every search excludes against. These are this project's own
contribution to them, which is a different and smaller thing.

## Why it is split by game

The two games number their asset types differently -- `xmodel` is pool 6 in Cold War and 4 in
Black Ops 4 -- so a file mixing them mislabels every row. You can see it in the type names
themselves: both `clipmap` and `clip_map` appear, and both `localizeentry` and
`localize_entry`, because those are the two games' own names for one pool.

A name appearing under both games is not duplication. Cold War carries a great deal of Black
Ops 4's content, and a name confirmed against both games' ids is a fact about both.

The 23 early submissions that predate the game going into the folder name are placed by
asking the snapshots which game holds an asset under that hash -- the same question that
made the name a find in the first place. A name both games hold is filed under both, which
is the right answer rather than a duplicate. `unplaced/` holds the remainder, which neither
snapshot carries -- almost certainly pools the snapshots do not cover, kept and labelled
rather than dropped.

## Contents

### `blkops04/` -- 57,266 names in 98 file(s)

| asset type | names |
|---|---:|
| `material` | 19,750 |
| `image` | 13,791 |
| `sound_alias` | 7,329 |
| `xmodel` | 6,303 |
| `xanim` | 2,751 |
| `technique_set` | 1,673 |
| `dynmodel` | 1,098 |
| `attachment` | 1,069 |
| `scriptbundle` | 586 |
| `sanim` | 391 |
| `weapon` | 294 |
| `scriptparsetree` | 266 |
| `sound_asset` | 170 |
| `weapontunables` | 120 |
| `cpu_occlusion_data` | 88 |
| `glasses` | 88 |
| `lighting` | 88 |
| `terraingfx` | 88 |
| `craftbackground` | 72 |
| `character` | 48 |
| `clipmap` | 48 |
| `uimodeldatastruct` | 47 |
| `navmesh` | 46 |
| `clip_map` | 45 |
| `com_map` | 45 |
| `districts` | 45 |
| `entitylist` | 45 |
| `game_map` | 45 |
| `gfx_map` | 45 |
| `navvolume` | 45 |
| `staticlevelfxlist` | 45 |
| `triggerlist` | 45 |
| `comworld` | 44 |
| `entity_list` | 44 |
| `gameworld` | 44 |
| `gfxworld` | 44 |
| `static_level_fx_list` | 44 |
| `trigger_list` | 44 |
| `localizeentry` | 27 |
| `talent` | 26 |
| `localize_entry` | 25 |
| `rumble` | 25 |
| `script_using` | 25 |
| `physpreset` | 24 |
| `script_using_wz` | 23 |
| `script_using_mp` | 16 |
| `impactsoundstable` | 14 |
| `sharedweaponsounds` | 12 |
| `script_using_zm` | 11 |
| `unlockableitem` | 11 |
| `crafticon` | 10 |
| `craftweaponsticker` | 10 |
| `fx` | 7 |
| `playeroutfit` | 7 |
| `shellshock` | 7 |
| `maptableentry` | 6 |
| `ragdoll` | 6 |
| `sound_duck` | 6 |
| `storagefile` | 6 |
| `unlockable_item` | 6 |
| `zbarrier` | 6 |
| `gametypetableentry` | 5 |
| `luafile` | 4 |
| `statuseffect` | 4 |
| `vehicle` | 4 |
| `xcollision` | 4 |
| `xskeleton` | 4 |
| `destructibledef` | 3 |
| `grouplodmodel` | 3 |
| `objective` | 3 |
| `postfxbundle` | 3 |
| `status_effect` | 3 |
| `tracer` | 3 |
| `bg_cache` | 2 |
| `bgcache` | 2 |
| `impact_sound` | 2 |
| `keyvaluepairs` | 2 |
| `scriptbundlelist` | 2 |
| `sound_bank` | 2 |
| `vehicledef` | 2 |
| `vehiclesounddef` | 2 |
| `weaponfrontend` | 2 |
| `entitysoundimpacts` | 1 |
| `fxlibraryvolume` | 1 |
| `klf` | 1 |
| `motion_matching_input` | 1 |
| `motionmatchinginput` | 1 |
| `rawstring` | 1 |
| `scriptparsetreeforced` | 1 |
| `sound` | 1 |
| `storecategory` | 1 |
| `surfacefx_table` | 1 |
| `surfacefxtable` | 1 |
| `tagfx` | 1 |
| `texture_combo` | 1 |
| `weapon_tunables` | 1 |
| `weaponblueprint` | 1 |
| `xcam` | 1 |

### `blkopscw/` -- 39,549 names in 40 file(s)

| asset type | names |
|---|---:|
| `sound_alias` | 24,509 |
| `scriptbundle` | 6,478 |
| `material` | 3,666 |
| `xanim` | 1,816 |
| `image` | 1,504 |
| `xmodel` | 920 |
| `attachment` | 178 |
| `sound_asset` | 144 |
| `clip_map` | 47 |
| `sound_bank` | 44 |
| `rumble` | 28 |
| `impactsoundstable` | 27 |
| `keyvaluepairs` | 25 |
| `weapon` | 22 |
| `physpreset` | 19 |
| `fxlibraryvolume` | 14 |
| `sound_duck` | 11 |
| `uimodeldatastruct` | 10 |
| `unlockableitem` | 9 |
| `vehiclesounddef` | 9 |
| `entitysoundimpacts` | 8 |
| `fx` | 8 |
| `impactsfxtable` | 7 |
| `shellshock` | 7 |
| `tagfx` | 6 |
| `objective` | 5 |
| `entityfximpacts` | 4 |
| `objectivelist` | 4 |
| `bgcache` | 3 |
| `statuseffect` | 3 |
| `laser` | 2 |
| `sound_alias_modifier` | 2 |
| `tracer` | 2 |
| `weaponfrontend` | 2 |
| `dynmodel` | 1 |
| `maptableentry` | 1 |
| `storecategory` | 1 |
| `surfacefxtable` | 1 |
| `tacticalquery` | 1 |
| `winddef` | 1 |
