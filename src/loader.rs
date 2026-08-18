//! The asset ids every search is judged against, and where they come from.
//!
//! An asset the game holds names itself with a hash, so those ids are the answer key: a candidate
//! whose hash is among them is a name the game itself refers to. That is the entire evidential
//! basis of this project.
//!
//! **The key is a data file, not a running game.** The ids were captured once, into
//! `snapshots/*.ids`, and both games are finished and will not be patched again -- so the capture
//! is final and a search needs nothing but the file. This is what lets somebody with no game, no
//! Cordycep and no Windows do the actual work.
//!
//! Whoever does own the game gets the live loader instead, behind the `cordycep` feature, which
//! is only useful for capturing a snapshot in the first place.

use std::collections::{HashMap, HashSet};

use crate::snapshot::Snapshot;
use crate::{config, paths};

/// Every asset the game holds, as id and pool index, with any strings that came with them.
///
/// The second half is the loader's own string pool, which is a candidate source rather than
/// evidence. It exists only when reading a live loader; a snapshot does not carry it, so a
/// contributor grinding from the snapshot gets an empty one and every other candidate source
/// unchanged. Callers print what they were given rather than assuming it is there.
pub fn loaded_assets() -> Result<(Vec<(u64, usize)>, Vec<String>), String> {
    #[cfg(feature = "cordycep")]
    match from_loader() {
        Ok(live) => return Ok(live),
        Err(why) => println!("the loader is not readable ({why}); reading the snapshot instead"),
    }

    from_snapshot()
}

/// The captured ids for the game these pool indexes and tables describe.
///
/// A snapshot carries its game internally and is matched on it rather than on its filename, so
/// one game's assets can never be used to judge another's names.
fn from_snapshot() -> Result<(Vec<(u64, usize)>, Vec<String>), String> {
    let folder = paths::snapshots();
    let wanted = config::game();

    let entries = std::fs::read_dir(&folder)
        .map_err(|error| format!("{} could not be read: {error}", folder.display()))?;

    let mut seen = Vec::new();

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|end| end.to_str()) != Some("ids") {
            continue;
        }

        let snapshot = match Snapshot::read(&path) {
            Ok(snapshot) => snapshot,
            Err(why) => {
                eprintln!("{} could not be read: {why}", path.display());
                continue;
            }
        };

        if snapshot.game() != wanted {
            seen.push(snapshot.game().to_owned());
            continue;
        }

        println!("{} assets from the {wanted} snapshot", snapshot.len());

        let assets = snapshot.records().map(|(id, pool)| (id, pool as usize)).collect();

        return Ok((assets, Vec::new()));
    }

    Err(format!(
        "no {wanted} snapshot in {}{}. It ships with the repository, so this means it was \
         deleted or `snapshots` in config.toml points elsewhere.",
        folder.display(),
        if seen.is_empty() { String::new() } else { format!(" (found {} instead)", seen.join(", ")) }
    ))
}

/// The live loader, for whoever has the game open. Only worth using to capture a snapshot.
#[cfg(feature = "cordycep")]
fn from_loader() -> Result<(Vec<(u64, usize)>, Vec<String>), String> {
    use crate::cordycep::CordycepInstance;
    use crate::{ID_MASK, POOLS};

    let instance = CordycepInstance::open().map_err(|error| error.to_string())?;

    if instance.game_id() != GAME {
        return Err(format!(
            "the loader has {} open, not {GAME}. Refusing to judge one game's names against \
             another's assets.",
            instance.game_id()
        ));
    }

    let mut assets = Vec::new();
    for index in 0..POOLS.len() {
        for asset in instance.assets(index) {
            assets.push(((asset.id as u64) & ID_MASK, index));
        }
    }

    Ok((assets, instance.string_pool()))
}

/// The loaded ids no table can name, as id to the pool it was found in.
///
/// An id several pools share is attributed to the first of them, which is why `xcollision` and
/// `xskeleton` look emptier than they are: they carry the model's own hash.
pub fn unnamed(assets: &[(u64, usize)], known: &HashSet<u64>) -> HashMap<u64, usize> {
    let mut wanted = HashMap::new();

    for (id, pool) in assets {
        if !known.contains(id) {
            wanted.entry(*id).or_insert(*pool);
        }
    }

    wanted
}

/// The ids a search should actually be looking for: unnamed, reachable, and in a pool this
/// machine is set to grind.
///
/// Every search built its wanted set the same way and then dropped the pools no rule can reach,
/// so that is done once here. The narrowing by type is the part that matters for time: the cost
/// of a pass is carried by how many ids it is hunting, and hunting two hundred pools when five
/// hold what was asked for makes every pass slower for names nobody wanted yet.
///
/// `unreachable` names the pools whose names cannot be built by any rule -- `xmodelmesh`, whose
/// tail is a hash of the mesh itself. Leaving them in cannot yield a name and doubles the ids a
/// candidate could land on by coincidence.
pub fn wanted_for_search(
    assets: &[(u64, usize)],
    known: &HashSet<u64>,
    unreachable: &[&str],
) -> HashMap<u64, usize> {
    let targets = crate::config::targets();
    println!("searching {}", targets.describe());

    let unreachable: Vec<usize> = unreachable
        .iter()
        .filter_map(|kind| crate::pool_index(kind))
        .collect();

    let mut wanted = unnamed(assets, known);
    wanted.retain(|_, pool| !unreachable.contains(pool) && targets.wants(*pool));

    wanted
}

/// The same, narrowed to one pool. A search aimed at a single kind of asset should not be told
/// it matched when it hit something else, or a wrong rule looks like a right one.
pub fn unnamed_in(assets: &[(u64, usize)], known: &HashSet<u64>, pool: usize) -> HashMap<u64, usize> {
    let mut wanted = HashMap::new();

    for (id, found) in assets {
        if *found == pool && !known.contains(id) {
            wanted.insert(*id, *found);
        }
    }

    wanted
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The narrowing must drop what no rule can reach, and keep what the config asked for.
    #[test]
    fn an_id_already_named_is_not_wanted() {
        let assets = vec![(1, 6), (2, 6), (3, 10)];
        let known: HashSet<u64> = [2].into_iter().collect();

        let wanted = unnamed(&assets, &known);

        assert!(wanted.contains_key(&1));
        assert!(!wanted.contains_key(&2), "a name the tables resolve is not a discovery");
        assert!(wanted.contains_key(&3));
    }

    /// An id in several pools is attributed once, to the first pool it was seen in.
    #[test]
    fn an_id_in_two_pools_is_counted_once() {
        let assets = vec![(7, 6), (7, 7)];
        let wanted = unnamed(&assets, &HashSet::new());

        assert_eq!(wanted.len(), 1);
        assert_eq!(wanted.get(&7), Some(&6));
    }

    #[test]
    fn one_pool_can_be_asked_for_on_its_own() {
        let assets = vec![(1, 6), (2, 10), (3, 6)];
        let wanted = unnamed_in(&assets, &HashSet::new(), 6);

        assert_eq!(wanted.len(), 2);
        assert!(!wanted.contains_key(&2), "another pool's id must not answer for this one");
    }
}
