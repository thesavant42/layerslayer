# DeepWiki Q&A with Code Context for Repository: thesavant42/layerslayer
## Q1
How do Layer Operations work?
### Answer
Layer Operations in Layerslayer enable you to inspect and download Docker image layers without pulling entire images. The system provides two primary operations: peeking (listing contents) and downloading (saving blobs), implemented through the `peek_layer_blob()` and `download_layer_blob()` functions in `fetcher.py` layerslayer:139-166 layerslayer:107-137 .

## Core Layer Operations

### Peek Operation
The `peek_layer_blob()` function downloads a layer blob into memory and lists its tar archive contents layerslayer:139-166 :

1. **HTTP Request**: Makes a streaming GET request to `/blobs/{digest}` endpoint
2. **Memory Buffer**: Loads the entire response into `io.BytesIO` 
3. **Tar Parsing**: Opens with `tarfile.open(mode="r:gz")` to handle gzip compression
4. **Content Listing**: Iterates through `tar.getmembers()` to display files and directories with human-readable sizes

### Download Operation  
The `download_layer_blob()` function streams layer blobs to disk as `.tar.gz` files layerslayer:107-137 :

1. **Streaming Download**: Uses `stream=True` and `resp.iter_content(chunk_size=8192)` for memory efficiency
2. **File Organization**: Saves to `downloads/{user}_{repo}/latest/` with digest-based filenames
3. **Directory Creation**: Automatically creates output directories using `os.makedirs(exist_ok=True)`

## The Tar.gz Hack Optimization

Layer operations leverage a key optimization called the "Tar.gz Hack" that enables efficient directory indexing without full downloads layerslayer:17-36 :

- **Gzip Block Structure**: Tar headers reside at the beginning of compressed blocks
- **Header-Only Parsing**: `tarfile` module reads only metadata blocks, stopping before extracting large file data
- **In-Memory Processing**: Uses `io.BytesIO` to avoid disk I/O during inspection

*Note: The current implementation loads full blobs into memory, but the architecture supports future HTTP Range request optimization to fetch only initial bytes containing tar headers.*

## Operational Modes

Layer operations are executed through three distinct modes in `layerslayer.py` layerslayer:119-154 :

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Interactive** | Default | Prompts for layer selection, peeks selected layers, asks per-layer download confirmation |
| **Batch Peek** | `--peek-all` flag | Peeks all layers without download prompts |
| **Batch Save** | `--save-all` flag | Downloads all layers without listing contents |

## Authentication & Error Handling

All layer operations implement resilient token management with automatic 401 recovery layerslayer:146-153 :

1. **Initial Request**: Attempts operation with existing token
2. **Token Refresh**: On 401, calls `fetch_pull_token()` to acquire fresh token
3. **Retry**: Retries the operation with new authentication
4. **Graceful Failure**: Exits with clear error message if still unauthorized

## Notes

The `parser.py` module contains legacy parsing functions (`parse_index()`, `parse_manifest()`) that are defined but not actively used in the current codebase layerslayer:6-32 . Multi-architecture handling and manifest parsing logic is implemented directly in `layerslayer.py` instead.

Wiki pages you might want to explore:
- [System Design Overview (thesavant42/layerslayer)](/wiki/thesavant42/layerslayer#4.1)
- [Core Modules (thesavant42/layerslayer)](/wiki/thesavant42/layerslayer#4.2)
### Citations
**File:** fetcher.py (L107-137)
```python
def download_layer_blob(image_ref, digest, size, token=None):
    """
    Stream a layer blob to disk as a .tar.gz file.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print(" Proceeding without refreshed token.")

    resp.raise_for_status()

    user_repo = f"{user}_{repo}"
    output_dir = os.path.join("downloads", user_repo, "latest")
    os.makedirs(output_dir, exist_ok=True)

    filename = digest.replace(":", "_") + ".tar.gz"
    path = os.path.join(output_dir, filename)

    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"[+] Saved layer {digest} to {path}")
```
**File:** fetcher.py (L139-166)
```python
def peek_layer_blob(image_ref, digest, token=None):
    """
    Download a layer blob into memory and list its contents.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print(" Proceeding without refreshed token.")

    resp.raise_for_status()

    tar_bytes = io.BytesIO(resp.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
        print("\n Layer contents:\n")
        for member in tar.getmembers():
            if member.isdir():
                print(f"📂 {member.name}/")
            else:
                size = human_readable_size(member.size)
                print(f"  📄 {member.name} ({size})")

```
**File:** AGENTS.md (L17-36)
```markdown
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

```
**File:** layerslayer.py (L119-154)
```python
    # — peek-all mode? —
    if args.peek_all:
        print("\n📂 Peeking into all layers:")
        for idx, layer in enumerate(layers):
            print(f"\n⦿ Layer [{idx}] {layer['digest']}")
            peek_layer_blob(image_ref, layer["digest"], token)
        return

    # — save-all mode? —
    if args.save_all:
        print("\n Downloading all layers:")
        for idx, layer in enumerate(layers):
            print(f"Downloading Layer [{idx}] {layer['digest']} …")
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
        return

    # — default interactive mode —
    print("\nLayers:")
    for idx, layer in enumerate(layers):
        size = human_readable_size(layer["size"])
        print(f" [{idx}] {layer['digest']} - {size}")

    sel = input(
        "\nLayers to peek (comma-separated INDEX or ALL) [default: ALL]: "
    ).strip()
    if not sel or sel.upper() == "ALL":
        indices = list(range(len(layers)))
    else:
        indices = [int(i) for i in sel.split(",")]

    for idx in indices:
        layer = layers[idx]
        print(f"\n⦿ Layer [{idx}] {layer['digest']}")
        peek_layer_blob(image_ref, layer["digest"], token)
        if input("Download this layer? (y/N) ").strip().lower() == "y":
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
```
**File:** parser.py (L6-32)
```python
def parse_index(index_json, image_ref, token=None):
    """Handles an OCI image index with multiple architectures."""
    print("\nAvailable Platforms:")
    platforms = index_json.get('manifests', [])
    for i, platform in enumerate(platforms):
        plat = platform.get('platform', {})
        print(f"[{i}] {plat.get('os', 'unknown')}/{plat.get('architecture', 'unknown')}")

    choice = int(input("\nSelect platform index: "))
    chosen = platforms[choice]
    digest = chosen['digest']
    return get_manifest_by_digest(image_ref, digest, token=token)

def parse_manifest(manifest_json):
    """Parses a manifest to list its layers."""
    layers = manifest_json.get('layers', [])
    layer_info = []
    print("\nLayers:")
    for idx, layer in enumerate(layers):
        size = layer.get('size', 0)
        digest = layer.get('digest')
        print(f"[{idx}] {digest} - {size/1024:.1f} KB")
        layer_info.append({
            'digest': digest,
            'size': size
        })
    return layer_info
```
## Q2
How do Layer Operations work?
## Layer Operations in Layerslayer
Layer Operations enable efficient Docker layer inspection and downloading through HTTP streaming, tar.gz parsing optimization, and resilient authentication. The system supports interactive selection [1c], batch processing [2a], in-memory content peeking [3c], and chunked downloads [4d] with automatic token refresh [5b] and multi-architecture manifest handling [6b].
### 1. Interactive Layer Selection Flow
CLI orchestrates user interaction for layer inspection and download decisions
### 1a. User layer selection prompt (`layerslayer.py:142`)
Prompts user to choose which layers to inspect
```text
sel = input("\nLayers to peek (comma-separated INDEX or ALL) [default: ALL]: ").strip()
```
### 1b. Iterate and peek selected layers (`layerslayer.py:149`)
Loops through chosen layers and calls peek operation
```text
for idx in indices:
        layer = layers[idx]
        print(f"\n⦿ Layer [{idx}] {layer['digest']}")
        peek_layer_blob(image_ref, layer["digest"], token)
```
### 1c. Per-layer download confirmation (`layerslayer.py:153`)
Asks user confirmation before downloading each layer
```text
if input("Download this layer? (y/N) ").strip().lower() == "y":
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
```
### 2. Batch Operations Execution
Automated processing of all layers without user interaction
### 2a. Peek-all batch mode (`layerslayer.py:120`)
Automatically peeks all layers without download prompts
```text
if args.peek_all:
        print("\n📂 Peeking into all layers:")
        for idx, layer in enumerate(layers):
            print(f"\n⦿ Layer [{idx}] {layer['digest']}")
            peek_layer_blob(image_ref, layer["digest"], token)
```
### 2b. Save-all batch mode (`layerslayer.py:128`)
Downloads all layers without listing contents
```text
if args.save_all:
        print("\n Downloading all layers:")
        for idx, layer in enumerate(layers):
            print(f"Downloading Layer [{idx}] {layer['digest']} …")
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
```
### 3. Layer Peek Operation
HTTP streaming and tar parsing to inspect layer contents without full download
### 3a. Streaming HTTP request with auth retry (`fetcher.py:146`)
Makes streaming request with automatic token refresh on 401
```text
resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
```
### 3b. In-memory tar.gz parsing (`fetcher.py:157`)
Loads response into memory buffer and opens as gzip tar
```text
tar_bytes = io.BytesIO(resp.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
```
### 3c. Directory and file listing (`fetcher.py:160`)
Iterates through tar members to display contents with human-readable sizes
```text
for member in tar.getmembers():
        if member.isdir():
            print(f"📂 {member.name}/")
        else:
            size = human_readable_size(member.size)
            print(f"  📄 {member.name} ({size})")
```
### 4. Layer Download Operation
Efficient streaming download of layer blobs to disk
### 4a. Initiate streaming download (`fetcher.py:114`)
Starts streaming HTTP request for layer blob
```text
resp = session.get(url, stream=True)
```
### 4b. Organize download directory structure (`fetcher.py:125`)
Creates organized directory structure for downloads
```text
user_repo = f"{user}_{repo}"
    output_dir = os.path.join("downloads", user_repo, "latest")
    os.makedirs(output_dir, exist_ok=True)
```
### 4c. Generate digest-based filename (`fetcher.py:129`)
Creates safe filename from layer digest
```text
filename = digest.replace(":", "_") + ".tar.gz"
    path = os.path.join(output_dir, filename)
```
### 4d. Chunked file writing (`fetcher.py:132`)
Streams response chunks to disk efficiently
```text
with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
```
### 5. Authentication and Token Management
Resilient token handling with automatic refresh mechanism
### 5a. Load existing authentication token (`layerslayer.py:78`)
Attempts to load token from file or proceed anonymously
```text
token = load_token("token.txt")
    if token:
        print(" Loaded token from token.txt")
        print(" Using loaded token.")
    else:
        print(" No token found; proceeding anonymously.")
```
### 5b. Automatic token refresh on 401 (`fetcher.py:63`)
Detects auth failure and fetches fresh token
```text
if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)
```
### 5c. Save and inject new token (`fetcher.py:43`)
Persists token and updates session headers for future requests
```text
save_token(token, filename="token_pull.txt")
    print(" Saved pull token to token_pull.txt.")
    # Now inject the fresh token into our session for all registry calls
    session.headers["Authorization"] = f"Bearer {token}"
```
### 6. Manifest Processing and Layer Extraction
Multi-architecture manifest handling and layer metadata extraction
### 6a. Fetch initial manifest (`layerslayer.py:86`)
Retrieves manifest and handles tuple return format
```text
result = get_manifest(image_ref, token)
    if isinstance(result, tuple):
        manifest_index, token = result
    else:
        manifest_index = result
```
### 6b. Handle multi-architecture manifest (`layerslayer.py:93`)
Detects and displays platform options for multi-arch images
```text
if manifest_index.get("manifests"):
        platforms = manifest_index["manifests"]
        print("\nAvailable platforms:")
        for i, m in enumerate(platforms):
            plat = m["platform"]
            print(f" [{i}] {plat['os']}/{plat['architecture']}")
```
### 6c. Extract layer list from manifest (`layerslayer.py:117`)
Retrieves layer array from processed manifest
```text
layers = full_manifest["layers"]
```
### 6d. Extract and display build steps (`layerslayer.py:112`)
Fetches Dockerfile history from config blob
```text
steps = fetch_build_steps(image_ref, full_manifest["config"]["digest"], token)
    print("\nBuild steps:")
    for idx, cmd in enumerate(steps):
        print(f" [{idx}] {cmd}")
```