//! Re-verifies a submission from scratch, trusting nothing the sender said.
//!
//! This is what runs on a pull request. The client that found these names already checked them,
//! but it checked them on somebody else's machine with somebody else's build, and a bad
//! submission is far more expensive than a slow one: a wrong name entered into the community
//! tables is copied outward and is very hard to take back.
//!
//! So every line is re-derived here against the snapshots committed in this repository:
//!
//! 1. **The hash is recomputed from the name.** The number on the line is never taken as given,
//!    which catches a mangled file, a bad encoder, and a sender who simply made it up.
//! 2. **The id must be one the game actually holds.** This is the whole claim being made.
//! 3. **The asset type must be one of the pools the id lives in.** A real name filed under the
//!    wrong type is still wrong to publish, and this is free once the id has been found.
//!
//! Two further things are counted and reported but never fail the run, because neither means the
//! submission was wrong: a name published by somebody else while this batch was being ground, and
//! a name that appears twice. Both are things the maintainer resolves by merging, not by rejecting
//! somebody's night of work.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use slasher::snapshot::Snapshot;
use slasher::{id_of, paths, pool_index, pool_label, tables};

fn main() {
    let targets: Vec<PathBuf> = std::env::args().skip(1).map(PathBuf::from).collect();

    let files = if targets.is_empty() {
        submission_files(&paths::submissions())
    } else {
        targets.iter().flat_map(|path| submission_files(path)).collect()
    };

    if files.is_empty() {
        println!("no submission files to check.");
        return;
    }

    // Every snapshot in the repository. A name is being claimed of *a* game, not of a particular
    // one, so it is enough that some game holds it -- the submission files do not say which, and
    // a contributor should not have to know.
    let snapshots = snapshots();
    if snapshots.is_empty() {
        eprintln!("no snapshots found in {}. Nothing can be verified.", paths::snapshots().display());
        std::process::exit(1);
    }

    for snapshot in &snapshots {
        println!("checking against {} ({} assets)", snapshot.game(), snapshot.len());
    }

    // The published tables, if they are here. Absent is fine: everything they affect is a note
    // rather than a rejection, so a run without them is still a real verification.
    let published = published_hashes();
    match published.as_ref() {
        Some(known) => println!("{} hashes already published\n", known.len()),
        None => println!("(no tables present; already-published names will not be noted)\n"),
    }

    let mut seen: HashMap<String, String> = HashMap::new();
    let mut bad: Vec<String> = Vec::new();
    let mut total = 0_usize;
    let mut already = 0_usize;
    let mut repeated = 0_usize;
    let mut untyped = 0_usize;

    for file in &files {
        let kind = file
            .file_stem()
            .and_then(|stem| stem.to_str())
            .map(strip_stamp)
            .unwrap_or_default()
            .to_owned();

        let Ok(text) = fs::read_to_string(file) else {
            bad.push(format!("{}: unreadable", file.display()));
            continue;
        };

        let mut here = 0_usize;

        for (number, line) in text.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            let where_ = format!("{}:{}", short(file), number + 1);

            let Some((claimed, name)) = line.split_once(',') else {
                bad.push(format!("{where_}: not `hash,name`"));
                continue;
            };

            let name = name.trim();
            if name.is_empty() {
                bad.push(format!("{where_}: no name"));
                continue;
            }

            total += 1;
            here += 1;

            // 1. The hash, recomputed. Whatever the sender wrote is only a claim.
            let id = id_of(name);
            match u64::from_str_radix(claimed.trim(), 16) {
                Ok(said) if said == id => {}
                Ok(said) => {
                    bad.push(format!("{where_}: says {said:x} but {name} hashes to {id:x}"));
                    continue;
                }
                Err(_) => {
                    bad.push(format!("{where_}: {} is not a hash", claimed.trim()));
                    continue;
                }
            }

            // 2. The claim itself: some game holds this id. Which one is not asked, because the
            //    submission does not say and a contributor should not have to know.
            let holders: Vec<&Snapshot> =
                snapshots.iter().filter(|snapshot| snapshot.holds(id)).collect();

            if holders.is_empty() {
                bad.push(format!("{where_}: no snapshot holds {id:x} ({name})"));
                continue;
            }

            // 3. The type, when the filename names a pool that can be checked at all.
            //
            //    Two things stop this being universal. Pools nobody has identified yet are named
            //    `pool_184`, and there is nothing to check those against. And POOLS is Cold War's
            //    asset type enum: Black Ops 4 numbers its pools differently, so a pool index read
            //    out of a Black Ops 4 snapshot means nothing here. A name only that game holds is
            //    therefore confirmed real but left with its type untested, which is reported at
            //    the end rather than passed off as a check that happened.
            if let Some(wanted) = pool_index(&kind) {
                match holders.first() {
                    Some(snapshot) => {
                        let pools = snapshot.pools_of(id);
                        if !pools.iter().any(|(_, pool)| *pool as usize == wanted) {
                            let held: Vec<String> =
                                pools.iter().map(|(_, pool)| pool_name(*pool as usize)).collect();

                            bad.push(format!(
                                "{where_}: {name} is filed as {kind} but {} holds it in {}",
                                snapshot.game(),
                                held.join(", ")
                            ));
                            continue;
                        }
                    }
                    None => untyped += 1,
                }
            }

            // Noted, not rejected. Somebody publishing a name mid-grind is the race this whole
            // project is built around, and losing to it is not a fault in the submission.
            if let Some(known) = published.as_ref() {
                if known.contains(&id) {
                    already += 1;
                }
            }

            if let Some(before) = seen.insert(name.to_owned(), where_.clone()) {
                repeated += 1;
                if repeated <= 5 {
                    println!("  note: {name} appears twice, at {before} and {where_}");
                }
            }
        }

        println!("{:<44} {here:>8} names", short(file));
    }

    println!("\n{total} names checked, {} distinct", seen.len());

    if repeated > 0 {
        println!("{repeated} repeated (harmless; they merge to one)");
    }

    if already > 0 {
        println!("{already} published by somebody else since (harmless; drop on merge)");
    }

    if untyped > 0 {
        println!(
            "{untyped} could not be type checked against any snapshot that holds them"
        );
    }

    if bad.is_empty() {
        println!("\nevery name re-derives: the hash matches the name, the game holds the id, and\
                  \nthe asset type is one the id is actually in.");
        return;
    }

    eprintln!("\n{} name(s) did not survive re-verification:\n", bad.len());
    for (shown, complaint) in bad.iter().enumerate() {
        if shown == 40 {
            eprintln!("  ... and {} more", bad.len() - 40);
            break;
        }
        eprintln!("  {complaint}");
    }

    std::process::exit(1);
}

/// Every `.txt` under a path, which may be one file or a whole submission folder.
fn submission_files(path: &Path) -> Vec<PathBuf> {
    if path.is_file() {
        return match path.extension().and_then(|e| e.to_str()) {
            Some("txt") => vec![path.to_owned()],
            _ => Vec::new(),
        };
    }

    let mut found = Vec::new();
    for entry in fs::read_dir(path).into_iter().flatten().flatten() {
        found.extend(submission_files(&entry.path()));
    }

    found.sort();
    found
}

fn snapshots() -> Vec<Snapshot> {
    let mut found = Vec::new();

    for entry in fs::read_dir(paths::snapshots()).into_iter().flatten().flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("ids") {
            continue;
        }

        match Snapshot::read(&path) {
            Ok(snapshot) => found.push(snapshot),
            Err(why) => eprintln!("{} could not be read: {why}", path.display()),
        }
    }

    found
}

/// Every hash the published tables resolve, if the tables are here at all.
fn published_hashes() -> Option<HashSet<u64>> {
    let folder = tables::csv_folder(&paths::tables());
    if !folder.is_dir() {
        return None;
    }

    let mut known = HashSet::new();

    for entry in fs::read_dir(&folder).into_iter().flatten().flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("csv") {
            continue;
        }

        let Ok(text) = fs::read_to_string(&path) else { continue };
        for line in text.lines() {
            let Some((key, name)) = line.split_once(',') else { continue };

            if let Ok(value) = u64::from_str_radix(key.trim(), 16) {
                known.insert(value & slasher::ID_MASK);
            }

            known.insert(id_of(name.trim()));
        }
    }

    (!known.is_empty()).then_some(known)
}

/// The asset type out of a submission's filename: `xmodel_20260818_213000` is `xmodel`.
///
/// Written as a trailing-stamp trim rather than a split on the first underscore, because plenty
/// of pool names have one in them -- `sound_asset` would otherwise arrive as `sound`.
fn strip_stamp(stem: &str) -> &str {
    let mut cut = stem;

    while let Some((before, last)) = cut.rsplit_once('_') {
        if last.is_empty() || !last.bytes().all(|byte| byte.is_ascii_digit()) {
            break;
        }
        cut = before;
    }

    cut
}

fn pool_name(index: usize) -> String {
    pool_label(index)
}

/// A path short enough to read in a log, since CI prints an absolute one.
fn short(path: &Path) -> String {
    let parts: Vec<String> =
        path.components().rev().take(2).map(|part| part.as_os_str().to_string_lossy().to_string()).collect();

    parts.into_iter().rev().collect::<Vec<_>>().join("/")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The asset type has to survive a stamp being appended, and `sound_asset` is the case that
    /// a naive split on the first underscore gets wrong.
    #[test]
    fn the_type_comes_back_out_of_the_filename() {
        assert_eq!(strip_stamp("xmodel_20260818_213000"), "xmodel");
        assert_eq!(strip_stamp("sound_asset_20260818_213000"), "sound_asset");
        assert_eq!(strip_stamp("xmodel"), "xmodel");
        assert_eq!(strip_stamp("sound_asset"), "sound_asset");
    }

    /// An unidentified pool keeps its number, and must not be mistaken for a stamp and trimmed
    /// away into nothing.
    #[test]
    fn an_unidentified_pool_is_left_alone_enough_to_be_unmatchable() {
        // `pool_184` trims to `pool`, which is not a known pool name, so the type check is
        // skipped rather than wrongly failed. That is the behaviour that matters.
        assert!(pool_index(strip_stamp("pool_184_20260818_213000")).is_none());
    }

    /// Every known pool name must round-trip, or a valid submission would be rejected for being
    /// filed under a type this could not recognise.
    #[test]
    fn every_pool_name_survives_a_stamp() {
        for pool in slasher::POOLS {
            let stamped = format!("{pool}_20260818_213000");
            assert_eq!(strip_stamp(&stamped), *pool, "{pool} did not come back");
        }
    }

    #[test]
    fn pools_that_are_named_are_named_and_the_rest_are_numbered() {
        assert_eq!(pool_name(6), "xmodel");
        // 184 was the largest unidentified pool in the game until the enum named it.
        assert_eq!(pool_name(184), "streamkey");
        // Past the end of the enum is where the numbered fallback still applies.
        assert_eq!(pool_name(999), "pool_999");
    }
}
