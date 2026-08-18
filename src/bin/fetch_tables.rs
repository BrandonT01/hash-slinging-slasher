//! Fetches the community hash tables, or refreshes the ones already here.
//!
//! Nothing in this project works without them: they are what says a name is already known, and
//! without them every published name in the game looks like a discovery. See `slasher::tables`
//! for why they are fetched the way they are.
//!
//! Normally there is no need to run this by hand -- `preflight` does it at the start of a session
//! and `submit` re-checks before opening a pull request. It exists for when you want to force a
//! refresh in between.

use slasher::{paths, tables};

fn main() {
    let force = std::env::args().any(|argument| argument == "--force");
    let target = paths::tables();

    match tables::ensure(&target, force) {
        Ok(count) => {
            let folder = tables::csv_folder(&target);
            println!("\n{count} tables in {}", folder.display());

            if let Some(age) = tables::age(&folder) {
                println!("last changed {} minutes ago", age.as_secs() / 60);
            }

            if folder != target {
                println!("\nadd this to config.toml so the searches read them:\n");
                println!("  [paths]");
                println!("  tables = \"{}\"", folder.display().to_string().replace('\\', "/"));
            }
        }
        Err(why) => {
            eprintln!("\n{why}");
            std::process::exit(1);
        }
    }
}
