//! Reading memory out of another process.

use std::io;

use windows::Win32::Foundation::{CloseHandle, HANDLE};
use windows::Win32::System::Diagnostics::Debug::ReadProcessMemory;
use windows::Win32::System::Threading::{OpenProcess, PROCESS_QUERY_INFORMATION, PROCESS_VM_READ};

/// The longest string read out of the target, which bounds a scan that never finds a
/// terminator.
const MAX_STRING_LENGTH: usize = 256;

/// A handle to another process, open for reading.
pub struct ProcessReader {
    handle: HANDLE,
}

// The handle is only ever read through, and the Windows API permits that from any thread.
unsafe impl Send for ProcessReader {}
unsafe impl Sync for ProcessReader {}

impl ProcessReader {
    /// Opens a process for reading.
    pub fn open(process_id: u32) -> io::Result<Self> {
        let handle = unsafe {
            OpenProcess(
                PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
                false,
                process_id,
            )
        }
        .map_err(|error| {
            io::Error::other(format!(
                "Failed to open process {process_id} ({error}). Try running as administrator."
            ))
        })?;

        Ok(Self { handle })
    }

    /// Reads raw bytes, returning how many were actually read.
    ///
    /// Asset data contains fields that are not always valid pointers, so a caller has to be
    /// able to attempt a read and find out it failed rather than treating that as an error.
    pub fn try_read(&self, address: i64, buffer: &mut [u8]) -> usize {
        if address <= 0 || buffer.is_empty() {
            return 0;
        }

        let mut read = 0_usize;

        let ok = unsafe {
            ReadProcessMemory(
                self.handle,
                address as *const _,
                buffer.as_mut_ptr().cast(),
                buffer.len(),
                Some(&mut read),
            )
        };

        if ok.is_ok() {
            read
        } else {
            0
        }
    }

    /// Reads exactly `size` bytes, failing if the whole range is not readable.
    pub fn read_bytes(&self, address: i64, size: usize) -> io::Result<Vec<u8>> {
        let mut buffer = vec![0_u8; size];

        if self.try_read(address, &mut buffer) != size {
            return Err(io::Error::other(format!(
                "Failed to read {size} bytes at {address:#X}."
            )));
        }

        Ok(buffer)
    }

    /// Reads a 32 bit value, yielding zero where the address cannot be read.
    pub fn try_read_i32(&self, address: i64) -> i32 {
        let mut buffer = [0_u8; 4];

        if self.try_read(address, &mut buffer) == 4 {
            i32::from_le_bytes(buffer)
        } else {
            0
        }
    }

    /// Reads a pointer, yielding zero where the address cannot be read.
    pub fn try_read_i64(&self, address: i64) -> i64 {
        let mut buffer = [0_u8; 8];

        if self.try_read(address, &mut buffer) == 8 {
            i64::from_le_bytes(buffer)
        } else {
            0
        }
    }

    /// Reads a null terminated ASCII string, giving up after [`MAX_STRING_LENGTH`] bytes.
    ///
    /// A read that straddles the end of a committed region fails outright rather than
    /// returning the readable prefix, so a failed read is narrowed before concluding that the
    /// address holds nothing. Without that, a string lying near the end of its region reads
    /// as empty.
    pub fn read_string(&self, address: i64) -> String {
        if address <= 0 {
            return String::new();
        }

        let mut address = address;
        let mut result = String::new();
        let mut buffer = [0_u8; 128];

        while result.len() < MAX_STRING_LENGTH {
            let mut read = self.try_read(address, &mut buffer);

            if read == 0 {
                read = self.try_read(address, &mut buffer[..16]);

                if read == 0 {
                    break;
                }
            }

            for &byte in &buffer[..read] {
                if byte == 0 {
                    return result;
                }

                result.push(byte as char);
            }

            address += read as i64;
        }

        result
    }
}

impl Drop for ProcessReader {
    fn drop(&mut self) {
        if !self.handle.is_invalid() {
            let _ = unsafe { CloseHandle(self.handle) };
        }
    }
}
