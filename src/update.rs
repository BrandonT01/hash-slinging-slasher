//! Bringing the clone up to date, and knowing when it is not.
//!
//! A stale clone is the most expensive failure this project has. It is not loud: everything
//! runs, the search finds names, and the batch is submitted -- it is simply that somebody
//! already found those names last night, and the whole run was spent rediscovering them. That
//! has happened repeatedly, and byte-identical submissions from different contributors are what
//! it looks like from the outside.
//!
//! So freshness is not left to an instruction in a markdown file. It is done here, by a program,
//! before a search is allowed to start.
//!
//! **The Windows lock.** A `git pull` that has to replace a running `.exe` fails, because
//! Windows will not unlink a file that is currently executing. The one binary guaranteed to be
//! running when the pull happens is the one doing the pulling, so it copies itself out to the
//! temporary folder and re-runs from there first. See [`relaunch_from_temp`].

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

/// What state the clone is in relative to its remote.
#[derive(Debug, PartialEq)]
pub enum State {
    /// Up to date with the remote, nothing to do.
    Current,
    /// Behind by this many commits, and a fast-forward will fix it.
    Behind(usize),
    /// Local commits the remote has not got. Normal for a maintainer, fine to grind on.
    Ahead(usize),
    /// Both sides have moved. A pull cannot be a fast-forward, so this needs a person.
    Diverged { ahead: usize, behind: usize },
    /// Not a git checkout at all -- somebody downloaded a zip.
    NotAClone,
    /// A checkout with no remote to compare against.
    NoRemote,
    /// git itself could not answer.
    Unknown(String),
}

impl State {
    /// Whether this state means work would be done against knowledge somebody has already moved
    /// past.
    pub fn is_stale(&self) -> bool {
        matches!(self, Self::Behind(_) | Self::Diverged { .. })
    }
}

/// Whether git is installed at all. Everything here and the hash tables both need it.
pub fn have_git() -> bool {
    Command::new("git")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

/// The exact words to type to install git, for the machine this is running on.
pub fn install_git_hint() -> &'static str {
    if cfg!(windows) {
        "winget install --id Git.Git -e --source winget"
    } else if cfg!(target_os = "macos") {
        "brew install git   (or: xcode-select --install)"
    } else {
        "sudo apt install git   (or your distribution's package manager)"
    }
}

/// Asks the remote what it has, then says where this clone stands against it.
///
/// The fetch is done first and deliberately: `git status` compares against whatever was last
/// fetched, which on a clone that has sat for a day is a comparison with yesterday. A clone that
/// has never fetched reports itself perfectly up to date, which is the exact lie this is here to
/// prevent.
pub fn check(repo: &Path) -> State {
    if !repo.join(".git").exists() {
        return State::NotAClone;
    }

    let Some(remote) = upstream(repo) else {
        return State::NoRemote;
    };

    if !git_ok(repo, &["fetch", "--quiet", "origin"]) {
        return State::Unknown("the remote could not be reached".to_owned());
    }

    let counts = match git_out(repo, &["rev-list", "--left-right", "--count", &format!("HEAD...{remote}")]) {
        Ok(text) => text,
        Err(why) => return State::Unknown(why),
    };

    let mut numbers = counts.split_whitespace();
    let ahead: usize = numbers.next().and_then(|n| n.parse().ok()).unwrap_or(0);
    let behind: usize = numbers.next().and_then(|n| n.parse().ok()).unwrap_or(0);

    match (ahead, behind) {
        (0, 0) => State::Current,
        (0, behind) => State::Behind(behind),
        (ahead, 0) => State::Ahead(ahead),
        (ahead, behind) => State::Diverged { ahead, behind },
    }
}

/// Fast-forwards the clone onto the remote, stashing local edits rather than refusing.
///
/// Refusing would be the safe-looking choice and it is the wrong one here: the person who
/// started this has gone to bed, and "there are local changes, please sort them out" means the
/// whole night runs stale or does not run. So anything in the way is stashed -- which loses
/// nothing, since a stash can be recovered -- and what happened is said plainly.
pub fn bring_current(repo: &Path) -> Result<String, String> {
    // Tracked changes only. Untracked files are deliberately left alone: a contributor's own
    // scripts in `contrib/` and their results are untracked, and sweeping those into a stash to
    // win a fast-forward would be taking away the very thing they are here to contribute. An
    // untracked file only blocks a pull if the pull would overwrite it, and that case is rare
    // enough to be worth reporting rather than silently resolving.
    let dirty = !git_out(repo, &["status", "--porcelain", "--untracked-files=no"])
        .unwrap_or_default()
        .trim()
        .is_empty();

    let mut said = String::new();

    if dirty {
        if git_ok(repo, &["stash", "push", "-m", "set aside by `start` to update the clone"]) {
            said.push_str("local changes stashed (`git stash pop` brings them back); ");
        } else {
            return Err("there are local changes and they could not be stashed. Sort them out \
                        with `git status`, then run this again."
                .to_owned());
        }
    }

    if !git_ok(repo, &["pull", "--ff-only", "--quiet"]) {
        return Err(format!(
            "{said}the fast-forward pull failed. Run `git pull --ff-only` yourself and read what \
             it says -- this refuses to guess at a merge."
        ));
    }

    Ok(said)
}

/// The commit the clone is on, short form, for recording what a run was built from.
pub fn head(repo: &Path) -> String {
    git_out(repo, &["rev-parse", "--short", "HEAD"]).unwrap_or_else(|_| "unknown".to_owned())
}

/// Whether the compiled binaries are older than the source they were built from.
///
/// On Windows the binaries are committed, so a pull brings both and this normally stays quiet.
/// It speaks up in the case that actually bites: a clone where somebody edited `src/` and then
/// ran the committed exe, which is the old behaviour wearing the new source's name.
pub fn binaries_behind_source(repo: &Path) -> Option<String> {
    let newest_source = newest_mtime(&repo.join("src"))?;

    let built = if cfg!(windows) {
        newest_mtime(&repo.join("bin").join("windows"))
    } else {
        newest_mtime(&repo.join("target").join("release"))
    };

    // No build at all is a different problem, reported elsewhere.
    let built = built?;

    if newest_source > built {
        Some(if cfg!(windows) {
            "src/ is newer than bin/windows/. The committed binaries are rebuilt when src/ \
             changes upstream, so this means local edits -- rebuild with `cargo build --release` \
             and run that build, or the search is the old code."
                .to_owned()
        } else {
            "src/ is newer than target/release/. Rebuild with `cargo build --release`.".to_owned()
        })
    } else {
        None
    }
}

/// Copies this executable to the temporary folder and runs it from there, so a `git pull` is
/// free to replace the original.
///
/// Windows refuses to unlink a running executable, so a pull that would update `start.exe`
/// itself fails with a permissions error that reads like something much worse. Every other
/// binary in the repository is idle while this one runs, so moving only this one out of the way
/// is enough.
///
/// Returns the exit code of the copy when it took over, or `None` when the caller should carry
/// on itself -- because this is already the copy, or because the copy could not be made and
/// running in place is better than not running.
pub fn relaunch_from_temp(marker: &str) -> Option<i32> {
    if std::env::args().any(|argument| argument == marker) {
        return None;
    }

    if !cfg!(windows) {
        return None;
    }

    let Ok(exe) = std::env::current_exe() else {
        return None;
    };

    // Already living in the temporary folder: this is the copy, started some other way.
    if exe.starts_with(std::env::temp_dir()) {
        return None;
    }

    let name = exe.file_stem().and_then(|stem| stem.to_str()).unwrap_or("start");
    let copy = std::env::temp_dir().join(format!("slasher-{name}-{}.exe", std::process::id()));

    // Whatever previous runs left behind. Harmless, but it accumulates otherwise.
    sweep_old_copies(&std::env::temp_dir(), name);

    if std::fs::copy(&exe, &copy).is_err() {
        return None;
    }

    // The repository, resolved **now** -- while this is still the real executable and its own
    // ancestors still lead there. The copy about to run lives in the temporary folder, so
    // `paths::root()` cannot find the repository from it and falls back to the working directory.
    // Started from `bin\windows`, that put every default path in `bin\windows`: cod-name-db was
    // cloned into `bin/windows/cod-name-db`, findings and state went there too, and the real clone
    // was never touched. Nothing errored, and the next run would have done it again.
    //
    // Handing the copy the repository as its working directory fixes it at the root: `root()`
    // then finds `data/suffixes.txt` in `.` and stops, exactly as on a normal run.
    let here = std::fs::canonicalize(crate::paths::root())
        .unwrap_or_else(|_| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    let rest: Vec<String> = std::env::args().skip(1).collect();

    let status = Command::new(&copy)
        .arg(marker)
        .args(&rest)
        .current_dir(here)
        .status();

    let code = match status {
        Ok(status) => status.code().unwrap_or(1),
        // The copy would not run. Carrying on in place is worse than nothing only if the pull
        // then fails, and it says so clearly when it does.
        Err(_) => {
            let _ = std::fs::remove_file(&copy);
            return None;
        }
    };

    // The copy cannot delete itself while it is running, so the original does it afterwards.
    let _ = std::fs::remove_file(&copy);
    Some(code)
}

/// Removes copies left by earlier runs that have since exited.
fn sweep_old_copies(temp: &Path, name: &str) {
    let prefix = format!("slasher-{name}-");

    let Ok(entries) = std::fs::read_dir(temp) else {
        return;
    };

    for entry in entries.flatten() {
        let file = entry.file_name();
        let file = file.to_string_lossy();

        if file.starts_with(&prefix) && file.ends_with(".exe") {
            // A copy still running holds a lock and this simply fails, which is the wanted
            // behaviour -- two `start`s at once should not shoot each other.
            let _ = std::fs::remove_file(entry.path());
        }
    }
}

/// The tracking branch, as `origin/main` or whatever this clone actually uses.
fn upstream(repo: &Path) -> Option<String> {
    if let Ok(tracked) = git_out(repo, &["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]) {
        if !tracked.is_empty() {
            return Some(tracked);
        }
    }

    // No tracking branch set: fall back to the remote's own default.
    let head = git_out(repo, &["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]).ok()?;
    (!head.is_empty()).then_some(head)
}

fn newest_mtime(directory: &Path) -> Option<std::time::SystemTime> {
    let mut newest = None;
    let mut stack = vec![directory.to_path_buf()];

    while let Some(here) = stack.pop() {
        for entry in std::fs::read_dir(&here).ok()?.flatten() {
            let path = entry.path();

            if path.is_dir() {
                stack.push(path);
                continue;
            }

            if let Ok(modified) = entry.metadata().and_then(|data| data.modified()) {
                newest = Some(newest.map_or(modified, |seen: std::time::SystemTime| seen.max(modified)));
            }
        }
    }

    newest
}

fn git_ok(repo: &Path, arguments: &[&str]) -> bool {
    Command::new("git")
        .args(arguments)
        .current_dir(repo)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

fn git_out(repo: &Path, arguments: &[&str]) -> Result<String, String> {
    let output = Command::new("git")
        .args(arguments)
        .current_dir(repo)
        .output()
        .map_err(|error| format!("git could not be run: {error}"))?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_owned());
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A folder that is not a checkout says so rather than reporting itself up to date, which is
    /// the failure this whole module exists to prevent.
    #[test]
    fn a_folder_that_is_not_a_clone_says_so() {
        let dir = std::env::temp_dir().join(format!("upd_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();

        assert_eq!(check(&dir), State::NotAClone);

        let _ = std::fs::remove_dir_all(&dir);
    }

    /// Only the two states a search must not start in count as stale.
    #[test]
    fn behind_and_diverged_are_stale_and_nothing_else_is() {
        assert!(State::Behind(1).is_stale());
        assert!(State::Diverged { ahead: 1, behind: 1 }.is_stale());

        assert!(!State::Current.is_stale());
        assert!(!State::Ahead(3).is_stale());
        assert!(!State::NoRemote.is_stale());
    }
}
