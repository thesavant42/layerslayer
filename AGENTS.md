# Agents

A high-level overview of the modular components ("agents") in this codebase, each responsible for a distinct aspect of Docker layer inspection.

## Agent Components

| Agent Name         | Module          | Responsibility                                                    |
| ------------------- | --------------- | ----------------------------------------------------------------- |
| **CLI Agent**       | layerslayer.py  | Parses CLI arguments, handles interactive and batch modes, and orchestrates overall flow. |
| **Fetcher Agent**   | fetcher.py      | Manages HTTP interactions with the Docker Registry API, token handling, and blob retrieval. |
| **Parser Agent**    | parser.py       | Parses multi-arch and single-arch manifests to present platforms and layer digests.       |
| **Build-Step Agent**| fetcher.py      | Extracts build steps (Dockerfile history) from the image config blob.                   |
| **Peek Agent**      | fetcher.py      | Streams layer blobs into memory and lists contents of compressed tar archives.           |
| **Download Agent**  | fetcher.py      | Streams and saves layer blobs (.tar.gz) to the `downloads/` directory for offline use.    |
| **Utility Agent**   | utils.py        | Provides helper functions (image reference parsing, headers, size formatting, etc.).     |

## Architecture Design: Tar.gz Hack for Directory Indexing

> **Goal:** Efficiently list the contents of a Docker layer without downloading the full data blob.

Most Docker layers are compressed tar archives (`.tar.gz`). A naive "peek" downloads the entire blob before listing contents. By leveraging HTTP range requests and the gzip format's block-based structure, it's possible to fetch only the minimal bytes needed to reconstruct the tar-header index:

1. **Gzip Block Structure:**
   Gzip archives consist of concatenated compressed blocks. Tar header records (file metadata) reside within these blocks at the beginning of the archive.

2. **HTTP Range Requests:**
   Issue a `Range` request to download just the first segment (e.g. the first few megabytes) of the compressed blob. This typically contains enough compressed data to decode all tar headers (directory and file metadata) without fetching file contents.

3. **In-Memory Indexing:**
   Feed the partial gzip stream into an in-memory buffer (`io.BytesIO`) and open it with `tarfile.open(..., mode="r:gz")`. In "list" mode, the tarfile module reads only header blocks and stops before extracting large file data.

4. **Progressive Fetch (Optional):**
   If the initial range does not contain all header records, issue additional range requests for subsequent byte ranges until the full header index is retrieved.

This hack dramatically reduces network bandwidth and latency when peeking at large layers, while preserving the ease of using Python's native tarfile APIs.

> *Tip:* Wrap this logic in a resilient "Peek Agent" to handle partial reads, retries, and in-memory caching of intermediate compressed data.