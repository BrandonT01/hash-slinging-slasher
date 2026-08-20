//! Attaching to the loader process and walking the asset pools it exposes.
//!
//! The loader maps fast files into its own process without running the game, and writes a
//! state file when a handler initialises: an eight character game id, the address of its
//! asset pool array, then its string pool. Assets live in a linked list per pool rather than
//! in the game's contiguous arrays.

use std::cell::RefCell;
use std::collections::HashMap;
use std::io;
use std::path::{Path, PathBuf};

use windows::core::PWSTR;
use windows::Win32::Foundation::{CloseHandle, HANDLE, MAX_PATH};
use windows::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS,
};
use windows::Win32::System::Threading::{
    OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_WIN32, PROCESS_QUERY_LIMITED_INFORMATION,
};

use crate::memory::ProcessReader;

/// The loader's executable, without its extension, most preferred first.
///
/// The loader ships as two builds of the same program. They map the same games and expose the
/// same pools at the same offsets, so either can be read. What they hold at those offsets is
/// not always the same, though - the two have been seen to record a fast file's name in
/// different shapes under the same version number - so nothing is read on the strength of which
/// build it came from. Both can also be running at once, and only one of them can be the
/// instance a load reads, so they are ranked here rather than raced and the windowed build
/// wins.
pub const PROCESS_NAMES: [&str; 2] = [WINDOWED_PROCESS, COMMAND_LINE_PROCESS];

/// The build with a window of its own.
pub const WINDOWED_PROCESS: &str = "Cordycep";

/// The build driven from a command line.
pub const COMMAND_LINE_PROCESS: &str = "Cordycep.CLI";

/// What the windowed build writes when a handler initialises.
const WINDOWED_STATE: &str = "CurrentHandler.json";

/// What the command line build writes.
const COMMAND_LINE_STATE: &str = "CurrentHandler.csi";

/// The loader always allocates this many pools.
pub const POOL_COUNT: usize = 512;

/// Size of one entry in the asset pool array.
const POOL_STRIDE: i64 = 0x28;

/// Size of one asset entry.
const ASSET_SIZE: usize = 0x60;

/// How the fast file's name might be recorded, most likely first.
///
/// Builds of the loader do not agree on this. Some hold the name as a standard library string
/// within the record and differ only in what precedes it; others hold a length and a pointer to
/// text kept outside the record entirely. A record read the wrong way yields no name at all,
/// and every asset in the game then belongs to the same nameless zone, so each shape is tried
/// in turn and the first to give a name is the one that build records.
const FAST_FILE_NAME_SHAPES: [NameShape; 3] = [
    NameShape::StdString(0x8),
    NameShape::StdString(0x0),
    NameShape::LengthAndText(0x0),
];

/// The smallest command line state file that can carry a game id and both addresses.
const STATE_FILE_SIZE: usize = 24;

/// How much of the string pool is taken at a time, and the finer step its last block is
/// approached with once a whole one runs off the end of the committed memory.
const STRING_POOL_BLOCK: usize = 1 << 20;
const STRING_POOL_TAIL: usize = 1 << 12;

/// How far the pool is followed before giving up on finding its end. Well past what a title has
/// been seen to hold, and there only so that a bad address cannot read forever.
const STRING_POOL_LIMIT: usize = 256 << 20;

/// The lengths of text taken from the pool as a name. Anything shorter is as likely to be two
/// bytes of a number, and nothing a game names an asset is anywhere near the upper bound.
const STRING_POOL_SHORTEST: usize = 4;
const STRING_POOL_LONGEST: usize = 160;

/// One running loader.
struct Loader {
    process_id: u32,

    /// Which of [`PROCESS_NAMES`] it is running under, which says which state file speaks for
    /// it.
    name: &'static str,
}

/// What a loader has loaded, however it recorded it.
struct HandlerState {
    game_id: String,
    pools_address: i64,
    strings_address: i64,
}

/// The windowed build's state file.
///
/// The field names are the whole of the contract with it. Anything else it writes - the game's
/// folder, the module it mapped, the size of the string pool - is not needed to walk the pools
/// and is left where it is.
#[derive(serde::Deserialize)]
struct RecordedState {
    /// The process the rest of this describes.
    pid: u32,

    /// The eight character game id, packed a character to a byte.
    game_id: i64,

    pools_addr: i64,
    strings_addr: i64,
}

/// One asset pool.
#[derive(Clone, Copy, Debug, Default)]
pub struct XAssetPool {
    pub root: i64,
    pub end: i64,
    pub lookup_table: i64,
    pub header_memory: i64,
    pub asset_memory: i64,
}

/// One asset entry within a pool's linked list.
#[derive(Clone, Copy, Debug, Default)]
pub struct XAsset {
    pub header: i64,
    pub temp: i64,
    pub next: i64,
    pub previous: i64,
    pub id: i64,
    pub kind: i64,
    pub header_size: i64,
    pub extended_data_pointer_offset: i64,
    pub extended_data_size: i64,
    pub first_child: i64,
    pub last_child: i64,
    pub owner: i64,
}

impl XAsset {
    fn parse(bytes: &[u8]) -> Self {
        let field = |index: usize| {
            i64::from_le_bytes(
                bytes[index * 8..index * 8 + 8]
                    .try_into()
                    .expect("eight bytes"),
            )
        };

        Self {
            header: field(0),
            temp: field(1),
            next: field(2),
            previous: field(3),
            id: field(4),
            kind: field(5),
            header_size: field(6),
            extended_data_pointer_offset: field(7),
            extended_data_size: field(8),
            first_child: field(9),
            last_child: field(10),
            owner: field(11),
        }
    }
}

/// One way a build of the loader records the name of a fast file.
#[derive(Clone, Copy)]
enum NameShape {
    /// A standard library string at this offset into the record, which is a sixteen byte inline
    /// buffer or a pointer, followed by its size and capacity.
    StdString(i64),

    /// A length at this offset into the record, followed by a pointer to text held outside it.
    LengthAndText(i64),
}

impl NameShape {
    /// The name this shape reads out of a record, or nothing where the record is not that
    /// shape.
    fn read(self, instance: &CordycepInstance, address: i64) -> String {
        match self {
            Self::StdString(offset) => instance.read_std_string(address + offset),
            Self::LengthAndText(offset) => instance.read_length_and_text(address + offset),
        }
    }
}

/// A running loader instance with a game loaded.
pub struct CordycepInstance {
    reader: ProcessReader,

    /// The eight character id of the game currently loaded.
    game_id: String,

    pools_address: i64,

    /// The loader's string pool; script strings are stored as offsets into it.
    strings_address: i64,

    /// The directory the loader is running from, which is where its state file lives.
    directory: PathBuf,

    fast_file_names: RefCell<HashMap<i64, String>>,
}

impl CordycepInstance {
    /// Whether the loader is running at all, under either of its names.
    pub fn is_running() -> bool {
        !find_loaders().is_empty()
    }

    /// Attaches to the running loader, or reports what is missing.
    ///
    /// Both builds can be running at once, so the instances are tried in the order they are
    /// preferred and the first with a game loaded is the one read. If none of them can be read,
    /// what is reported is why the most preferred one could not be: that is the instance
    /// whoever pressed Load was most likely looking at.
    pub fn open() -> io::Result<Self> {
        let mut failure = None;

        for loader in find_loaders() {
            match Self::attach(&loader) {
                Ok(instance) => return Ok(instance),
                Err(error) => {
                    failure.get_or_insert(error);
                }
            }
        }

        Err(failure.unwrap_or_else(|| {
            io::Error::other("Cordycep is not running. Start Cordycep and load a game first.")
        }))
    }

    /// Attaches to one running loader, if it has a game loaded.
    fn attach(loader: &Loader) -> io::Result<Self> {
        let directory = process_directory(loader.process_id).ok_or_else(|| {
            io::Error::other(
                "Failed to locate Cordycep's directory. Try running Amadeus as administrator.",
            )
        })?;

        let state = handler_state(&directory, loader)?;

        Ok(Self {
            reader: ProcessReader::open(loader.process_id)?,
            game_id: state.game_id,
            pools_address: state.pools_address,
            strings_address: state.strings_address,
            directory,
            fast_file_names: RefCell::new(HashMap::new()),
        })
    }

    /// The process reader itself, for anything not yet wrapped in a method here. A binary that
    /// needs to look at a structure this module does not model -- an asset header's own fields,
    /// say -- reads it through this rather than opening a second handle to the same process.
    pub fn reader(&self) -> &ProcessReader {
        &self.reader
    }

    pub fn game_id(&self) -> &str {
        &self.game_id
    }

    pub fn pools_address(&self) -> i64 {
        self.pools_address
    }

    pub fn strings_address(&self) -> i64 {
        self.strings_address
    }

    pub fn directory(&self) -> &Path {
        &self.directory
    }

    /// Every string in the loader's string pool.
    ///
    /// The later games record an asset by the hash of its name and never by the name, but the
    /// strings those hashes were made from are still here: the loader keeps the pool the game's
    /// script strings live in, and the names go in with them. Hashing what is in it puts a great
    /// many of those names back without a lookup table having been published for them at all.
    ///
    /// The pool is one block of null terminated text. Nothing to hand says how long it is - the
    /// windowed build records the size and the command line build does not - so it is read in
    /// blocks until one will not read, and the end of the committed block is where it stops.
    /// That answer is the same for both builds.
    pub fn string_pool(&self) -> Vec<String> {
        let mut strings = Vec::new();
        let mut buffer = vec![0_u8; STRING_POOL_BLOCK];
        let mut block = STRING_POOL_BLOCK;
        let mut offset = 0_usize;

        // Carried across blocks, so a string lying over a boundary is still read whole.
        let mut current: Vec<u8> = Vec::new();
        let mut overlong = false;

        while offset < STRING_POOL_LIMIT {
            let read = self
                .reader
                .try_read(self.strings_address + offset as i64, &mut buffer[..block]);

            if read == 0 {
                // The last block of the pool is rarely a whole one, so the end is approached
                // once at a finer step before giving up on it.
                if block > STRING_POOL_TAIL {
                    block = STRING_POOL_TAIL;
                    continue;
                }

                break;
            }

            for &byte in &buffer[..read] {
                if (0x20..0x7F).contains(&byte) {
                    if current.len() == STRING_POOL_LONGEST {
                        overlong = true;
                        current.clear();
                    } else if !overlong {
                        current.push(byte);
                    }

                    continue;
                }

                if byte == 0 && !overlong && current.len() >= STRING_POOL_SHORTEST {
                    strings.push(current.iter().map(|&byte| byte as char).collect());
                }

                current.clear();
                overlong = false;
            }

            offset += read;
        }

        strings
    }

    pub(crate) fn read_pool(&self, index: usize) -> io::Result<XAssetPool> {
        let bytes = self
            .reader
            .read_bytes(self.pools_address + index as i64 * POOL_STRIDE, 40)?;

        let field = |slot: usize| {
            i64::from_le_bytes(
                bytes[slot * 8..slot * 8 + 8]
                    .try_into()
                    .expect("eight bytes"),
            )
        };

        Ok(XAssetPool {
            root: field(0),
            end: field(1),
            lookup_table: field(2),
            header_memory: field(3),
            asset_memory: field(4),
        })
    }

    /// Walks a pool's linked list, skipping the root slot and temp assets, which are name
    /// only placeholders.
    pub fn assets(&self, index: usize) -> Assets<'_> {
        Assets {
            reader: &self.reader,
            next: self.read_pool(index).map(|pool| pool.root).unwrap_or(0),
        }
    }

    /// The name of the fast file that owns an asset.
    pub fn fast_file_name(&self, address: i64) -> String {
        if address == 0 {
            return "unknown".to_owned();
        }

        if let Some(name) = self.fast_file_names.borrow().get(&address) {
            return name.clone();
        }

        let name = FAST_FILE_NAME_SHAPES
            .iter()
            .map(|shape| shape.read(self, address))
            .find(|candidate| names_a_fast_file(candidate))
            .unwrap_or_else(|| "unknown".to_owned());

        self.fast_file_names
            .borrow_mut()
            .insert(address, name.clone());

        name
    }

    /// Reads a length followed by a pointer to the text it counts, which is always held
    /// outside the record rather than within it.
    fn read_length_and_text(&self, address: i64) -> String {
        let length = self.reader.try_read_i64(address);
        let data = self.reader.try_read_i64(address + 0x8);

        if length <= 0 || length > 256 || data == 0 {
            return String::new();
        }

        let mut buffer = vec![0_u8; length as usize];

        if self.reader.try_read(data, &mut buffer) == buffer.len() {
            buffer.iter().map(|&byte| byte as char).collect()
        } else {
            String::new()
        }
    }

    /// Reads a standard library string, which is a sixteen byte inline buffer or a pointer,
    /// followed by its size and capacity. The capacity says which of the two is in use.
    fn read_std_string(&self, address: i64) -> String {
        let size = self.reader.try_read_i64(address + 0x10);
        let capacity = self.reader.try_read_i64(address + 0x18);

        // An inline buffer always reports the one capacity it has, so a record read at the
        // wrong offset is turned away here rather than being followed to a pointer that is
        // really somebody else's field.
        if size <= 0 || size > 256 || capacity < size || (capacity < 16 && capacity != 15) {
            return String::new();
        }

        let data = if capacity >= 16 {
            self.reader.try_read_i64(address)
        } else {
            address
        };

        if data == 0 {
            return String::new();
        }

        let mut buffer = vec![0_u8; size as usize];

        if self.reader.try_read(data, &mut buffer) == buffer.len() {
            buffer.iter().map(|&byte| byte as char).collect()
        } else {
            String::new()
        }
    }
}

/// Iterates one pool's linked list of assets.
pub struct Assets<'a> {
    reader: &'a ProcessReader,
    next: i64,
}

impl Iterator for Assets<'_> {
    type Item = XAsset;

    fn next(&mut self) -> Option<XAsset> {
        let mut buffer = [0_u8; ASSET_SIZE];

        while self.next != 0 {
            // A failed read means the list is being rebuilt underneath us, or the game was
            // unloaded. Either way there is nothing further to walk.
            if self.reader.try_read(self.next, &mut buffer) != ASSET_SIZE {
                self.next = 0;
                return None;
            }

            let asset = XAsset::parse(&buffer);
            self.next = asset.next;

            if asset.header != 0 && asset.temp == 0 {
                return Some(asset);
            }
        }

        None
    }
}

/// Whether text taken out of a record is a fast file's name rather than whatever else happened
/// to read as a string at that offset.
///
/// A fast file is named the way a file is, so text carrying anything a name cannot hold was
/// read from the wrong member and is no answer at all.
fn names_a_fast_file(text: &str) -> bool {
    !text.is_empty()
        && text.chars().all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '_' | '-' | '.' | '/')
        })
}

/// Where an executable's name stands among the loader's, if it is one of them at all. The whole
/// name has to match: a process that merely begins the same way is somebody else's.
fn preference(stem: &str) -> Option<usize> {
    PROCESS_NAMES
        .iter()
        .position(|name| stem.eq_ignore_ascii_case(name))
}

/// What the loader in a folder has loaded, taken from whichever state file speaks for this
/// process.
///
/// The two builds record it differently, and both write into the same folder when they are
/// installed side by side. The windowed one writes the process id alongside the addresses, so
/// its file can be matched to the instance it describes - which it has to be, because the
/// alternative is walking one game's pools in another game's process and calling the result an
/// export. The command line one writes a file that names nobody, so that file is only read for
/// the build that writes it.
fn handler_state(directory: &Path, loader: &Loader) -> io::Result<HandlerState> {
    let data = directory.join("Data");

    if let Some(state) = recorded_state(&data.join(WINDOWED_STATE), loader.process_id)? {
        return Ok(state);
    }

    if loader.name == COMMAND_LINE_PROCESS {
        return command_line_state(&data.join(COMMAND_LINE_STATE));
    }

    Err(io::Error::other(
        "Cordycep has no game loaded yet. Load one and try again.",
    ))
}

/// The windowed build's state, if it is there and speaks for this process.
///
/// A file naming another process says nothing about the memory about to be read: it belongs to
/// the other build, or to a run that has since ended. Either way this instance has nothing
/// loaded as far as anyone can prove, which is the answer given.
fn recorded_state(path: &Path, process_id: u32) -> io::Result<Option<HandlerState>> {
    if !path.exists() {
        return Ok(None);
    }

    // Read shared, because the loader rewrites this the moment a different game is loaded and
    // an exclusive open would fail exactly then.
    let text = std::fs::read_to_string(path).map_err(|_| {
        io::Error::other("Cordycep is changing games right now. Try again in a moment.")
    })?;

    let state: RecordedState = serde_json::from_str(&text).map_err(|_| {
        io::Error::other(
            "Cordycep's state file is incomplete, which usually means it is still loading.",
        )
    })?;

    if state.pid != process_id {
        return Ok(None);
    }

    Ok(Some(HandlerState {
        game_id: game_id(state.game_id),
        pools_address: state.pools_addr,
        strings_address: state.strings_addr,
    }))
}

/// The command line build's state: the eight character game id, then the two addresses.
fn command_line_state(path: &Path) -> io::Result<HandlerState> {
    if !path.exists() {
        return Err(io::Error::other(
            "Cordycep has no game loaded yet. Load one and try again.",
        ));
    }

    // Read shared, for the reason the other one is.
    let state = std::fs::read(path).map_err(|_| {
        io::Error::other("Cordycep is changing games right now. Try again in a moment.")
    })?;

    if state.len() < STATE_FILE_SIZE {
        return Err(io::Error::other(
            "Cordycep's state file is truncated, which usually means it is still loading.",
        ));
    }

    let word = |offset: usize| {
        i64::from_le_bytes(state[offset..offset + 8].try_into().expect("eight bytes"))
    };

    Ok(HandlerState {
        game_id: state[..8].iter().map(|&byte| byte as char).collect(),
        pools_address: word(8),
        strings_address: word(16),
    })
}

/// The eight character game id the windowed build packs into a number, a character to a byte in
/// the order they are written. The other build writes those same eight characters as text.
fn game_id(packed: i64) -> String {
    packed
        .to_le_bytes()
        .iter()
        .map(|&byte| byte as char)
        .collect()
}

/// Every running loader, most preferred first.
///
/// One pass over the process list rather than one per name, and ordered by which build it is
/// rather than by whatever order the system happens to list them in, so which instance gets
/// read does not come down to which was started first. Instances of the same build keep the
/// order they were listed in, so a second copy is only reached if the first has nothing loaded.
fn find_loaders() -> Vec<Loader> {
    let Ok(snapshot) = (unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) }) else {
        return Vec::new();
    };

    let mut entry = PROCESSENTRY32W {
        dwSize: size_of::<PROCESSENTRY32W>() as u32,
        ..Default::default()
    };

    let mut found: Vec<(usize, Loader)> = Vec::new();

    if unsafe { Process32FirstW(snapshot, &mut entry) }.is_ok() {
        loop {
            let length = entry
                .szExeFile
                .iter()
                .position(|&unit| unit == 0)
                .unwrap_or(entry.szExeFile.len());
            let executable = String::from_utf16_lossy(&entry.szExeFile[..length]);
            let stem = executable
                .strip_suffix(".exe")
                .or_else(|| executable.strip_suffix(".EXE"))
                .unwrap_or(&executable);

            if let Some(rank) = preference(stem) {
                found.push((
                    rank,
                    Loader {
                        process_id: entry.th32ProcessID,
                        name: PROCESS_NAMES[rank],
                    },
                ));
            }

            if unsafe { Process32NextW(snapshot, &mut entry) }.is_err() {
                break;
            }
        }
    }

    let _ = unsafe { CloseHandle(snapshot) };

    found.sort_by_key(|(rank, _)| *rank);

    found.into_iter().map(|(_, loader)| loader).collect()
}

/// The directory a process's executable lives in.
fn process_directory(process_id: u32) -> Option<PathBuf> {
    let handle: HANDLE =
        unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, process_id) }.ok()?;

    let mut buffer = [0_u16; MAX_PATH as usize];
    let mut length = buffer.len() as u32;

    let result = unsafe {
        QueryFullProcessImageNameW(
            handle,
            PROCESS_NAME_WIN32,
            PWSTR(buffer.as_mut_ptr()),
            &mut length,
        )
    };

    let _ = unsafe { CloseHandle(handle) };
    result.ok()?;

    let path = PathBuf::from(String::from_utf16_lossy(&buffer[..length as usize]));

    path.parent().map(Path::to_path_buf)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Both builds can be running at once, and which of them a load reads must not come down to
    /// the order the system happens to list them in.
    #[test]
    fn the_plain_build_is_preferred_over_the_command_line_one() {
        assert_eq!(preference("Cordycep"), Some(0));
        assert_eq!(preference("Cordycep.CLI"), Some(1));
        assert!(preference("Cordycep") < preference("Cordycep.CLI"));
    }

    #[test]
    fn a_name_is_matched_whatever_case_it_is_written_in() {
        assert_eq!(preference("cordycep"), Some(0));
        assert_eq!(preference("CORDYCEP.cli"), Some(1));
    }

    #[test]
    fn a_name_that_only_begins_the_same_is_not_the_loader() {
        assert_eq!(preference("Cordycep.CLI.Updater"), None);
        assert_eq!(preference("CordycepLauncher"), None);
        assert_eq!(preference(""), None);
    }

    /// The windowed build's file, in the shape it writes it. These field names are the whole of
    /// the contract with that build, and a rename would otherwise go unnoticed until a load
    /// failed in front of somebody.
    #[test]
    fn the_windowed_builds_state_is_read_from_the_shape_it_writes() {
        let text = r#"{
            "pid": 7356,
            "game_id": 3985772854892383298,
            "game_dir": "D:/_COD/_BO7_S4",
            "game_module_path": "C:\\Cordycep\\Data\\Dumps\\cod_dump.exe",
            "pools_addr": 1486424146000,
            "strings_addr": 1486627012608,
            "str_pool_size_addr": 1486205577544,
            "flags": []
        }"#;

        let state: RecordedState = serde_json::from_str(text).expect("the state file parses");

        assert_eq!(state.pid, 7356);
        assert_eq!(state.pools_addr, 1_486_424_146_000);
        assert_eq!(state.strings_addr, 1_486_627_012_608);
    }

    /// The name is looked for at more than one offset, so whatever comes back has to be judged
    /// on its own before a zone is named after it.
    #[test]
    fn a_fast_file_is_named_the_way_a_file_is() {
        assert!(names_a_fast_file("core_ui"));
        assert!(names_a_fast_file("en_core_bootstrap"));
        assert!(names_a_fast_file("zm_common"));
        assert!(names_a_fast_file("1080_core_ui"));
    }

    /// Text read from the wrong member of the record can still parse as a string, and naming a
    /// zone after whatever it happened to hold is worse than admitting the name is not known.
    #[test]
    fn text_from_the_wrong_member_is_not_a_name() {
        assert!(!names_a_fast_file(""));
        assert!(!names_a_fast_file("core ui"));
        assert!(!names_a_fast_file("\u{1}\u{2}\u{3}"));
        assert!(!names_a_fast_file("core_ui\u{7f}"));
    }

    /// Both builds name the game the same way, one as text and one as the number those same
    /// characters make, so both arrive at the id the game table is keyed by.
    #[test]
    fn a_packed_game_id_reads_as_the_characters_it_is_made_of() {
        assert_eq!(game_id(3_985_772_854_892_383_298), "BLACKOP7");
        assert_eq!(game_id(i64::from_le_bytes(*b"REMAST00")), "REMAST00");
    }
}
