//! The community hash tables: what is already known, and therefore what is not a discovery.
//!
//! Nothing here works without them. A search that cannot read them does not fail -- it reports
//! every published name in the game as a new find, which is worse, because the mistake looks
//! exactly like success. So they are fetched before anything else runs, and they are a blocking
//! requirement rather than a nicety.
//!
//! They live in [`cod-name-db`](https://github.com/echo000/cod-name-db), which is also where
//! findings go. The same repository is both the thing a name is checked against and its
//! destination, which is why it has to be current at two moments: **at the start**, so there is
//! something to check against, and **again before submitting**, because a day is enough for
//! somebody else's submission to land and turn a find into a duplicate.
//!
//! Fetched by shelling out to `git`, so the grinding path keeps its zero dependencies. Shallow and
//! blobless, so the first fetch is the only expensive one and a refresh costs what changed.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, SystemTime};

/// Where the tables come from. Without this there is no app.
pub const UPSTREAM: &str = "https://github.com/echo000/cod-name-db.git";

/// The folder inside that repository holding the csv.
const FOLDER: &str = "csv";

/// How old the tables may be before they are refetched.
///
/// Submissions land within hours and this work's own results came back into the tables inside a
/// day, so anything older than this is judging finds against a set that has moved.
pub const STALE_AFTER: Duration = Duration::from_secs(12 * 60 * 60);

/// Where the checkout goes: beside the tables folder, not inside it, so the folder the searches
/// read holds csv and nothing else.
pub fn checkout(tables: &Path) -> PathBuf {
    if tables.join(".git").exists() {
        return tables.to_path_buf();
    }

    tables.parent().unwrap_or(Path::new(".")).join("cod-name-db")
}

/// The csv folder of a checkout, which is what the searches actually read.
pub fn csv_folder(tables: &Path) -> PathBuf {
    // A folder already full of csv is taken as-is: somebody has pointed the config straight at a
    // checkout they keep themselves, and re-fetching over the top of that would be rude.
    if count(tables) > 0 {
        return tables.to_path_buf();
    }

    let inside = checkout(tables).join(FOLDER);
    if count(&inside) > 0 {
        return inside;
    }

    inside
}

/// How many csv a folder holds.
pub fn count(folder: &Path) -> usize {
    std::fs::read_dir(folder)
        .map(|entries| {
            entries
                .flatten()
                .filter(|entry| {
                    entry.path().extension().and_then(|e| e.to_str()) == Some("csv")
                })
                .count()
        })
        .unwrap_or(0)
}

/// How long since the tables were last written, if they are here at all.
pub fn age(folder: &Path) -> Option<Duration> {
    let newest = std::fs::read_dir(folder)
        .ok()?
        .flatten()
        .filter_map(|entry| entry.metadata().ok()?.modified().ok())
        .max()?;

    SystemTime::now().duration_since(newest).ok()
}

/// Whether the tables are old enough to be worth refetching.
pub fn stale(folder: &Path) -> bool {
    age(folder).map(|age| age > STALE_AFTER).unwrap_or(true)
}

/// Makes sure current tables are on disk, fetching or refreshing as needed.
///
/// Returns how many csv are available. `force` refreshes even when they look recent, which is what
/// the check before a submission wants: by then the question is not "are these fresh enough to
/// search with" but "has anybody published these exact names while we were working".
pub fn ensure(tables: &Path, force: bool) -> Result<usize, String> {
    if !have_git() {
        return Err("git is not installed, and it is how the tables are fetched. \
                    Install it from https://git-scm.com."
            .to_owned());
    }

    let folder = csv_folder(tables);
    let here = count(&folder);

    if here > 0 && !force && !stale(&folder) {
        return Ok(here);
    }

    let checkout = checkout(tables);

    let ok = if checkout.join(".git").join("HEAD").exists() {
        if here > 0 {
            println!("refreshing the hash tables");
        }
        refresh(&checkout)
    } else {
        println!("fetching the hash tables from {UPSTREAM}");
        println!("a few hundred MB this once; refreshes afterwards cost only what changed.\n");
        clone(&checkout)
    };

    if !ok {
        // Failing with tables already present is survivable; failing with none is not.
        if here > 0 {
            return Err(format!(
                "the tables could not be refreshed, and the {here} already here may be stale"
            ));
        }

        return Err("the tables could not be fetched, and nothing can be judged without them"
            .to_owned());
    }

    let folder = csv_folder(tables);
    let now = count(&folder);

    if now == 0 {
        return Err(format!(
            "the fetch reported success but {} holds no csv",
            folder.display()
        ));
    }

    Ok(now)
}

/// A first fetch: no history, and no file contents beyond the paths actually wanted.
fn clone(into: &Path) -> bool {
    if let Some(parent) = into.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let cloned = git(
        None,
        &[
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            UPSTREAM,
            &into.display().to_string(),
        ],
    );

    // Only the csv, not the converter source or its build output.
    cloned && git(Some(into), &["sparse-checkout", "set", FOLDER])
}

/// A refresh: whatever changed, and nothing else.
fn refresh(checkout: &Path) -> bool {
    git(Some(checkout), &["fetch", "--depth", "1", "origin"])
        && (git(Some(checkout), &["reset", "--hard", "origin/HEAD"])
            || git(Some(checkout), &["reset", "--hard", "FETCH_HEAD"]))
}

fn have_git() -> bool {
    Command::new("git")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

fn git(directory: Option<&Path>, arguments: &[&str]) -> bool {
    let mut command = Command::new("git");
    command.args(arguments);

    if let Some(directory) = directory {
        command.current_dir(directory);
    }

    command
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A folder somebody has pointed straight at their own checkout is used as it is, rather than
    /// having a second copy fetched underneath it.
    #[test]
    fn a_folder_already_full_of_csv_is_used_directly() {
        let dir = std::env::temp_dir().join(format!("tbl_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("fnv1a_xmodels.csv"), b"1a,thing\n").unwrap();

        assert_eq!(csv_folder(&dir), dir);
        assert_eq!(count(&dir), 1);

        let _ = std::fs::remove_dir_all(&dir);
    }

    /// An empty folder resolves to where a checkout would put them.
    #[test]
    fn an_empty_folder_points_at_the_checkout() {
        let dir = std::env::temp_dir().join(format!("tbl_empty_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();

        assert!(csv_folder(&dir).ends_with(Path::new("cod-name-db").join("csv")));

        let _ = std::fs::remove_dir_all(&dir);
    }

    /// Absent tables count as stale, so the first run always fetches rather than deciding it has
    /// nothing to do.
    #[test]
    fn missing_tables_are_stale() {
        assert!(stale(Path::new("no-such-folder-anywhere")));
    }
}
