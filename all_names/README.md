# Every name this project has recovered

<table><tr>
<td valign="top">

<table>
<tr><th align="left"><code>blkops04/</code></th>
<th align="right" colspan="1">67,049 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">names</th>
</tr>
<tr><td><code>material</code></td><td align="right">26,671</td></tr>
<tr><td><code>image</code></td><td align="right">18,797</td></tr>
<tr><td><code>sound_alias</code></td><td align="right">9,522</td></tr>
<tr><td><code>xmodel</code></td><td align="right">8,379</td></tr>
<tr><td><code>xanim</code></td><td align="right">3,502</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">178</td></tr>
</table>

</td>
<td valign="top">

<table>
<tr><th align="left"><code>blkopscw/</code></th>
<th align="right" colspan="1">50,883 names in 6 file(s)</th>
</tr>
<tr><th align="left">asset type</th><th align="right">names</th>
</tr>
<tr><td><code>sound_alias</code></td><td align="right">25,661</td></tr>
<tr><td><code>material</code></td><td align="right">13,971</td></tr>
<tr><td><code>image</code></td><td align="right">5,806</td></tr>
<tr><td><code>xanim</code></td><td align="right">2,666</td></tr>
<tr><td><code>xmodel</code></td><td align="right">2,604</td></tr>
<tr><td><code>sound_asset</code></td><td align="right">175</td></tr>
</table>

</td>
</tr></table>

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
