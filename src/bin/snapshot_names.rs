//! Captures every asset name a loader holds in plain text, for a title that does not hash them.
//!
//! `snapshot` captures ids, because Black Ops 4 and Cold War hold their assets under a hash and
//! the name is the thing nobody has. Modern Warfare 2019 is the opposite case: the loader holds
//! the name itself, as a `char*` in the asset header, so there is nothing to recover and nothing
//! to grind. What there is, is a very large corpus of real Call of Duty asset names.
//!
//! That is worth capturing for a project that recovers names for *other* titles, because every
//! method here builds candidates out of names known to be real (CLAUDE.md §7). Modern Warfare
//! 2019 shipped Warzone, so it carries a great deal of Cold War's content under names that are
//! either identical or a decoration away, and its naming conventions are the ones the later
//! titles inherit.
//!
//! ## Why this cannot reuse `name_field_probe`
//!
//! That tool finds the name field by looking for text whose FNV-1a equals the id the loader
//! holds the asset under. That test is exactly right for a hashed title and can never pass here:
//! Modern Warfare 2019's id is not a hash of its name, so the probe reports 0% for every pool
//! while the names sit in plain sight. Run against MODWAR19 it finds nothing at all.
//!
//! So the verifier is different. A candidate is accepted when the pointer leads to text that
//! *looks like an asset name* -- printable, sanely long, and made of the characters asset names
//! are made of. That is weaker than a hash match by construction, which is why the offset is
//! chosen by agreement across a sample rather than trusted per asset: a pool commits to one
//! offset only if most of the sample agrees, and the walk then reads every asset at that offset.
//!
//! Usage: `snapshot_names [sample]` -- how many assets per pool the offset scan looks at.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::fs::{self, File};
use std::io::{BufWriter, Write};

use slasher::cordycep::{CordycepInstance, POOL_COUNT};
use slasher::{paths, POOLS};

/// How many assets of a pool the offset scan looks at. The scan only has to *find* the offset;
/// the walk that follows reads the whole pool at it.
const SCAN_SAMPLE: usize = 96;

/// How far into the header to look, in bytes.
const SCAN_BYTES: usize = 0x80;

/// A user address on Win64 is well under this. Only ever used to decide whether dereferencing is
/// worth a try.
const PLAUSIBLE_POINTER: u64 = 0x0000_8000_0000_0000;

/// A full load, matching `snapshot`. Well short of it means the loader is still mapping files.
const A_FULL_LOAD: usize = 100_000;

/// Does this text look like a Call of Duty asset name?
///
/// Deliberately strict about *shape* rather than about vocabulary, because guessing at vocabulary
/// is how a capture quietly drops a whole pool whose names do not look like the ones you thought
/// of. Printable, sanely long, no whitespace, and mostly the characters these names are built
/// from -- which still admits every path, tag, dotted sound tail and numbered take in the game.
fn looks_like_an_asset_name(text: &str) -> bool {
    if text.len() < 3 || text.len() > 256 {
        return false;
    }

    let mut wordish = 0_usize;

    for byte in text.bytes() {
        match byte {
            b'a'..=b'z' | b'A'..=b'Z' | b'0'..=b'9' | b'_' => wordish += 1,
            // Every other printable ASCII except space. Enumerating the punctuation instead was
            // the first attempt, and it silently dropped this title's largest pool: 253,933
            // images are named `$black`, `$black_3d`, `$white` and so on, and `$` was not on the
            // list. Guessing which punctuation a title uses is exactly the mistake this
            // function's own doc comment warns about, so it no longer guesses -- shape and
            // density carry the decision rather than a hand-written alphabet.
            0x21..=0x7e => {}
            _ => return false,
        }
    }

    // Mostly word characters, and at least one letter: a run of digits or punctuation is a
    // number or a separator that happens to be readable, not a name.
    wordish * 2 >= text.len() && text.bytes().any(|b| b.is_ascii_alphabetic())
}

/// What to call a pool.
///
/// `POOLS` is this project's enum for Black Ops 4 and Cold War, and those two do not even agree
/// with each other -- `xmodel` is pool 6 in one and 4 in the other (CLAUDE.md §4). Applying it to
/// a third title would put a confident and wrong type on every name captured, which is worse than
/// leaving them unlabelled: a mislabelled corpus is used, a plainly unlabelled one is looked at.
/// So it is used only for the titles it describes.
fn pool_label(game: &str, pool: usize) -> String {
    let ours = matches!(game, "BLKOPS04" | "BLKOPSCW");
    match POOLS.get(pool) {
        Some(name) if ours => (*name).to_owned(),
        _ => format!("pool_{pool}"),
    }
}

fn main() {
    let sample = match std::env::args().nth(1).as_deref() {
        None => SCAN_SAMPLE,
        Some("all") => usize::MAX,
        Some(count) => count.parse().unwrap_or(SCAN_SAMPLE),
    };

    let instance = match CordycepInstance::open() {
        Ok(instance) => instance,
        Err(error) => {
            eprintln!("the loader is not readable: {error}");
            eprintln!("open Cordycep with the game you want and run `loadall`, then try again.");
            return;
        }
    };

    // `inspect:N` dumps a few of one pool's headers word by word, for working out why a pool the
    // scan gave up on holds its name somewhere the scan does not look.
    let first = std::env::args().nth(1).unwrap_or_default();
    if let Some(rest) = first.strip_prefix("inspect:") {
        let pool: usize = rest.parse().unwrap_or(0);
        println!("pool {pool}, first 6 assets, {SCAN_BYTES} header bytes\n");
        for (n, asset) in instance.assets(pool).take(6).enumerate() {
            println!("asset {n}: header 0x{:x} id 0x{:x}", asset.header, asset.id);
            let Ok(header) = instance.reader().read_bytes(asset.header, SCAN_BYTES) else {
                println!("  header unreadable");
                continue;
            };
            for offset in (0..SCAN_BYTES).step_by(8) {
                let word = u64::from_le_bytes(header[offset..offset + 8].try_into().unwrap());
                if word == 0 {
                    continue;
                }
                let text = if word < PLAUSIBLE_POINTER {
                    instance.reader().read_string(word as i64)
                } else {
                    String::new()
                };
                let shown: String = text.chars().take(70).collect();
                println!("  +0x{offset:02x}  0x{word:016x}  {shown:?}");
            }
            println!();
        }
        return;
    }

    let game = instance.game_id().to_owned();
    println!("the loader has {game} open");
    println!("scanning {SCAN_BYTES} bytes of each header, {sample} assets per pool\n");

    println!("{:<8} {:<26} {:>10} {:>8} {:>10}", "index", "type", "assets", "offset", "named");

    // pool -> its names. Sorted and deduplicated as it is built.
    let mut by_pool: BTreeMap<usize, BTreeSet<String>> = BTreeMap::new();
    let mut total_assets = 0_usize;
    let mut total_named = 0_usize;
    let mut pools_without_names = Vec::new();

    for pool in 0..POOL_COUNT {
        // ---- phase 1: which offset holds a pointer to something name-shaped ----
        let mut hits: BTreeMap<usize, usize> = BTreeMap::new();
        let mut scanned = 0_usize;

        for asset in instance.assets(pool).take(sample) {
            let Ok(header) = instance.reader().read_bytes(asset.header, SCAN_BYTES) else {
                continue;
            };
            scanned += 1;

            for offset in (0..SCAN_BYTES).step_by(8) {
                let word = u64::from_le_bytes(header[offset..offset + 8].try_into().unwrap());
                if word == 0 || word >= PLAUSIBLE_POINTER {
                    continue;
                }
                let text = instance.reader().read_string(word as i64);
                if looks_like_an_asset_name(&text) {
                    *hits.entry(offset).or_default() += 1;
                }
            }
        }

        if scanned == 0 {
            continue;
        }

        // The earliest offset most of the sample agrees on. Earliest rather than best because a
        // tie is the same field seen twice and the first is the one in the struct; "most of the
        // sample" because a pointer that only sometimes leads to text is a coincidence, not the
        // name field.
        let offset = hits
            .iter()
            .filter(|(_, count)| **count * 2 >= scanned)
            .map(|(offset, _)| *offset)
            .next();

        // A pool whose names are sparse rather than absent. Some pools hold a mix -- a few real
        // names among entries whose first word is a number or a buffer -- and requiring majority
        // agreement throws all of them away. Falling back to the busiest offset keeps them, and
        // costs nothing to be wrong about: `looks_like_an_asset_name` still vets every string
        // read, so a bad offset yields few names rather than bad ones. Marked `?` in the output
        // so the distinction is visible rather than buried.
        let (offset, confident) = match offset {
            Some(offset) => (Some(offset), true),
            None => {
                let best = hits
                    .iter()
                    .max_by_key(|(_, count)| **count)
                    .filter(|(_, count)| **count * 10 >= scanned)
                    .map(|(offset, _)| *offset);
                (best, false)
            }
        };

        // ---- phase 2: read every asset in the pool at that offset ----
        let mut count = 0_usize;
        let mut named = 0_usize;
        let names = by_pool.entry(pool).or_default();

        for asset in instance.assets(pool) {
            count += 1;

            let Some(offset) = offset else { continue };
            let Ok(header) = instance.reader().read_bytes(asset.header + offset as i64, 8) else {
                continue;
            };
            let word = u64::from_le_bytes(header[..8].try_into().unwrap());
            if word == 0 || word >= PLAUSIBLE_POINTER {
                continue;
            }
            let text = instance.reader().read_string(word as i64);
            if looks_like_an_asset_name(&text) {
                names.insert(text);
                named += 1;
            }
        }

        if count == 0 {
            by_pool.remove(&pool);
            continue;
        }

        total_assets += count;
        total_named += named;

        let type_name = pool_label(&game, pool);

        let shown = match offset {
            Some(offset) if confident => format!("+0x{offset:02x}"),
            Some(offset) => format!("+0x{offset:02x}?"),
            None => {
                pools_without_names.push(pool);
                "none".to_owned()
            }
        };

        println!("{pool:<8} {type_name:<26} {count:>10} {shown:>8} {named:>10}");
    }

    let distinct: usize = by_pool.values().map(|names| names.len()).sum();

    println!("\nassets walked: {total_assets}");
    println!("names read:    {total_named}");
    println!("distinct:      {distinct}");

    if !pools_without_names.is_empty() {
        println!(
            "\n{} pool(s) had no offset the sample agreed on: {:?}",
            pools_without_names.len(),
            pools_without_names
        );
        println!("their assets are counted in the census but contribute no names.");
    }

    if total_assets < A_FULL_LOAD {
        eprintln!(
            "\nonly {total_assets} assets are loaded, far short of a full load. A capture taken \
             now would be a fraction of the game. Run `loadall` and try again."
        );
        return;
    }

    // ---- the corpus ----
    //
    // `pool,name` so a consumer can take one asset type or all of them, matching how findings and
    // the name lists are already read elsewhere. Names are unique per pool, not globally: the
    // same name under two pools is two assets.
    let snapshots = paths::root().join("snapshots");
    let _ = fs::create_dir_all(&snapshots);
    let stem = game.to_lowercase();

    let names_path = snapshots.join(format!("{stem}.names.txt"));
    match File::create(&names_path) {
        Ok(file) => {
            let mut out = BufWriter::new(file);
            let mut written = 0_usize;
            for (pool, names) in &by_pool {
                for name in names {
                    if writeln!(out, "{pool},{name}").is_ok() {
                        written += 1;
                    }
                }
            }
            let _ = out.flush();
            println!("\n{written} name(s) written to {}", names_path.display());
            // The raw file is gitignored and the committed artefact is the gzip -- 54 MB against
            // 7.3 MB for Modern Warfare 2019, against 16.8 MB for the largest `.ids` in the
            // repository. `snapshot.name_corpus()` reads either, so nothing downstream cares
            // which one a clone has.
            println!(
                "gzip it before committing -- `gzip -9 -k {}` -- the raw file is gitignored.",
                names_path.display()
            );
        }
        Err(error) => eprintln!("\n{} could not be written: {error}", names_path.display()),
    }

    // ---- the census, in the same shape the other snapshots use ----
    let census = snapshots.join(format!("{stem}.pools.txt"));
    let mut text = String::new();
    for (pool, names) in &by_pool {
        // An example name beside the count, because this title's pool indexes are its own and
        // nothing here can name them yet. One real name identifies a pool at a glance, which is
        // how they get named later.
        let example = names.iter().next().map(String::as_str).unwrap_or("");
        let _ = writeln!(
            text,
            "{pool},{},{},{example}",
            pool_label(&game, *pool),
            names.len()
        );
    }
    let _ = fs::write(&census, text);
    println!("pool census written to {}", census.display());
}
