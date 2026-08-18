//! Derives image names from material names.
//!
//! An image is usually named for the material that uses it, with a map suffix on the end and a
//! different beginning: a material called `mc/mtl_wpn_t9_ak47_barrel` has images called
//! `i_wpn_t9_ak47_barrel_c`, `..._n`, `..._g` and so on. So the material tables, which are
//! published and complete, describe images that are not.
//!
//! That makes this a far narrower search than the general one. There is no scraping and no
//! guessing at what a name might be: the stem comes from a material known to exist, and the
//! ending comes from a table, which is asked for every ending it holds rather than only the
//! common ones. Both tables are read for endings, because an ending is an ending whichever kind
//! of asset it was seen on, and the material table holds two hundred thousand the image table
//! does not.

use slasher::loader::{loaded_assets, wanted_for_search};
use slasher::search::run_best;
use slasher::{
    endings_of, paths, table_names, table_keys, tables_look_complete, Results, pool_label,
};

/// The tables the stems and the endings come from.
const MATERIALS: &str = "fnv1a_xmaterials";
const IMAGES: &str = "fnv1a_ximages";

/// The beginnings an image carries where its material carried something else. The empty one is
/// there because an image is as often the bare stem as the prefixed one.
const OPENINGS: &[&str] = &["i_", "", "i_mtl_", "mtl_", "c_", "i_c_"];

/// The beginnings stripped off a material name to leave the part the image shares, longest first
/// so the longest match is the one taken.
const STRIP: &[&str] = &["i_mtl_", "mtl_mtl_", "mtl_", "i_c_", "i_", "c_"];

/// Mesh entries cannot be named by any rule here: the tail of one is a hash of the mesh. They
/// are left out so that a candidate has half as many ids to land on by coincidence.
const UNREACHABLE: &[&str] = &["xmodelmesh"];

/// The parts of a material name an image might share, longest first.
///
/// A material is a path and carries a beginning the image does not: the directory goes, then
/// whichever of the known beginnings it starts with. Every step is kept, because which one the
/// image shares is not knowable in advance.
fn stems_of(name: &str) -> Vec<String> {
    let lowered = name.to_lowercase();
    let mut found: Vec<String> = Vec::new();

    let push = |value: &str, found: &mut Vec<String>| {
        if value.len() >= 4 && !found.iter().any(|held| held == value) {
            found.push(value.to_owned());
        }
    };

    push(&lowered, &mut found);

    let bare = match lowered.rsplit_once('/') {
        Some((_, rest)) => rest,
        None => &lowered,
    };
    push(bare, &mut found);

    // Past whichever beginning it has, then once more, since a doubled one occurs.
    let mut rest = bare;
    for _ in 0..2 {
        let mut stripped = rest;
        for opening in STRIP {
            if let Some(shorter) = rest.strip_prefix(opening) {
                if shorter.len() >= 4 {
                    stripped = shorter;
                    break;
                }
            }
        }

        if stripped == rest {
            break;
        }

        push(stripped, &mut found);
        rest = stripped;
    }

    found
}

fn main() {
    let began = std::time::Instant::now();
    let (assets, _) = match loaded_assets() {
        Ok(loaded) => loaded,
        Err(reason) => {
            eprintln!("{reason}");
            return;
        }
    };

    let known = table_keys();
    println!("hashes already resolved by the tables: {}", known.len());

    if !tables_look_complete(&known) {
        eprintln!("the tables read short. Check {}", paths::tables().display());
        return;
    }

    let wanted = wanted_for_search(&assets, &known, UNREACHABLE);
    println!("unnamed assets a name here could belong to: {}", wanted.len());
    drop(known);

    let endings = endings_of(&[IMAGES, MATERIALS]);
    println!("endings taken from both tables: {}", endings.len());

    // Every material known to exist: the published ones, the ones this search has found before,
    // and the ones the general search has found. A material no table holds is exactly the kind
    // whose images no table holds either.
    let mut results = Results::load(paths::findings());
    let mut materials = table_names(MATERIALS);
    println!("materials from the table: {}", materials.len());

    materials.extend(results.names("material"));
    let general = Results::load(paths::findings());
    let found = general.names("material");
    println!("materials the general search has confirmed: {}", found.len());
    materials.extend(found);

    let stems: Vec<String> = materials.iter().flat_map(|name| stems_of(name)).collect();
    println!("stems those materials offer: {}", stems.len());
    drop(materials);

    let openings: Vec<String> = OPENINGS.iter().map(|text| (*text).to_owned()).collect();

    for (id, name) in run_best(&openings, &endings, &stems, &wanted, false) {
        results.add(&pool_label(wanted[&id]), id, name);
    }

    println!("this run added {}", results.added());
    results.write(paths::findings()).expect("the results");

    match results.write_run(paths::findings(), "images") {
        Ok(Some(folder)) => {
            println!("this run's own names: {}", folder.display());
            let _ = Results::note_run(
                &folder,
                "images derived from materials (images_from_materials)",
                "each confirmed material name stripped of mtl_ and retried as an image name \
                 with every semantic suffix, both prefixed and bare",
                began.elapsed(),
            );
        }
        Ok(None) => println!("this run found nothing new"),
        Err(error) => eprintln!("the run folder could not be written: {error}"),
    }
}
