//! The one command to remember.
//!
//! Updates the clone, installs and checks git and the GitHub CLI, refreshes the community hash
//! tables, reads every open submission so tonight does not duplicate one, and only then says a
//! search may begin. It exits non-zero when it cannot, and the searches refuse to run until it
//! has passed, so there is nothing here anybody has to remember to do in the right order.
//!
//! Everything it does is in `slasher::startup`. This file is small on purpose: `preflight` is the
//! same program under the name the older documentation uses, and the two must never drift.

use slasher::{startup, update};

fn main() {
    // A `git pull` cannot replace a running executable on Windows, and this executable is the one
    // guaranteed to be running when the pull happens. So it steps out of its own way first.
    if let Some(code) = update::relaunch_from_temp(startup::RELAUNCHED) {
        std::process::exit(code);
    }

    if !startup::run() {
        std::process::exit(1);
    }
}
