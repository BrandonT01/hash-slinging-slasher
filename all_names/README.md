# Every name this project has recovered

<table><tr>
<td valign="top">

<table>
<tr><th align="left"><code>blkops04/</code></th>
<th align="right" colspan="2">67,662 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">names</th><th align="right">% found</th>
</tr>
<tr><td><code>material</code></td><td align="right">26,988</td><td align="right">80.7%</td></tr>
<tr><td><code>image</code></td><td align="right">19,023</td><td align="right">75.3%</td></tr>
<tr><td><code>sound_alias</code></td><td align="right">9,522</td><td align="right">71.9%</td></tr>
<tr><td><code>xmodel</code></td><td align="right">8,423</td><td align="right">79.4%</td></tr>
<tr><td><code>xanim</code></td><td align="right">3,528</td><td align="right">70.5%</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">178</td><td align="right">10.8%</td></tr>
</table>

</td>
<td valign="top">

<table>
<tr><th align="left"><code>blkopscw/</code></th>
<th align="right" colspan="2">50,883 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">names</th><th align="right">% found</th>
</tr>
<tr><td><code>sound_alias</code></td><td align="right">25,661</td><td align="right">67.0%</td></tr>
<tr><td><code>material</code></td><td align="right">13,971</td><td align="right">84.9%</td></tr>
<tr><td><code>image</code></td><td align="right">5,806</td><td align="right">83.5%</td></tr>
<tr><td><code>xanim</code></td><td align="right">2,666</td><td align="right">66.7%</td></tr>
<tr><td><code>xmodel</code></td><td align="right">2,604</td><td align="right">78.3%</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">175</td><td align="right">80.3%</td></tr>
</table>

</td>
</tr></table>

**names** is what this project has recovered and published here. **% found** is how much
of that pool *anybody* can name -- these names plus every one already in the community
tables, over every id the game holds. A type at 80% has one id in five still unnamed;
`sound_asset` on Black Ops 4 at 11% is the largest unworked ground in either game.

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
