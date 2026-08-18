//! Checks everything a grind needs *before* the grind, and refuses to be vague about it.
//!
//! A pass takes an hour and a night's work takes several. Every one of those hours is wasted if
//! the findings cannot be submitted at the end, and the commonest reason they cannot is that
//! nobody was signed in to GitHub. That is a ten second check which has to happen first, not a
//! discovery made at four in the morning with a full results folder and no way to send it.
//!
//! Everything here is read-only. It changes nothing and fixes nothing; it says plainly what is
//! wrong and what to type, and exits non-zero so a script or an assistant cannot mistake a
//! failure for a pass.

use std::path::Path;

use slasher::{config, disk, github, paths, snapshot, tables};

fn main() {
    println!("checking what a grind needs before starting one\n");

    let mut blocked: Vec<String> = Vec::new();
    let mut warned = Vec::new();

    // 1. GitHub, first and loudest. Without it a night of grinding has nowhere to go. The
    //    three ways this goes wrong get three different instructions, because the person
    //    reading them may never have used a terminal before: `gh` genuinely missing, `gh`
    //    installed but invisible to a terminal older than the install, and `gh` present but
    //    not signed in.
    match github() {
        GitHub::SignedIn { who, on_path } => {
            if on_path {
                println!("  [ok]      signed in to GitHub as {who}");
            } else {
                println!(
                    "  [ok]      signed in to GitHub as {who} (gh found by its install path; \
                     this terminal is older than the install and does not know the `gh` \
                     command, which is fine)"
                );
            }
        }
        GitHub::NotSignedIn(gh) => {
            println!("  [BLOCKED] GitHub: not signed in");
            blocked.push(format!(
                "Sign in to GitHub. Run:\
                 \n              {}\
                 \n          then answer its questions: GitHub.com, HTTPS, and login with a web\
                 \n          browser. Findings cannot be submitted without this.",
                gh.login_hint()
            ));
        }
        GitHub::NotInstalled => {
            println!("  [BLOCKED] GitHub: the GitHub CLI (`gh`) is not installed");
            blocked.push(
                "Install the GitHub CLI. On Windows:\
                 \n              winget install --id GitHub.cli\
                 \n          (anywhere else, see https://cli.github.com). Then sign in:\
                 \n              gh auth login\
                 \n          and run this check again. If the terminal says it does not know\
                 \n          `gh` right after installing, that terminal is older than the\
                 \n          install -- just run this check again and it will say what to type.\
                 \n          Findings cannot be submitted without it, so do this before grinding."
                    .to_owned(),
            );
        }
    }

    // 2. A snapshot. This is what a name is confirmed against, and the only file that cannot be
    //    regenerated without owning the game.
    let snapshots = Path::new("snapshots");
    let mut games = Vec::new();

    if let Ok(entries) = std::fs::read_dir(snapshots) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("ids") {
                continue;
            }

            match snapshot::Snapshot::read(&path) {
                Ok(snap) => {
                    println!(
                        "  [ok]      snapshot for {} holds {} assets",
                        snap.game(),
                        snap.len()
                    );
                    games.push(snap.game().to_owned());
                }
                Err(why) => println!("  [BLOCKED] {} is unreadable: {why}", path.display()),
            }
        }
    }

    if games.is_empty() {
        println!("  [BLOCKED] no snapshot found in snapshots/");
        blocked.push(
            "The snapshots ship with the repository and never change, so this means\
             \n          one has been deleted, or `snapshots` in config.toml points\
             \n          elsewhere. Nothing can be confirmed without one."
                .to_owned(),
        );
    }

    // 3. The tables, pulled now rather than later. Nothing can be judged without them: a search
    //    that cannot read them reports every published name in the game as a discovery, which
    //    looks exactly like success. They also go stale in a day, so this refreshes as well as
    //    fetches.
    let target = paths::tables();
    match tables::ensure(&target, false) {
        Ok(count) => {
            let folder = tables::csv_folder(&target);
            let age = tables::age(&folder)
                .map(|age| format!(", last changed {}h ago", age.as_secs() / 3600))
                .unwrap_or_default();
            println!("  [ok]      {count} hash tables to exclude against{age}");
        }
        Err(why) => {
            println!("  [BLOCKED] hash tables: {why}");
            blocked.push(
                "Fetch the hash tables. They come from https://github.com/echo000/cod-name-db
          and nothing here works without them:
              cargo run --release --bin fetch-tables"
                    .to_owned(),
            );
        }
    }

    // 4. What this machine is set to hunt. Not a problem, but a surprise if unsaid.
    println!("  [ok]      {}", config::targets().describe());

    // 5. Disk. A grind ends abruptly by design, so this checks every startup rather than
    //    trusting that the last session cleaned up after itself.
    let findings = paths::findings();
    if !findings.exists() && std::fs::create_dir_all(&findings).is_err() {
        warned.push("the findings folder could not be created; results will have nowhere to go.");
    }

    let leftovers = disk::leftovers(Path::new("."));
    let reclaimable: u64 = leftovers.iter().map(|left| left.bytes).sum();

    if reclaimable > 200_000_000 {
        println!(
            "  [warn]    {} of leftovers from previous sessions -- `cargo run --release --bin tidy`",
            disk::human(reclaimable)
        );
    } else {
        println!("  [ok]      disk is tidy ({} reclaimable)", disk::human(reclaimable));
    }

    if !warned.is_empty() {
        println!();
        for warning in &warned {
            println!("  [warn]    {warning}");
        }
    }

    if blocked.is_empty() {
        println!("\nready. Nothing here will stop a grind.");
        return;
    }

    println!("\n{} thing(s) must be fixed before grinding:\n", blocked.len());
    for (number, fix) in blocked.iter().enumerate() {
        println!("  {}. {fix}\n", number + 1);
    }

    std::process::exit(1);
}

/// The three states GitHub access can be in, each needing different words.
enum GitHub {
    SignedIn { who: String, on_path: bool },
    NotSignedIn(github::Gh),
    NotInstalled,
}

/// Who GitHub thinks we are, or exactly what stands in the way of it knowing.
///
/// `gh auth status` is asked rather than a token file read, because it is the same question the
/// submission itself will ask and there is no value in the two disagreeing. gh itself is looked
/// for beyond PATH, because the commonest failure is a terminal older than the install.
fn github() -> GitHub {
    let Some(gh) = github::locate() else {
        return GitHub::NotInstalled;
    };

    let output = match gh.command().arg("auth").arg("status").output() {
        Ok(output) => output,
        Err(_) => return GitHub::NotInstalled,
    };

    if !output.status.success() {
        return GitHub::NotSignedIn(gh);
    }

    // `gh` writes this to stderr on older versions and stdout on newer ones.
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );

    // "Logged in to github.com account NAME (...)" on current versions, "as NAME" on older ones.
    for line in text.lines() {
        for marker in ["account ", " as "] {
            if let Some(at) = line.find(marker) {
                let rest = line[at + marker.len()..].trim();
                let name = rest
                    .split_whitespace()
                    .next()
                    .unwrap_or("")
                    .trim_matches(|c: char| !c.is_ascii_alphanumeric() && c != '-' && c != '_');

                if !name.is_empty() {
                    return GitHub::SignedIn { who: name.to_owned(), on_path: gh.on_path };
                }
            }
        }
    }

    GitHub::SignedIn { who: "an account it did not name".to_owned(), on_path: gh.on_path }
}
