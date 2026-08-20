//! How much of a snapshot is explained by the strings the loader is already holding.
//!
//! The claim this settles: that a lot of the ids in a snapshot are "just the xfile name or
//! already xstrings" -- that is, hashes of fast file names or of the game's script strings,
//! rather than of asset names anybody needs to recover.
//!
//! Both halves of that are checkable against the live loader, because it holds both:
//!
//! - the **fast file name** that owns each asset (`core_ui`, `mp_embassy`, and so on), and
//! - the **string pool**, one block of null terminated script strings, which is where the game's
//!   own text lives.
//!
//! So every one of those strings is hashed with the game's hash and looked for among the ids the
//! loader holds. A hit means that id *is* explained by a string already in the build; a miss
//! means it is not, and no amount of reading strings out of memory would have produced it.
//!
//! The point is the proportion. Anyone can find one string that hashes to something; the
//! question is whether this accounts for a lot of a snapshot or a rounding error.
//!
//! Every hit is a real name, already confirmed by construction, so they are written out too --
//! the file is in `confirm_list` order and can be piped straight into it.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::File;
use std::io::{BufWriter, Write};

use slasher::cordycep::{CordycepInstance, POOL_COUNT};
use slasher::{id_of, ID_MASK};

fn main() {
    let instance = match CordycepInstance::open() {
        Ok(instance) => instance,
        Err(error) => {
            eprintln!("the loader is not readable: {error}");
            eprintln!("open Cordycep and load a game first.");
            return;
        }
    };

    let game = instance.game_id().to_owned();
    println!("the loader has {game} open\n");

    // Every id the loader holds, and the pools it holds it in. The same evidence a snapshot is,
    // read live so this needs no snapshot to agree with.
    let mut loaded: HashMap<u64, Vec<usize>> = HashMap::new();
    let mut owners: HashSet<i64> = HashSet::new();
    let mut assets = 0_usize;

    for pool in 0..POOL_COUNT {
        for asset in instance.assets(pool) {
            let id = (asset.id as u64) & ID_MASK;
            loaded.entry(id).or_default().push(pool);
            owners.insert(asset.owner);
            assets += 1;
        }
    }

    println!("{assets} assets, {} distinct ids", loaded.len());

    // ---- the xfile names ----
    let mut fast_files: HashSet<String> = HashSet::new();
    for owner in &owners {
        let name = instance.fast_file_name(*owner);
        if name != "unknown" {
            fast_files.insert(name);
        }
    }
    println!("{} distinct fast file names", fast_files.len());

    // ---- the xstrings ----
    let pool_strings = instance.string_pool();
    let distinct: HashSet<&String> = pool_strings.iter().collect();
    println!("{} strings in the string pool, {} distinct", pool_strings.len(), distinct.len());

    // ---- hash both, and see what they explain ----
    let out_path = format!("logs/names_from_strings_{}.csv", game.to_lowercase());
    let mut out = BufWriter::new(File::create(&out_path).expect("logs/ exists"));

    let report = |label: &str,
                      candidates: Vec<String>,
                      out: &mut BufWriter<File>|
     -> (usize, usize) {
        let mut hit_ids: HashSet<u64> = HashSet::new();
        let mut per_pool: BTreeMap<usize, usize> = BTreeMap::new();
        let mut tested: HashSet<String> = HashSet::new();

        for text in candidates {
            if !tested.insert(text.clone()) {
                continue;
            }
            let id = id_of(&text);
            if let Some(pools) = loaded.get(&id) {
                if hit_ids.insert(id) {
                    for pool in pools {
                        *per_pool.entry(*pool).or_default() += 1;
                    }
                    let _ = writeln!(out, "{id:016x},{text},{label}");
                }
            }
        }

        println!("\n{label}: {} distinct candidates", tested.len());
        println!(
            "  ids explained: {} of {} ({:.3}% of the snapshot)",
            hit_ids.len(),
            loaded.len(),
            hit_ids.len() as f64 * 100.0 / loaded.len() as f64
        );
        print!("  by pool:");
        let mut shown = 0;
        for (pool, count) in per_pool.iter().rev() {
            if shown == 12 {
                print!(" ...");
                break;
            }
            print!(" {pool}:{count}");
            shown += 1;
        }
        println!();

        (tested.len(), hit_ids.len())
    };

    let (_, ff_hits) = report(
        "xfile name",
        fast_files.iter().cloned().collect(),
        &mut out,
    );
    let (_, xs_hits) = report(
        "xstring",
        pool_strings.clone(),
        &mut out,
    );

    // Strings are also worth trying the way a path is written, since the pool holds bare tokens
    // and plenty of asset names are those tokens under a directory.
    let _ = out.flush();

    println!("\n---");
    println!(
        "of {} distinct ids the loader holds, the fast file names explain {ff_hits} and the\n\
         string pool explains {xs_hits}: {:.3}% between them.",
        loaded.len(),
        (ff_hits + xs_hits) as f64 * 100.0 / loaded.len() as f64
    );
    println!("\nhits written to {out_path}");
}
