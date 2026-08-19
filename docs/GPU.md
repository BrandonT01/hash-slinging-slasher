# Would a GPU help?

Short answer: **not yet, and not for the reason people expect.** The recommendation at the bottom
is a specific experiment rather than "add CUDA", because the measurements below say the hashing is
not what this project is spending its time on.

Everything here is either a measurement taken on the machine named, or a statement about code with
the file and line to check it against. Where something is a hypothesis it says so.

---

## What we actually do per second

**Measured** on a Ryzen 7 7800X3D (8 cores, 16 threads), Cold War snapshot, 2026-08-19:

| workload | rate | what that rate counts |
|---|---|---|
| general search (`confirm_cw`, the `Meet` engine) | **3.94 × 10^10 equivalent candidates/s** | 41.72 T candidates in 1058 s |
| the same run, actual work done | **1.81 × 10^8 forward hashes/s** | 191.2 G forward hashes in 1058 s |
| `confirm_list` from a file | **6.43 × 10^7 candidates/s** | 39.49 M candidates in 1 s |
| `confirm_list` from a Python pipe | **7.7 × 10^5 candidates/s** | generator-bound, not hash-bound |

Reproduce the first two:

```
bin\windows\confirm_cw.exe > logs\general.log 2>&1
```

and read the `candidates:` line at the top and the `swept ... forward hashes in ...` line at the
bottom.

The gap between the first two rows is the whole architecture. The engine does not hash
`stems × beginnings × endings` candidates. Because FNV-1a is invertible, it **peels** each ending
off each wanted id once and looks the result up, so the ending list costs a sum rather than a
product. 41.7 trillion candidates get *asked about*; 191 billion hashes get *computed*. Removing
work beats doing work faster, and it already has, by a factor of 218.

---

## What the reference GPU tools do

### `acts hashbrutedictgpu` — OpenCL, so it already runs on AMD

`atian-cod-tools` uses **OpenCL**, not CUDA: the kernels are in `atian-cod-tools/config/data/opencl/` (
`hashbrutegpu.cl`, `hash_mini.cl`) and the host is `atian-cod-tools/src/core/acts/tools/hashes/hash_gpu.cpp`. So
the common assumption that it is NVIDIA-only is **wrong** — that matters here, because the
community splits roughly evenly between vendors and the machine these measurements come from has
a Radeon RX 7900 XT.

**The throughput limit is real and it is architectural, not a throttle.** From that host file:

```cpp
constexpr size_t hashesPerWork = 0x800000;                       // line 365 (0x1000000 at line 571)
CLMem gpuOutBufferA{ gpu.CreateBuffer(CL_MEM_WRITE_ONLY, hashesPerWork * sizeof(cl_ulong)) };
...
for (size_t i = 0; i < hashesPerWork; i++) { ... }               // line 468, host-side scan
```

Every candidate writes eight bytes into a 64 MiB (or 128 MiB) buffer, the buffer is copied back
over PCIe, and the host loops over **every** slot to find the hits. Three costs per candidate that
have nothing to do with hashing: a global store, a PCIe byte, and a host-side iteration. That caps
a run near 10^9 candidates/s no matter how cheap the arithmetic gets. Nobody chose that number;
it falls out of writing one result per candidate.

*(Verified by reading the code. Not benchmarked here — `acts` is not built on this machine.)*

### `codehash` — CUDA, so it does not run on AMD at all

`codehash.cu`, `mitm_frag.cu`, `t7sweep.cu`, built with `nvcc -arch=sm_86`. NVIDIA only, no
portable path. Its author's measurements on an RTX 3090:

| | rate |
|---|---|
| flat word search, depth 2 | 1.28 × 10^10 candidates/s |
| flat word search, tuned bitmap | 1.75 × 10^10 candidates/s |
| **prefix-table (backward) mode** | **1.11 × 10^6 stems/s** |

That last row is the one that matters to us, and it is four orders of magnitude below the first.
The reason is stated plainly in its README: the backward mode probes a ~100 MB table that no
longer fits in L2, and **that probe sets the pace**.

### The measurement that settles it

`codehash`'s author tested three dictionaries identical in every way but word length:

| mean word length | rate |
|---|---|
| 3.5 | 1.67 × 10^10/s |
| 7.5 | 1.64 × 10^10/s |
| 15.5 | 1.55 × 10^10/s |

4.4× the characters costs 7%. Solving for the two terms: **at a realistic word length the hashing
is about 5% of the GPU's runtime.** The other 95% is the dictionary load, the membership probe and
the loop around them.

---

## Why that applies to us, only more so

Our inner loop is `feed(opening, stem)` — one FNV fold over ~15 bytes — followed by
`Peeled::holds`, which is two bitmap probes and then a binary search into a sorted array of up to
60 million hashes.

Arithmetic on the measured rate: 1.81 × 10^8 forward hashes/s ÷ 16 threads at ~4.5 GHz is roughly
**400 cycles per candidate**. A 15-byte FNV fold is about 60 cycles of dependent multiply-xor. The
other ~340 cycles are the filter probe: `Filter::sized` for 60M entries builds two bitmaps of
64 MB each, so both probes are random accesses into 128 MB — past even this CPU's unusually large
96 MB L3.

**So we are memory-bound, by roughly the same ratio the GPU tools measured.** A GPU makes the 15%
cheaper and leaves the 85% where it is, and moves it onto a bus that is worse for random access
than a CPU's cache hierarchy. That is exactly the regime where `codehash`'s own backward mode
collapsed to 1.11 × 10^6/s.

> **Hypothesis, not measured:** a GPU port of the *forward* sweep could still win if the peeled set
> were made small enough to live in shared memory per block — the same trick `codehash` uses for
> the flat search. That means restructuring the peeling into many small batches, which costs
> re-sweeping the stems once per batch. Whether that trade pays is an open question and the
> experiment is described below.

---

## What to do instead, in order of expected value

1. **Fix the thing that was actually the bottleneck.** `confirm_list` originally read candidates
   with `BufRead::lines()`, allocating a `String` per candidate. That capped it at 5.2M/s.
   Reading raw bytes and hashing slices took it to **64.3M/s on identical input with identical
   results — a 12× speedup, on the CPU, for about forty lines.** There was more than an order of
   magnitude sitting in a convenience API. Look for the next one of those before buying a GPU.

2. **Make the generators faster.** A Python generator feeding `confirm_list` through a pipe runs
   at 7.7 × 10^5 candidates/s — the confirmer is idle 99% of the time. **For every script-driven
   method, candidate generation is the bottleneck by a factor of eighty**, and no GPU addresses
   that at all. Writing a hot generator in Rust would be worth more than any GPU work.

3. **Shrink the wanted set.** Cost is carried by how many ids are hunted. Dropping `xmodelmesh`
   already halves the coincidence rate; targeting five pools instead of two hundred is what makes
   a pass an hour instead of a day. A narrower search is a faster search and a more accurate one.

4. **Only then, the GPU experiment.**

## The experiment, if somebody wants to do it

Do not start by porting the search. Start by measuring whether the probe can be made to fit.

- **Backend: `wgpu` or OpenCL, never CUDA.** CUDA excludes half the community, including the
  machine these measurements were taken on. `acts` demonstrates OpenCL is sufficient for this
  problem on both vendors. Whatever is chosen must be **optional**, behind a Cargo feature, and
  the default build must stay dependency-free — that property is why anyone can clone this and
  compile it anywhere in a minute.
- **Measure first, in this order:** (a) how large a peeled batch fits in a workgroup's shared
  memory; (b) what re-sweeping the stems once per batch costs; (c) only then, the kernel.
- **Record, for any figure that gets quoted:** CPU model, GPU model, backend, candidate count,
  runtime, candidates/s, batch size, result count. A rate without its batch size is not
  reproducible.
- **Verify every name the GPU proposes on the CPU.** `codehash`'s README records a real instance
  of this: a slot index overflowed eight bits into a prefix index and 355 of 8,125 reported names
  came back as the wrong string. They still matched a target, so only recomputing the hash could
  have caught it.

---

## What is worth taking from those repositories regardless

Neither tool's code is needed here — the hashing is already correct and matches cod-name-db, which
is the ground truth. Their **measurements** are worth a great deal, and two ideas have already
been adopted:

- **Per-prefix continuations beat a global word list.** Offering `i_c_t8_mp_spe_` the words that
  have actually followed `spe` beats offering it the 256 commonest words in the game — measured at
  2.4× the names for less than half the search. This is now `scripts/continuations.py`, and its
  first run here reached **496 names in 51 seconds** that the general search's committed lists did
  not — though only 5 of those were new to the community; see METHODS.md for why that
  distinction matters.
- **Names are long, so word composition cannot work.** Measured on 22,481 recovered Black Ops 4
  names, the median has nine words and only 4.4% have three or fewer. Measured on this project's
  own confirmed names, the median has seven or eight underscore-separated segments. Past four
  words the hash is a checksum, not a filter: there are more word sequences than there are hashes.
  Fragment recombination is the only shape that works, which is what everything here already does.

---

*Measurements on this project: Ryzen 7 7800X3D, 32 GB, Radeon RX 7900 XT, Windows 11, 2026-08-19.
Figures for `acts` are from reading its source; figures for `codehash` are its author's, on an
RTX 3090, and are quoted rather than reproduced.*
