//! Finding the GitHub CLI, wherever the installer put it.
//!
//! Everything that talks to GitHub goes through `gh`, and the commonest way that fails has
//! nothing to do with GitHub at all: on Windows the installer amends the machine's PATH, but
//! every terminal that was already open keeps the PATH it started with. So somebody who
//! installed gh a minute ago, exactly as told, is standing in the one shell that cannot see
//! it -- and a tool that only asks PATH reports gh missing, which reads as the install having
//! failed. The standard install locations are checked directly so a just-installed gh simply
//! works, and the sign-in instructions are printed in a form that works in the shell the
//! person is actually in.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::OnceLock;

/// Where `gh` was found, and whether the shell that started this process could find it too.
#[derive(Clone)]
pub struct Gh {
    pub program: PathBuf,
    pub on_path: bool,
}

impl Gh {
    /// A command ready to be given arguments.
    pub fn command(&self) -> Command {
        Command::new(&self.program)
    }

    /// The exact words to type to sign in, from the shell the person is in right now.
    ///
    /// When gh is only reachable by its full path, the plain `gh auth login` every guide gives
    /// fails with "not recognized", which looks like a broken install to somebody who has never
    /// used a terminal. So the full-path form is given first and the tidy form second.
    pub fn login_hint(&self) -> String {
        if self.on_path {
            "gh auth login".to_owned()
        } else {
            format!(
                "& \"{}\" auth login\n          (that full path matters: this terminal predates the install and cannot\n          see the plain `gh` command. A newly opened terminal can.)",
                self.program.display()
            )
        }
    }
}

/// Looks for `gh`: on PATH first, then in the places installers put it. Cached, because the
/// answer cannot change inside one run and locating it costs a process spawn.
pub fn locate() -> Option<Gh> {
    static FOUND: OnceLock<Option<Gh>> = OnceLock::new();
    FOUND.get_or_init(find).clone()
}

/// A command for callers that just want to run gh and let any failure carry gh's own words.
/// The located program when there is one, the plain name otherwise, so the error for a missing
/// install still says `gh` rather than a path that never existed.
pub fn command() -> Command {
    match locate() {
        Some(gh) => gh.command(),
        None => Command::new("gh"),
    }
}

fn find() -> Option<Gh> {
    if works(Path::new("gh")) {
        return Some(Gh { program: PathBuf::from("gh"), on_path: true });
    }

    for candidate in installed_locations() {
        if candidate.is_file() && works(&candidate) {
            return Some(Gh { program: candidate, on_path: false });
        }
    }

    None
}

/// Where the supported installers leave gh when PATH does not say.
fn installed_locations() -> Vec<PathBuf> {
    let mut found = Vec::new();

    if cfg!(windows) {
        // winget and the MSI, machine-wide.
        for variable in ["ProgramFiles", "ProgramFiles(x86)"] {
            if let Ok(programs) = std::env::var(variable) {
                found.push(PathBuf::from(programs).join("GitHub CLI").join("gh.exe"));
            }
        }

        // The per-user MSI.
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            found.push(PathBuf::from(local).join("Programs").join("GitHub CLI").join("gh.exe"));
        }
    } else {
        // Homebrew on either kind of Mac, Linuxbrew, and the package managers' usual spot.
        for place in [
            "/opt/homebrew/bin/gh",
            "/usr/local/bin/gh",
            "/home/linuxbrew/.linuxbrew/bin/gh",
        ] {
            found.push(PathBuf::from(place));
        }
    }

    found
}

/// Whether this really is a runnable gh, asked of the program itself rather than judged by the
/// file existing -- a half-removed install leaves files that cannot answer.
fn works(program: &Path) -> bool {
    Command::new(program)
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}
