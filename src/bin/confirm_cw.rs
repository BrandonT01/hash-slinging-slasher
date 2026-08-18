//! Confirms harvested names against what the game actually has loaded.
//!
//! Every asset the loader holds names itself with a hash. Hashing candidate names and looking
//! for those hashes among the loaded assets turns a guess into a fact: a match means the game
//! itself refers to that name. Anything the published tables already resolve is left out, so
//! what comes back is only what is new.
//!
//! The candidates are not only the harvested strings. A scraped line carries noise at both ends,
//! and a package entry is named for a model's meshes or an image's base rather than for the
//! asset, so each line is cut into every piece that could be a name in its own right, and each
//! piece is tried with the beginnings and endings these names are measured to carry.
//!
//! The names the tables already resolve are a source in their own right, and the best one: they
//! are this game's own vocabulary rather than a scrape of it. They can never be a find, being
//! already resolved, but the piece an unnamed sibling shares with them is exactly what the rules
//! need. Only the tables that are this game are read for it by default. Every table is still
//! read for exclusion, which is free; reading them all for pieces is not, and `all-tables` says
//! to do it anyway -- it quadruples the pieces, and with them both the time and the number of
//! names expected to match by coincidence.
//!
//! Candidates are streamed past the loaded ids rather than collected, because the combinations
//! run to trillions and only the few that match need keeping. Nothing is built into a string
//! unless it matches.

use std::collections::HashSet;
use std::time::{Duration, Instant};

use slasher::loader::{loaded_assets, unnamed, wanted_for_search};
use slasher::search::Meet;
use slasher::{
    all_table_names, folder_names, hash64, paths, read_list, table_keys,
    table_names, tables_look_complete, Results, pool_label,
};

/// The shortest piece of a line worth trying. Anything shorter matches by accident as often as
/// it matches for a reason.
const SHORTEST: usize = 3;

/// The tables that are this game rather than a newer one, judged by how thick they are with its
/// marker. A newer game's names teach the wrong conventions and mostly yield nothing.
const COLD_WAR_TABLES: &[&str] = &[
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_xsounds",
    "fnv1a_soundbanks_aliases",
    "fnv1a_strings",
];

/// Pools this search cannot reach, and so should not be asked about.
///
/// A mesh entry is named `<model>_s1_geo_rigid_bs_` followed by twenty six characters of base32,
/// and that tail is a hash of the mesh rather than anything a rule could produce. Every mesh name
/// any table holds is shaped that way, so none of the rest is reachable without inverting it.
///
/// They are also most of the unnamed ids. Leaving them in cannot yield a name, and would roughly
/// double the ids a candidate can land on by coincidence, so taking them out buys accuracy for
/// every other pool at no cost.
const UNREACHABLE: &[&str] = &["xmodelmesh"];

/// How often a long pass writes what it has found so far.
///
/// The point is not to lose an hour when the thing driving the search stops early, and a minute
/// is the balance: a full write is several megabytes, and protecting work newer than that costs
/// more in disk churn than the work is worth.
const SAVE_EVERY: Duration = Duration::from_secs(60);

/// Which lines a run draws its pieces from.
#[derive(Clone, Copy, PartialEq)]
enum Sources {
    /// Everything: the harvests, the tables, the loader's string pool, and what has already been
    /// confirmed.
    All,

    /// Only what has already been confirmed. Small enough to run in minutes, which is what makes
    /// it worth repeating after a long run to pick up the siblings of whatever that one found.
    Seeds,
}

/// Every distinct piece of the source lines that could be a name in its own right.
///
/// A line is cut at the marks these names are built from, from both ends, because a scrape
/// carries noise at the start as often as at the end: underscores, path separators, and the dot
/// a package entry decorates a name with before appending its own hash. Cutting at the dot is
/// what recovers a name from a map entry, which no other rule reaches. The same piece arrived at
/// from twenty different lines is kept once.
fn stems(lines: &[String]) -> Vec<Box<str>> {
    let mut seen: HashSet<u64> = HashSet::new();
    let mut pieces: Vec<Box<str>> = Vec::new();
    let mut starts: Vec<usize> = Vec::new();
    let mut ends: Vec<usize> = Vec::new();

    for line in lines {
        starts.clear();
        starts.push(0);

        // Past any leading punctuation, which a scraped line often carries and which no asset
        // name begins with.
        if let Some(first) = line.find(|c: char| c.is_ascii_alphanumeric()) {
            if first > 0 {
                starts.push(first);
            }
        }

        for offset in 1..4.min(line.len()) {
            starts.push(offset);
        }

        for (index, &byte) in line.as_bytes().iter().enumerate() {
            if matches!(byte, b'_' | b'/' | b'\\') && index + 1 < line.len() {
                starts.push(index + 1);
            }
        }

        for index in 0..starts.len() {
            let start = starts[index];
            if !line.is_char_boundary(start) {
                continue;
            }

            let left = &line[start..];

            ends.clear();
            ends.push(left.len());

            for (offset, &byte) in left.as_bytes().iter().enumerate() {
                if matches!(byte, b'_' | b'.') && offset >= SHORTEST {
                    ends.push(offset);
                }
            }

            for &end in &ends {
                let stem = &left[..end];
                if stem.len() < SHORTEST {
                    continue;
                }

                if seen.insert(hash64(stem)) {
                    pieces.push(stem.into());
                }
            }
        }
    }

    pieces
}

fn main() {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let sources = if arguments.iter().any(|value| value == "seeds") {
        Sources::Seeds
    } else {
        Sources::All
    };
    let every_table = arguments.iter().any(|value| value == "all-tables");

    let root = paths::root();
    let endings = read_list(&root.join(paths::SUFFIX_LIST));
    let prefixes = read_list(&root.join(paths::PREFIX_LIST));

    println!(
        "sources: {}, {} beginnings, {} endings",
        match sources {
            Sources::All => "everything",
            Sources::Seeds => "confirmed names only",
        },
        prefixes.len(),
        endings.len()
    );

    let (assets, pool) = match loaded_assets() {
        Ok(loaded) => loaded,
        Err(reason) => {
            eprintln!("{reason}");
            return;
        }
    };

    let known = table_keys();
    println!("hashes already resolved by the tables: {}", known.len());

    if !tables_look_complete(&known) {
        eprintln!("the tables read short. Check {}", paths::tables().display());
        return;
    }

    let before_pruning = unnamed(&assets, &known).len();
    let wanted = wanted_for_search(&assets, &known, UNREACHABLE);

    println!(
        "loaded assets: {}, of which unnamed by the tables: {} ({} of them in {UNREACHABLE:?},          which no rule here can reach, left out)",
        assets.len(),
        wanted.len(),
        before_pruning - wanted.len()
    );

    // Held only long enough to say which ids are still wanted, and let go before the scan, which
    // needs every byte of memory it can have.
    drop(known);

    // The confirmed names are proven patterns, so they always go back in as seeds.
    let mut results = Results::load(paths::findings());
    let mut lines = results.all_names();
    println!("confirmed names as seeds: {}", lines.len());

    if sources == Sources::All {
        for (label, folder) in [
            ("harvested from the alpha", paths::harvest().unwrap_or_default()),
            ("harvested from the retail build", paths::harvest().unwrap_or_default()),
            ("borrowed from the earlier game", paths::borrowed().unwrap_or_default()),
            ("found deriving images from materials", paths::findings()),
        ] {
            let found = folder_names(folder);
            println!("{label}: {}", found.len());
            lines.extend(found);
        }

        let vocabulary = if every_table {
            all_table_names()
        } else {
            COLD_WAR_TABLES.iter().flat_map(|table| table_names(table)).collect()
        };
        println!(
            "names {} tables already resolve: {}",
            if every_table { "all the" } else { "this game's" },
            vocabulary.len()
        );
        lines.extend(vocabulary);

        println!("strings in the loader's pool: {}", pool.len());
        lines.extend(pool);
    }

    let started = Instant::now();
    let pieces = stems(&lines);
    println!(
        "distinct pieces: {} in {:.0}s",
        pieces.len(),
        started.elapsed().as_secs_f64()
    );
    drop(lines);

    // Saved as the search goes rather than after it. A pass is an hour and the thing driving it
    // may not last that long, so what has been found is on disk long before the end.
    //
    // Every batch's names are taken, but the file is only rewritten once a minute: a full write
    // is several megabytes and a batch is a few seconds, so writing every batch would churn
    // gigabytes over a pass to protect work that is at most sixty seconds old.
    let search = Meet::new(&prefixes, &endings);
    let mut last_saved = Instant::now();

    let found = search.run_checkpointed(&pieces, &wanted, &mut |batch| {
        for (id, name) in batch {
            results.add(&pool_label(wanted[id]), *id, name.clone());
        }

        if last_saved.elapsed() >= SAVE_EVERY {
            last_saved = Instant::now();

            match results.write(paths::findings()) {
                Ok(()) => println!("  checkpoint: {} names safe on disk", results.len()),
                Err(error) => eprintln!("  a checkpoint could not be written: {error}"),
            }
        }
    });

    println!("{} names found across the run", found.len());

    results.write(paths::findings()).expect("the results");

    match results.write_run(paths::findings(), match sources {
        Sources::All => "all",
        Sources::Seeds => "seeds",
    }) {
        Ok(Some(folder)) => println!("this run's own names: {}", folder.display()),
        Ok(None) => println!("this run found nothing new"),
        Err(error) => eprintln!("the run folder could not be written: {error}"),
    }
}
