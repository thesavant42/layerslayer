# BUG - Layer Peeking is catastrophically broken

"Layer Peeking" - verb; to infer the filesystem of an SOCI container image by scanning only the targz headers, not decompressing the entire image (only enough to get the peek) and then severing the connection immediately.

- Why? - By learning the file contents before hand it is easier to predict whether the container is even worth the time/space/effort to download.

---

## Problem Statement

- A programming agent with some bad assumptions broke layerpeek streaming; 
- The logic is corrupted and now the fies take a long time to download
    -  because the buffer is the wrong size, they fully decompress,
-  In short; they do NONE of the clever time saving hacks that this repository was designed to do.



- The first commit to sucessfully introduce layer peeking via file STREAMING is at this commit: [GitHub link to commit:](https://github.com/thesavant42/layerslayer/commit/9098b5be09e1215ff4deb107ace89205bbb90fb6)
    - Here is a diff link for you if that's easier. [diff](https://github.com/thesavant42/layerslayer/commit/9098b5be09e1215ff4deb107ace89205bbb90fb6.diff)

This is the commit that made things work.  **This commit modified `fetcher.py` and `layerslayer.py` for file stream "peeking".**


The architecture has shifted quite a bit, but the core technique of stream-peeking is still valid. Below is the formal documentation for the code *AT THIS STAGE*

## Constraints

There have been *MANY* code changes since then, I **cannot** simply revert to this state in Git time and start over.
- This information should be used for comparison to a "known good", and to repair the current code base.

## Diagrams & Docs

[Links to Mermaid Charts in the repository /doc](plans\layerslayerbug\legacy-docs) folder at the date and time of the previous git commit

## Open Questions:

Q: What are the substantial differences between the current code base's core modules and the "working" copy from the commit that made things work?
A:


Q: At what point did the current code base stop working? I first noticed on 01/19/2026
A:


Q: 
A:

## Goals:

1. Fix the bugs in file streaming peeking
2. Create unit tests for CI/CD
    1. Establish a base line of known-good and known-bad
    1. Create pipeline for Jenkins to run unit tests
        1. pull the git code
        1. run unit tests in a container w/ reports
        1. aggregate results and notify
        1. Build in safety valves so we dont bake in bad bugs.

## CI/CD TBD
- Tracked in the Wiki [here.](https://github.com/thesavant42/layerslayer/wiki/CI-CD-Requirements)

---

## Core Differences in Tar Parsing Techniques: Legacy vs Current

### The Critical Difference

Both approaches use the same tar header parsing logic ([`parse_tar_header()`](app/modules/finders/tar_parser.py:108)), which calculates `next_offset` by **skipping over file content**:

```python
content_blocks = (size + 511) // 512
next_offset = offset + 512 + (content_blocks * 512)
```

The difference is in **when they stop fetching data**.

---

### Legacy "Tar.gz Hack" (`peek_layer_blob_partial`)

From legacy docs ([`fetcher-py.md`](plans/layerslayerbug/legacy-docs/fetcher-py.md:181)):

1. **Single HTTP Range Request**: `Range: bytes=0-262143` (256KB limit)
2. **Fixed byte budget**: Downloads exactly `initial_bytes`, then stops
3. **Immediate connection close**: `resp.close()` after reading
4. **Partial parsing**: Parses headers until `next_offset > buffer_size`, then returns
5. **Returns `partial=True`**: Indicates incomplete enumeration

**Result**: Downloads 256KB, enumerates maybe 1-50 files depending on their sizes, done.

---

### Current Implementation (`peek_layer_streaming`)

From [`peekers.py:146-238`](app/modules/finders/peekers.py:146):

```python
while not reader.exhausted and not archive_complete:
    compressed = reader.fetch_chunk()
    # ... decompresses, parses headers ...
    
    while parse_offset + 512 <= len(buffer):
        if buffer[parse_offset:parse_offset + 512] == b'\x00' * 512:
            archive_complete = True  # Only exits on null block
            break
        entry, next_offset = parse_tar_header(buffer, parse_offset)
        # ...
        parse_offset = next_offset
```

1. **Multiple HTTP Range Requests**: Keeps calling `fetch_chunk()` in a loop
2. **No byte budget**: Loop continues until `archive_complete` or `reader.exhausted`
3. **Connection stays open**: Keeps fetching chunks
4. **Full parsing attempted**: Downloads enough data to skip over ALL file content
5. **Returns `partial=False`**: Claims complete enumeration

**Result**: To parse header #2 after a 5MB file, must download 5MB+ of decompressed data. For a layer with large files, downloads the entire layer.

---

### Concrete Example

Layer: 50MB compressed, contains `/bin/bash` (2MB) followed by `/etc/passwd` (2KB)

| Step | Legacy (256KB budget) | Current (no budget) |
|------|----------------------|---------------------|
| 1 | Fetch 256KB, decompress to ~800KB | Fetch 64KB chunk |
| 2 | Parse `/bin/bash` header, next_offset=2.1MB | Parse `/bin/bash` header, next_offset=2.1MB |
| 3 | 2.1MB > 800KB, **stop** | 2.1MB > buffer, need more data |
| 4 | Return 1 entry, partial=True | Fetch another chunk... |
| 5 | **Done: 256KB downloaded** | ...keep fetching until buffer >= 2.1MB |
| 6 | - | Parse `/etc/passwd`, continue to end |
| 7 | - | **Done: ~50MB downloaded** |

---

### Root Cause

The current [`peek_layer_streaming()`](app/modules/finders/peekers.py:181) outer loop lacks early termination:

```python
while not reader.exhausted and not archive_complete:  # <-- No byte limit!
```

It should have a condition like:
```python
while not reader.exhausted and not archive_complete and reader.bytes_downloaded < max_bytes:
```

This would restore the "peek" behavior: enumerate as many headers as possible within a byte budget, then return partial results.