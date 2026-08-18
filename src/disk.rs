//! What this is using on disk, and what it left behind.
//!
//! A session fetches a few hundred megabytes of tables, writes results continuously, and builds a
//! Rust target directory that runs to gigabytes. None of that is a problem while it is wanted, and
//! all of it is a problem when it is abandoned -- and a grind is abandoned abruptly by design,
//! since the thing driving it stops when its limit does.
//!
//! So nothing here relies on a tidy shutdown. Every check reads the current state of the disk and
//! reports it, which means an ugly ending leaves evidence rather than a mess nobody notices until
//! the drive is full.
//!
//! The one rule: **findings are never cleanable.** A confirmed name is the entire product of the
//! work. Everything else here can be re-fetched or rebuilt, so everything else is fair game.

use std::fs;
use std::path::{Path, PathBuf};

/// Something taking up space that can safely go.
pub struct Leftover {
    pub path: PathBuf,
    pub bytes: u64,
    /// Why it is safe to remove, said in a way that can be printed to the user.
    pub because: &'static str,
}

/// How big a folder is, following it all the way down.
///
/// Returns zero for a path that is not there, since "absent" and "empty" want the same handling
/// everywhere this is used.
pub fn size(path: &Path) -> u64 {
    if path.is_file() {
        return path.metadata().map(|meta| meta.len()).unwrap_or(0);
    }

    let Ok(entries) = fs::read_dir(path) else {
        return 0;
    };

    entries
        .flatten()
        .map(|entry| {
            let path = entry.path();
            if path.is_dir() {
                size(&path)
            } else {
                path.metadata().map(|meta| meta.len()).unwrap_or(0)
            }
        })
        .sum()
}

/// Bytes as something a person reads without counting digits.
pub fn human(bytes: u64) -> String {
    const UNITS: [&str; 4] = ["B", "KB", "MB", "GB"];
    let mut value = bytes as f64;
    let mut unit = 0;

    while value >= 1000.0 && unit < UNITS.len() - 1 {
        value /= 1000.0;
        unit += 1;
    }

    if unit == 0 {
        format!("{bytes} B")
    } else {
        format!("{value:.1} {}", UNITS[unit])
    }
}

/// Everything safe to remove, largest first.
///
/// Deliberately conservative. A thing is only listed when it is certain it can be rebuilt or
/// re-fetched, because a tool that offers to free space and takes something irreplaceable is worse
/// than a full disk.
pub fn leftovers(root: &Path) -> Vec<Leftover> {
    let mut found = Vec::new();

    let mut consider = |relative: &str, because: &'static str| {
        let path = root.join(relative);
        let bytes = size(&path);
        if bytes > 0 {
            found.push(Leftover { path, bytes, because });
        }
    };

    consider(
        "target",
        "compiled output; `cargo build` remakes it",
    );
    consider(
        "logs",
        "run logs; the findings they describe are already saved",
    );

    // A clone that died partway leaves a directory git will not use and cannot resume. Its
    // presence is the whole signal, since a healthy checkout has a HEAD.
    let checkout = root.join("tables").join("cod-name-db");
    if checkout.exists() && !checkout.join(".git").join("HEAD").exists() {
        let bytes = size(&checkout);
        if bytes > 0 {
            found.push(Leftover {
                path: checkout,
                bytes,
                because: "an interrupted table fetch; it cannot be resumed, only redone",
            });
        }
    }

    // Partial writes from a run that was killed mid-file.
    for temporary in scan_for(root, &[".tmp", ".partial", ".part"]) {
        let bytes = size(&temporary);
        found.push(Leftover {
            path: temporary,
            bytes,
            because: "a partial file from a run that was cut off",
        });
    }

    found.sort_by(|a, b| b.bytes.cmp(&a.bytes));
    found
}

/// Files anywhere under a folder whose name ends in one of these, not following into the build
/// directory, which has thousands of its own and is handled whole.
fn scan_for(root: &Path, endings: &[&str]) -> Vec<PathBuf> {
    let mut found = Vec::new();
    walk(root, endings, &mut found, 0);
    found
}

fn walk(directory: &Path, endings: &[&str], found: &mut Vec<PathBuf>, depth: usize) {
    // Deep enough for the layout this uses, shallow enough that a stray symlink cannot spin.
    if depth > 6 {
        return;
    }

    let Ok(entries) = fs::read_dir(directory) else {
        return;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_lowercase();

        if path.is_dir() {
            if name == "target" || name == ".git" {
                continue;
            }
            walk(&path, endings, found, depth + 1);
            continue;
        }

        if endings.iter().any(|ending| name.ends_with(ending)) {
            found.push(path);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bytes_read_as_something_human() {
        assert_eq!(human(0), "0 B");
        assert_eq!(human(999), "999 B");
        assert_eq!(human(1_500), "1.5 KB");
        assert_eq!(human(336_000_000), "336.0 MB");
        assert_eq!(human(4_200_000_000), "4.2 GB");
    }

    #[test]
    fn size_counts_a_whole_tree_and_forgives_a_missing_one() {
        let dir = std::env::temp_dir().join(format!("disk_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(dir.join("deeper")).unwrap();
        fs::write(dir.join("a.txt"), b"12345").unwrap();
        fs::write(dir.join("deeper").join("b.txt"), b"1234567890").unwrap();

        assert_eq!(size(&dir), 15);
        assert_eq!(size(&dir.join("nothing-here")), 0);

        let _ = fs::remove_dir_all(&dir);
    }

    /// The findings are the product of the work and must never be offered up for deletion,
    /// whatever else is going on.
    #[test]
    fn findings_are_never_listed_as_removable() {
        let dir = std::env::temp_dir().join(format!("disk_keep_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(dir.join("findings")).unwrap();
        fs::write(dir.join("findings").join("xmodel.txt"), b"1a,p9_thing\n").unwrap();
        fs::create_dir_all(dir.join("logs")).unwrap();
        fs::write(dir.join("logs").join("run.log"), b"noise").unwrap();

        let listed = leftovers(&dir);

        assert!(listed.iter().any(|l| l.path.ends_with("logs")));
        assert!(
            !listed.iter().any(|l| l.path.to_string_lossy().contains("findings")),
            "findings must never be offered for deletion"
        );

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_partial_file_is_spotted() {
        let dir = std::env::temp_dir().join(format!("disk_part_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("xmodel.txt.partial"), b"half a file").unwrap();

        let listed = leftovers(&dir);
        assert!(listed.iter().any(|l| l.path.ends_with("xmodel.txt.partial")));

        let _ = fs::remove_dir_all(&dir);
    }
}
