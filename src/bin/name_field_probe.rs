//! Where an asset's name actually lives in its header, measured against the live loader.
//!
//! Two questions get asked about a snapshot and answered by guesswork. Whether the captured id is
//! the hash of a name or a *pointer* to one read out of the wrong field -- plausible, because in
//! every Call of Duty before these two the name was a `char*` and it is the first member of the
//! asset struct. And, for the pools where the first member is *not* the id, whether the name is
//! sitting somewhere else in the header in plain text, waiting to be read rather than ground for.
//!
//! Neither is worth an opinion, so this measures both:
//!
//! 1. For every pool, compare `entry.id` -- the field `snapshot` stores -- against the first
//!    `u64` of the header it points at.
//! 2. Wherever those differ, scan the header word by word for the name: either the id itself
//!    stored at some other offset, or a pointer to text that *hashes to* the id. Hashing is the
//!    whole point. A readable string near an asset proves nothing; a string whose FNV-1a equals
//!    the id the loader holds it under is that asset's name.
//! 3. Walk the whole pool at whichever offset won, so the coverage figure is exact rather than
//!    inferred from the sample that found it.
//!
//! Recovered names are written to a file, since a name read out of the loader is already
//! confirmed by construction: it hashes to an id the game is holding.
//!
//! Usage: `name_field_probe [sample|all]` -- how many assets per pool in the scan phase.
//! The confirming walk is always over the whole pool.

use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufWriter, Write};

use slasher::cordycep::CordycepInstance;
use slasher::{id_of, ID_MASK};

/// How many assets of a pool the offset scan looks at. The scan only has to *find* the offset;
/// the walk that follows confirms it over everything, so this buys speed and costs nothing.
const SCAN_SAMPLE: usize = 128;

/// How far into the header to look, in bytes. Asset headers put the name in the first few words
/// or not at all -- nothing here has ever been found past this, and every byte costs a read.
const SCAN_BYTES: usize = 0x80;

/// A user address on Win64 is well under this, and a hash is above it far more often than not.
/// Only ever used to decide whether dereferencing is worth a try, never whether a name is real.
const PLAUSIBLE_POINTER: u64 = 0x0000_8000_0000_0000;

/// What the scan concluded about one pool.
enum Where {
    /// The id is at this offset in the header.
    Id(usize),
    /// A pointer at this offset leads to text that hashes to the id.
    Text(usize),
    /// Neither, anywhere in the first `SCAN_BYTES`.
    Nowhere,
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
            eprintln!("open Cordycep and load a game first.");
            return;
        }
    };

    let game = instance.game_id().to_owned();
    println!("the loader has {game} open");
    println!("scanning {SCAN_BYTES} bytes of each asset header, {sample} assets per pool\n");

    let out_path = format!("logs/names_from_headers_{}.csv", game.to_lowercase());
    let mut out = BufWriter::new(File::create(&out_path).expect("logs/ exists"));
    let mut recovered_total = 0_usize;

    let mut rows: Vec<(usize, usize, &'static str, usize, usize)> = Vec::new();

    for pool in 0..slasher::cordycep::POOL_COUNT {
        // ---- phase 1: where, if anywhere, is the name ----
        let mut id_hits = BTreeMap::<usize, usize>::new();
        let mut text_hits = BTreeMap::<usize, usize>::new();
        let mut scanned = 0;

        for asset in instance.assets(pool).take(sample) {
            let id = (asset.id as u64) & ID_MASK;
            let Ok(header) = instance.reader().read_bytes(asset.header, SCAN_BYTES) else {
                continue;
            };
            scanned += 1;

            for offset in (0..SCAN_BYTES).step_by(8) {
                let word = u64::from_le_bytes(header[offset..offset + 8].try_into().unwrap());

                if (word & ID_MASK) == id {
                    *id_hits.entry(offset).or_default() += 1;
                    continue;
                }

                if word != 0 && word < PLAUSIBLE_POINTER {
                    let text = instance.reader().read_string(word as i64);
                    if !text.is_empty() && id_of(&text) == id {
                        *text_hits.entry(offset).or_default() += 1;
                    }
                }
            }
        }

        if scanned == 0 {
            continue;
        }

        // The earliest offset that works for most of what was scanned. Earliest rather than best
        // because a tie is the same field seen twice, and the first is the one in the struct.
        let best = |hits: &BTreeMap<usize, usize>| -> Option<usize> {
            let top = *hits.values().max()?;
            if top * 2 < scanned {
                return None;
            }
            hits.iter().find(|(_, &n)| n == top).map(|(&off, _)| off)
        };

        let found = match (best(&id_hits), best(&text_hits)) {
            (Some(0), _) => Where::Id(0),
            (Some(off), None) => Where::Id(off),
            (Some(off), Some(text_off)) if off <= text_off => Where::Id(off),
            (_, Some(off)) => Where::Text(off),
            (None, None) => Where::Nowhere,
        };

        // ---- phase 2: confirm over the whole pool ----
        let mut total = 0;
        let mut covered = 0;

        for asset in instance.assets(pool) {
            let id = (asset.id as u64) & ID_MASK;
            total += 1;

            match found {
                Where::Id(offset) => {
                    let word =
                        instance.reader().try_read_i64(asset.header + offset as i64) as u64;
                    if (word & ID_MASK) == id {
                        covered += 1;
                    }
                }
                Where::Text(offset) => {
                    let word =
                        instance.reader().try_read_i64(asset.header + offset as i64) as u64;
                    if word != 0 && word < PLAUSIBLE_POINTER {
                        let text = instance.reader().read_string(word as i64);
                        if !text.is_empty() && id_of(&text) == id {
                            covered += 1;
                            recovered_total += 1;
                            let _ = writeln!(out, "{id:016x},{text},{pool}");
                        }
                    }
                }
                Where::Nowhere => {}
            }
        }

        let (label, offset) = match found {
            Where::Id(off) => ("id", off),
            Where::Text(off) => ("name as text", off),
            Where::Nowhere => ("not in the header", 0),
        };

        rows.push((pool, total, label, offset, covered));
        println!(
            "pool {pool:3}  {total:7} assets  {label:17} at +0x{offset:02x}  covers {covered:7} ({:5.1}%)",
            if total == 0 { 0.0 } else { covered as f64 * 100.0 / total as f64 }
        );
    }

    let _ = out.flush();

    println!("\n---");
    let at_zero = rows.iter().filter(|r| r.2 == "id" && r.3 == 0).count();
    let elsewhere = rows.iter().filter(|r| r.2 == "id" && r.3 != 0).count();
    let as_text = rows.iter().filter(|r| r.2 == "name as text").count();
    let nowhere = rows.iter().filter(|r| r.2 == "not in the header").count();

    println!("pools examined:                      {}", rows.len());
    println!("id at header+0x00:                   {at_zero}");
    println!("id at some other offset:             {elsewhere}");
    println!("name readable as text, hash checked: {as_text}");
    println!("name not in the header at all:       {nowhere}");
    println!("\nnames recovered and hash-verified:   {recovered_total}  -> {out_path}");
    println!(
        "\nEvery one of those hashes to an id the loader is holding, so they are confirmed by\n\
         construction. Whether they are *wanted* is a separate question: submit files only the\n\
         five asset types, and most of these pools are not among them."
    );
}
