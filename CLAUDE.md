# Read this first

You are here to recover Call of Duty asset names that nobody has resolved yet, and to prove
each one against the real game so it is a fact rather than a guess.

The person who started you has gone to do something else. They are not waiting at the keyboard.
Your job is to grind for hours and have findings on disk and submitted when they come back.

## Nobody grinds until git and GitHub are working

**Do this before anything else, and do not skip it because the user seems keen to start.** A run
that cannot fetch the tables or send its findings is a wasted night, and that is discovered at 4am
with a full results folder.

The user needs three things. **Help them install and configure each one -- do not just tell them
to and carry on.**

1. **git** -- `fetch-tables` clones the community tables with it. Without it nothing can be
   excluded, and a search that cannot read the tables reports every published name in the game as
   a discovery, which looks exactly like success.
2. **GitHub CLI (`gh`)**, installed *and signed in* with `gh auth login`. This is the one people
   forget. Walk them through it.
3. **Nothing else on Windows.** The compiled tools are in `bin/windows/`, so no Rust toolchain is
   needed. On Linux or macOS, build once with `cargo build --release` -- there are no
   dependencies, so it takes about a minute.

`preflight` checks all of this and exits non-zero if anything would stop a grind. Run it, read it,
and fix what it says before starting a pass.

## Running the tools

On Windows use the committed binaries and skip cargo entirely:

```
bin/windows/preflight.exe
bin/windows/confirm_cw.exe
bin/windows/submit.exe
```

Everywhere else, `cargo run --release --bin preflight` and so on. The two are the same programs;
every command in this file works either way.

## Before anything else

Two steps, in this order, and neither is optional.

**First, bring the clone up to date:**

```
git pull --ff-only
```

The repository improves between sessions — fixed tools, new methods in `METHODS.md`, fresher
measured lists, and everybody's merged submissions — so an assistant on a stale clone spends
the night rediscovering what somebody already wrote down, with tools that may since have been
fixed. If local changes block the pull, stash them (`git stash`) and pull rather than skip
this. When a pull changes `src/`, the committed Windows binaries in `bin/windows/` were
rebuilt to match; on Linux or macOS rebuild once with `cargo build --release`.

**Then run preflight.** It takes ten seconds and it is not optional:

```
cargo run --release --bin preflight
```

It exits non-zero if anything would stop a grind. **The most important thing it checks is that
the user is signed in to GitHub**, because a night of grinding that cannot be submitted is a
night wasted, and that is discovered at 4am with a full results folder otherwise. If it says
`gh auth login`, stop and tell the user that one thing, then continue once it passes.

## Grind. Do not ask.

This is the part most assistants get wrong, so it is stated plainly.

- **Do not stop to ask which method to try.** Pick one and run it. If you have a choice between
  asking and grinding, grind.
- **Do not summarise and wait for approval.** There is nobody to approve it.
- **Do not stop because a pass found little.** A pass that finds nothing still feeds the next
  one — see the seeding principle below. Runs compound; a single pass judged alone is
  meaningless.
- **Do not stop because you think you are done.** You are not done. Cold War has ~745,000
  unnamed reachable ids and Black Ops 4 ~731,000. Nobody has come close.
- **Keep going for hours.** Run a pass, re-measure the lists from what it found, run another.
  That loop is the whole job.
- **Invent a new method when the one you are running goes quiet.** This is an instruction, not an
  aspiration, and it is the part most assistants miss. A pass that adds little is *not* a reason
  to run the same pass again -- it is the signal to go and build a new way of generating
  candidates and run that. `METHODS.md` gives every method a "spent when" line; when you see that
  signal, the next thing you do is invent, not repeat.

  A new method is a new way of *recombining* names already known to be real -- see the seeding
  principle below. Look for what the confirmed names have in common that no current rule
  expresses, and write something that expresses it. You are better at this than any fixed
  program, which is the entire reason this repo is pointed at you. Add what you invent to
  `METHODS.md` so the next assistant starts from further along than you did.
- **Report at the end**, once, with what was found and submitted.

The one thing worth interrupting for is preflight failing, because nothing works without it.

## The grinding costs your CPU, not your AI usage

Worth understanding, because it changes how you should work and it is the first thing the user
will want to know.

**The expensive part is not you.** The searching is compiled Rust running on every core of the
machine, hashing tens of billions of candidates a pass. That is CPU time and electricity. It
costs **no** tokens and no AI usage at all — while a one-hour pass runs, you are simply waiting
on a process.

Your usage goes on deciding what to try, launching it, and reading a short summary afterwards.
That is a few thousand tokens for an hour of grinding. A whole night is affordable.

**So do not waste usage on output.** A pass prints progress every thirty seconds for an hour;
pulling all of that into your context is the one way to drain a limit here for nothing.

- Send output to a log and read only the end of it:
  `cargo run --release --bin confirm_cw > logs/general.log 2>&1`, then read the last ~30 lines.
- Or filter the noise as it goes: `... | grep -Ev "^  (batch|checkpoint)"`.
- Never read a results file in full to count it. Count the lines.
- Never paste found names into your reasoning to "check" them. The tools already verified them
  against the game; that is what confirmation *is*.

Long searches are the cheap part. Treat your context as the scarce resource and the CPU as the
abundant one, and a night of grinding costs very little.

## What is already established — do not re-derive any of this

Every line here cost real time to work out. Re-deriving it is pure waste.

**The hash.** FNV-1a, 64 bit. Basis `0xCBF29CE484222325`, prime `0x100000001B3`. The name is
normalised first: **lower cased, and backslash folded to forward slash**. Missing that
normalisation makes everything fail to match. Compare at **63 bits** — loader ids always have
bit 63 clear, and narrowing further loses real matches and invents collisions.

**The same hash works for both games.** Cold War and Black Ops 4 use identical hashing and
normalisation. One implementation, one set of tables.

**The hash runs backwards.** The prime is odd, so it has an inverse modulo 2^64, and
`h = (h * prime_inverse) ^ byte` removes a byte exactly. So an ending does not have to be
appended to every stem — it can be *peeled off each wanted id once*, leaving the hash the stem
must reach. The cost stops being `stems × beginnings × endings` and becomes a sum. This is
already implemented in `src/search.rs`; use `run_best`, which picks the cheaper direction.

**Material names are paths.** Almost every material name carries a directory, and the directory
is part of what the engine hashes. There are **twelve** of them, not one:
`mc/ wc/ clt/ splm/ vd/ mcs/ ei/ cltp/ vdd/ el/ mcp/ ec/`. Ranking beginnings by popularity
keeps the first two and silently drops the rest, which is the entire naming of everything under
them. Carry all twelve.

**Mesh names cannot be reached.** An `xmodelmesh` name is `<model>_s1_geo_rigid_bs_` plus
twenty six characters of base32, and that tail is a hash of the mesh itself. They are excluded
from the wanted set deliberately: they cannot yield a name, and leaving them in doubles the ids
a candidate can hit by coincidence.

**Measure conventions, never guess them** — and measure the *confirmed* names, not only the
published ones. The tables hold no xmodel with a directory on it; confirmed xmodels are full of
them. `scripts/derive_lists.py` measures both.

## The seeding principle

**Candidates are always built from names already known to be real.** The published tables, the
names already confirmed, and strings scraped from the build are the raw material. A method is a
way of *recombining* that material.

Feeding the published tables in as a *source* rather than only as an exclusion list was worth
more than every rule change before it, because the piece an unnamed asset shares with a named
sibling is exactly what a rule needs. They can never be a find, being already resolved — but
their vocabulary is the game's own.

This is also why the search is self-feeding: every confirmed name is a new beginning, a new
ending, and a new numbered family for the next pass to measure. **Run a pass, re-measure, run
again.** Keep going until a round adds nothing.

**Mine the past submissions too.** Every merged batch in `submissions/` records more than its
names: the `about_*.md` beside them says which method found them and how long it ran. Read a
few recent ones before choosing what to run — another machine's names are seed vocabulary for
yours, and a method its notes prove worked is a better first pick than a guess. This is the
snowball: every batch that lands makes the next assistant's first hour smarter, but only if
the next assistant actually looks.

## Methods that work — a springboard, not a menu

- **Materials → images.** Strip `mtl_`, try `i_` plus every semantic suffix (`_c _n _s _g _o
  _m` and the rest), and also try it with *no* prefix at all. Images are frequently named for
  the material that uses them.
- **Read the tables for patterns and extend them.** Look at what the cdb tables already resolve,
  notice the shape, and generate the neighbours that are missing.
- **Cut at underscores and recombine.** A scraped line carries noise at both ends; every piece
  between marks is a candidate in its own right.
- **Vary the number in place.** A family number usually sits in the middle, so no
  beginning-stem-ending rule can change it. `confirm_variants` does this; `swaps` widens it.
- **Unfold `CATEGORY/KEY` localize pairs against each other.** Known categories against every
  harvested word yields keys; known keys against every candidate word yields categories.
- **Sound names carry dotted tails** like `.rn75.pc.en.snd`. The general search treats a dot as
  the end of a name, so it can never put one back on.

**These are examples, not the list.** Inventing a new method is the single highest-value thing
you can do here, because every method exhausts. That is the main reason this repo is pointed at
an assistant rather than run as a fixed program.

## Order of resort

Seeded methods first, always — that is where the yield is and they compound. Exhaustive or
random character combination is a legitimate *last* resort once seeded methods are genuinely
exhausted, not a starting point. If you get there, constrain it with what has been measured —
known directories, known prefixes, known segment shapes, known endings — rather than sweeping
raw character space. A combination built from measured parts is enormously more likely to land
than an arbitrary string of the same length.

## Things already tried that did not work

Do not spend the night rediscovering these.

- Scanning `xsub` files for names — they hold none. 85 GB of nothing.
- A NUL-terminated-only string scanner over xpak/ff/fd — misses ~800,000 names.
- Salsa20 for the encrypted fast files. It is AES-256-CTR, little-endian counter.
- Training a name classifier on the `_v2` tables. Those are MW2022/BO6 and teach wrong
  conventions.
- Stripping `_geo_rigid_bs_` as its own rule — underscore truncation already covers it, and mesh
  names are unobtainable anyway.

## Collisions, briefly

A match proves the string hashes to an id the game holds. With ~1.5M ids in a 2^63 space, a
coincidental match is possible but vanishingly rare — a normal pass expects ~0.00001 of them.
Every binary prints the figure. It is not something to worry about or design around; the only
regime where it matters is unconstrained character sweeps, which is why those are the last
resort.

## Rules that are not negotiable

1. **Results only ever grow.** Never rewrite a results file to be smaller. A rule change that no
   longer reaches an old name must not delete it.
2. **Exclude against the tables** before calling anything a find. A name any table resolves is
   already known to the community, whoever found it.
3. **Never write one game's names into another's files.** Snapshots carry their game internally;
   the tools check it. Do not defeat that check.
4. **Submit after every job.** Not at the end of the night — see below.

## Submitting

Findings are written to disk continuously, and a long pass checkpoints every sixty seconds, so
work is never more than a minute from being safe.

**Submit after each completed job rather than at the end.** Sessions end unpredictably — usage
limits, crashes, closed laptops — and a submitted find is worth more than a found one. Submitting
is cheap and safe to repeat: it tracks what has already been sent and will not send it twice.

```
cargo run --release --bin submit
```

Filenames carry the date and time to the second, so nothing collides with a previous submission.

## Where to look when stuck

- `README.md` — what this is and how to run each search.
- `METHODS.md` — the methods in more detail, and what each reaches that nothing else does.
- `src/lib.rs` — the hash, the filter, the results type.
- `src/search.rs` — the peeling engine. Read the comments before changing anything here.
- `snapshots/*.pools.txt` — every pool, with how many assets it holds. The unidentified ones are
  named `pool_NNN`; **working out what any of them is, is a genuinely valuable contribution**,
  because names in an unidentified pool cannot be submitted upstream until the type is known.
