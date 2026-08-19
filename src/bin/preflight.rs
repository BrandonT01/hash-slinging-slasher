//! `start` under its older name.
//!
//! This used to be a read-only check that reported problems and fixed none of them. Reporting
//! turned out not to be enough: it said the clone should be updated, and it was not; it said to
//! sign in to GitHub, and people did not know how; and it could not say anything at all about the
//! pull requests other contributors had open, which is where duplicate work actually comes from.
//!
//! So the checks became a program that does the work, and this name kept because it is what the
//! documentation, the muscle memory and half the assistants in the world already say. It is the
//! same program as `start`, not a similar one -- see `slasher::startup`.

use slasher::{startup, update};

fn main() {
    if let Some(code) = update::relaunch_from_temp(startup::RELAUNCHED) {
        std::process::exit(code);
    }

    if !startup::run() {
        std::process::exit(1);
    }
}
