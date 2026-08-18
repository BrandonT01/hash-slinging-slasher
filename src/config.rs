//! What this machine is set to grind, read from `config.toml` beside the binaries.
//!
//! The searches can look for names in every pool the game has, and eventually should. But the
//! cost of a search is carried by how many ids it is looking for: the peeled batches are
//! `wanted x endings` entries, the filter is sized from it, and every candidate is tested
//! against it. Searching two hundred pools when four of them hold what is actually wanted makes
//! every pass several times slower for names nobody asked for yet.
//!
//! So which pools a search targets is a setting rather than a constant. Narrow while the types
//! that matter are still far from complete; widened later, when they are close and the rest
//! becomes the interesting part. Capturing is unaffected -- a snapshot always holds every pool,
//! because throwing away a capture is expensive and re-taking one needs the game.
//!
//! The parser understands the subset of TOML this file actually uses -- comments, a section
//! header, `key = value`, and arrays of strings -- rather than pulling in a dependency to read
//! forty lines.

use std::collections::HashSet;
use std::fs;
use std::path::Path;

use crate::{pool_index, POOLS};

/// Where the settings live, looked for beside the working directory.
const CONFIG: &str = "config.toml";

/// The asset types worth grinding first, when nothing says otherwise.
///
/// These are the five that were asked for: models, animations, images, materials and sounds.
/// Everything else the game holds is still captured and still confirmable -- it is simply not
/// what a search spends its time looking for until these are close to done.
pub const DEFAULT_POOLS: &[&str] = &["xmodel", "xanim", "image", "material", "sound_asset"];

/// Which pools the searches should look in.
pub enum Targets {
    /// Every pool the game holds, including the ones nobody has named yet.
    Everything,
    /// Only these pool indexes.
    Only(HashSet<usize>),
}

impl Targets {
    /// Whether a search should be looking for ids in this pool.
    pub fn wants(&self, pool: usize) -> bool {
        match self {
            Self::Everything => true,
            Self::Only(pools) => pools.contains(&pool),
        }
    }

    /// How this reads in a run's opening lines, since a search that quietly ignores most of the
    /// game should say so rather than let the numbers be a surprise.
    pub fn describe(&self) -> String {
        match self {
            Self::Everything => "every pool".to_owned(),
            Self::Only(pools) => {
                let mut names: Vec<&str> = pools
                    .iter()
                    .filter_map(|index| POOLS.get(*index).copied())
                    .collect();
                names.sort_unstable();

                format!("{} pool(s): {}", pools.len(), names.join(", "))
            }
        }
    }
}

/// A path from the settings, if it is set to anything.
///
/// Absent rather than defaulted: a path nobody configured is a path this machine does not have,
/// and guessing at somebody's folder layout is how one person's Desktop ends up in everyone's
/// source code.
pub fn path(key: &str) -> Option<std::path::PathBuf> {
    let text = fs::read_to_string(CONFIG).unwrap_or_default();
    let raw = value_of(&text, key)?;
    let raw = raw.trim().trim_matches('"').trim_matches('\'');

    if raw.is_empty() {
        return None;
    }

    Some(std::path::PathBuf::from(raw))
}

/// Which game to grind, as the tag a snapshot carries internally.
///
/// The hash and the normalisation are identical across these games, and the tables are a plain
/// hash to name mapping with no game in them, so nothing about a search is Cold War specific
/// except which ids it is hunting. That is a snapshot, and a snapshot is a setting.
pub fn game() -> String {
    let text = fs::read_to_string(CONFIG).unwrap_or_default();

    value_of(&text, "game")
        .map(|raw| raw.trim().trim_matches('"').trim_matches('\'').to_uppercase())
        .filter(|raw| !raw.is_empty())
        .unwrap_or_else(|| crate::GAME.to_owned())
}

/// Reads the settings, falling back to the defaults when there is no file or it says nothing.
pub fn targets() -> Targets {
    read_targets(Path::new(CONFIG))
}

fn read_targets(path: &Path) -> Targets {
    let text = fs::read_to_string(path).unwrap_or_default();

    if flag(&text, "all_pools") == Some(true) {
        return Targets::Everything;
    }

    let listed = list(&text, "pools");
    let names: Vec<String> = if listed.is_empty() {
        DEFAULT_POOLS.iter().map(|name| (*name).to_owned()).collect()
    } else {
        listed
    };

    let mut pools = HashSet::new();
    for name in &names {
        match pool_index(name) {
            Some(index) => {
                pools.insert(index);
            }
            None => eprintln!("config.toml lists a pool this game has no name for: {name}"),
        }
    }

    Targets::Only(pools)
}

/// The value of a `key = true` line, ignoring comments.
fn flag(text: &str, key: &str) -> Option<bool> {
    value_of(text, key).and_then(|value| value.parse().ok())
}

/// The entries of a `key = ["a", "b"]` line.
fn list(text: &str, key: &str) -> Vec<String> {
    let Some(value) = value_of(text, key) else {
        return Vec::new();
    };

    value
        .trim_start_matches('[')
        .trim_end_matches(']')
        .split(',')
        .map(|entry| entry.trim().trim_matches('"').trim_matches('\'').to_owned())
        .filter(|entry| !entry.is_empty())
        .collect()
}

/// The raw right-hand side of `key = ...`, with any trailing comment removed.
fn value_of(text: &str, key: &str) -> Option<String> {
    for line in text.lines() {
        let line = line.trim();
        if line.starts_with('#') {
            continue;
        }

        let Some((name, value)) = line.split_once('=') else {
            continue;
        };

        if name.trim() != key {
            continue;
        }

        // A comment after the value, but not a `#` inside a quoted string.
        let value = match value.find('#') {
            Some(at) if value[..at].matches('"').count() % 2 == 0 => &value[..at],
            _ => value,
        };

        return Some(value.trim().to_owned());
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_default_is_the_five_types_that_matter() {
        let targets = read_targets(Path::new("no-such-config.toml"));

        assert!(targets.wants(pool_index("xmodel").unwrap()));
        assert!(targets.wants(pool_index("image").unwrap()));
        assert!(targets.wants(pool_index("sound_asset").unwrap()));
        assert!(!targets.wants(pool_index("localizeentry").unwrap()));
        assert!(!targets.wants(pool_index("gesture").unwrap()));
    }

    #[test]
    fn the_switch_opens_everything_up() {
        let text = "[search]\nall_pools = true\npools = [\"xmodel\"]\n";
        let dir = std::env::temp_dir().join(format!("cfg_all_{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("config.toml");
        fs::write(&path, text).unwrap();

        let targets = read_targets(&path);
        assert!(targets.wants(pool_index("localizeentry").unwrap()));
        assert!(targets.wants(999));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_listed_set_replaces_the_default_rather_than_adding_to_it() {
        let dir = std::env::temp_dir().join(format!("cfg_list_{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("config.toml");
        fs::write(&path, "pools = [\"localizeentry\", \"xanim\"]  # what I want\n").unwrap();

        let targets = read_targets(&path);
        assert!(targets.wants(pool_index("localizeentry").unwrap()));
        assert!(targets.wants(pool_index("xanim").unwrap()));
        assert!(!targets.wants(pool_index("xmodel").unwrap()));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn comments_and_quotes_are_not_taken_as_values() {
        assert_eq!(value_of("# pools = [\"no\"]\npools = [\"yes\"]", "pools").unwrap(), "[\"yes\"]");
        assert_eq!(flag("all_pools = false # not yet", "all_pools"), Some(false));
    }
}
