## Q2
how does this work?
## The Tar.gz Hack Optimization - Docker Layer Inspection Flow
This codemap traces the complete flow of the Tar.gz Hack optimization, from CLI invocation through HTTP layer retrieval to header-only tar parsing. Key locations include the peek-all flag activation [1a], the core peek_layer_blob function [2a], and the critical tarfile header parsing [3b] that enables reading metadata without extracting file contents.
### 1. CLI Entry Point and Layer Selection
How the --peek-all flag triggers layer inspection across all Docker layers
### 1a. Peek-all mode activation (`layerslayer.py:120`)
CLI argument check that triggers batch layer inspection
```text
if args.peek_all:
```
### 1b. Layer iteration loop (`layerslayer.py:122`)
Iterates through all available layers in the Docker image
```text
for idx, layer in enumerate(layers):
```
### 1c. Core peek function call (`layerslayer.py:124`)
Invokes the tar.gz hack implementation for each layer
```text
peek_layer_blob(image_ref, layer["digest"], token)
```
### 2. HTTP Layer Blob Retrieval
How the fetcher agent downloads layer data from Docker registry with authentication
### 2a. Peek function definition (`fetcher.py:139`)
Entry point for the tar.gz hack optimization
```text
def peek_layer_blob(image_ref, digest, token=None):
```
### 2b. Registry URL construction (`fetcher.py:144`)
Builds the Docker registry blob URL for the specific layer
```text
url = f"{registry_base_url(user, repo)}/blobs/{digest}"
```
### 2c. HTTP streaming request (`fetcher.py:146`)
Downloads the layer blob using streaming to handle large files
```text
resp = session.get(url, stream=True)
```
### 2d. Authentication handling (`fetcher.py:147`)
Automatic token refresh on unauthorized responses
```text
if resp.status_code == 401:
```
### 3. Tar.gz Header Parsing Implementation
How the optimization extracts file metadata without downloading full contents
### 3a. In-memory buffer creation (`fetcher.py:157`)
Loads the entire blob into memory for tarfile processing
```text
tar_bytes = io.BytesIO(resp.content)
```
### 3b. Gzip-tar extraction (`fetcher.py:158`)
Opens the compressed tar using Python's native tarfile module
```text
with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
```
### 3c. Header-only iteration (`fetcher.py:160`)
Iterates through tar members reading only metadata headers
```text
for member in tar.getmembers():
```
### 3d. Directory detection (`fetcher.py:161`)
Distinguishes between directories and files in the layer
```text
if member.isdir():
```
### 3e. Size formatting (`fetcher.py:164`)
Formats file sizes for human-readable output
```text
size = human_readable_size(member.size)
```
### 4. Interactive Mode Layer Selection
How users can selectively peek at specific layers in interactive mode
### 4a. User prompt for selection (`layerslayer.py:141`)
Prompts user to choose which layers to inspect
```text
sel = input("\nLayers to peek (comma-separated INDEX or ALL) [default: ALL]: ").strip()
```
### 4b. Default all layers selection (`layerslayer.py:144`)
Handles default case of inspecting all layers
```text
if not sel or sel.upper() == "ALL":
```
### 4c. Index parsing (`layerslayer.py:147`)
Parses comma-separated layer indices from user input
```text
indices = [int(i) for i in sel.split(",")]
```
### 4d. Selective peek execution (`layerslayer.py:152`)
Executes peek only on user-selected layers
```text
peek_layer_blob(image_ref, layer["digest"], token)
```