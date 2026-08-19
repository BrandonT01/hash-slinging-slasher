//! Confirms a plain list of candidate names against what the game holds.
//!
//! This is the piece that makes inventing a method cheap.
//!
//! Every other search here is a *method* compiled into Rust: it decides what candidates are and
//! then tries them. That is right for the handful of methods worth running for hours, and it is
//! completely wrong for the thing this project actually depends on, which is somebody having a
//! new idea about what a name might look like. Under the old shape, having an idea meant writing
//! a Rust binary, and so most ideas were never tried.
//!
//! With this, a method is a script that prints candidate names. Generate them however you like --
//! Python, awk, a language model, a text file typed by hand -- and pipe them in. The expensive,
//! careful half (the game's hash, the unnamed set, exclusion against the tables, the run notes,
//! the results that only ever grow) is done here and is the same for every idea.
//!
//! ```text
//! python scripts/continuations.py | confirm_list - --label "per-prefix continuations"
//! confirm_list candidates.txt --label "weapon families, third attempt"
//! ```
//!
//! Nothing is held in memory except one batch, so a candidate file larger than this machine's
//! RAM is fine -- and a generator that streams costs no disk at all.

use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use slasher::fingerprint::Fingerprint;
use slasher::loader::{loaded_assets, wanted_for_search};
use slasher::{
    config, feed, low_value_reason, paths, pool_label, readiness, recon, table_keys,
    tables_look_complete, Filter, Results, RunNote, BASIS, ID_MASK,
};

/// Pools no rule can reach. A mesh name ends in twenty-six characters of base32 that are a hash
/// of the mesh itself, so it cannot be produced by any generator and leaving it in the wanted set
/// only doubles what a candidate can hit by coincidence.
const UNREACHABLE: &[&str] = &["xmodelmesh"];

/// How much candidate text is read and swept at a time.
///
/// Bytes rather than lines, and read as raw bytes rather than through `lines()`, because the
/// first version of this did the obvious thing and paid for it: `BufRead::lines()` allocates a
/// `String` per candidate, and at forty million candidates that allocation *was* the program.
/// Measured on this workload it capped the whole tool at 5.2M candidates/s while the hashing
/// itself is an order of magnitude faster than that. Nothing is allocated here until something
/// matches.
const CHUNK: usize = 64 << 20;

/// How often a long run writes what it has found so far.
const SAVE_EVERY: Duration = Duration::from_secs(60);

fn main() {
    readiness::require();

    let began = Instant::now();
    let arguments: Vec<String> = std::env::args().skip(1).collect();

    let label = argument(&arguments, "--label").unwrap_or_else(|| "an unnamed method".to_owned());
    let describe = argument(&arguments, "--describe").unwrap_or_else(|| {
        "a candidate list generated outside the search and confirmed here".to_owned()
    });

    // Everything that is not a flag and not the value belonging to one. Positional, so that a
    // file which happens to be named the same as the label is still read -- comparing against the
    // label's text would silently drop it, and a candidate file not read is a run that reports
    // success having tested nothing.
    let mut sources: Vec<String> = Vec::new();
    let mut skip_next = false;

    for argument in &arguments {
        if skip_next {
            skip_next = false;
            continue;
        }

        if argument.starts_with("--") {
            skip_next = matches!(argument.as_str(), "--label" | "--describe");
            continue;
        }

        sources.push(argument.clone());
    }

    if sources.is_empty() {
        eprintln!(
            "usage: confirm_list <file>... [--label \"what this method is\"] [--describe \"how it \
             builds candidates\"]\n\n\
             `-` reads standard input, so a generator can be piped straight in:\n\n    \
             python scripts/continuations.py | confirm_list - --label \"per-prefix continuations\"\n\n\
             One candidate name per line. A `hash,name` line is accepted too and the name is \
             taken.\nEverything the tables already resolve is excluded, so what comes out is \
             only what is new."
        );
        std::process::exit(2);
    }

    let (assets, _) = match loaded_assets() {
        Ok(loaded) => loaded,
        Err(reason) => {
            eprintln!("{reason}");
            std::process::exit(1);
        }
    };

    let known = table_keys();
    if !tables_look_complete(&known) {
        eprintln!("the tables read short. Check {}", paths::tables().display());
        std::process::exit(1);
    }
    println!("hashes already resolved by the tables: {}", known.len());

    let wanted = wanted_for_search(&assets, &known, UNREACHABLE);
    println!("unnamed ids a candidate could land on: {}", wanted.len());
    drop(known);
    drop(assets);

    // The filter answers the overwhelming majority of candidates without touching the map, which
    // is what lets this keep up with a generator rather than becoming the bottleneck itself.
    let filter = Filter::sized(wanted.keys(), wanted.len());

    let mut results = Results::load(paths::findings());
    let seen = AtomicU64::new(0);
    let mut matched = 0_usize;
    let mut last_saved = Instant::now();
    let mut digest: u64 = 0;

    let started = Instant::now();
    let threads = std::thread::available_parallelism().map(|count| count.get()).unwrap_or(8);
    println!("confirming across {threads} threads\n");

    for source in &sources {
        let mut reader: Box<dyn Read> = if source == "-" {
            Box::new(std::io::stdin())
        } else {
            match std::fs::File::open(source) {
                Ok(file) => Box::new(file),
                Err(error) => {
                    eprintln!("{source} could not be read: {error}");
                    std::process::exit(1);
                }
            }
        };

        // One buffer for the whole source. `carry` is the partial last line of the previous
        // chunk, which has to be joined to the start of this one rather than dropped -- a
        // candidate cut in half by a buffer boundary is a candidate silently not tested.
        let mut buffer = vec![0_u8; CHUNK];
        let mut carry: Vec<u8> = Vec::new();

        loop {
            let filled = fill(&mut reader, &mut buffer);
            if filled == 0 {
                break;
            }

            // Only up to the last complete line; the tail becomes the next round's carry.
            let end = buffer[..filled]
                .iter()
                .rposition(|byte| *byte == b'\n')
                .map(|at| at + 1)
                .unwrap_or(0);

            let mut text: Vec<u8> = Vec::with_capacity(carry.len() + end);
            text.extend_from_slice(&carry);
            text.extend_from_slice(&buffer[..end]);

            carry.clear();
            carry.extend_from_slice(&buffer[end..filled]);

            let (hits, counted, chunk_digest) = sweep(&text, &filter, &wanted, threads);
            digest = digest.wrapping_add(chunk_digest);
            seen.fetch_add(counted, Ordering::Relaxed);
            matched += file_them(hits, &wanted, &mut results);

            report(&seen, started);

            if last_saved.elapsed() >= SAVE_EVERY {
                last_saved = Instant::now();
                match results.write(paths::findings()) {
                    Ok(()) => println!("  checkpoint: {} names safe on disk", results.len()),
                    Err(error) => eprintln!("  a checkpoint could not be written: {error}"),
                }
            }
        }

        if !carry.is_empty() {
            carry.push(b'\n');
            let (hits, counted, chunk_digest) = sweep(&carry, &filter, &wanted, threads);
            digest = digest.wrapping_add(chunk_digest);
            seen.fetch_add(counted, Ordering::Relaxed);
            matched += file_them(hits, &wanted, &mut results);
        }
    }

    let candidates = seen.load(Ordering::Relaxed);
    let elapsed = started.elapsed().as_secs_f64().max(0.001);

    println!(
        "\n{candidates} candidates in {:.0}s ({:.1}M/s), {matched} matched, {} of them new",
        elapsed,
        candidates as f64 / elapsed / 1e6,
        results.added()
    );
    println!(
        "names expected to match by chance at this size: {:.4}",
        slasher::expected_by_chance(candidates, wanted.len())
    );

    results.write(paths::findings()).expect("the results");

    // Only knowable now: a list run is defined by the candidates it was given, and they arrive on
    // a pipe. Said even when nothing was found, because "somebody already ran this and it also
    // found nothing" is exactly what the next person needs to hear.
    let fingerprint = Fingerprint::of("confirm_list")
        .with("game", &config::game())
        .with("label", &label)
        .with_count("candidates", candidates as usize)
        .with("digest", &format!("{digest:016x}"))
        .with_count("wanted", wanted.len())
        .finish();

    println!("fingerprint: {fingerprint}");
    recon::note_if_swept(&fingerprint);

    match results.write_run(paths::findings(), "list") {
        Ok(Some(folder)) => {
            println!("this run's own names: {}", folder.display());

            let _ = Results::note_run(
                &folder,
                &RunNote::new(label, describe, began.elapsed())
                    .measured("game", config::game())
                    .measured("candidates tested", candidates)
                    .measured("matched", matched)
                    .measured("new", results.added())
                    .measured("ids hunted", wanted.len())
                    .measured("throughput", format!("{:.1}M candidates/s", candidates as f64 / elapsed / 1e6))
                    .fingerprint(fingerprint)
                    .next_step(
                        "if this paid, feed what it found back into the generator and run it \
                         again -- every confirmed name is new vocabulary. If it did not, say so \
                         in METHODS.md under the dead ends, which is worth as much as a find.",
                    ),
            );

            // The generator that produced this is the reusable part. Say so, once, where it will
            // be read: a script in a submission makes the next contributor's first hour better,
            // and a list of names does not.
            println!(
                "\nif a script generated these, drop it in `contrib/` and `submit` will carry it \
                 into the pull request."
            );
        }
        Ok(None) => println!("this run found nothing new"),
        Err(error) => eprintln!("the run folder could not be written: {error}"),
    }

    let _ = std::io::stdout().flush();
}

/// Reads until the buffer is full or the source runs out, since one `read` need not fill it.
fn fill(reader: &mut Box<dyn Read>, buffer: &mut [u8]) -> usize {
    let mut filled = 0;

    while filled < buffer.len() {
        match reader.read(&mut buffer[filled..]) {
            Ok(0) => break,
            Ok(read) => filled += read,
            Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(_) => break,
        }
    }

    filled
}

/// Hashes one chunk of candidate text in parallel.
///
/// Returns what matched, how many candidates there were, and their order-independent digest.
/// The workers walk raw bytes and allocate only for a hit, which is what makes this keep up with
/// a generator rather than become the bottleneck itself.
fn sweep(
    text: &[u8],
    filter: &Filter,
    wanted: &HashMap<u64, usize>,
    threads: usize,
) -> (Vec<(u64, String)>, u64, u64) {
    // Split the text into as many pieces as there are threads, each ending on a line boundary.
    let mut bounds = vec![0_usize];
    let step = text.len() / threads.max(1);

    for index in 1..threads {
        let from = (step * index).min(text.len());
        let at = text[from..]
            .iter()
            .position(|byte| *byte == b'\n')
            .map(|offset| from + offset + 1)
            .unwrap_or(text.len());

        if at > *bounds.last().unwrap() {
            bounds.push(at);
        }
    }
    bounds.push(text.len());

    let mut hits: Vec<(u64, String)> = Vec::new();
    let mut counted = 0_u64;
    let mut digest = 0_u64;

    std::thread::scope(|scope| {
        let mut workers = Vec::new();

        for pair in bounds.windows(2) {
            let piece = &text[pair[0]..pair[1]];

            workers.push(scope.spawn(move || {
                let mut found: Vec<(u64, String)> = Vec::new();
                let mut lines = 0_u64;
                let mut digest = 0_u64;

                for line in piece.split(|byte| *byte == b'\n') {
                    let candidate = candidate_bytes(line);
                    if candidate.is_empty() {
                        continue;
                    }

                    lines += 1;

                    // `feed` normalises as it goes -- lower cased, backslashes folded -- so the
                    // hash is the game's however the generator spelled it.
                    let hash = feed(BASIS, candidate);
                    digest = digest.wrapping_add(hash);

                    let id = hash & ID_MASK;
                    if filter.may_hold(id) && wanted.contains_key(&id) {
                        found.push((id, String::from_utf8_lossy(candidate).into_owned()));
                    }
                }

                (found, lines, digest)
            }));
        }

        for worker in workers {
            let (found, lines, part) = worker.join().expect("a worker");
            hits.extend(found);
            counted += lines;
            digest = digest.wrapping_add(part);
        }
    });

    (hits, counted, digest)
}

/// Files what matched, dropping anything that landed in a pool not worth publishing.
fn file_them(
    hits: Vec<(u64, String)>,
    wanted: &HashMap<u64, usize>,
    results: &mut Results,
) -> usize {
    let mut kept = 0;

    for (id, name) in hits {
        let pool = pool_label(wanted[&id]);

        // A pool that has already cost somebody a night for nothing is not filed, whatever
        // generated it. Otherwise a generator that wanders into `streamkey` fills the results
        // folder with the exact thing this project learned to stop doing.
        if low_value_reason(&pool).is_some() {
            continue;
        }

        kept += 1;
        results.add(&pool, id, name);
    }

    kept
}

fn report(seen: &AtomicU64, started: Instant) {
    let count = seen.load(Ordering::Relaxed);
    let elapsed = started.elapsed().as_secs_f64().max(0.001);

    println!(
        "  {count} candidates  {:.1}M/s  {:.0}s elapsed",
        count as f64 / elapsed / 1e6,
        elapsed
    );
}

/// The candidate on a line, whether it is a bare name or a `hash,name` row.
///
/// Accepting both means a results file, a table row and a generator's raw output are all valid
/// input without anybody having to convert between them.
///
/// Bytes rather than `&str`, so a chunk of candidate text is walked without being validated as
/// utf-8 first. A trailing `\r` is trimmed here and that is not cosmetic: a candidate file
/// written on Windows carries one, it hashes into the name, and it matches nothing. It is the
/// single most likely way to waste a run.
fn candidate_bytes(line: &[u8]) -> &[u8] {
    let mut line = line;

    while let Some((last, rest)) = line.split_last() {
        if last.is_ascii_whitespace() {
            line = rest;
        } else {
            break;
        }
    }

    while let Some((first, rest)) = line.split_first() {
        if first.is_ascii_whitespace() {
            line = rest;
        } else {
            break;
        }
    }

    // A `hash,name` row: hex up to the first comma, and a name after it.
    if let Some(comma) = line.iter().position(|byte| *byte == b',') {
        let (key, rest) = line.split_at(comma);

        if !key.is_empty() && key.len() <= 16 && key.iter().all(u8::is_ascii_hexdigit) {
            let mut name = &rest[1..];
            while let Some((first, tail)) = name.split_first() {
                if first.is_ascii_whitespace() {
                    name = tail;
                } else {
                    break;
                }
            }
            return name;
        }
    }

    line
}

fn argument(arguments: &[String], flag: &str) -> Option<String> {
    let at = arguments.iter().position(|argument| argument == flag)?;
    arguments.get(at + 1).cloned()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn candidate_of(line: &str) -> String {
        String::from_utf8_lossy(candidate_bytes(line.as_bytes())).into_owned()
    }

    /// Both input shapes are accepted, so a results file can be piped back in unchanged.
    #[test]
    fn a_row_and_a_bare_name_both_yield_the_name() {
        assert_eq!(candidate_of("1a2b3c,mc/mtl_thing"), "mc/mtl_thing");
        assert_eq!(candidate_of("  mc/mtl_thing  "), "mc/mtl_thing");
        assert_eq!(candidate_of(""), "");
    }

    /// A name that happens to contain a comma but no leading hash is not truncated at it.
    #[test]
    fn a_comma_in_a_name_is_not_mistaken_for_a_key() {
        assert_eq!(candidate_of("not_hex,thing"), "not_hex,thing");
    }

    /// A file written on Windows carries a trailing carriage return, which hashes into the name
    /// and matches nothing. Trimming it is the difference between a run and a wasted run.
    #[test]
    fn a_windows_line_ending_does_not_reach_the_hash() {
        assert_eq!(candidate_of("mc/mtl_thing\r"), "mc/mtl_thing");
        assert_eq!(candidate_of("1a2b,mc/mtl_thing\r"), "mc/mtl_thing");
    }
}
