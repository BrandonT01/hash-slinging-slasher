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

/// The pools a `--sounds` pass hunts, and that every other pass leaves alone.
///
/// Sound names look nothing like the rest -- dotted encoding tails, deep directories, and in
/// Black Ops 4 backslashes -- so the vocabulary that reaches them reaches nothing else, and the
/// vocabulary that reaches models reaches none of them. Splitting the run costs nothing and each
/// half gets a whole ceiling of endings that can actually land.
const SOUND_POOLS: &[&str] = &["sound_asset", "sound_alias"];

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
    let no_fold = arguments.iter().any(|value| value == "--no-fold");
    let sounds = arguments.iter().any(|value| value == "--sounds");
    if sounds {
        println!("hunting the sound pools, with the vocabulary measured from the sound tables");
    }
    if no_fold {
        println!("hashing without folding backslashes (Black Ops 4 SAB sound names)");
    }

    let root = paths::root();
    // Which vocabulary this pass draws on. A sound pass and a general pass are different runs
    // with different targets, so they read different lists -- see `paths::SOUND_SUFFIX_LIST`.
    let (suffix_list, prefix_list) = if sounds {
        (paths::SOUND_SUFFIX_LIST, paths::SOUND_PREFIX_LIST)
    } else {
        (paths::SUFFIX_LIST, paths::PREFIX_LIST)
    };

    let mut endings = read_list(&root.join(suffix_list));
    let mut prefixes = read_list(&root.join(prefix_list));

    // The measured lists are kept in one canonical form, with forward slashes, because a sound
    // path's *shape* is identical in both games and only the separator differs. Measured across
    // the tables: Black Ops 4's SAB names use backslashes throughout (8,403 of them), Cold War's
    // use forward slashes throughout (49,189), and not one name mixes the two. Measuring both
    // spellings would have spent half a capped list saying the same thing twice.
    //
    // So a run that does not fold translates them back as it loads. The ids it hunts are the hash
    // of the unfolded string, so a beginning spelled `amb/environment/` misses every one of them
    // where the same beginning spelled with backslashes lands.
    if no_fold {
        for item in endings.iter_mut().chain(prefixes.iter_mut()) {
            if item.contains('/') {
                *item = item.replace('/', "\\");
            }
        }

        println!("translated the measured lists to backslashes for this run");
    }

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

    let mut wanted = wanted_for_search(&assets, &known, UNREACHABLE);

    // The targets split with the vocabulary. A general pass hunting sound ids with model endings
    // cannot match any of them, but still pays for them: they enlarge the peeled batches, so the
    // pass takes longer, and they enlarge the wanted set, so every candidate is likelier to hit
    // one by coincidence. Both halves are worse off sharing a run, exactly as they were sharing a
    // list. Measured on Black Ops 4: 216,217 ids hunted together against 122,000 and 94,000 apart.
    {
        let before = wanted.len();
        wanted.retain(|_, pool| SOUND_POOLS.contains(&pool_label(*pool).as_str()) == sounds);

        println!(
            "hunting {} {} ids, leaving {} to the {} pass",
            wanted.len(),
            if sounds { "sound" } else { "non-sound" },
            before - wanted.len(),
            if sounds { "general" } else { "sound" }
        );
    }
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
    // A run that did not fold must keep its names spelled exactly as they were hashed;
    // see `Results::keeping_spelling`. Folding them here is what left 37 submitted rows
    // whose name does not produce the id beside it.
    let mut results = Results::load(paths::findings());
    if no_fold {
        results = results.keeping_spelling();
    }
    let mut lines = results.seed_names();
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
    let fingerprint = Fingerprint::of(match (sounds, sources) {
        (true, _) => "confirm_cw/sounds",
        (false, Sources::All) => "confirm_cw/all",
        (false, Sources::Seeds) => "confirm_cw/seeds",
    })
    .with("game", &config::game())
    .with("pools", &config::targets().describe())
    .with("all-tables", if every_table { "yes" } else { "no" })
    .with("fold", if no_fold { "no" } else { "yes" })
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
    // Black Ops 4's SAB sound names keep their backslashes and their ids are the hash of exactly
    // that, so folding matches nothing. `Meet::unfolded` switches the peel and the feed together.
    let search = if no_fold {
        Meet::unfolded(&prefixes, &endings)
    } else {
        Meet::new(&prefixes, &endings)
    };
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

    match results.write_run(paths::findings(), run_label(sounds, sources)) {
        Ok(Some(folder)) => {
            println!("this run's own names: {}", folder.display());
            let _ = Results::note_run(
                &folder,
                &RunNote::new(
                    match (sounds, sources) {
                        (true, _) => "sound files and aliases (confirm_cw --sounds)",
                        (false, Sources::All) => "general search (confirm_cw)",
                        (false, Sources::Seeds) => {
                            "general search, confirmed seeds only (confirm_cw seeds)"
                        }
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
                .measured("matches", found.len())
                .measured("distinct names reached", distinct.len())
                .measured("new here", results.added())
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

/// The name a run folder carries, which is also how `start` knows what this clone has run.
///
/// A sound pass must not answer to the same label as a general one. It used to: both wrote `all`,
/// so one general pass marked sound as already done, `start` stopped offering it, and the largest
/// unnamed ground in either game -- 70,878 of Black Ops 4's 79,263 `sound_asset` ids -- quietly
/// retired itself. `soundfiles` rather than `sounds` because `confirm_sounds` already owns that
/// one, and two methods sharing a label is the same bug wearing a different hat.
fn run_label(sounds: bool, sources: Sources) -> &'static str {
    match (sounds, sources) {
        (true, Sources::All) => "soundfiles",
        (true, Sources::Seeds) => "soundseeds",
        (false, Sources::All) => "all",
        (false, Sources::Seeds) => "seeds",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Every pass this binary can run must be distinguishable on disk from every other, and from
    /// the other binaries' labels. `start` reads nothing but these strings to decide what is left
    /// to try, so a collision does not look like a bug -- it looks like a finished job.
    #[test]
    fn every_pass_has_its_own_label() {
        let labels = [
            run_label(false, Sources::All),
            run_label(false, Sources::Seeds),
            run_label(true, Sources::All),
            run_label(true, Sources::Seeds),
        ];

        // All four are distinct. The seeds-only sound pass matters as much as the others: it is
        // the cheap one, so it is the one somebody runs first, and if it answered to the same
        // label as the full sound pass it would retire the expensive one before it ever ran.
        for (left, right) in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)] {
            assert_ne!(labels[left], labels[right], "two passes share a run label");
        }

        // Nor with the labels the other binaries write, which `start` reads from the same folder.
        for taken in ["sounds", "list", "localize", "swaps", "variants", "images", "techsets"] {
            for label in labels {
                assert_ne!(label, taken, "{label} collides with another method's run label");
            }
        }
    }
}
