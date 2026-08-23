//! Recovers localize entry names, which no published table holds a single one of.
//!
//! Of the localize entries the game loads, the published tables name one. A localize name is
//! `CATEGORY/KEY`: `KILLSTREAK/CHOPPER_GUNNER`, `ARENA/ARENA_LEAGUE_PLAY_SUBDIVISION_NAME_1`.
//! The general search cannot reach them because its beginnings are measured from the material
//! and image tables, and a localize category appears in neither.
//!
//! The two halves are found off each other. A category proves keys: run one against every string
//! ever harvested and the keys under it fall out. A key proves categories: run every known key
//! against a candidate category and the category announces itself by matching. So the search
//! alternates, and each round's findings widen the next one's lists, until a round adds nothing.
//!
//! Both halves start from the same place: the handful of localize names the general search
//! happened to reach. Everything here is an unfolding of those.

use std::collections::{HashMap, HashSet};

use slasher::loader::{loaded_assets, unnamed_in};
use slasher::search::run_best;
use slasher::fingerprint::{Fingerprint, Sketch};
use slasher::{all_table_names, config, folder_names, paths, pool_index, pool_label, read_list, readiness, recon, table_keys, tables_look_complete, Results, RunNote};

/// How many times to go round before calling it saturated. It stops on its own when a round
/// adds nothing, so this is only a guard against a rule that keeps finding one more.
const ROUNDS: usize = 8;

/// The longest a category is worth trying. Categories are short words; a long one is a scraped
/// line that happens to have a slash in it, and it multiplies the whole key list.
const LONGEST_CATEGORY: usize = 24;

/// The shortest piece of a line worth trying as a key.
const SHORTEST_KEY: usize = 3;

/// Every ending the known localize keys carry, at every depth, plus the numbers a family counts
/// itself with. No threshold: the list is small enough that the rare ending is affordable, and
/// the rare ending is the one nothing else can name.
fn endings_from(names: &[String]) -> Vec<String> {
    let mut endings: HashSet<String> = HashSet::new();

    for name in names {
        let key = name.rsplit('/').next().unwrap_or(name).to_lowercase();
        let marks: Vec<usize> = key
            .bytes()
            .enumerate()
            .filter(|(_, byte)| *byte == b'_')
            .map(|(index, _)| index)
            .collect();

        for depth in 1..=3 {
            if marks.len() >= depth {
                let at = marks[marks.len() - depth];
                if at + 1 < key.len() {
                    endings.insert(key[at..].to_owned());
                }
            }
        }
    }

    // A localize family counts itself: name_1 through name_50, level_1 through level_20. The
    // tables show the shape but only ever a few of the members.
    for number in 0..=150 {
        endings.insert(format!("_{number}"));
    }
    for number in 0..=20 {
        endings.insert(format!("_{number:02}"));
    }

    endings.into_iter().collect()
}

/// The categories a set of localize names uses, as the `category/` they start with.
fn categories_of(names: &[String]) -> HashSet<String> {
    names
        .iter()
        .filter_map(|name| name.split_once('/'))
        .map(|(head, _)| format!("{}/", head.to_lowercase()))
        .collect()
}

/// The keys a set of localize names uses, cut down the way a sibling would share them.
fn keys_of(names: &[String]) -> Vec<String> {
    let mut keys = HashSet::new();

    for name in names {
        let key = name.rsplit('/').next().unwrap_or(name).to_lowercase();
        keys.insert(key.clone());

        // Every leading piece, so a key proves the family it belongs to rather than only itself.
        for (index, byte) in key.bytes().enumerate() {
            if byte == b'_' && index >= SHORTEST_KEY {
                keys.insert(key[..index].to_owned());
            }
        }
    }

    keys.into_iter().collect()
}

/// Every string worth trying as a key, cut at the marks a key is built from.
fn key_candidates(lines: &[String]) -> Vec<String> {
    let mut seen: HashSet<String> = HashSet::new();

    for line in lines {
        let line = line.trim().to_lowercase();
        if line.is_empty() || line.len() > 120 {
            continue;
        }

        // A harvested line may already be the key, may be `category/key` written out in full,
        // or may be a key with something in front of it.
        let after_slash = line.rsplit('/').next().unwrap_or(&line).to_owned();

        for form in [line.clone(), after_slash] {
            if form.len() >= SHORTEST_KEY {
                seen.insert(form.clone());
            }

            for (index, byte) in form.bytes().enumerate() {
                if byte == b'_' && index >= SHORTEST_KEY {
                    seen.insert(form[..index].to_owned());
                }
                if byte == b'_' && index + 1 < form.len() && form.len() - index - 1 >= SHORTEST_KEY
                {
                    seen.insert(form[index + 1..].to_owned());
                }
            }
        }
    }

    seen.into_iter().collect()
}

/// The beginnings the known localize names share, as `category/` plus each leading piece of the
/// key. A family like `menu/attach_t9_charm_...` is a beginning in its own right, and its unseen
/// members differ only in the word after it.
fn key_openings(names: &[String], least: usize) -> Vec<String> {
    let mut counted: HashMap<String, usize> = HashMap::new();

    for name in names {
        let Some((head, key)) = name.split_once('/') else {
            continue;
        };
        let head = head.to_lowercase();
        let key = key.to_lowercase();

        *counted.entry(format!("{head}/")).or_default() += 1;

        for (index, byte) in key.bytes().enumerate() {
            if byte == b'_' {
                *counted.entry(format!("{head}/{}", &key[..=index])).or_default() += 1;
            }
        }
    }

    counted
        .into_iter()
        .filter(|(_, count)| *count >= least)
        .map(|(opening, _)| opening)
        .collect()
}

/// The single words the game uses, as whole segments rather than pieces of one.
///
/// These are what fills the gap in a family: the beginning and the ending are known, and what
/// varies between one member and the next is one word.
fn words(lines: &[String], least: usize) -> Vec<String> {
    let mut counted: HashMap<&str, usize> = HashMap::new();

    for line in lines {
        for word in line.split(|c: char| c == '_' || c == '/' || c == '.' || c == ' ') {
            if (3..=24).contains(&word.len()) && word.bytes().all(|b| b.is_ascii_alphanumeric()) {
                *counted.entry(word).or_default() += 1;
            }
        }
    }

    counted
        .into_iter()
        .filter(|(_, count)| *count >= least)
        .map(|(word, _)| word.to_lowercase())
        .collect::<HashSet<String>>()
        .into_iter()
        .collect()
}

/// Every word that could be a category, from anything ever harvested.
fn category_candidates(lines: &[String]) -> Vec<String> {
    let mut seen: HashSet<String> = HashSet::new();

    for line in lines {
        let line = line.trim().to_lowercase();
        if line.is_empty() {
            continue;
        }

        // What sits in front of a slash is a category wherever it was written.
        for (index, byte) in line.bytes().enumerate() {
            if byte == b'/' && index > 0 && index <= LONGEST_CATEGORY {
                seen.insert(format!("{}/", &line[..index]));
            }
        }

        // And a bare short word is worth trying as one, since a category is only ever a word.
        if line.len() <= LONGEST_CATEGORY && line.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_') {
            seen.insert(format!("{line}/"));
        }
    }

    seen.into_iter().collect()
}

/// The argument that says the caller has read why this is a waste and wants it anyway.
const ANYWAY: &str = "--i-know-localize-is-worthless";

fn main() {
    readiness::require();

    // This search works, and what it finds is worth nothing. It is left in the repository so the
    // next assistant can see *why* rather than rediscover it, and it refuses to run so that
    // seeing it in the binary list is not enough to start it.
    if !std::env::args().any(|argument| argument == ANYWAY) {
        eprintln!(
            "{}

This is not a warning about priorities. It ran once for twenty minutes and confirmed 8,667 names,
every one of them useless. Nothing here should spend a night on it.

Run a method from METHODS.md instead. If you genuinely need this pool, pass {ANYWAY}.",
            slasher::low_value_reason("localizeentry").unwrap_or_default()
        );
        std::process::exit(2);
    }

    let began = std::time::Instant::now();
    let root = paths::root();
    let pool = pool_index("localizeentry").expect("the localize pool");

    let (assets, strings) = match loaded_assets() {
        Ok(loaded) => loaded,
        Err(reason) => {
            eprintln!("{reason}");
            return;
        }
    };

    let known = table_keys();
    if !tables_look_complete(&known) {
        eprintln!("the tables read short. Check {}", paths::tables().display());
        return;
    }
    println!("hashes already resolved by the tables: {}", known.len());

    let wanted = unnamed_in(&assets, &known, pool);
    println!(
        "localize entries loaded: {}, of which unnamed: {}",
        assets.iter().filter(|(_, index)| *index == pool).count(),
        wanted.len()
    );
    drop(known);

    // Method and game, and nothing else -- so every contributor computes the same one and the
    // first submission retires the pass for everybody. That is the intended outcome here and
    // nowhere else: this pool is worthless (`AGENTS.md` §5 -- the entry holds a pointer to its own
    // unhashed string, so 8,667 confirmed names in one pass were all of them useless), the binary
    // is off by default, and a pass nobody should run is a pass worth stopping on sight.
    let fingerprint = Fingerprint::of("confirm_localize")
        .with("game", &config::game())
        .finish();
    recon::warn_if_swept(&fingerprint);

    // Everything ever harvested, which is where both the keys and the categories come from.
    // One harvest folder, read once: it was listed twice, under two labels for the same path.
    let mut vocabulary: Vec<String> = Vec::new();
    for folder in [paths::harvest(), paths::borrowed()].into_iter().flatten() {
        vocabulary.extend(folder_names(folder));
    }
    vocabulary.extend(all_table_names());
    vocabulary.extend(strings);
    println!("harvested lines: {}", vocabulary.len());

    let keys = key_candidates(&vocabulary);
    let possible_categories = category_candidates(&vocabulary);
    println!(
        "candidate keys: {}, candidate categories: {}",
        keys.len(),
        possible_categories.len()
    );

    let mut results = Results::load(paths::findings());
    let mut found: Vec<String> = results.names("localizeentry");
    println!("localize names already known: {}", found.len());

    // A category never seen in a name is still worth carrying if it is a word the game uses for
    // one. These are the ones the general search's own findings show.
    let mut categories: HashSet<String> = categories_of(&found);
    for extra in read_list(&root.join("data/localize_categories.txt")) {
        categories.insert(extra);
    }
    println!("categories to start from: {}", categories.len());

    let vocabulary_words = words(&vocabulary, 3);
    println!("words the game uses: {}", vocabulary_words.len());

    let mut total_new = 0_usize;

    for round in 1..=ROUNDS {
        let before = found.len();

        // Broad and bare. Every string ever harvested, under every category known, with nothing
        // appended. This is the cheap half: no ending list means no multiplication, so the whole
        // vocabulary can be asked at a cost of a few billion hashes and a chance of coincidence
        // too small to write down.
        let openings: Vec<String> = categories.iter().cloned().collect();
        println!("
--- round {round}: every key under {} categories ---", openings.len());

        for (id, name) in run_best(&openings, &[], &keys, &wanted, false, true) {
            results.add(&pool_label(pool), id, name);
        }

        found = results.names("localizeentry");
        println!("localize names now: {} (+{})", found.len(), found.len() - before);

        // Which words are categories, proven by the keys that are known landing under them. The
        // keys are few here, so the category list can be everything.
        let proven = keys_of(&found);
        let middle = found.len();
        println!(
            "--- round {round}: {} candidate categories over {} known keys ---",
            possible_categories.len(),
            proven.len()
        );

        for (id, name) in run_best(&possible_categories, &[], &proven, &wanted, false, true) {
            results.add(&pool_label(pool), id, name);
        }

        found = results.names("localizeentry");
        let discovered = categories_of(&found);
        let fresh: Vec<String> = discovered.difference(&categories).cloned().collect();
        println!(
            "localize names now: {} (+{}), {} new categories {:?}",
            found.len(),
            found.len() - middle,
            fresh.len(),
            fresh.iter().take(24).collect::<Vec<_>>()
        );
        for name in discovered {
            categories.insert(name);
        }

        // Narrow and dressed. Only the key families already proven, which is thousands rather
        // than millions, so the whole ending list is affordable against them. This is what
        // reaches a family's unseen members: the numbered ones, and the _desc or _hint of a key
        // whose plain form is known.
        let endings = endings_from(&found);
        let openings: Vec<String> = categories.iter().cloned().collect();
        let proven = keys_of(&found);
        let dressed = found.len();
        println!(
            "--- round {round}: {} known key families x {} endings x {} categories ---",
            proven.len(),
            endings.len(),
            openings.len()
        );

        for (id, name) in run_best(&openings, &endings, &proven, &wanted, false, true) {
            results.add(&pool_label(pool), id, name);
        }

        found = results.names("localizeentry");
        println!("localize names now: {} (+{})", found.len(), found.len() - dressed);

        // One word inside a known family. The beginning is a family that is already proved to
        // exist, the ending is measured, and what goes between them is any word the game uses.
        // Nothing else here can fill that gap: the other phases vary only the two ends.
        let families = key_openings(&found, 2);
        let filled = found.len();
        println!(
            "--- round {round}: {} known families x {} words x {} endings ---",
            families.len(),
            vocabulary_words.len(),
            endings.len()
        );

        for (id, name) in run_best(&families, &endings, &vocabulary_words, &wanted, false, true) {
            results.add(&pool_label(pool), id, name);
        }

        found = results.names("localizeentry");
        println!("localize names now: {} (+{})", found.len(), found.len() - filled);

        let gained = found.len() - before;
        total_new += gained;
        println!("round {round} added {gained}");

        if gained == 0 {
            println!("
round {round} added nothing; saturated");
            break;
        }
    }


    println!("\nlocalize names added across every round: {total_new}");

    results.write(paths::findings()).expect("the results");

    match results.write_run(paths::findings(), "localize") {
        Ok(Some(folder)) => {
            println!("this run's own names: {}", folder.display());
            let _ = Results::note_run(
                &folder,
                &RunNote::new(
                    "localize category/key unfolding (confirm_localize)",
                    "known categories played against harvested words and known keys against \
                     candidate words, completing CATEGORY/KEY pairs",
                    began.elapsed(),
                )
                .measured("game", config::game())
                // The two lists that decide what this can reach. Recorded even though the
                // pool is worthless: consistency costs nothing, and an exception is how the
                // sketch came to be missing from six binaries in the first place.
                .measured("sketch stems", Sketch::of(&keys))
                .measured("sketch beginnings", Sketch::of(&possible_categories))
                .fingerprint(&fingerprint),
            );
        }
        Ok(None) => println!("this run found nothing new"),
        Err(error) => eprintln!("the run folder could not be written: {error}"),
    }
}
