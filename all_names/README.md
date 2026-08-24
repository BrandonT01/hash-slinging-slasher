# Every name this project has recovered

<table><tr>
<td valign="top">

<table>
<tr><th align="left"><code>blkops04/</code></th>
<th align="right" colspan="2">67,927 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">found here</th><th align="right">named, of all in the game</th>
</tr>
<tr><td><code>xmodel</code></td><td align="right">8,469</td><td align="right">48,592 / 61,139 &nbsp;(79.5%)</td></tr>
<tr><td><code>material</code></td><td align="right">27,050</td><td align="right">99,164 / 122,750 &nbsp;(80.8%)</td></tr>
<tr><td><code>image</code></td><td align="right">19,156</td><td align="right">126,183 / 167,360 &nbsp;(75.4%)</td></tr>
<tr><td><code>xanim</code></td><td align="right">3,530</td><td align="right">15,499 / 21,968 &nbsp;(70.6%)</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">178</td><td align="right">8,562 / 79,263 &nbsp;(10.8%)</td></tr>
<tr><td><code>sound_alias</code></td><td align="right">9,544</td><td align="right">36,015 / 50,043 &nbsp;(72.0%)</td></tr>
</table>

</td>
<td valign="top">

<table>
<tr><th align="left"><code>blkopscw/</code></th>
<th align="right" colspan="2">50,902 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">found here</th><th align="right">named, of all in the game</th>
</tr>
<tr><td><code>xmodel</code></td><td align="right">2,606</td><td align="right">67,071 / 85,612 &nbsp;(78.3%)</td></tr>
<tr><td><code>material</code></td><td align="right">13,977</td><td align="right">134,348 / 158,158 &nbsp;(84.9%)</td></tr>
<tr><td><code>image</code></td><td align="right">5,817</td><td align="right">204,825 / 245,235 &nbsp;(83.5%)</td></tr>
<tr><td><code>xanim</code></td><td align="right">2,666</td><td align="right">18,997 / 28,468 &nbsp;(66.7%)</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">175</td><td align="right">78,113 / 97,217 &nbsp;(80.3%)</td></tr>
<tr><td><code>sound_alias</code></td><td align="right">25,661</td><td align="right">34,080 / 50,890 &nbsp;(67.0%)</td></tr>
</table>

</td>
</tr></table>

**found here** is what this project has recovered and published in these files.
**named, of all in the game** is the whole pool: those names plus every one already in
the community tables, against every id the game holds.

They are not the same measure, and the second is much the larger.

Where `image` under `blkops04/` reads 19,156 and 126,183 / 167,360:
this project found 19,156 of the 126,183 names anybody has for that pool, and
41,177 of its ids are still nameless. The percentage is the fraction named,
not the fraction found here.

The emptiest pool is `sound_asset` under `blkops04/`: 8,562 of 79,263 named,
so 70,701 ids carry no name at all. That is the largest unworked ground
here, and it is invisible from a count on its own.

The community half of that is measured against `cod-name-db` on 2026-08-24 and stored in
`coverage.json`, because the tables are 345 MB and are not in this repository. Names
recovered here since are added on top, which is exact rather than approximate: `submit`
drops anything the tables already publish, so a later find cannot already be counted.
What a stale baseline misses is names *somebody else* published upstream, so it
under-reports rather than over-reports. `scripts/measure_coverage.py` refreshes it.

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

Twenty-three submissions predate the game going into the folder name. They are placed by
hashing each name and asking each game's `.ids` snapshot whether it holds an asset under it
-- the same question that made the name a find. A name both snapshots hold is filed under
both, because it is genuinely a fact about both.

Only the five asset types worth searching are here. Submissions carry names for 105 types;
the rest stay in `submissions/`, which is the record.
