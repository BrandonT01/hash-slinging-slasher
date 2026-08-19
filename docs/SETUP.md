# Setting up, for somebody who has never used a terminal

You need three things, and the tool installs two of them for you. The whole of it should take
about five minutes, most of which is a download.

If any of this goes wrong, the fix is almost always in what `start` prints. Read it — it is
written for exactly this moment.

---

## 1. Get the repository

If you have git already:

```
git clone https://github.com/KingslayerKyle/hash-slinging-slasher
cd hash-slinging-slasher
```

If you do not, download the zip from that page and unpack it. **Cloning is better**: a download
cannot be updated, and this project moves daily — `start` will warn you about that every time.

## 2. Run one command

```
bin\windows\start.exe
```

That is it. It will:

- install **git** if it is missing (via `winget`)
- install the **GitHub CLI** if it is missing
- bring the repository up to date
- download the community hash tables (a few hundred MB, once)
- read what other contributors have submitted and what they have in flight
- tell you if anything is still in the way

On Linux or macOS, install Rust first (`https://rustup.rs`), then
`cargo run --release --bin start`. The build takes about a minute and has no dependencies.

## 3. The one step nobody can do for you

`start` will stop and ask you to sign in to GitHub. This cannot be automated — it opens a browser
and asks *you* to approve it.

It prints the exact command. **Use the one it prints, not the one you have seen elsewhere.**

If it says something like:

```
& "C:\Program Files\GitHub CLI\gh.exe" auth login
```

then type that, including the quotes and the `&` at the start. That full path matters. The
installer adds `gh` to your PATH, but a terminal that was already open keeps the PATH it started
with — so in *this* window, the plain `gh auth login` everybody's guide tells you to type will say
`gh: not recognized`, and it looks like the install failed when it did not. Opening a new terminal
also fixes it.

Answer its questions:

| it asks | answer |
|---|---|
| What account do you want to log into? | **GitHub.com** |
| What is your preferred protocol? | **HTTPS** |
| Authenticate Git with your GitHub credentials? | **Yes** |
| How would you like to authenticate? | **Login with a web browser** |

It shows you a one-time code. Copy it, press Enter, and paste it into the page that opens.

Then run `start` again. It should end with `ready. Nothing here will stop a grind.`

## 4. Point an assistant at the folder

> Have a look at this repo and start grinding.

It reads `AGENTS.md` and does the rest: chooses a method, runs it for as long as you leave it, and
opens a pull request with whatever it finds. You do not need to know git, and you do not need to
approve anything.

Leave it running. The searching is compiled code on your CPU, not your AI usage — an hour-long
pass costs the assistant a few thousand tokens of waiting.

---

## If something goes wrong

**`start` says the clone has diverged.** You have local commits and so does the remote. Nothing
here will guess at a merge. `git status` and `git log --oneline --graph --all` will show you what
happened; usually the answer is that you want the remote's version.

**`start` says `winget` could not install something.** Install it by hand:
- git: <https://git-scm.com/download/win>
- GitHub CLI: <https://cli.github.com>

Then run `start` again.

**A search says "the startup checks have not been run in this clone".** Run `start`. Every search
refuses to run without it, on purpose: searching against a day-old picture of the world means
rediscovering names somebody submitted last night, and the run looks completely successful right
up until the pull request is a duplicate.

**A search says the fingerprint has already been run by somebody.** That is the tool telling you
this exact search will return their names and nothing else. Do not pass `--anyway`. Read
`METHODS.md` and run something else, or run `python scripts/derive_lists.py` first — that folds
every newly confirmed name into the search's lists and genuinely reopens it.

**`submit` says there is nothing left to send.** That is a good outcome, not a failure. It means
everything found is already somebody's, which is what an exhausted method looks like. A submission
of zero is worth more than a submission of duplicates.

**A pass has been running for an hour and printed nothing new.** It is fine. It writes what it has
found to disk every sixty seconds, so nothing is lost if you stop it. `Ctrl+C` and then `submit`.

---

## What you do not need

No game. No Cordycep, no Saluki, no Windows-only tooling, no GPU, and no game files of any kind.
The asset ids are captured and committed in `snapshots/` — 26 MB for both games — and both games
are finished and will never be patched again, so that capture is final rather than a cache that
goes stale.

You need this repository, a CPU, and a GitHub account.
