# DeepWiki Q&A with Code Context for Repository: thesavant42/layerslayer
## Q1
How does parser work?
### Answer
The parser module in `parser.py` handles Docker manifest parsing with two main functions for different manifest types layerslayer:1-34 .

## Core Functions

### `parse_index()`
Handles OCI image indexes containing multiple architectures by:
1. Extracting platform manifests from the index JSON layerslayer:6-12 
2. Displaying available OS/architecture combinations to the user
3. Prompting for platform selection and fetching the specific manifest digest layerslayer:14-17 

### `parse_manifest()`
Parses single-architecture manifests to extract layer information by:
1. Retrieving the layers array from the manifest JSON layerslayer:19-21 
2. Iterating through layers to display digest and size information layerslayer:23-27 
3. Returning structured layer data with digest and size fields layerslayer:28-31 

## System Integration

The parser works as part of the Business Logic Layer, collaborating with the fetcher module which handles HTTP requests to the Docker Registry API layerslayer:4-4 . When `parse_index()` needs a specific platform's manifest, it calls `get_manifest_by_digest()` from the fetcher.

## Notes
The parser module is specifically designed for Docker Registry API v2 manifest structures and assumes standard OCI image index/manifest formats. It doesn't handle validation or error cases - those are managed by the calling code in the main application flow.

Wiki pages you might want to explore:
- [System Design Overview (thesavant42/layerslayer)](/wiki/thesavant42/layerslayer#4.1)
### Citations
**File:** parser.py (L1-34)
```python
# parser.py
# Parses manifest and config data

from fetcher import get_manifest_by_digest

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
how does parser work?
## Parser Module Flow
The parser module handles Docker/OCI manifest parsing with two main flows: multi-architecture index parsing via [1a] and single-architecture manifest parsing via [2a]. The parser integrates with the main application flow at [3a] and depends on the fetcher module at [4a] for registry communication.
### 1. Multi-architecture Index Parsing
Handling OCI image indexes with platform selection
### 1a. Index parser entry point (`parser.py:6`)
Function that processes multi-architecture image indexes
```text
def parse_index(index_json, image_ref, token=None):
```
### 1b. Extract platform manifests (`parser.py:9`)
Gets the manifests array containing platform information
```text
platforms = index_json.get('manifests', [])
```
### 1c. User platform selection (`parser.py:14`)
Interactive prompt for user to choose architecture
```text
choice = int(input("\nSelect platform index: "))
```
### 1d. Fetch specific manifest (`parser.py:17`)
Calls fetcher to get the chosen platform's manifest
```text
return get_manifest_by_digest(image_ref, digest, token=token)
```
### 2. Single-architecture Manifest Parsing
Extracting layer information from Docker manifests
### 2a. Manifest parser entry point (`parser.py:19`)
Function that processes single-architecture manifests
```text
def parse_manifest(manifest_json):
```
### 2b. Extract layer array (`parser.py:21`)
Gets the layers array from the manifest
```text
layers = manifest_json.get('layers', [])
```
### 2c. Extract layer size (`parser.py:25`)
Gets the size information for each layer
```text
size = layer.get('size', 0)
```
### 2d. Build layer info structure (`parser.py:28`)
Creates structured data for each layer
```text
layer_info.append({'digest': digest, 'size': size})
```
### 2e. Return layer data (`parser.py:32`)
Returns structured layer information to caller
```text
return layer_info
```
### 3. Parser Integration in Main Flow
How parser functions are used in the main application
### 3a. Detect multi-arch manifest (`layerslayer.py:93`)
Main app checks if this is a multi-architecture index
```text
if manifest_index.get("manifests"):
```
### 3b. Platform selection in main (`layerslayer.py:99`)
Main app replicates platform selection logic
```text
choice = int(input("Select a platform [0]: ") or 0)
```
### 3c. Fetch specific platform manifest (`layerslayer.py:102`)
Main app directly calls fetcher instead of parser
```text
result = get_manifest(image_ref, token, specific_digest=digest)
```
### 3d. Extract layers in main (`layerslayer.py:117`)
Main app directly extracts layers without calling parser
```text
layers = full_manifest["layers"]
```
### 4. Fetcher Dependency
Parser's dependency on the fetcher module
### 4a. Import fetcher function (`parser.py:4`)
Parser imports the digest-based manifest fetcher
```text
from fetcher import get_manifest_by_digest
```
### 4b. Fetcher function signature (`fetcher.py:49`)
The function that parser calls to fetch manifests
```text
def get_manifest(image_ref, token=None, specific_digest=None):
```
### 4c. Build registry URL (`fetcher.py:56`)
Constructs the Docker registry API endpoint
```text
url = f"{registry_base_url(user, repo)}/manifests/{ref}"
```
### 4d. HTTP request to registry (`fetcher.py:62`)
Makes the actual HTTP request to Docker registry
```text
resp = session.get(url)
```