//! Says what this is using on disk, and offers to give back what it does not need.
//!
//! A grind ends abruptly by design: the thing driving it stops when its limit does, usually in the
//! middle of something. So nothing here assumes a tidy shutdown — it reads the disk as it actually
//! is and reports what is left over, which means an ugly ending leaves evidence rather than a slow
//! leak nobody notices until the drive is full.
//!
//! Run with no arguments it only *reports*. `--clean` actually removes things. That way it is safe
//! to run at the start of every session, which is the point: the check has to be routine, or a
//! session that died last week is still holding gigabytes today.
//!
//! **Findings are never removable.** A confirmed name is the whole product of the work. Everything
//! this offers to delete can be rebuilt or re-fetched.

use std::path::{Path, PathBuf};

use slasher::{disk, paths};

fn main() {
    let clean = std::env::args().any(|argument| argument == "--clean");
    let root = PathBuf::from(".");

    println!("what this is using on disk\n");

    // What is here on purpose, so the total is understandable rather than alarming.
    let mut kept: Vec<(String, PathBuf)> = vec![
        ("findings (never deleted)".to_owned(), paths::findings()),
        ("snapshots".to_owned(), paths::snapshots()),
        ("hash tables".to_owned(), paths::tables()),
    ];
    kept.push(("submissions".to_owned(), paths::submissions()));

    let mut total = 0_u64;

    for (label, path) in &kept {
        let bytes = disk::size(path);
        total += bytes;

        if bytes > 0 {
            println!("  {:<28} {:>10}", label, disk::human(bytes));
        }
    }

    let leftovers = disk::leftovers(&root);
    let reclaimable: u64 = leftovers.iter().map(|left| left.bytes).sum();

    if leftovers.is_empty() {
        println!("\nnothing left over. {} in use, all of it wanted.", disk::human(total));
        return;
    }

    println!("\n{} that can go:\n", disk::human(reclaimable));

    for left in &leftovers {
        println!(
            "  {:<40} {:>10}   {}",
            shorten(&left.path),
            disk::human(left.bytes),
            left.because
        );
    }

    if !clean {
        println!("\n{} in use, {} of it reclaimable.", disk::human(total + reclaimable), disk::human(reclaimable));
        println!("run with --clean to free it.");
        return;
    }

    println!();
    let mut freed = 0_u64;

    for left in &leftovers {
        let removed = if left.path.is_dir() {
            std::fs::remove_dir_all(&left.path)
        } else {
            std::fs::remove_file(&left.path)
        };

        match removed {
            Ok(()) => {
                freed += left.bytes;
                println!("  removed {:<38} {:>10}", shorten(&left.path), disk::human(left.bytes));
            }
            Err(error) => eprintln!("  could not remove {}: {error}", shorten(&left.path)),
        }
    }

    println!("\nfreed {}.", disk::human(freed));
}

/// A path short enough to line up in a column, since the absolute ones are mostly noise.
fn shorten(path: &Path) -> String {
    let text = path.display().to_string();
    let text = text.trim_start_matches("./").trim_start_matches(".\\");

    if text.len() <= 40 {
        return text.to_owned();
    }

    format!("...{}", &text[text.len() - 37..])
}
