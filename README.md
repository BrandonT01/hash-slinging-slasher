# hash-slinging-slasher

<p align="center">
  <img src="https://static.wikia.nocookie.net/spongebob/images/b/bd/Hashslingingslasher.png"
       alt="The Hash-Slinging Slasher" width="360">
</p>

<p align="center"><em>Slinging hashes at Call of Duty until the names fall out.</em></p>

Call of Duty stores most of its asset names as hashes rather than text. The name is gone; only
the number survives. This recovers them — and proves each one against the real game, so what
comes out is a fact rather than a guess.

Currently **Black Ops Cold War** and **Black Ops 4**.

## You do not need the game

This is the part worth understanding, because it is why anyone can help.

Confirming a name asks one question: *is the hash of this string the id of an asset the game
holds?* The answer is a set of numbers, and those numbers have already been captured — 1.6
million of them for Cold War, 1.0 million for Black Ops 4, in a file of a few megabytes.

Those numbers are committed here, in `snapshots/`. Both games are finished and will never be
patched again, so the capture was a one-off: these files are final, not a cache that goes stale.

So you need **no game, no Cordycep, no Saluki, and not even Windows**. You need this repo and a
CPU.

## Your CPU does the work, not your AI

The searching is compiled Rust running on every core, hashing tens of billions of candidates a
pass. That is CPU time and electricity — it costs **no AI usage at all**. While an hour-long
pass runs, your assistant is just waiting on a process.

Usage goes on deciding what to try and reading a short summary afterwards: a few thousand tokens
for an hour of grinding. A whole night is cheap.

## What you need

**One command.** On Windows:

```
bin\windows\start.exe
```

It installs git and the GitHub CLI if they are missing, brings the repository up to date, fetches
the community hash tables, and reads what every other contributor has in flight so tonight does
not duplicate one. It stops and tells you exactly what to type if anything is in the way.

The only step it cannot do for you is `gh auth login`, because that opens a browser and asks you
to approve it — and it prints the exact command for your machine, full path included.
[`docs/SETUP.md`](docs/SETUP.md) walks through it for somebody who has never used a terminal.

On Linux or macOS, install Rust and run `cargo run --release --bin start`. There are no
dependencies, so the build takes about a minute once.

## Getting started

Point your assistant at this folder and say so:

> Have a look at this repo and start grinding.

It reads [`AGENTS.md`](AGENTS.md), which tells it everything: the one command to run first, what
is already established, what methods have already been exhausted by somebody else, and that it
should grind for hours rather than stop and ask you things. That is the whole setup.

If you would rather drive it yourself:

```
bin\windows\start.exe             # always first; every search refuses to run until it passes
bin\windows\confirm_cw.exe        # the general search
bin\windows\submit.exe            # send what was found
```

Or invent a method, which is the useful thing to do here — a generator that prints candidate
names, and one command that confirms them against the game:

```
python scripts/continuations.py | bin\windows\confirm_list.exe - --label "per-prefix continuations"
```

## How it actually works

1. **Build candidates** out of names already known to be real — the published hash tables, the
   names this project has already confirmed, strings scraped out of a build. Never out of thin
   air; see the seeding principle in `AGENTS.md`.
2. **Hash them** with the game's own hash (FNV-1a, 64 bit, normalised, compared at 63 bits).
3. **Look for the result** among the captured asset ids. A match means the game itself refers to
   that name.
4. **Exclude anything already published**, so what remains is genuinely new.
5. **Submit it**, and it goes upstream into the community hash tables.

The interesting part is step 1, and it is open-ended. Every method eventually exhausts, so
inventing a new way to build candidates is the highest-value thing anyone can do here — which is
exactly what an assistant is good at, and why this repo is written to be read by one.

## The two halves

Grinding needs nothing. **Capturing** needed the game, Cordycep with everything loaded, and
Windows — and has already been done, for every pool in both games. It is kept for whenever a
third title is worth adding, behind a feature that is off by default:

```
cargo build --release --features cordycep
cargo run --release --features cordycep --bin snapshot
```

A default build has **zero external dependencies** and compiles anywhere. Nobody is asked to
build a process-memory reader they cannot use.

## Contributing

Findings arrive as pull requests, opened for you — you do not need to know git. They are
checked automatically and reviewed by hand before going upstream.

The most useful non-grinding contribution: **a home for the types that have no table**. Every
pool in both games is identified — `snapshots/*.pools.txt` is the complete map of every index,
its asset type, and how many assets it holds. What some types still lack is a *destination*:
cod-name-db carries tables for models, anims, images, materials and sounds, but a confirmed
`technique_set` name, for example, has no csv upstream to land in yet. Proposing and seeding
those tables is how whole pools' worth of findings become publishable.

## The hash tables

`tables/` says what the community has already resolved, which is the whole difference between a
discovery and a name somebody published last week. They come from
[cod-name-db](https://github.com/echo000/cod-name-db), which is also where confirmed names end
up — so the same repository is both what you check against and where your findings go.

They go stale in about a day. `start` fetches and refreshes them, so there is normally nothing to
do; `cargo run --release --bin fetch-tables` forces it in between.

Which file belongs to which game, and which hash and mask each uses, is in
[`docs/HASHES.md`](docs/HASHES.md). Getting the mask wrong is the commonest reason a correct name
fails to resolve, and it fails silently.

## Standing on other people's work

- [Cordycep](https://github.com/Scobalula/Cordycep) — loads fast files without running the game,
  which is what makes capturing a snapshot possible at all.
- [cod-name-db](https://github.com/echo000/cod-name-db) — the community hash tables, both the
  source of what is already known and the destination for what gets found here.

Licensed GPL-3.0-or-later.
