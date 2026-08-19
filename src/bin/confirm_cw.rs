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

use slasher::fingerprint::Fingerprint;
use slasher::loader::{loaded_assets, unnamed, wanted_for_search};
use slasher::search::Meet;
use slasher::{
    all_table_names, config, folder_names, hash64, paths, read_list, readiness, recon, table_keys,
    table_names, tables_look_complete, Results, RunNote, pool_label,
};

/// The shortest piece of a line worth trying. Anything shorter matches by accident as often as
/// it matches for a reason.
const SHORTEST: usize = 3;

/// The tables that are this game rather than a newer one. A newer game's names teach the wrong
/// conventions and mostly yield nothing.
///
/// Which files belong to which game is not a guess: it is Saluki's own loading code, written down
/// in `docs/HASHES.md`. Everything without a `_v2` suffix is Black Ops 4 and Cold War.
///
/// **The twelve per-language sound tables matter and were missing.** This list used to name only
/// `fnv1a_xsounds`, the legacy file, which holds 57,593 names in the older `.ln75.pc.all.snd`
/// shape. The twelve files Saluki actually loads hold **825,316 distinct names** between them, in
/// the `.rn75.pc.<lang>.snd` shape, and they share *nothing* with the legacy file -- the overlap
/// is exactly zero rows. Sound names are also the richest seed material in the set: they carry
/// full directory paths, speaker codes and dotted tails that no other table has. Leaving them out
/// cost every general pass ever run here fourteen times its sound vocabulary.
const COLD_WAR_TABLES: &[&str] = &[
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
    "fnv1a_strings",
    // The legacy sound file, still worth reading: zero of its names appear in the twelve below.
    "fnv1a_xsounds",
    // The twelve Saluki loads, one per shipped language.
    "fnv1a_english_xsounds",
    "fnv1a_french_xsounds",
    "fnv1a_german_xsounds",
    "fnv1a_italian_xsounds",
    "fnv1a_spanish_xsounds",
    "fnv1a_americanspanish_xsounds",
    "fnv1a_brazilianportugese_xsounds",
    "fnv1a_russian_xsounds",
    "fnv1a_polish_xsounds",
    "fnv1a_japanese_xsounds",
    "fnv1a_korean_xsounds",
    "fnv1a_chinese_xsounds",
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
    // Refuses to start on a clone that has not been brought up to date and checked against what
    // other people already have in flight. This is the whole of the duplicate problem, and it is
    // enforced here rather than requested in a document because requesting it did not work.
    readiness::require();

    let began = Instant::now();
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

    // Counted apart, because these are two different reasons for an id not to be hunted and
    // reporting them as one has already misled this project once.
    //
    // The old line here subtracted the wanted set from *every* unnamed id and attributed the
    // whole difference to `xmodelmesh`. Most of that difference is nothing of the kind: it is
    // every pool this machine was not asked to search -- `streamkey` alone is 420,229 ids in Cold
    // War. The figure it printed, 827,933, went into METHODS.md as the size of the mesh pool,
    // which actually holds 271,840. Say which is which.
    let all_unnamed = unnamed(&assets, &known);
    let mesh: Vec<usize> = UNREACHABLE.iter().filter_map(|kind| slasher::pool_index(kind)).collect();
    let unreachable = all_unnamed.values().filter(|pool| mesh.contains(pool)).count();

    let wanted = wanted_for_search(&assets, &known, UNREACHABLE);
    let not_targeted = all_unnamed.len() - unreachable - wanted.len();
    drop(all_unnamed);

    println!(
        "loaded assets: {}, unnamed by the tables: {}\n  hunting {} of them\n  {unreachable} left \
         out as unreachable {UNREACHABLE:?}\n  {not_targeted} left out as pools this machine is \
         not set to search",
        assets.len(),
        unreachable + not_targeted + wanted.len(),
        wanted.len(),
    );

    // Held only long enough to say which ids are still wanted, and let go before the scan, which
    // needs every byte of memory it can have.
    drop(known);

    // The confirmed names are proven patterns, so they always go back in as seeds.
    let mut results = Results::load(paths::findings());
    let mut lines = results.all_names();
    println!("confirmed names as seeds: {}", lines.len());

    if sources == Sources::All {
        // What the *other* game has confirmed. Findings are kept per game because the two number
        // their asset types differently and a mixed folder mislabels every name -- but that is a
        // rule about where results are written, not about where candidates come from. Cold War
        // carries a great deal of Black Ops 4's content, so each game's confirmed names are
        // among the best seed material the other has.
        for other in config::GAMES.iter().filter(|game| **game != config::game()) {
            let borrowed = folder_names(paths::findings_root().join(other.to_lowercase()));
            println!("confirmed in {other} and worth trying here: {}", borrowed.len());
            lines.extend(borrowed);
        }

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

    let seeds = lines.len();
    let started = Instant::now();
    let pieces = stems(&lines);
    println!(
        "distinct pieces: {} in {:.0}s",
        pieces.len(),
        started.elapsed().as_secs_f64()
    );
    drop(lines);

    // What this search *is*, reduced to sixteen characters. Everything that decides which names
    // come out goes in; nothing about this machine or this moment does. If somebody has already
    // run and submitted this exact configuration, it will find precisely what they found, and
    // saying so now is worth more than an hour of confirming it.
    let fingerprint = Fingerprint::of(match sources {
        Sources::All => "confirm_cw/all",
        Sources::Seeds => "confirm_cw/seeds",
    })
    .with("game", &config::game())
    .with("pools", &config::targets().describe())
    .with("all-tables", if every_table { "yes" } else { "no" })
    .with_list("beginnings", &prefixes)
    .with_list("endings", &endings)
    .with_count("seed lines", seeds)
    .with_count("pieces", pieces.len())
    .with_count("wanted", wanted.len())
    .finish();

    println!("fingerprint: {fingerprint}");
    recon::warn_if_swept(&fingerprint);

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

    // Matches and names are different numbers and this used to print the first under the second's
    // name. `found` is one entry per beginning-stem-ending combination that landed, so a name
    // reachable three ways is in it three times -- 7,640 matches over one measured pass were 1,029
    // distinct names. Reporting the raw figure as "names found" overstates a pass by a factor of
    // seven and is precisely how wrong numbers have got into this project's documentation before.
    let distinct: std::collections::HashSet<u64> = found.iter().map(|(id, _)| *id).collect();
    println!(
        "{} matches across the run, {} distinct name(s) -- see the table below for how many were \
         new",
        found.len(),
        distinct.len()
    );

    results.write(paths::findings()).expect("the results");

    match results.write_run(paths::findings(), match sources {
        Sources::All => "all",
        Sources::Seeds => "seeds",
    }) {
        Ok(Some(folder)) => {
            println!("this run's own names: {}", folder.display());
            let _ = Results::note_run(
                &folder,
                &RunNote::new(
                    match sources {
                        Sources::All => "general search (confirm_cw)",
                        Sources::Seeds => "general search, confirmed seeds only (confirm_cw seeds)",
                    },
                    "every seed cut to pieces at its marks and recombined as beginning + stem + \
                     ending, each candidate hashed and looked up among the game's unnamed ids",
                    began.elapsed(),
                )
                .measured("game", config::game())
                .measured("pools searched", config::targets().describe())
                .measured("seed lines", seeds)
                .measured("distinct pieces", pieces.len())
                .measured("beginnings", prefixes.len())
                .measured("endings", endings.len())
                .measured("ids hunted", wanted.len())
                .measured("names found", found.len())
                .fingerprint(&fingerprint)
                .next_step(
                    "this configuration is now exhausted. Re-measure the lists with \
                     `python scripts/derive_lists.py` so the confirmed names widen them, which \
                     changes the fingerprint and reopens the method -- or run a method that \
                     reaches somewhere else entirely (METHODS.md).",
                ),
            );
        }
        Ok(None) => println!("this run found nothing new"),
        Err(error) => eprintln!("the run folder could not be written: {error}"),
    }
}
