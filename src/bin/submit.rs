//! Sends what was found, after checking it is all still new.
//!
//! Two things make this more than a `git push`.
//!
//! **The tables move while you work.** A name that was unpublished when a pass started can be in
//! the tables by the time it finishes, because other people are submitting too. So the tables are
//! refreshed *here*, immediately before the pull request, and anything that has since been
//! published is simply dropped from the batch. Nothing is re-searched -- the candidates were
//! already confirmed against the game and that has not changed; the only question is whether they
//! are still *new*, and that is a set difference costing seconds.
//!
//! **Sessions end abruptly.** An assistant on a usage limit stops mid-job, so submitting is done
//! after every job rather than at the end of a night. That makes this safe to run repeatedly: it
//! keeps a ledger of what has already gone, and a run that was already sent is skipped rather than
//! sent twice. If a session dies, the next one submits the backlog.
//!
//! Filenames carry the date and time to the second, so two submissions never collide.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::OnceLock;

use slasher::{
    config, expected_by_chance, github, hash64, low_value_reason, paths, recon, stamp, strip_stamp,
    tables, ID_MASK,
};

/// Where findings go. Set `submit_repo` in `config.toml` to override.
const DEFAULT_REPO: &str = "KingslayerKyle/hash-slinging-slasher";

/// Scripts a run wants to contribute, if it left any here.
///
/// The single best thing a night can leave behind is not its names -- it is the thing that found
/// them. A script in a pull request makes the next contributor's first hour smarter; a list of
/// names only makes the tables bigger. So anything dropped in this folder rides along.
const CONTRIBUTED: &str = "contrib";

/// The ledger of run folders already sent, so nothing is submitted twice.
const LEDGER: &str = ".submitted";

fn main() {
    // Every game's findings, not just the configured one. A session may have ground both, and a
    // run left unsent because the config moved on afterwards is a run lost.
    let findings = paths::findings_root();
    let outbox = paths::submissions();

    // 1. Who we are. Without this the whole night has nowhere to go, which is why `preflight`
    //    checks it before any searching rather than leaving it until now.
    let Some(who) = github_user() else {
        match github::locate() {
            Some(gh) => eprintln!("not signed in to GitHub. Sign in with:\n    {}", gh.login_hint()),
            None => eprintln!(
                "the GitHub CLI (`gh`) is not installed. On Windows: winget install --id \
                 GitHub.cli (anywhere else, https://cli.github.com), then `gh auth login`."
            ),
        }
        eprintln!("(this is what `preflight` warns about before a grind starts.)");
        std::process::exit(1);
    };
    println!("submitting as {who}");

    // 2. Anything a killed pass left behind, gathered up first so it can be sent like any other
    //    run. See `recover_stranded` -- this used to be lost silently.
    recover_stranded(&findings, &outbox);

    // 3. What has not been sent yet.
    let sent = already_sent(&outbox);
    let pending: Vec<PathBuf> = run_folders(&findings)
        .into_iter()
        .filter(|folder| {
            let name = folder.file_name().unwrap_or_default().to_string_lossy().to_string();
            !sent.contains(&name)
        })
        .collect();

    if pending.is_empty() {
        println!("nothing new to submit -- every run here has already been sent.");
        return;
    }

    println!("{} run(s) not yet submitted", pending.len());

    // 4. Refresh the tables *now*, so the batch is judged against what the community has this
    //    minute rather than whenever the session started.
    println!("\nrefreshing the tables before sending, in case anything was published meanwhile");
    let table_folder = match tables::ensure(&paths::tables(), true) {
        Ok(_) => tables::csv_folder(&paths::tables()),
        Err(why) => {
            eprintln!("\n{why}");
            eprintln!("refusing to submit against tables that may be stale.");
            std::process::exit(1);
        }
    };

    let known = known_hashes(&table_folder);
    if known.len() < 1_000_000 {
        eprintln!(
            "the tables read short at {} hashes, which means they moved rather than that the game \
             got smaller. Not submitting.",
            known.len()
        );
        std::process::exit(1);
    }
    println!("{} hashes already published", known.len());

    // 4b. What everybody else has claimed, asked of GitHub *now*.
    //
    //     The tables only know what has been merged and published upstream, which lags by days.
    //     The thing that actually causes duplicates is faster than that: somebody grinding on the
    //     same evening whose pull request is open but not yet merged. Nothing on this disk can
    //     know about that, and it has already happened repeatedly here: five submissions carry the
    //     same 430 names and two more carry the same 372, byte for byte.
    //     `python scripts/methods_report.py --duplicates` lists them.
    let repo = config::path("submit_repo")
        .map(|path| path.display().to_string())
        .unwrap_or_else(|| DEFAULT_REPO.to_owned());

    println!("\nreading what other people have in flight");
    let landscape = recon::survey(&repo, &outbox);

    if let Some(why) = &landscape.offline {
        eprintln!(
            "  [warn] GitHub would not answer ({why}), so open pull requests could not be read.\n  \
             [warn] Falling back to the last survey `start` saved, which may be hours old."
        );
    } else {
        println!(
            "  {} open submission(s); {} name(s) claimed in them and not yet merged",
            landscape.open.len(),
            landscape.claimed_in_flight
        );
    }

    // 5. One batch per game, and one pull request per game.
    //
    //    A name means nothing without the game it came from: the two number their asset types
    //    differently, so `xmodel` is pool 6 in Cold War and 4 in Black Ops 4. A batch mixing the
    //    two cannot state its own game truthfully, and a reviewer cannot tell at a glance which
    //    title a submission is for. The run folder's path says which game it was ground under,
    //    and that is what groups them here.
    let mut by_game: std::collections::BTreeMap<String, Vec<PathBuf>> = Default::default();
    for folder in pending {
        let game = paths::game_of(&folder).unwrap_or_else(config::game);
        by_game.entry(game).or_default().push(folder);
    }

    let cached = recon::load_cached();
    let mut opened = 0;

    for (game, runs) in &by_game {
        println!("\n--- {game} ---");

        if let Some(url) = send(game, runs, &repo, &outbox, &who, &known, &landscape, &cached) {
            println!("\nsubmitted: {url}");
            opened += 1;
        }

        record(&outbox, runs);
    }

    if opened == 0 {
        println!("\nnothing was sent.");
    }
}

/// Sends one game's runs, and returns the pull request it opened.
#[allow(clippy::too_many_arguments)]
fn send(
    game: &str,
    pending: &[PathBuf],
    repo: &str,
    outbox: &Path,
    who: &str,
    known: &HashSet<u64>,
    landscape: &recon::Landscape,
    cached: &HashSet<u64>,
) -> Option<String> {
    // Drop anything already claimed: published in the tables, merged into submissions, or sitting
    // in somebody's open pull request. This is the cheap part and the whole reason a long grind
    // does not have to be redone when the world moves under it.
    let mut batch: Vec<(String, u64, String)> = Vec::new(); // (type, id as found, name)
    let mut dropped = 0_usize;
    let mut claimed_elsewhere = 0_usize;
    let mut worthless: std::collections::BTreeMap<String, usize> = Default::default();

    for folder in pending {
        for (kind, id, name) in names_in(folder) {
            // A pool that has already cost somebody a night for nothing does not go upstream,
            // whoever found it and however genuine the hash is. See LOW_VALUE_POOLS.
            if low_value_reason(&kind).is_some() {
                *worthless.entry(kind).or_default() += 1;
                continue;
            }

            // Both the id the run found and the hash of the name, because for every pool but
            // the one that keeps its backslashes they are the same number, and for that one they
            // are not. Excluding on either is right: a name already published is already
            // published however it was reached.
            let hash = hash64(&name);
            let seen = |set: &HashSet<u64>| {
                set.contains(&id) || set.contains(&hash) || set.contains(&(hash & ID_MASK))
            };

            if seen(known) {
                dropped += 1;
                continue;
            }

            if landscape.holds(&name) || seen(cached) {
                claimed_elsewhere += 1;
                continue;
            }

            batch.push((kind, id, name));
        }
    }

    for (kind, count) in &worthless {
        println!(
            "held back {count} `{kind}` name(s): {}",
            low_value_reason(kind).unwrap_or_default()
        );
    }

    // The same name can be reached by several runs; it only needs sending once.
    batch.sort();
    batch.dedup();

    println!(
        "{} names to send\n  {dropped} dropped: published in the tables\n  {claimed_elsewhere} \
         dropped: already claimed by a merged submission or an open pull request",
        batch.len()
    );

    // What that second number means, said out loud.
    //
    // It is the only signal anywhere that somebody else is grinding the same ground right now,
    // and it was sitting in this output being read as bookkeeping. Measured over one night with
    // two agents running: the general search and `swaps` came back 70-99% claimed, while the
    // Cold War sound pass -- ground the other was not touching -- came back 3 claimed of 115.
    // Same machine, same hours. The difference was entirely which method the other one ran.
    //
    // Fingerprints stop you re-running a search somebody has *finished*. They cannot stop two
    // people running the same method at the same time, and this is what that looks like from
    // the inside.
    let offered = batch.len() + claimed_elsewhere;
    if claimed_elsewhere > 0 && offered >= 20 {
        let share = claimed_elsewhere as f64 * 100.0 / offered as f64;
        if share >= 50.0 {
            println!(
                "\n  [!] {share:.0}% of what this run found was already claimed by somebody else.\n  \
                 [!] They are grinding the same ground with the same method, and running it again\n  \
                 [!] will mostly rediscover their work. Pick a method they are not running --\n  \
                 [!] METHODS.md says what each one reaches that nothing else does."
            );
        }
    }

    if batch.is_empty() {
        println!(
            "\nnothing left to send for {game} -- every name found is already somebody's.\n\n\
             That is not a failed night, it is an honest one, and a submission of zero is worth \
             more\nthan a submission of duplicates. What it means is that this method is spent at \
             these\ninputs. Widen the lists (`python scripts/derive_lists.py`), run a method that \
             reaches\nsomewhere else, or invent one -- METHODS.md says what each one gets at that \
             nothing else does."
        );
        return None;
    }

    // Write the batch, named for the game and the moment it was sent, so nothing ever collides
    // and a folder says what it holds without being opened.
    let when = stamp();
    let folder = outbox.join(format!("{who}_{game}_{when}"));
    if let Err(error) = fs::create_dir_all(&folder) {
        eprintln!("could not make {}: {error}", folder.display());
        std::process::exit(1);
    }

    let mut by_kind: std::collections::BTreeMap<String, Vec<(u64, String)>> = Default::default();
    for (kind, id, name) in &batch {
        by_kind.entry(kind.clone()).or_default().push((*id, name.clone()));
    }

    println!("\n{:<24} {:>8}", "type", "names");
    for (kind, names) in &by_kind {
        let path = folder.join(format!("{kind}_{when}.txt"));
        let mut text = String::new();
        for (id, name) in names {
            // The id the run actually matched, never a fresh hash of the name. See `names_in`.
            text.push_str(&format!("{id:x},{name}\n"));
        }

        if let Err(error) = fs::write(&path, text) {
            eprintln!("could not write {}: {error}", path.display());
            std::process::exit(1);
        }

        println!("{kind:<24} {:>8}", names.len());
    }

    // The collision estimate, recorded rather than enforced. It is vanishingly small for any
    // seeded method; it is worth carrying so a strange batch can be traced afterwards.
    let estimate = expected_by_chance(batch.len() as u64, known.len());

    // What each run has to say for itself -- which method, and how long it ground for. Written
    // by the run into its own folder; a folder without one is from an older or interrupted run.
    let accounts = run_accounts(pending);

    // How many of each asset type, so a reviewer can see the shape of a batch without opening
    // five files and counting lines. A submission of 2,000 images and one model is a different
    // thing from an even spread across the five types, and only the breakdown says which it is.
    let breakdown = per_type(&batch);

    let notes = folder.join(format!("about_{when}.md"));
    let _ = fs::write(
        &notes,
        format!(
            "# Submission {when}\n\n\
             - game: **{game}**\n\
             - from: {who}\n\
             - names: {}\n\
             - dropped as already published: {dropped}\n\
             - dropped as already claimed by a merged or open submission: {claimed_elsewhere}\n\
             - runs included: {}\n\
             - searched: {}\n\
             - platform: {}\n\
             - confirmed on: {}\n\
{breakdown}\
             - expected coincidental matches: {estimate:.6}\n\
             - checked against: the community tables, every merged submission, and the {} pull \
             request(s) open at the moment of sending\n\n\
             Every name here was confirmed against the game's own loaded assets, and checked \
             against the community tables immediately before sending.\n\
             \n## How these were found\n{accounts}",
            batch.len(),
            pending.len(),
            config::targets().describe(),
            platforms_used(pending),
            backends_used(pending),
            landscape.open.len(),
        ),
    );

    // Anything the run wants to teach the next contributor, rather than only feed them.
    let scripts = contributed_scripts(pending);
    if !scripts.is_empty() {
        println!(
            "\ncarrying {} script(s) along with the names, so the next contributor inherits the \
             method and not just its output",
            scripts.len()
        );
    }

    println!("\nwritten to {}", folder.display());

    match open_pull_request(
        repo, game, &folder, &scripts, &when, who, batch.len(), dropped, claimed_elsewhere,
        &accounts, &breakdown,
    ) {
        Ok(url) => Some(url),
        Err(why) => {
            eprintln!("\nthe pull request could not be opened: {why}");
            eprintln!("the batch is saved at {} and will be sent next time.", folder.display());
            std::process::exit(1);
        }
    }
}

/// Each pending run's account of itself, as markdown: the folder, then whatever `notes.md` its
/// run wrote about which method ran and for how long.
fn run_accounts(pending: &[PathBuf]) -> String {
    let mut accounts = String::new();

    for folder in pending {
        let name = folder.file_name().unwrap_or_default().to_string_lossy();
        let note = fs::read_to_string(folder.join("notes.md"))
            .unwrap_or_else(|_| "- method: not recorded (an older or interrupted run)\n".to_owned());
        accounts.push_str(&format!("\n### {name}\n{note}"));
    }

    accounts
}

/// The scripts a run wants to contribute, from `contrib/` beside the findings and from a
/// `contrib/` folder inside any run being submitted.
///
/// The rule this enforces is the snowball: a night that invents a way of generating candidates
/// has produced two things, and the names are the less valuable of them. A name goes into a
/// table and is finished. A script makes every later contributor's first hour better, and the
/// evidence that this compounds is in `submissions/` -- the batches that came with a method
/// written down are the ones later batches built on.
///
/// Only text, and only files with something in them: a half-written script is worse than none.
fn contributed_scripts(pending: &[PathBuf]) -> Vec<PathBuf> {
    let mut folders = vec![paths::findings().join(CONTRIBUTED), PathBuf::from(CONTRIBUTED)];
    folders.extend(pending.iter().map(|run| run.join(CONTRIBUTED)));

    let mut found = scripts_in(&folders);

    // And anything new sitting in `scripts/` itself.
    //
    // Told "add your generator to the script library", somebody writes it into `scripts/`, which
    // is the obvious and arguably correct place. Under the folder rule alone that script is then
    // silently not sent -- and silently not sent is exactly how the seven generators named in
    // past submission notes (`attachments.py`, `pathmine.py`, `crosspool.py` and the rest) came
    // to exist nowhere. Being right about where it *should* go must not be the thing that loses
    // it. Untracked only, so the library's own files are not re-sent every time.
    let mut seen: HashSet<String> = found
        .iter()
        .filter_map(|path| Some(path.file_name()?.to_str()?.to_owned()))
        .collect();

    for path in untracked_scripts() {
        let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };

        if seen.insert(name.to_owned()) {
            found.push(path);
        }
    }

    found.sort();
    found
}

/// Where a contributed script lands in the shared library: stamped, like everything beside it.
///
/// Five pull requests once carried five different versions of `slotswap.py` under that one bare
/// name. Four of them merged only because the contributor's branches happened to build on each
/// other; the fifth was an add/add conflict that had to be resolved by hand. That is a bad thing
/// to hand a maintainer -- resolving a conflict inside somebody else's method means reading two
/// versions of a script you did not write and picking one, and picking wrong silently discards
/// the newer work. The submission files never had this problem, because they have carried a
/// `yyyymmdd-hhmmss` stamp from the beginning. The scripts now get the same treatment.
///
/// A script that has not changed keeps the name it already has, rather than gaining a fresh
/// stamped copy every run: the point is to stop collisions, not to accumulate one file per
/// submission. So an evolving generator leaves a readable trail of versions, and a stable one
/// leaves a single file.
fn library_name(name: &str, when: &str, bytes: &[u8]) -> String {
    let (stem, extension) = name.rsplit_once('.').unwrap_or((name, "py"));
    let base = strip_stamp(stem);

    match already_in_library(base, extension, bytes) {
        Some(existing) => existing,
        None => format!("{base}_{when}.{extension}"),
    }
}

/// Whether two files are the same script, ignoring how they reached the disk.
///
/// Not a byte comparison, because on Windows that answers the wrong question. git checks a file
/// out with CRLF while a script a run just wrote has LF, so the identical script differs in every
/// line depending only on its route to the disk. Comparing raw bytes meant the library copy never
/// matched: the first real submission after the stamping went in carried
/// `image_siblings_20260819-232739.py` alongside the byte-for-byte identical
/// `image_siblings_20260819-190013.py` already sitting there, and every run afterwards would have
/// added another. A folder of identical scripts under different stamps is worse than the name
/// collision this was all meant to fix.
fn same_text(left: &[u8], right: &[u8]) -> bool {
    let bare = |bytes: &[u8]| -> Vec<u8> { bytes.iter().copied().filter(|byte| *byte != b'\r').collect() };

    bare(left) == bare(right)
}

/// The scripts the library upstream actually holds, as repository-relative paths with forward
/// slashes.
///
/// `None` when git cannot answer -- outside a checkout, or without git on the path -- and every
/// caller then falls back to trusting the disk, which is what this did before.
///
/// This exists because "the library" and "what is sitting in `scripts/`" are not the same set,
/// and treating them as one lost a generator. A file an agent writes straight into `scripts/`
/// during a run is on the disk and absent from git, so it matched *itself* and was skipped as
/// already present while nothing upstream held it: `materials_from_images.py` was named by pull
/// requests #204 and #205 on 2026-08-20 and carried by neither. Asking git instead of the
/// filesystem makes the check mean what it always said it meant.
fn tracked_scripts() -> Option<&'static HashSet<String>> {
    static TRACKED: OnceLock<Option<HashSet<String>>> = OnceLock::new();

    TRACKED
        .get_or_init(|| {
            // What the *upstream branch* holds, not what this clone has staged.
            //
            // `ls-files` reads the local index, which is a different question and the wrong one
            // twice over. A script committed here but not pushed counts as library and is then
            // skipped, so the pull request names a generator it does not carry. And a contributor
            // grinding continuously never pulls between submissions, so their index cannot show
            // the copy merged five minutes ago -- which is how eighteen submissions in one night
            // re-carried the same five generators and left 125 duplicate copies to sweep up.
            //
            // `origin/HEAD` is a local ref, so this is still no network call; `start` refreshes
            // it. Falling back to `ls-files` when there is no such ref keeps a fresh clone, a
            // detached checkout or an odd remote working exactly as before.
            let upstream = Command::new("git")
                .args(["ls-tree", "-r", "--name-only", "origin/HEAD", "--", "scripts"])
                .current_dir(paths::root())
                .stderr(Stdio::null())
                .output()
                .ok();

            let output = match upstream {
                Some(done) if done.status.success() && !done.stdout.is_empty() => done,
                _ => Command::new("git")
                    .args(["ls-files", "--", "scripts"])
                    .current_dir(paths::root())
                    .stderr(Stdio::null())
                    .output()
                    .ok()?,
            };

            if !output.status.success() {
                return None;
            }

            let listing = String::from_utf8_lossy(&output.stdout);
            let paths: HashSet<String> = listing
                .lines()
                .map(|line| line.trim().replace('\\', "/"))
                .filter(|line| !line.is_empty())
                .collect();

            // An empty answer is a real one only if git succeeded and the repository genuinely
            // holds no scripts. Treating it as "nothing is tracked" would skip every match and
            // re-send the whole library, so it is refused rather than trusted.
            if paths.is_empty() {
                None
            } else {
                Some(paths)
            }
        })
        .as_ref()
}

/// Whether git tracks this file, given the listing. Unknown listing means yes: the fallback is
/// the old disk-only behaviour, which is wrong only in the narrow case above and must not start
/// refusing to recognise a library that is genuinely there.
fn is_tracked(path: &Path, tracked: Option<&HashSet<String>>) -> bool {
    let Some(tracked) = tracked else {
        return true;
    };

    let Ok(relative) = path.strip_prefix(paths::root()) else {
        return true;
    };

    tracked.contains(&relative.to_string_lossy().replace('\\', "/"))
}

/// The library's own copy of this script, under whatever stamp it carries.
///
/// Best effort: the library is only as current as the clone, and `start` refreshes that. Missing
/// a match costs one redundant file, which is why this is allowed to give up quietly. Claiming a
/// match that is not one would overwrite somebody's version, so the comparison is deliberately
/// narrow: the same base name, the same extension, and the same text bar line endings.
fn already_in_library(base: &str, extension: &str, bytes: &[u8]) -> Option<String> {
    // Both halves of the library. A generator that earned its place is moved into `scripts/`
    // proper and listed in `scripts/README.md`; `scripts/contributed/` is where a submission
    // files one on arrival. Checking only the second meant a script promoted to the first was
    // re-sent by every run afterwards, under a fresh stamp each time -- so an overnight grind
    // would have left a folder full of dated copies of a file already sitting one level up.
    let root = paths::root().join("scripts");

    let tracked = tracked_scripts();

    for folder in [root.join("contributed"), root] {
        if let Some(found) = matching_in(&folder, base, extension, bytes, tracked) {
            return Some(found);
        }
    }

    None
}

/// The one file in this folder that is this script, byte for byte bar line endings.
fn matching_in(
    folder: &Path,
    base: &str,
    extension: &str,
    bytes: &[u8],
    tracked: Option<&HashSet<String>>,
) -> Option<String> {
    for entry in fs::read_dir(folder).ok()?.flatten() {
        let path = entry.path();

        // On the disk but not in git is not in the library -- see `tracked_scripts`.
        if !is_tracked(&path, tracked) {
            continue;
        }

        let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        let Some((stem, ending)) = name.rsplit_once('.') else {
            continue;
        };

        if ending != extension || strip_stamp(stem) != base {
            continue;
        }

        if fs::read(&path).is_ok_and(|held| same_text(&held, bytes)) {
            return Some(name.to_owned());
        }
    }

    None
}

/// How many names of each asset type, as markdown list items.
///
/// A batch's total says how big it is and nothing about what it is. 2,000 images and one model is
/// a different submission from an even spread across the five types, and only this says which --
/// otherwise a reviewer has to open every file in the folder and count its lines, which is what
/// this replaces.
///
/// Ordered by count, largest first, because the question being asked is almost always "what is
/// this batch mostly?".
fn per_type(batch: &[(String, u64, String)]) -> String {
    let mut counts: Vec<(String, usize)> = {
        let mut seen: std::collections::HashMap<&str, usize> = std::collections::HashMap::new();
        for (kind, _, _) in batch {
            *seen.entry(kind.as_str()).or_insert(0) += 1;
        }
        seen.into_iter().map(|(kind, count)| (kind.to_owned(), count)).collect()
    };

    // Largest first, then alphabetically so two types of equal size do not swap places between
    // runs -- a diff that changes for no reason is a diff nobody reads.
    counts.sort_by(|left, right| right.1.cmp(&left.1).then(left.0.cmp(&right.0)));

    counts
        .iter()
        .map(|(kind, count)| format!("- {kind}: {count}\n"))
        .collect()
}

/// Which engine confirmed the runs in this batch, read back from each run's own notes.
///
/// Written per run rather than assumed here, because a batch can mix them: a night that starts on
/// the GPU and falls back to the CPU when a driver complains is a normal outcome, not an error,
/// and the submission should say so rather than pick one.
///
/// The point is traceability. If a GPU backend is ever found to have a fault, the batches it
/// produced can be identified and re-checked rather than guessed at — and provenance is cheap to
/// write now and impossible to reconstruct afterwards.
fn platforms_used(runs: &[PathBuf]) -> String {
    field_across(runs, "- platform: ", "not recorded (run predates this field)")
}

/// One field, read out of every run's notes, distinct values in the order first seen.
fn field_across(runs: &[PathBuf], prefix: &str, missing: &str) -> String {
    let mut seen: Vec<String> = Vec::new();

    for run in runs {
        let Ok(notes) = fs::read_to_string(run.join("notes.md")) else {
            continue;
        };

        for line in notes.lines() {
            if let Some(value) = line.strip_prefix(prefix) {
                let value = value.trim().to_owned();
                if !value.is_empty() && !seen.contains(&value) {
                    seen.push(value);
                }
            }
        }
    }

    if seen.is_empty() {
        return missing.to_owned();
    }

    seen.join(", ")
}

fn backends_used(runs: &[PathBuf]) -> String {
    let mut seen: Vec<String> = Vec::new();

    for run in runs {
        let Ok(notes) = fs::read_to_string(run.join("notes.md")) else {
            continue;
        };

        for line in notes.lines() {
            if let Some(value) = line.strip_prefix("- confirmed on: ") {
                let value = value.trim().to_owned();
                if !value.is_empty() && !seen.contains(&value) {
                    seen.push(value);
                }
            }
        }
    }

    // A run folder written before this field existed says nothing, and answering "CPU" for it
    // would be a guess dressed as a fact.
    if seen.is_empty() {
        return "not recorded (run predates this field)".to_owned();
    }

    seen.join(", ")
}

/// Files in `scripts/` that git does not know about yet: somebody's new generator.
///
/// Asked of git rather than judged by timestamps, because "new" here means "not part of the
/// library yet", which is a question only git can answer.
fn untracked_scripts() -> Vec<PathBuf> {
    let Ok(output) = std::process::Command::new("git")
        .args(["status", "--porcelain", "--untracked-files=all", "--", "scripts"])
        .stderr(Stdio::null())
        .output()
    else {
        return Vec::new();
    };

    let mut found = Vec::new();

    for line in String::from_utf8_lossy(&output.stdout).lines() {
        let Some(path) = line.strip_prefix("?? ") else {
            continue;
        };

        let path = PathBuf::from(path.trim().trim_matches('"'));

        let sensible = matches!(
            path.extension().and_then(|extension| extension.to_str()),
            Some("py" | "rs" | "sh" | "ps1")
        );

        let has_content = path.metadata().map(|data| data.len() > 0).unwrap_or(false);

        if sensible && has_content {
            found.push(path);
        }
    }

    found
}

/// The contributable files in a set of folders, first spelling of a name winning.
fn scripts_in(folders: &[PathBuf]) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();

    for folder in folders {
        let Ok(entries) = fs::read_dir(&folder) else {
            continue;
        };

        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }

            let sensible = matches!(
                path.extension().and_then(|extension| extension.to_str()),
                Some("py" | "rs" | "sh" | "ps1" | "md" | "txt" | "toml" | "json")
            );

            let has_content = entry.metadata().map(|data| data.len() > 0).unwrap_or(false);

            let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
                continue;
            };

            if sensible && has_content && seen.insert(name.to_owned()) {
                found.push(path);
            }
        }
    }

    found.sort();
    found
}

/// Every `run_*` folder in a findings tree, at any depth.
/// Findings that exist on disk but belong to no run folder, gathered into one so they can be sent.
///
/// **This recovers work that was silently unsubmittable.** A pass checkpoints its names into the
/// aggregate `findings/<game>/<type>.txt` every sixty seconds, but wrote its *run folder* only on
/// finishing -- and `submit` sends run folders. So a pass killed part way through (a usage limit,
/// a closed laptop, a crash) left every name it had found on disk in a shape nothing would ever
/// send, and said nothing: the next `submit` reported "nothing new to submit" and looked like
/// success. Contributors running on constrained assistants hit this hardest, which is exactly the
/// group least able to notice it.
///
/// `write_run_as` stops it happening again. This picks up what is already stranded.
///
/// Being over-eager here is safe. Anything already published, merged or claimed is dropped before
/// sending, so the worst case of counting a name stranded when it is not is a batch that comes to
/// nothing -- against a best case of recovering somebody's whole session.
fn recover_stranded(findings: &Path, outbox: &Path) -> Vec<PathBuf> {
    // Keyed on game, type and name, not on the name alone.
    //
    // A bare name set collapses both titles into one. Measured on this clone: 1,653 names appear
    // in both games' findings, so a name sitting in a Cold War run folder marked the identical
    // Black Ops 4 name as accounted for -- and a Black Ops 4 pass that was killed then had that
    // name skipped by the recovery written to save it. The same collapse happened across types,
    // a name filed under `image` shadowing the identical string stranded under `material`.
    let mut accounted: HashSet<(String, String, String)> = HashSet::new();

    let remember = |game: &str, kind: &str, name: &str, set: &mut HashSet<_>| {
        set.insert((game.to_owned(), kind.to_lowercase(), name.to_lowercase()));
    };

    // Every run folder, *including* superseded ones. `run_folders` skips those deliberately --
    // they are organised-away results and must not be sent again -- but skipping them here left
    // their names looking stranded, so every `submit` rebuilt a recovery folder holding them and
    // re-offered names that had already gone. They died at the exclusion step, so it was churn
    // rather than loss: dozens of pointless folders across an overnight rotation.
    for folder in every_run_folder(findings) {
        let game = game_under(findings, &folder);
        for (kind, _, name) in names_in(&folder) {
            remember(&game, &kind, &name, &mut accounted);
        }
    }

    for folder in fs::read_dir(outbox).into_iter().flatten().flatten() {
        let folder = folder.path();
        // `submissions/<who>_<GAME>_<stamp>/`, which is where the game is.
        let game = folder
            .file_name()
            .and_then(|name| name.to_str())
            .and_then(|name| name.split('_').nth(1))
            .unwrap_or_default()
            .to_uppercase();

        for (kind, _, name) in names_in(&folder) {
            // A submission names its files `<kind>_<stamp>.txt`.
            let kind = strip_stamp(&kind).to_owned();
            remember(&game, &kind, &name, &mut accounted);
        }
    }

    let mut recovered = Vec::new();

    for game in fs::read_dir(findings).into_iter().flatten().flatten() {
        let folder = game.path();
        if !folder.is_dir() {
            continue;
        }

        // The aggregate files sit directly in the game folder; run folders are below it.
        let game = game_under(findings, &folder);

        let mut stranded: Vec<(String, u64, String)> = Vec::new();
        for (kind, id, name) in names_in(&folder) {
            let key = (game.clone(), kind.to_lowercase(), name.to_lowercase());
            if !accounted.contains(&key) {
                stranded.push((kind, id, name));
            }
        }

        if stranded.is_empty() {
            continue;
        }

        let into = folder.join(format!("run_{}_recovered", stamp()));
        if fs::create_dir_all(&into).is_err() {
            continue;
        }

        let mut by_kind: std::collections::BTreeMap<String, Vec<(u64, String)>> = Default::default();
        for (kind, id, name) in stranded {
            by_kind.entry(kind).or_default().push((id, name));
        }

        let mut wrote = 0;
        for (kind, mut rows) in by_kind {
            rows.sort_by(|a, b| a.1.to_lowercase().cmp(&b.1.to_lowercase()));
            let text: String =
                rows.iter().map(|(id, name)| format!("{id:x},{name}
")).collect();
            if fs::write(into.join(format!("{kind}.txt")), text).is_ok() {
                wrote += rows.len();
            }
        }

        if wrote == 0 {
            let _ = fs::remove_dir_all(&into);
            continue;
        }

        println!(
            "  recovered {wrote} name(s) that belonged to no run folder -- from a pass that was              interrupted before it could write one"
        );
        recovered.push(into);
    }

    recovered
}

/// Which game a path under a findings tree belongs to: the first component below the root.
///
/// Taken relative to the tree being walked rather than through `paths::game_of`, which strips
/// the *installed* findings root. That is the same answer in a real run and the wrong one
/// anywhere else -- including under test, where every folder would come back with no game at all
/// and the two titles would collapse into one set again, which is the bug this is here to stop.
fn game_under(findings: &Path, path: &Path) -> String {
    path.strip_prefix(findings)
        .ok()
        .and_then(|rest| rest.components().next())
        .map(|first| first.as_os_str().to_string_lossy().to_uppercase())
        .unwrap_or_default()
}

/// Every `run_*` folder, superseded ones included, for deciding what is *accounted for*.
///
/// `run_folders` is the list of runs to consider sending and rightly leaves `superseded/` out.
/// This is the other question -- has this name already been written down anywhere -- and there
/// the answer for a superseded run is yes.
fn every_run_folder(findings: &Path) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(findings) else {
        return found;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        if entry.file_name().to_string_lossy().starts_with("run_") {
            found.push(path);
        } else {
            found.extend(every_run_folder(&path));
        }
    }

    found
}

fn run_folders(findings: &Path) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(findings) else {
        return found;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with("run_") {
            // A run still being written is not a run to send. Sending one ledgers its folder
            // name, and every name the pass finds afterwards then has no route: `already_sent`
            // skips the folder for ever, and `recover_stranded` will not strand a name that
            // sits inside a run folder. Skipping it here closes both, and loses nothing if the
            // pass is abandoned -- the folder is left out of `accounted` too, so its names come
            // back as stranded and are recovered.
            if slasher::Results::run_unfinished(&path) {
                continue;
            }

            found.push(path);
        } else if name != "superseded" {
            found.extend(run_folders(&path));
        }
    }

    found.sort();
    found
}

/// The `(type, name)` pairs in one run folder.
/// The `(type, id, name)` triples in one run folder.
///
/// **The id is read, never recomputed.** A run records the id it actually matched, and that is
/// the only thing that knows which normalisation produced it. Recomputing from the name assumes
/// backslashes fold -- true for every pool but one. Black Ops 4's SAB sound names keep theirs, so
/// `wave_crash_01.ln100.pc.snd` under a folding hash gives `43802e73bbb1bef9` where the game
/// actually holds `100116a5a23b8100`. Every sound name from that game would have been submitted
/// against a key belonging to nothing.
fn names_in(folder: &Path) -> Vec<(String, u64, String)> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(folder) else {
        return found;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("txt") {
            continue;
        }

        let Some(kind) = path.file_stem().and_then(|s| s.to_str()) else {
            continue;
        };

        let Ok(bytes) = fs::read(&path) else { continue };
        for line in String::from_utf8_lossy(&bytes).lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            let (id, name) = match line.split_once(',') {
                Some((key, name)) => match u64::from_str_radix(key.trim(), 16) {
                    Ok(id) => (id & ID_MASK, name.trim()),
                    Err(_) => continue,
                },
                None => continue,
            };

            if !name.is_empty() {
                found.push((kind.to_owned(), id, name.to_owned()));
            }
        }
    }

    found
}

/// Every hash the tables resolve: the stored key, and the hash of the stored name.
fn known_hashes(folder: &Path) -> HashSet<u64> {
    let mut known = HashSet::new();
    let Ok(entries) = fs::read_dir(folder) else {
        return known;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("csv") {
            continue;
        }

        let Ok(bytes) = fs::read(&path) else { continue };
        for line in String::from_utf8_lossy(&bytes).lines() {
            let Some((key, name)) = line.split_once(',') else {
                continue;
            };

            if let Ok(value) = u64::from_str_radix(key.trim(), 16) {
                known.insert(value);
                known.insert(value & ID_MASK);
            }

            let hash = hash64(name.trim());
            known.insert(hash);
            known.insert(hash & ID_MASK);
        }
    }

    known
}

fn already_sent(outbox: &Path) -> HashSet<String> {
    fs::read_to_string(outbox.join(LEDGER))
        .unwrap_or_default()
        .lines()
        .map(|line| line.trim().to_owned())
        .filter(|line| !line.is_empty())
        .collect()
}

/// Notes the runs as sent. Appended, never rewritten, so a crash cannot lose the record and cause
/// the same names to be submitted twice.
fn record(outbox: &Path, sent: &[PathBuf]) {
    let _ = fs::create_dir_all(outbox);

    let mut text = fs::read_to_string(outbox.join(LEDGER)).unwrap_or_default();
    for folder in sent {
        let name = folder.file_name().unwrap_or_default().to_string_lossy();
        text.push_str(&format!("{name}\n"));
    }

    let _ = fs::write(outbox.join(LEDGER), text);
}

fn github_user() -> Option<String> {
    let output = github::command()
        .args(["api", "user", "--jq", ".login"])
        .stderr(Stdio::null())
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let who = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if who.is_empty() {
        None
    } else {
        Some(who)
    }
}
/// Sends the batch and opens the pull request, doing the whole of git on the contributor's behalf.
///
/// The point of this program is that somebody who has never used git can contribute, so none of
/// the usual sequence is asked of them. There is no clone, no working copy and no `git` on the
/// machine: the branch is built through GitHub's own API out of the files just written, which
/// means the submissions folder can live anywhere and need not be a repository at all.
///
/// It is one commit rather than one per file, so a run that dies halfway leaves the fork exactly
/// as it was rather than a branch holding half a batch.
fn open_pull_request(
    repo: &str,
    game: &str,
    folder: &Path,
    scripts: &[PathBuf],
    when: &str,
    who: &str,
    names: usize,
    dropped: usize,
    claimed: usize,
    accounts: &str,
    breakdown: &str,
) -> Result<String, String> {
    let branch = format!("findings/{who}-{game}-{when}");
    let base = default_branch(repo)?;

    // Push into a fork, unless this is the maintainer submitting to their own repository, where
    // there is nothing to fork and the branch simply goes straight in.
    let fork = if repo.starts_with(&format!("{who}/")) {
        repo.to_owned()
    } else {
        ensure_fork(repo, who)?
    };

    // A fork that has sat unused for a week is behind. Branching from a stale head still produces
    // a correct pull request, because the diff is taken against the merge base, so this is done
    // for tidiness and its failure is not worth stopping for.
    if fork != repo {
        let _ = gh(&["repo", "sync", &fork, "--source", repo], None);
    }

    let parent = head_sha(&fork, &base)?;
    let base_tree = tree_of(&fork, &parent)?;

    // The files, as they will appear in the repository. One folder per submission, named for who
    // sent it and when, so two people submitting at once cannot collide.
    let mut entries = Vec::new();
    for file in files_in(folder) {
        let Some(name) = file.file_name().and_then(|n| n.to_str()) else {
            continue;
        };

        let bytes = fs::read(&file).map_err(|error| format!("could not read {name}: {error}"))?;
        let blob = make_blob(&fork, &bytes)?;
        entries.push((format!("submissions/{who}_{game}_{when}/{name}"), blob));
    }

    // Scripts go to the shared library rather than into the submission folder, because a method
    // nobody can find is a method nobody inherits. Each is stamped like the submission files
    // beside it -- see `library_name`.
    let mut landed: Vec<String> = Vec::new();

    for script in scripts {
        let Some(name) = script.file_name().and_then(|name| name.to_str()) else {
            continue;
        };

        let bytes = fs::read(script).map_err(|error| format!("could not read {name}: {error}"))?;

        // Already in the library, byte for byte bar line endings: send nothing at all.
        //
        // Reusing the name was not enough. The blob still went up, and since git checks the
        // library copy out with CRLF while the copy being sent has LF, the pull request rewrote
        // every line of a file whose content had not changed -- 95 insertions and 95 deletions on
        // a no-op. Two pull requests carried that before anybody looked.
        let (stem, extension) = name.rsplit_once('.').unwrap_or((name, "py"));
        if let Some(existing) = already_in_library(strip_stamp(stem), extension, &bytes) {
            println!("  {name} is already in the library as {existing}; not sending it again");
            landed.push(existing);
            continue;
        }

        let target = library_name(name, &when, &bytes);
        let blob = make_blob(&fork, &bytes)?;
        entries.push((format!("scripts/contributed/{target}"), blob));
        landed.push(target);
    }

    if entries.is_empty() {
        return Err("the batch folder held no files to send".to_owned());
    }

    // The game leads the title. It is the first thing a reviewer needs, and a list of pull
    // requests cannot otherwise show which title a submission is for -- which matters now that
    // both games are ground rather than only whichever one the config happened to default to.
    let title = format!("[{game}] findings from {who}, {when} ({names} names)");
    let tree = make_tree(&fork, &base_tree, &entries)?;
    let commit = make_commit(&fork, &title, &tree, &parent)?;
    make_branch(&fork, &branch, &commit)?;

    let contributed = if landed.is_empty() {
        String::new()
    } else {
        let listed: Vec<String> = landed
            .iter()
            .map(|name| format!("- `scripts/contributed/{name}`"))
            .collect();

        format!(
            "\n\n## Tooling this run leaves behind\n\n{}\n\nThese are the scripts that produced \
             the names above. They are here so the next contributor inherits the method rather \
             than only its output.",
            listed.join("\n")
        )
    };

    let body = format!(
        "**{game}** — {names} asset names, confirmed against that game's own loaded assets.\n\n\
{breakdown}\n\
         **Checked against, at the moment of sending:** the community hash tables (refreshed \
         first), every merged submission in this repository, and every pull request open right \
         now. A name any of those already holds was dropped rather than sent.\n\n\
         - dropped as already published: {dropped}\n\
         - dropped as already claimed by a merged or open submission: {claimed}\n\
         - submitted by: @{who}\n\n\
         Files are named with the time they were sent, so nothing collides with an earlier batch. \
         Every hash here is re-verified against the shipped snapshot by CI; nothing is taken on \
         the word of the client that found it.\n\n\
         ## How these were found\n{accounts}{contributed}",
    );

    // `who:branch` is how GitHub names a branch that lives in somebody else's fork.
    let head = if fork == repo { branch.clone() } else { format!("{who}:{branch}") };

    gh(
        &[
            "api",
            &format!("repos/{repo}/pulls"),
            "-X",
            "POST",
            "-f",
            &format!("title={title}"),
            "-f",
            &format!("head={head}"),
            "-f",
            &format!("base={base}"),
            "-f",
            &format!("body={body}"),
            "--jq",
            ".html_url",
        ],
        None,
    )
}

/// Every file directly inside the batch folder, in a settled order.
fn files_in(folder: &Path) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = fs::read_dir(folder)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.is_file())
        .collect();

    found.sort();
    found
}

/// The branch a pull request should be opened against, asked of the repository rather than assumed
/// to be `main` -- upstream has been called `master` for years in this corner of the world.
fn default_branch(repo: &str) -> Result<String, String> {
    gh(&["api", &format!("repos/{repo}"), "--jq", ".default_branch"], None)
}

/// The contributor's fork, made if they have not got one.
///
/// Forking is asynchronous: GitHub answers before the repository exists, so the fork is waited for
/// rather than used immediately. Somebody who already has a fork skips the wait entirely.
fn ensure_fork(repo: &str, who: &str) -> Result<String, String> {
    let name = repo.split('/').next_back().unwrap_or(repo);
    let fork = format!("{who}/{name}");

    if gh(&["api", &format!("repos/{fork}"), "--jq", ".name"], None).is_ok() {
        return Ok(fork);
    }

    println!("making your fork of {repo}");
    gh(&["repo", "fork", repo, "--clone=false"], None)
        .map_err(|why| format!("could not fork {repo}: {why}"))?;

    for _ in 0..30 {
        if gh(&["api", &format!("repos/{fork}"), "--jq", ".name"], None).is_ok() {
            return Ok(fork);
        }
        std::thread::sleep(std::time::Duration::from_secs(1));
    }

    Err(format!("{fork} was asked for but has not appeared after thirty seconds"))
}

fn head_sha(repo: &str, branch: &str) -> Result<String, String> {
    gh(
        &["api", &format!("repos/{repo}/git/ref/heads/{branch}"), "--jq", ".object.sha"],
        None,
    )
}

fn tree_of(repo: &str, commit: &str) -> Result<String, String> {
    gh(&["api", &format!("repos/{repo}/git/commits/{commit}"), "--jq", ".tree.sha"], None)
}

/// Uploads one file's bytes. Base64 rather than plain text, so a name holding something that is
/// not valid utf-8 is carried exactly rather than mangled on the way.
fn make_blob(repo: &str, bytes: &[u8]) -> Result<String, String> {
    let body = format!("{{\"content\":\"{}\",\"encoding\":\"base64\"}}", base64(bytes));
    gh(&["api", &format!("repos/{repo}/git/blobs"), "--input", "-", "--jq", ".sha"], Some(&body))
}

/// Lays the new files on top of the branch as it already stands. Without `base_tree` this would
/// describe a repository holding nothing but the submission.
fn make_tree(repo: &str, base_tree: &str, entries: &[(String, String)]) -> Result<String, String> {
    let files: Vec<String> = entries
        .iter()
        .map(|(path, blob)| {
            format!(
                "{{\"path\":{},\"mode\":\"100644\",\"type\":\"blob\",\"sha\":{}}}",
                quoted(path),
                quoted(blob)
            )
        })
        .collect();

    let body = format!(
        "{{\"base_tree\":{},\"tree\":[{}]}}",
        quoted(base_tree),
        files.join(",")
    );

    gh(&["api", &format!("repos/{repo}/git/trees"), "--input", "-", "--jq", ".sha"], Some(&body))
}

fn make_commit(repo: &str, message: &str, tree: &str, parent: &str) -> Result<String, String> {
    let body = format!(
        "{{\"message\":{},\"tree\":{},\"parents\":[{}]}}",
        quoted(message),
        quoted(tree),
        quoted(parent)
    );

    gh(&["api", &format!("repos/{repo}/git/commits"), "--input", "-", "--jq", ".sha"], Some(&body))
}

fn make_branch(repo: &str, branch: &str, commit: &str) -> Result<String, String> {
    gh(
        &[
            "api",
            &format!("repos/{repo}/git/refs"),
            "-X",
            "POST",
            "-f",
            &format!("ref=refs/heads/{branch}"),
            "-f",
            &format!("sha={commit}"),
            "--jq",
            ".ref",
        ],
        None,
    )
}

/// Runs `gh`, which already knows who the contributor is, and returns what it said.
///
/// Failures carry gh's own words rather than an exit code, because the useful part of a refused
/// request is the sentence GitHub sent back with it.
fn gh(args: &[&str], body: Option<&str>) -> Result<String, String> {
    let mut command = github::command();
    command.args(args).stdout(Stdio::piped()).stderr(Stdio::piped());

    if body.is_some() {
        command.stdin(Stdio::piped());
    }

    let mut child = command.spawn().map_err(|error| format!("gh could not be run: {error}"))?;

    if let Some(text) = body {
        use std::io::Write;
        let mut stdin = child.stdin.take().ok_or("gh would not take the request body")?;
        stdin
            .write_all(text.as_bytes())
            .map_err(|error| format!("the request body could not be sent to gh: {error}"))?;
    }

    let output = child.wait_with_output().map_err(|error| format!("gh did not finish: {error}"))?;

    if !output.status.success() {
        let said = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stderr),
            String::from_utf8_lossy(&output.stdout)
        );

        return Err(said.trim().to_owned());
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

/// A json string, escaped. Only the handful of things json insists on, since everything here is a
/// path, a sha or a message this program wrote itself.
fn quoted(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');

    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }

    out.push('"');
    out
}

/// Base64, written out rather than depended on: a build with no features has no dependencies at
/// all, and that is the property that lets this be published in the first place.
fn base64(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);

    for chunk in bytes.chunks(3) {
        let a = chunk[0] as u32;
        let b = *chunk.get(1).unwrap_or(&0) as u32;
        let c = *chunk.get(2).unwrap_or(&0) as u32;
        let triple = (a << 16) | (b << 8) | c;

        out.push(ALPHABET[(triple >> 18) as usize & 63] as char);
        out.push(ALPHABET[(triple >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 { ALPHABET[(triple >> 6) as usize & 63] as char } else { '=' });
        out.push(if chunk.len() > 2 { ALPHABET[triple as usize & 63] as char } else { '=' });
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A pass killed before it wrote its run folder is recovered, and one that was not is left be.
    ///
    /// This is the failure it guards: names checkpointed into the aggregate file every sixty
    /// seconds, no run folder because the pass never finished, and `submit` sending only run
    /// folders -- so the work existed on disk and could never be sent, silently.
    #[test]
    /// The same name in both games is two names, and one being safe does not save the other.
    ///
    /// `accounted` used to be a set of bare lowercase names, so a name sitting in a Cold War run
    /// folder marked the identical Black Ops 4 name as accounted for. Measured on this clone:
    /// 1,653 names appear in both games' findings, so a killed Black Ops 4 pass could have any of
    /// them silently skipped by the recovery written to save it.
    #[test]
    fn a_name_in_one_game_does_not_account_for_the_other() {
        let root = std::env::temp_dir().join(format!("crossgame_{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);

        let findings = root.join("findings");
        let cw = findings.join("blkopscw");
        let bo4 = findings.join("blkops04");
        let outbox = root.join("submissions");
        fs::create_dir_all(cw.join("run_20260820-010101_all")).unwrap();
        fs::create_dir_all(&bo4).unwrap();
        fs::create_dir_all(&outbox).unwrap();

        // Cold War holds this name in a run folder, so Cold War's copy is accounted for.
        fs::write(cw.join("xmodel.txt"), "1111111111111111,shared_between_games\n").unwrap();
        fs::write(
            cw.join("run_20260820-010101_all").join("xmodel.txt"),
            "1111111111111111,shared_between_games\n",
        )
        .unwrap();

        // Black Ops 4 holds the same name, stranded by a kill, in no run folder at all.
        fs::write(bo4.join("xmodel.txt"), "1111111111111111,shared_between_games\n").unwrap();

        let recovered = recover_stranded(&findings, &outbox);

        let where_to: Vec<String> = recovered.iter().map(|p| p.display().to_string()).collect();

        assert!(
            recovered.iter().any(|path| path.starts_with(&bo4)),
            "the Black Ops 4 copy was treated as accounted for because Cold War held the same \
             name, so a killed pass loses it with nothing said. recovered: {where_to:?}"
        );
        assert!(
            !recovered.iter().any(|path| path.starts_with(&cw)),
            "Cold War's copy sits in a run folder and should not have been recovered. \
             recovered: {where_to:?}"
        );
    }

    /// A superseded run still accounts for its names, so they are not recovered again and again.
    ///
    /// `run_folders` skips `superseded/` on purpose -- those results were organised away and must
    /// not be sent twice. Asking the *other* question with the same walk left their names looking
    /// stranded, so every `submit` built a fresh recovery folder holding names that had already
    /// gone. They died at the exclusion step, so it was churn rather than loss, but an overnight
    /// rotation submits after every job and that is dozens of folders for nothing.
    #[test]
    fn a_superseded_run_still_accounts_for_its_names() {
        let root = std::env::temp_dir().join(format!("superseded_{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);

        let findings = root.join("findings");
        let game = findings.join("blkops04");
        let outbox = root.join("submissions");
        fs::create_dir_all(game.join("superseded").join("run_20260819-010101_all")).unwrap();
        fs::create_dir_all(&outbox).unwrap();

        fs::write(game.join("xmodel.txt"), "3333333333333333,filed_away_earlier\n").unwrap();
        fs::write(
            game.join("superseded")
                .join("run_20260819-010101_all")
                .join("xmodel.txt"),
            "3333333333333333,filed_away_earlier\n",
        )
        .unwrap();

        let recovered = recover_stranded(&findings, &outbox);

        assert!(
            recovered.is_empty(),
            "a name held by a superseded run was recovered again, which every submit would repeat"
        );
    }

    fn a_killed_run_is_recovered_from_the_aggregate_files() {
        let root = std::env::temp_dir().join(format!("stranded_{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);

        let findings = root.join("findings");
        let game = findings.join("blkops04");
        let outbox = root.join("submissions");
        fs::create_dir_all(game.join("run_20260820-010101_all")).unwrap();
        fs::create_dir_all(&outbox).unwrap();

        // Two names in the aggregate. One belongs to a run folder; the other is stranded.
        fs::write(
            game.join("xmodel.txt"),
            "1111111111111111,already_in_a_run
2222222222222222,stranded_by_a_kill
",
        )
        .unwrap();
        fs::write(
            game.join("run_20260820-010101_all").join("xmodel.txt"),
            "1111111111111111,already_in_a_run
",
        )
        .unwrap();

        let recovered = recover_stranded(&findings, &outbox);
        assert_eq!(recovered.len(), 1, "the stranded name was not recovered");

        let rows = names_in(&recovered[0]);
        assert_eq!(rows.len(), 1, "recovered the wrong number of names");
        assert_eq!(rows[0].0, "xmodel", "recovered under the wrong asset type");
        assert_eq!(rows[0].2, "stranded_by_a_kill");

        // And it must not recover the same thing twice: the folder it just wrote now accounts
        // for the name, so a second call finds nothing.
        assert!(
            recover_stranded(&findings, &outbox).is_empty(),
            "recovering twice would submit the same names again"
        );

        let _ = fs::remove_dir_all(&root);
    }

    /// The rfc's own examples, plus the two lengths that need padding. A wrong encoder here would
    /// upload a corrupted file that still looked like a successful submission.
    #[test]
    fn base64_matches_the_rfc() {
        for (plain, encoded) in [
            ("", ""),
            ("f", "Zg=="),
            ("fo", "Zm8="),
            ("foo", "Zm9v"),
            ("foob", "Zm9vYg=="),
            ("fooba", "Zm9vYmE="),
            ("foobar", "Zm9vYmFy"),
        ] {
            assert_eq!(base64(plain.as_bytes()), encoded, "encoding {plain:?}");
        }
    }

    /// Bytes above the ascii range go through untouched, which is the reason for encoding the
    /// files at all rather than sending them as text.
    #[test]
    fn base64_carries_bytes_that_are_not_text() {
        assert_eq!(base64(&[0xff, 0xfe, 0xfd]), "//79");
        assert_eq!(base64(&[0x00]), "AA==");
    }

    /// The per-type breakdown: what it says, and that its order is stable.
    ///
    /// Stability matters more than it looks. These lines go into a file that is committed, so an
    /// order that varied between runs would produce a diff that changed for no reason -- and a
    /// diff that changes for no reason is one nobody reads.
    #[test]
    fn the_breakdown_counts_each_type_largest_first() {
        let row = |kind: &str, name: &str| (kind.to_owned(), 0u64, name.to_owned());

        let batch = vec![
            row("image", "a"),
            row("xmodel", "b"),
            row("image", "c"),
            row("image", "d"),
            row("sound_alias", "e"),
            row("xmodel", "f"),
        ];

        assert_eq!(per_type(&batch), "- image: 3\n- xmodel: 2\n- sound_alias: 1\n");

        // Equal counts fall back to alphabetical, so two types of the same size cannot swap
        // places between runs.
        let tie = vec![row("xmodel", "a"), row("image", "b")];
        assert_eq!(per_type(&tie), "- image: 1\n- xmodel: 1\n");

        assert_eq!(per_type(&[]), "");
    }

    /// A contributed script is stamped, and re-stamping never compounds.
    ///
    /// The compounding case is the one worth pinning: a contributor pulls the library, edits
    /// `slotswap_20260819-225818.py` and submits it. Naively appending would give
    /// `slotswap_20260819-225818_20260820-0130.py`, and the run after that would add a third.
    /// The stamp is replaced, not accumulated, so the base name stays readable for ever.
    #[test]
    fn contributed_scripts_are_stamped_once() {
        let when = "20260820-013000";

        assert_eq!(library_name("slotswap.py", when, b"x"), "slotswap_20260820-013000.py");
        assert_eq!(
            library_name("slotswap_20260819-225818.py", when, b"x"),
            "slotswap_20260820-013000.py",
            "an already-stamped script must not gain a second stamp"
        );

        // A name with underscores of its own keeps them: only the stamp comes off.
        assert_eq!(
            library_name("image_siblings.py", when, b"x"),
            "image_siblings_20260820-013000.py"
        );

        // Extensionless, and non-python, both survive.
        assert_eq!(library_name("gen", when, b"x"), "gen_20260820-013000.py");
        assert_eq!(library_name("gen.sh", when, b"x"), "gen_20260820-013000.sh");
    }

    /// A file on the disk but absent from git is not the library.
    ///
    /// The case this pins cost a generator. `already_in_library` read `scripts/` off the
    /// filesystem, so a script written straight into that folder during a run matched *itself*
    /// and was skipped as already present -- while nothing upstream held it.
    /// `materials_from_images.py` was named by pull requests #204 and #205 on 2026-08-20 and
    /// carried by neither.
    ///
    /// Goes through the real folder for the same reason the test below does: the stamping had a
    /// passing unit test over a fixture and still shipped a live bug.
    ///
    /// Skips rather than fails where git cannot answer, since `tracked_scripts` then falls back
    /// to trusting the disk and there is no invariant left to assert.
    #[test]
    fn a_script_the_repository_does_not_track_is_not_the_library() {
        if tracked_scripts().is_none() {
            return;
        }

        let folder = paths::root().join("scripts");
        if !folder.is_dir() {
            return;
        }

        // Distinctive enough that it cannot collide with a real generator, and removed either
        // way below.
        let name = "zz_untracked_library_probe.py";
        let path = folder.join(name);
        let body = b"# written by a test, never committed\n";

        if path.exists() {
            return;
        }
        if fs::write(&path, body).is_err() {
            return;
        }

        let picked = library_name(name, "20260820-013000", body);
        let _ = fs::remove_file(&path);

        assert_eq!(
            picked, "zz_untracked_library_probe_20260820-013000.py",
            "an untracked file in scripts/ was treated as the library, so a new generator would \
             be silently dropped from the pull request"
        );
    }

    /// A script already in the library is recognised, against the library that actually exists.
    ///
    /// `same_text` on its own only proves the comparison; this proves the lookup around it --
    /// that `strip_stamp` recovers the base name from a stamped file, that the extension check
    /// does not reject it, and that the folder is found where `paths::root()` says. The stamping
    /// had a passing unit test and still shipped a live bug that only a real submission exposed,
    /// which is the reason this one goes through the real folder rather than a fixture.
    ///
    /// Skips rather than fails when the library is empty: a fresh clone has nothing to match, and
    /// a test that demanded otherwise would fail for everyone but us.
    #[test]
    fn a_script_already_in_the_library_is_recognised() {
        let folder = paths::root().join("scripts").join("contributed");
        let Ok(entries) = fs::read_dir(&folder) else {
            return;
        };

        let mut checked = 0;
        for entry in entries.flatten() {
            let path = entry.path();
            let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
                continue;
            };
            if !name.ends_with(".py") {
                continue;
            }

            let Ok(held) = fs::read(&path) else { continue };

            // Offered back under its bare name, exactly as a contributor's `contrib/` copy would
            // arrive, and with the line endings a freshly written file carries rather than the
            // ones git checked this one out with.
            let bare = format!("{}.py", strip_stamp(name.trim_end_matches(".py")));
            let unix: Vec<u8> = held.iter().copied().filter(|byte| *byte != b'\r').collect();

            // The invariant is "reuse something already here", not "reuse this exact file".
            // Asserting the latter looked equivalent and is not: the library really does hold two
            // byte-identical copies of `soundxfer.py` under different stamps, left by two
            // submissions made 48 seconds apart before this dedup worked. Only one of them can be
            // the one returned, so the strict form made a true dedup fail -- and it failed in CI
            // on Linux while passing here, purely because the duplicates arrived between the two
            // runs. What matters is that no *new* stamp is minted.
            let picked = library_name(&bare, "20260820-013000", &unix);
            let reused = folder.join(&picked);

            assert!(
                reused.is_file(),
                "{bare} was stamped afresh as {picked} instead of reusing a library copy"
            );
            assert!(
                fs::read(&reused).is_ok_and(|held| same_text(&held, &unix)),
                "{bare} was matched to {picked}, which holds different content"
            );

            checked += 1;
        }

        if checked > 0 {
            println!("{checked} library script(s) recognised");
        }
    }

    /// The same script is the same script however it reached the disk.
    ///
    /// This is the whole of the deduplication: git hands out CRLF on Windows and a run writes LF,
    /// so a raw byte comparison says every library copy is a different script and every submission
    /// adds another stamped duplicate of it.
    #[test]
    fn line_endings_do_not_make_a_new_script() {
        assert!(same_text(b"print(1)\r\nprint(2)\r\n", b"print(1)\nprint(2)\n"));
        assert!(same_text(b"same", b"same"));
        assert!(!same_text(b"print(1)\n", b"print(2)\n"));

        // A difference that is only a *missing* line must still count as different.
        assert!(!same_text(b"a\r\nb\r\n", b"a\n"));
    }

    /// The rules a contributed script has to pass, asserted rather than trusted: a folder that
    /// is not there is normal and not an error, a build artefact is not a script, an empty file
    /// is worse than none, and the same name reached from two folders is carried once.
    #[test]
    fn only_real_scripts_are_carried() {
        let dir = std::env::temp_dir().join(format!("contrib_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);

        let one = dir.join("one");
        let two = dir.join("two");
        fs::create_dir_all(&one).unwrap();
        fs::create_dir_all(&two).unwrap();

        fs::write(one.join("families.py"), b"print('hello')
").unwrap();
        fs::write(one.join("notes.md"), b"what it does
").unwrap();
        fs::write(one.join("a.exe"), b"MZ").unwrap();
        fs::write(one.join("empty.py"), b"").unwrap();
        fs::write(two.join("families.py"), b"a later copy
").unwrap();
        fs::write(two.join("other.rs"), b"fn main() {}
").unwrap();

        let folders = vec![one.clone(), two.clone(), dir.join("not-there")];
        let names: Vec<String> = scripts_in(&folders)
            .iter()
            .map(|path| path.file_name().unwrap().to_string_lossy().to_string())
            .collect();

        assert_eq!(names, vec!["families.py", "notes.md", "other.rs"]);

        // The first folder's copy is the one carried, not the second's.
        let carried = scripts_in(&folders)
            .into_iter()
            .find(|path| path.ends_with("families.py"))
            .unwrap();
        assert!(carried.starts_with(&one));

        let _ = fs::remove_dir_all(&dir);
    }

    /// A path or a message carrying a quote must not be able to break the request open.
    #[test]
    fn json_strings_are_escaped() {
        assert_eq!(quoted("a\"b"), "\"a\\\"b\"");
        assert_eq!(quoted("a\\b"), "\"a\\\\b\"");
        assert_eq!(quoted("a\nb"), "\"a\\nb\"");
        assert_eq!(quoted("plain"), "\"plain\"");
    }
}
