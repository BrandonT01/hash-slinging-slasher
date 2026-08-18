//! Sends what was found, after checking it is all still new.
//!
//! Two things make this more than a `git push`.
//!
//! **The tables move while you work.** A name that was unpublished when a pass started can be in
//! the tables by the time it finishes, because other people are submitting too. So the tables are
//! refreshed *here*, immediately before the pull request, and anything that has since been
//! published is simply dropped from the batch. Nothing is re-searched -- the candidates were
//! already confirmed against the game and that has not changed; the only question is whether they
//! are still *new*, and that is a set difference costing seconds.
//!
//! **Sessions end abruptly.** An assistant on a usage limit stops mid-job, so submitting is done
//! after every job rather than at the end of a night. That makes this safe to run repeatedly: it
//! keeps a ledger of what has already gone, and a run that was already sent is skipped rather than
//! sent twice. If a session dies, the next one submits the backlog.
//!
//! Filenames carry the date and time to the second, so two submissions never collide.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Stdio;

use slasher::{config, expected_by_chance, github, hash64, paths, stamp, tables, ID_MASK};

/// Where findings go. Set `submit_repo` in `config.toml` to override.
const DEFAULT_REPO: &str = "KingslayerKyle/hash-slinging-slasher";

/// The ledger of run folders already sent, so nothing is submitted twice.
const LEDGER: &str = ".submitted";

fn main() {
    let findings = paths::findings();
    let outbox = paths::submissions();

    // 1. Who we are. Without this the whole night has nowhere to go, which is why `preflight`
    //    checks it before any searching rather than leaving it until now.
    let Some(who) = github_user() else {
        match github::locate() {
            Some(gh) => eprintln!("not signed in to GitHub. Sign in with:\n    {}", gh.login_hint()),
            None => eprintln!(
                "the GitHub CLI (`gh`) is not installed. On Windows: winget install --id \
                 GitHub.cli (anywhere else, https://cli.github.com), then `gh auth login`."
            ),
        }
        eprintln!("(this is what `preflight` warns about before a grind starts.)");
        std::process::exit(1);
    };
    println!("submitting as {who}");

    // 2. What has not been sent yet.
    let sent = already_sent(&outbox);
    let pending: Vec<PathBuf> = run_folders(&findings)
        .into_iter()
        .filter(|folder| {
            let name = folder.file_name().unwrap_or_default().to_string_lossy().to_string();
            !sent.contains(&name)
        })
        .collect();

    if pending.is_empty() {
        println!("nothing new to submit -- every run here has already been sent.");
        return;
    }

    println!("{} run(s) not yet submitted", pending.len());

    // 3. Refresh the tables *now*, so the batch is judged against what the community has this
    //    minute rather than whenever the session started.
    println!("\nrefreshing the tables before sending, in case anything was published meanwhile");
    let table_folder = match tables::ensure(&paths::tables(), true) {
        Ok(_) => tables::csv_folder(&paths::tables()),
        Err(why) => {
            eprintln!("\n{why}");
            eprintln!("refusing to submit against tables that may be stale.");
            std::process::exit(1);
        }
    };

    let known = known_hashes(&table_folder);
    if known.len() < 1_000_000 {
        eprintln!(
            "the tables read short at {} hashes, which means they moved rather than that the game \
             got smaller. Not submitting.",
            known.len()
        );
        std::process::exit(1);
    }
    println!("{} hashes already published", known.len());

    // 4. Drop anything that has been published since. This is the cheap part and the whole reason
    //    a long grind does not have to be redone when the tables move under it.
    let mut batch: Vec<(String, String)> = Vec::new(); // (type, name)
    let mut dropped = 0_usize;

    for folder in &pending {
        for (kind, name) in names_in(folder) {
            let hash = hash64(&name);
            if known.contains(&hash) || known.contains(&(hash & ID_MASK)) {
                dropped += 1;
                continue;
            }
            batch.push((kind, name));
        }
    }

    // The same name can be reached by several runs; it only needs sending once.
    batch.sort();
    batch.dedup();

    println!(
        "\n{} names to send, {dropped} dropped because somebody published them while you were \
         grinding",
        batch.len()
    );

    if batch.is_empty() {
        println!("\nnothing left to send. Every name found had already been published.");
        record(&outbox, &pending);
        return;
    }

    // 5. Write the batch, named for the moment it was sent so nothing ever collides.
    let when = stamp();
    let folder = outbox.join(format!("{who}_{when}"));
    if let Err(error) = fs::create_dir_all(&folder) {
        eprintln!("could not make {}: {error}", folder.display());
        std::process::exit(1);
    }

    let mut by_kind: std::collections::BTreeMap<String, Vec<String>> = Default::default();
    for (kind, name) in &batch {
        by_kind.entry(kind.clone()).or_default().push(name.clone());
    }

    println!("\n{:<24} {:>8}", "type", "names");
    for (kind, names) in &by_kind {
        let path = folder.join(format!("{kind}_{when}.txt"));
        let mut text = String::new();
        for name in names {
            text.push_str(&format!("{:x},{name}\n", hash64(name) & ID_MASK));
        }

        if let Err(error) = fs::write(&path, text) {
            eprintln!("could not write {}: {error}", path.display());
            std::process::exit(1);
        }

        println!("{kind:<24} {:>8}", names.len());
    }

    // 6. The collision estimate, recorded rather than enforced. It is vanishingly small for any
    //    seeded method; it is worth carrying so a strange batch can be traced afterwards.
    let estimate = expected_by_chance(batch.len() as u64, known.len());

    // What each run has to say for itself -- which method, and how long it ground for. Written
    // by the run into its own folder; a folder without one is from an older or interrupted run.
    let accounts = run_accounts(&pending);

    let notes = folder.join(format!("about_{when}.md"));
    let _ = fs::write(
        &notes,
        format!(
            "# Submission {when}\n\n\
             - from: {who}\n\
             - names: {}\n\
             - dropped as already published: {dropped}\n\
             - runs included: {}\n\
             - searched: {}\n\
             - expected coincidental matches: {estimate:.6}\n\n\
             Every name here was confirmed against the game's own loaded assets, and checked \
             against the community tables immediately before sending.\n\
             \n## How these were found\n{accounts}",
            batch.len(),
            pending.len(),
            config::targets().describe(),
        ),
    );

    println!("\nwritten to {}", folder.display());

    // 7. The pull request. One per job, deliberately: a session that dies has already sent
    //    everything up to its last completed job.
    let repo = config::path("submit_repo")
        .map(|path| path.display().to_string())
        .unwrap_or_else(|| DEFAULT_REPO.to_owned());

    match open_pull_request(&repo, &folder, &when, &who, batch.len(), dropped, &accounts) {
        Ok(url) => {
            println!("\nsubmitted: {url}");
            record(&outbox, &pending);
        }
        Err(why) => {
            eprintln!("\nthe pull request could not be opened: {why}");
            eprintln!("the batch is saved at {} and will be sent next time.", folder.display());
            std::process::exit(1);
        }
    }
}

/// Each pending run's account of itself, as markdown: the folder, then whatever `notes.md` its
/// run wrote about which method ran and for how long.
fn run_accounts(pending: &[PathBuf]) -> String {
    let mut accounts = String::new();

    for folder in pending {
        let name = folder.file_name().unwrap_or_default().to_string_lossy();
        let note = fs::read_to_string(folder.join("notes.md"))
            .unwrap_or_else(|_| "- method: not recorded (an older or interrupted run)\n".to_owned());
        accounts.push_str(&format!("\n### {name}\n{note}"));
    }

    accounts
}

/// Every `run_*` folder in a findings tree, at any depth.
fn run_folders(findings: &Path) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(findings) else {
        return found;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with("run_") {
            found.push(path);
        } else if name != "superseded" {
            found.extend(run_folders(&path));
        }
    }

    found.sort();
    found
}

/// The `(type, name)` pairs in one run folder.
fn names_in(folder: &Path) -> Vec<(String, String)> {
    let mut found = Vec::new();
    let Ok(entries) = fs::read_dir(folder) else {
        return found;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("txt") {
            continue;
        }

        let Some(kind) = path.file_stem().and_then(|s| s.to_str()) else {
            continue;
        };

        let Ok(bytes) = fs::read(&path) else { continue };
        for line in String::from_utf8_lossy(&bytes).lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            let name = match line.split_once(',') {
                Some((_, name)) => name.trim(),
                None => line,
            };

            if !name.is_empty() {
                found.push((kind.to_owned(), name.to_owned()));
            }
        }
    }

    found
}

/// Every hash the tables resolve: the stored key, and the hash of the stored name.
fn known_hashes(folder: &Path) -> HashSet<u64> {
    let mut known = HashSet::new();
    let Ok(entries) = fs::read_dir(folder) else {
        return known;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("csv") {
            continue;
        }

        let Ok(bytes) = fs::read(&path) else { continue };
        for line in String::from_utf8_lossy(&bytes).lines() {
            let Some((key, name)) = line.split_once(',') else {
                continue;
            };

            if let Ok(value) = u64::from_str_radix(key.trim(), 16) {
                known.insert(value);
                known.insert(value & ID_MASK);
            }

            let hash = hash64(name.trim());
            known.insert(hash);
            known.insert(hash & ID_MASK);
        }
    }

    known
}

fn already_sent(outbox: &Path) -> HashSet<String> {
    fs::read_to_string(outbox.join(LEDGER))
        .unwrap_or_default()
        .lines()
        .map(|line| line.trim().to_owned())
        .filter(|line| !line.is_empty())
        .collect()
}

/// Notes the runs as sent. Appended, never rewritten, so a crash cannot lose the record and cause
/// the same names to be submitted twice.
fn record(outbox: &Path, sent: &[PathBuf]) {
    let _ = fs::create_dir_all(outbox);

    let mut text = fs::read_to_string(outbox.join(LEDGER)).unwrap_or_default();
    for folder in sent {
        let name = folder.file_name().unwrap_or_default().to_string_lossy();
        text.push_str(&format!("{name}\n"));
    }

    let _ = fs::write(outbox.join(LEDGER), text);
}

fn github_user() -> Option<String> {
    let output = github::command()
        .args(["api", "user", "--jq", ".login"])
        .stderr(Stdio::null())
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let who = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if who.is_empty() {
        None
    } else {
        Some(who)
    }
}
/// Sends the batch and opens the pull request, doing the whole of git on the contributor's behalf.
///
/// The point of this program is that somebody who has never used git can contribute, so none of
/// the usual sequence is asked of them. There is no clone, no working copy and no `git` on the
/// machine: the branch is built through GitHub's own API out of the files just written, which
/// means the submissions folder can live anywhere and need not be a repository at all.
///
/// It is one commit rather than one per file, so a run that dies halfway leaves the fork exactly
/// as it was rather than a branch holding half a batch.
fn open_pull_request(
    repo: &str,
    folder: &Path,
    when: &str,
    who: &str,
    names: usize,
    dropped: usize,
    accounts: &str,
) -> Result<String, String> {
    let branch = format!("findings/{who}-{when}");
    let base = default_branch(repo)?;

    // Push into a fork, unless this is the maintainer submitting to their own repository, where
    // there is nothing to fork and the branch simply goes straight in.
    let fork = if repo.starts_with(&format!("{who}/")) {
        repo.to_owned()
    } else {
        ensure_fork(repo, who)?
    };

    // A fork that has sat unused for a week is behind. Branching from a stale head still produces
    // a correct pull request, because the diff is taken against the merge base, so this is done
    // for tidiness and its failure is not worth stopping for.
    if fork != repo {
        let _ = gh(&["repo", "sync", &fork, "--source", repo], None);
    }

    let parent = head_sha(&fork, &base)?;
    let base_tree = tree_of(&fork, &parent)?;

    // The files, as they will appear in the repository. One folder per submission, named for who
    // sent it and when, so two people submitting at once cannot collide.
    let mut entries = Vec::new();
    for file in files_in(folder) {
        let Some(name) = file.file_name().and_then(|n| n.to_str()) else {
            continue;
        };

        let bytes = fs::read(&file).map_err(|error| format!("could not read {name}: {error}"))?;
        let blob = make_blob(&fork, &bytes)?;
        entries.push((format!("submissions/{who}_{when}/{name}"), blob));
    }

    if entries.is_empty() {
        return Err("the batch folder held no files to send".to_owned());
    }

    let title = format!("findings from {who}, {when} ({names} names)");
    let tree = make_tree(&fork, &base_tree, &entries)?;
    let commit = make_commit(&fork, &title, &tree, &parent)?;
    make_branch(&fork, &branch, &commit)?;

    let body = format!(
        "{names} asset names, confirmed against the game's own loaded assets and checked against \
         the tables immediately before sending.\n\n\
         - dropped as already published: {dropped}\n\
         - submitted by: @{who}\n\n\
         Files are named with the time they were sent, so nothing collides with an earlier batch. \
         Every hash here is re-verified against the shipped snapshot by CI; nothing is taken on \
         the word of the client that found it.\n\n\
         ## How these were found\n{accounts}",
    );

    // `who:branch` is how GitHub names a branch that lives in somebody else's fork.
    let head = if fork == repo { branch.clone() } else { format!("{who}:{branch}") };

    gh(
        &[
            "api",
            &format!("repos/{repo}/pulls"),
            "-X",
            "POST",
            "-f",
            &format!("title={title}"),
            "-f",
            &format!("head={head}"),
            "-f",
            &format!("base={base}"),
            "-f",
            &format!("body={body}"),
            "--jq",
            ".html_url",
        ],
        None,
    )
}

/// Every file directly inside the batch folder, in a settled order.
fn files_in(folder: &Path) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = fs::read_dir(folder)
        .into_iter()
        .flatten()
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.is_file())
        .collect();

    found.sort();
    found
}

/// The branch a pull request should be opened against, asked of the repository rather than assumed
/// to be `main` -- upstream has been called `master` for years in this corner of the world.
fn default_branch(repo: &str) -> Result<String, String> {
    gh(&["api", &format!("repos/{repo}"), "--jq", ".default_branch"], None)
}

/// The contributor's fork, made if they have not got one.
///
/// Forking is asynchronous: GitHub answers before the repository exists, so the fork is waited for
/// rather than used immediately. Somebody who already has a fork skips the wait entirely.
fn ensure_fork(repo: &str, who: &str) -> Result<String, String> {
    let name = repo.split('/').next_back().unwrap_or(repo);
    let fork = format!("{who}/{name}");

    if gh(&["api", &format!("repos/{fork}"), "--jq", ".name"], None).is_ok() {
        return Ok(fork);
    }

    println!("making your fork of {repo}");
    gh(&["repo", "fork", repo, "--clone=false"], None)
        .map_err(|why| format!("could not fork {repo}: {why}"))?;

    for _ in 0..30 {
        if gh(&["api", &format!("repos/{fork}"), "--jq", ".name"], None).is_ok() {
            return Ok(fork);
        }
        std::thread::sleep(std::time::Duration::from_secs(1));
    }

    Err(format!("{fork} was asked for but has not appeared after thirty seconds"))
}

fn head_sha(repo: &str, branch: &str) -> Result<String, String> {
    gh(
        &["api", &format!("repos/{repo}/git/ref/heads/{branch}"), "--jq", ".object.sha"],
        None,
    )
}

fn tree_of(repo: &str, commit: &str) -> Result<String, String> {
    gh(&["api", &format!("repos/{repo}/git/commits/{commit}"), "--jq", ".tree.sha"], None)
}

/// Uploads one file's bytes. Base64 rather than plain text, so a name holding something that is
/// not valid utf-8 is carried exactly rather than mangled on the way.
fn make_blob(repo: &str, bytes: &[u8]) -> Result<String, String> {
    let body = format!("{{\"content\":\"{}\",\"encoding\":\"base64\"}}", base64(bytes));
    gh(&["api", &format!("repos/{repo}/git/blobs"), "--input", "-", "--jq", ".sha"], Some(&body))
}

/// Lays the new files on top of the branch as it already stands. Without `base_tree` this would
/// describe a repository holding nothing but the submission.
fn make_tree(repo: &str, base_tree: &str, entries: &[(String, String)]) -> Result<String, String> {
    let files: Vec<String> = entries
        .iter()
        .map(|(path, blob)| {
            format!(
                "{{\"path\":{},\"mode\":\"100644\",\"type\":\"blob\",\"sha\":{}}}",
                quoted(path),
                quoted(blob)
            )
        })
        .collect();

    let body = format!(
        "{{\"base_tree\":{},\"tree\":[{}]}}",
        quoted(base_tree),
        files.join(",")
    );

    gh(&["api", &format!("repos/{repo}/git/trees"), "--input", "-", "--jq", ".sha"], Some(&body))
}

fn make_commit(repo: &str, message: &str, tree: &str, parent: &str) -> Result<String, String> {
    let body = format!(
        "{{\"message\":{},\"tree\":{},\"parents\":[{}]}}",
        quoted(message),
        quoted(tree),
        quoted(parent)
    );

    gh(&["api", &format!("repos/{repo}/git/commits"), "--input", "-", "--jq", ".sha"], Some(&body))
}

fn make_branch(repo: &str, branch: &str, commit: &str) -> Result<String, String> {
    gh(
        &[
            "api",
            &format!("repos/{repo}/git/refs"),
            "-X",
            "POST",
            "-f",
            &format!("ref=refs/heads/{branch}"),
            "-f",
            &format!("sha={commit}"),
            "--jq",
            ".ref",
        ],
        None,
    )
}

/// Runs `gh`, which already knows who the contributor is, and returns what it said.
///
/// Failures carry gh's own words rather than an exit code, because the useful part of a refused
/// request is the sentence GitHub sent back with it.
fn gh(args: &[&str], body: Option<&str>) -> Result<String, String> {
    let mut command = github::command();
    command.args(args).stdout(Stdio::piped()).stderr(Stdio::piped());

    if body.is_some() {
        command.stdin(Stdio::piped());
    }

    let mut child = command.spawn().map_err(|error| format!("gh could not be run: {error}"))?;

    if let Some(text) = body {
        use std::io::Write;
        let mut stdin = child.stdin.take().ok_or("gh would not take the request body")?;
        stdin
            .write_all(text.as_bytes())
            .map_err(|error| format!("the request body could not be sent to gh: {error}"))?;
    }

    let output = child.wait_with_output().map_err(|error| format!("gh did not finish: {error}"))?;

    if !output.status.success() {
        let said = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stderr),
            String::from_utf8_lossy(&output.stdout)
        );

        return Err(said.trim().to_owned());
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

/// A json string, escaped. Only the handful of things json insists on, since everything here is a
/// path, a sha or a message this program wrote itself.
fn quoted(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');

    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }

    out.push('"');
    out
}

/// Base64, written out rather than depended on: a build with no features has no dependencies at
/// all, and that is the property that lets this be published in the first place.
fn base64(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);

    for chunk in bytes.chunks(3) {
        let a = chunk[0] as u32;
        let b = *chunk.get(1).unwrap_or(&0) as u32;
        let c = *chunk.get(2).unwrap_or(&0) as u32;
        let triple = (a << 16) | (b << 8) | c;

        out.push(ALPHABET[(triple >> 18) as usize & 63] as char);
        out.push(ALPHABET[(triple >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 { ALPHABET[(triple >> 6) as usize & 63] as char } else { '=' });
        out.push(if chunk.len() > 2 { ALPHABET[triple as usize & 63] as char } else { '=' });
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The rfc's own examples, plus the two lengths that need padding. A wrong encoder here would
    /// upload a corrupted file that still looked like a successful submission.
    #[test]
    fn base64_matches_the_rfc() {
        for (plain, encoded) in [
            ("", ""),
            ("f", "Zg=="),
            ("fo", "Zm8="),
            ("foo", "Zm9v"),
            ("foob", "Zm9vYg=="),
            ("fooba", "Zm9vYmE="),
            ("foobar", "Zm9vYmFy"),
        ] {
            assert_eq!(base64(plain.as_bytes()), encoded, "encoding {plain:?}");
        }
    }

    /// Bytes above the ascii range go through untouched, which is the reason for encoding the
    /// files at all rather than sending them as text.
    #[test]
    fn base64_carries_bytes_that_are_not_text() {
        assert_eq!(base64(&[0xff, 0xfe, 0xfd]), "//79");
        assert_eq!(base64(&[0x00]), "AA==");
    }

    /// A path or a message carrying a quote must not be able to break the request open.
    #[test]
    fn json_strings_are_escaped() {
        assert_eq!(quoted("a\"b"), "\"a\\\"b\"");
        assert_eq!(quoted("a\\b"), "\"a\\\\b\"");
        assert_eq!(quoted("a\nb"), "\"a\\nb\"");
        assert_eq!(quoted("plain"), "\"plain\"");
    }
}
